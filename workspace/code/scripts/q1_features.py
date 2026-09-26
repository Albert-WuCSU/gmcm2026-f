"""Q1 共享特征层：22 指标标量化、方向表、三种归一化口径。

被 probe_q1_quality.py 与后续建模复用。本模块只做 GC2/GC3 要求的"必要预处理"，
不含任何评价模型或权重。

方向表分三层可信度（tier）：
  A = 有直接证据或题目明示，机械可定
  B = 由 RedPajama-v2 / Gopher / C4 过滤器的公开语义推得，本队已在数据上核对不矛盾
  C = 语义方向本身是建模判断，或指标对质量非单调 —— 须由使用者裁定，探针须报敏感性

规格状态：本模块已按 G2.5 人工决策 q1_tierC_direction = D 更新为 CANONICAL 规格，
即 dsir 逐 token 归一化 + 三合一 + 长度类非单调。使用 build_canonical() 取决策后的矩阵。

注意：workspace/data/ 下 q1_probe_quality*.json / q1_probe_corr.json /
q1_probe_configs.json 是决策前规格的历史证据，不随本次更新重跑；
若需复现决策前的数值，用 PRE_DECISION_OVERRIDE 作 tier_c_override。

种子：20260924
"""
from __future__ import annotations

import json
import lzma
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "workspace/data_raw/real_attachments/A_data_value"
A1_PATH = RAW / "slimpajama_quality_signal_sample.jsonl.xz"
A2_PATH = RAW / "slimpajama_quality_extended/arxiv_part-6777d8857c6e-000486.jsonl.xz"
A3_PATH = RAW / "slimpajama_quality_extended/github_part-6777d8857c6e-000275.jsonl.xz"

SEED = 20260924

# ---------------------------------------------------------------- 方向表
# (sign, tier, basis)  sign=+1 表示标量化后已是"越高越好"；-1 表示须补转换
DIRECTION: dict[str, tuple[int, str, str]] = {
    "fineweb_edu": (+1, "A", "赛题正文明示：教育价值越高越好"),
    "ad_en_margin": (+1, "A", "原文核验：margin 最低 6/6 条为广告文案，最高端为论坛/新闻 → margin 度量非广告性"),
    "fluency_en_margin": (+1, "A", "原文核验：margin 最低端为 SEO 垃圾/机翻乱码，最高端为通顺散文 → margin 度量流畅度"),
    "modernbert_cleanliness": (+1, "A", "6 类有序 logits 的 softmax 期望类别，与 fineweb_edu pearson +0.302"),
    "modernbert_readability": (+1, "A", "期望类别与 fineweb_edu pearson +0.331"),
    "modernbert_reasoning": (+1, "A", "期望类别与 fineweb_edu spearman +0.485"),
    "modernbert_professionalism": (+1, "A", "期望类别与 fineweb_edu spearman +0.368"),
    "qurater": (+1, "A", "4 个准则与 fineweb_edu 全为正相关 +0.24~+0.61"),
    # dsir：G2 补充探针证实原始字段为"按 token 求和"的对数似然比，被长度主导
    # （log(-dsir) ~ log(word_count) 的 Pearson = 0.937~0.939）。逐 token 归一化后
    # 与 fineweb_edu 的 Spearman 由 -0.499 转为 +0.374，dsir_books 上 book 域由第 7 升至第 1。
    # 故方向依据由"建模判断"升级为"数据可证"，tier C -> B。逐 token 化是使用该字段的前置条件。
    "dsir_books": (+1, "B", "逐 token 归一化后的 DSIR 对数似然比；归一化后与 fineweb_edu Spearman +0.374，book 域在 book 相似度上升至第 1（原始字段下为第 7）"),
    "dsir_wiki": (+1, "B", "同上；与 dsir_books 逐 token 后互相关 0.99966，canonical 规格下合并"),
    "dsir_math": (+1, "B", "同上；与 dsir_books 逐 token 后互相关 0.99623，canonical 规格下合并"),
    # 长度类：非单调。Gopher / RedPajama-v2 过滤器以区间方式使用长度，两端皆劣。
    "rps_doc_word_count": (0, "C", "文档长度对质量非单调（Gopher/RPv2 按区间过滤）；AUC=0.987 近乎纯域标签。按到域内中位数距离处理"),
    "rps_doc_num_sentences": (0, "C", "句数对质量非单调；AUC=0.947。按到域内中位数距离处理"),
    "rps_doc_unigram_entropy": (+1, "B", "一元词熵 = 词汇多样性，低熵对应重复/模板文本"),
    "rps_doc_frac_unique_words": (+1, "B", "唯一词占比高 = 重复度低"),
    "rps_doc_frac_no_alph_words": (-1, "B", "非字母词占比高 = 符号/数字噪声，Gopher 过滤视为劣质"),
    "rps_doc_frac_chars_top_2gram": (-1, "B", "最高频 2-gram 字符占比高 = 模板化重复"),
    "rps_doc_frac_chars_top_3gram": (-1, "B", "最高频 3-gram 字符占比高 = 模板化重复"),
    "rps_lines_uppercase_letter_fraction": (-1, "B", "大写字母占比高 = 标题堆砌/全大写喊话"),
    "rps_lines_ending_with_terminal_punctution_mark": (+1, "B", "C4 规则保留以终止标点结尾的行，句子完整性"),
    "rps_lines_numerical_chars_fraction": (-1, "B", "数字字符占比高 = 表格/清单残渣"),
    "rps_doc_mean_word_length": (0, "C", "非单调：Gopher 过滤保留区间约 [3,10]，过短为乱码、过长为连写/编码残渣（本库 max=83）"),
}

# 语义分组：P = 污染组（原始方向为负者 + 广告性），V = 价值组
POLLUTION_COLS = [
    "rps_doc_frac_no_alph_words",
    "rps_doc_frac_chars_top_2gram",
    "rps_doc_frac_chars_top_3gram",
    "rps_lines_uppercase_letter_fraction",
    "rps_lines_numerical_chars_fraction",
    "ad_en_margin",          # 取负后为广告性
]

# 决策前规格（历史复现用）：dsir 用原始值、word_count 与 num_sentences 取正。
# 注意 mean_word_length 在决策前就已是非单调（sign=0），故不在此表内；
# 决策 D 只把 word_count 与 num_sentences 由 +1 改为 0。
PRE_DECISION_OVERRIDE = {
    "rps_doc_word_count": +1,
    "rps_doc_num_sentences": +1,
}

DSIR_COLS = ["dsir_books", "dsir_wiki", "dsir_math"]
DSIR_REP = "dsir_prose_likeness"
TIER_C_COLS = [c for c, (_, t, _) in DIRECTION.items() if t == "C"]
ALL_COLS = list(DIRECTION.keys())
assert len(ALL_COLS) == 22, len(ALL_COLS)

LIST_FIELDS = ["fineweb_edu", "ad_en", "fluency_en", "modernbert_cleanliness",
               "modernbert_readability", "modernbert_reasoning",
               "modernbert_professionalism", "qurater"]


def _softmax_expected_class(v: list[float]) -> float:
    m = max(v)
    e = [math.exp(x - m) for x in v]
    s = sum(e)
    return sum(i * ei for i, ei in enumerate(e)) / s


def scalarize(rec: dict) -> dict[str, float] | None:
    """按 F1 已定案的规则把 8 个列表型字段压为标量，返回 22 列。

    None 表示该行含 NaN 向量（A1 18 条 / A3 1 条），由调用方计入缺失。
    """
    out: dict[str, float] = {}
    for f in LIST_FIELDS:
        v = rec.get(f)
        # 注意：A1/A3 的缺失在 JSON 中是 NaN 字面量而非 null，
        # 故须同时判 None 与 x != x（NaN）。仅判 None 会漏掉全部 19 条异常行。
        if not isinstance(v, list) or any(x is None or x != x for x in v):
            return None
        if f == "fineweb_edu":
            out["fineweb_edu"] = float(v[0])
        elif f == "ad_en":
            out["ad_en_margin"] = float(v[1]) - float(v[0])
        elif f == "fluency_en":
            out["fluency_en_margin"] = float(v[1]) - float(v[0])
        elif f == "qurater":
            # 题目把 qurater 计为 1 个指标；4 准则等权合成为 1 列（替代口径见敏感性）
            out["qurater"] = sum(float(x) for x in v) / len(v)
        else:
            out[f] = _softmax_expected_class([float(x) for x in v])
    for f, (_, _, _) in DIRECTION.items():
        if f in out:
            continue
        v = rec.get(f)
        if v is None or v != v:
            return None
        out[f] = float(v)
    return out


def load_all(limit_per_file: int | None = None) -> tuple[np.ndarray, np.ndarray, dict]:
    """流式读 A1+A2+A3 全量，返回 (X[n,22], domain_idx[n], meta)。"""
    domains: list[str] = []
    rows: list[list[float]] = []
    n_skipped = {"A1": 0, "A2": 0, "A3": 0}
    per_file = {}
    for tag, path, fixed_dom in (("A1", A1_PATH, None),
                                 ("A2", A2_PATH, "arxiv"),
                                 ("A3", A3_PATH, "github")):
        cnt = 0
        with lzma.open(path, "rt", encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                sc = scalarize(rec)
                if sc is None:
                    n_skipped[tag] += 1
                    continue
                rows.append([sc[c] for c in ALL_COLS])
                domains.append(fixed_dom or rec["_source_domain"])
                cnt += 1
                if limit_per_file and cnt >= limit_per_file:
                    break
        per_file[tag] = cnt
    X = np.asarray(rows, dtype=np.float64)
    dom_names = sorted(set(domains))
    dom_map = {d: i for i, d in enumerate(dom_names)}
    dom_idx = np.asarray([dom_map[d] for d in domains], dtype=np.int32)
    meta = {"columns": ALL_COLS, "domains": dom_names,
            "rows_per_file": per_file, "rows_skipped_nan": n_skipped,
            "n_rows": int(X.shape[0])}
    return X, dom_idx, meta


# ------------------------------------------------------- 归一化与方向统一
def _ecdf_rank(col: np.ndarray, ref: np.ndarray | None = None) -> np.ndarray:
    """经验 CDF 归一化到 (0,1)。ref 给定时用 ref 的分布作参照 CDF。"""
    base = col if ref is None else ref
    order = np.argsort(base, kind="mergesort")
    srt = base[order]
    pos = np.searchsorted(srt, col, side="left")
    pos2 = np.searchsorted(srt, col, side="right")
    mid = (pos + pos2) / 2.0
    return (mid + 0.5) / (len(srt) + 1.0)


def _winsor_minmax(col: np.ndarray, lo_q=0.01, hi_q=0.99) -> np.ndarray:
    lo, hi = np.quantile(col, [lo_q, hi_q])
    if hi <= lo:
        return np.full_like(col, 0.5)
    return np.clip((col - lo) / (hi - lo), 0.0, 1.0)


def normalize(X: np.ndarray, dom_idx: np.ndarray, population: str,
              scheme: str = "ecdf", ref_mask: np.ndarray | None = None) -> np.ndarray:
    """归一化到 [0,1]，不含方向统一。

    population: 'pooled' 合并全体 | 'per_domain' 按域分别 | 'ref_A1' 以 A1 分布为参照
    scheme:     'ecdf' 经验分位数 | 'winsor_minmax' 1%-99% 截尾后 Min-Max
    """
    fn = _ecdf_rank if scheme == "ecdf" else _winsor_minmax
    Z = np.empty_like(X)
    if population == "per_domain":
        for d in np.unique(dom_idx):
            m = dom_idx == d
            for j in range(X.shape[1]):
                Z[m, j] = fn(X[m, j])
    elif population == "ref_A1":
        if ref_mask is None:
            raise ValueError("ref_A1 需要 ref_mask 指明 A1 行")
        for j in range(X.shape[1]):
            if scheme == "ecdf":
                Z[:, j] = _ecdf_rank(X[:, j], ref=X[ref_mask, j])
            else:
                lo, hi = np.quantile(X[ref_mask, j], [0.01, 0.99])
                Z[:, j] = np.full(X.shape[0], 0.5) if hi <= lo else \
                    np.clip((X[:, j] - lo) / (hi - lo), 0.0, 1.0)
    elif population == "pooled":
        for j in range(X.shape[1]):
            Z[:, j] = fn(X[:, j])
    else:
        raise ValueError(population)
    return Z


def apply_direction(Z: np.ndarray, columns: list[str],
                    tier_c_override: dict[str, int] | None = None,
                    nonmonotone_as_distance: bool = True) -> np.ndarray:
    """把已归一化的 Z 统一为"越高越好"。

    tier_c_override: 覆写 tier C 指标的方向（+1/-1/0），用于敏感性分析。
    nonmonotone_as_distance: sign=0 的非单调指标按"到域内中位数的距离"取反处理，
        即 1-2*|z-0.5|，两端劣、中间优；False 时退化为 sign=+1。
    """
    U = Z.copy()
    ov = tier_c_override or {}
    for j, c in enumerate(columns):
        sign = ov.get(c, DIRECTION[c][0])
        if sign == -1:
            U[:, j] = 1.0 - U[:, j]
        elif sign == 0:
            if nonmonotone_as_distance:
                U[:, j] = 1.0 - 2.0 * np.abs(U[:, j] - 0.5)
    return U


# =============================================================== CANONICAL
# G2.5 决策后的规格。三条决策的落地：
#   q1_tierC_direction = D          -> dsir 逐 token + 三合一 + 长度类非单调
#   q1_normalization_population = A -> pooled ecdf 为主口径，per_domain 为消融臂
# 决策记录：methods/Q1/q1_decisions.jsonl
CANONICAL = {
    "dsir_per_token": True,
    "dsir_collapse": True,
    "population_primary": "pooled",
    "population_ablation": "per_domain",
    "scheme": "ecdf",
    "n_columns_after_collapse": 20,
}


def per_token_dsir(X: np.ndarray, columns: list[str]) -> np.ndarray:
    """dsir 三列各除以词数。修正"按 token 求和"导致的长度主导。"""
    Xo = X.copy()
    wc = X[:, columns.index("rps_doc_word_count")]
    for c in DSIR_COLS:
        Xo[:, columns.index(c)] = X[:, columns.index(c)] / np.maximum(wc, 1.0)
    return Xo


def collapse_dsir(U: np.ndarray, columns: list[str]) -> tuple[np.ndarray, list[str]]:
    """把逐 token 后互相关仍达 0.996 的 dsir 三列合为 1 个代表量。"""
    ids = [columns.index(c) for c in DSIR_COLS]
    keep = [j for j in range(len(columns)) if j not in ids]
    rep = U[:, ids].mean(1, keepdims=True)
    return np.hstack([U[:, keep], rep]), [columns[j] for j in keep] + [DSIR_REP]


def build_canonical(X: np.ndarray, dom_idx: np.ndarray, columns: list[str],
                    ref_mask: np.ndarray | None = None,
                    population: str | None = None) -> tuple[np.ndarray, list[str]]:
    """按 G2.5 决策规格产出方向统一后的指标矩阵（默认 20 列）。

    population 缺省取 CANONICAL['population_primary']；传 'per_domain' 得到消融臂。
    """
    pop = population or CANONICAL["population_primary"]
    Xp = per_token_dsir(X, columns) if CANONICAL["dsir_per_token"] else X
    Z = normalize(Xp, dom_idx, pop, scheme=CANONICAL["scheme"], ref_mask=ref_mask)
    U = apply_direction(Z, columns)
    if CANONICAL["dsir_collapse"]:
        U, columns = collapse_dsir(U, columns)
    return U, columns

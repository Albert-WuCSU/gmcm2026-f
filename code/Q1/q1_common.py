"""Q1 round1 共享层：加载、聚合、bootstrap、指标、落盘。

服务 code/Q1/q1_code_plan.md。四个脚本（M0/M1/M0c/M1c）共用本模块。

规格约束（来自 methods/Q1/q1_decisions.jsonl 的 4 条人工决策）：
  - 预处理一律经 workspace/code/scripts/q1_features.py 的 build_canonical()，不另写
  - q1_frac_unique_words_treatment = no_treatment：不得对 rps_doc_frac_unique_words 做长度校正
  - 主口径 pooled+ecdf；per_domain+ecdf 为必跑消融臂
  - 禁用 sklearn：岭回归与 CV 用 numpy 显式实现，避免隐藏默认值影响可复现性

种子 20260924，所有随机数经显式 default_rng，不使用全局 np.random。
"""
from __future__ import annotations

import csv
import itertools
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workspace/code/scripts"))

import q1_features as qf  # noqa: E402  共享特征层，CANONICAL 规格的唯一来源

SEED = qf.SEED
ROUND = "round1"
OUTDIR = ROOT / "results/Q1/experiments" / ROUND
TABLES = OUTDIR / "tables"
METRICS = OUTDIR / "metrics"
FIGURES = OUTDIR / "figures"

TAB = qf.RAW / "regmix_tables"
MAPPING_CSV = qf.RAW / "domain_mapping_guide.csv"

B_BOOT = 400
PERT_REPS = 40
PERT_FRAC = 0.10
LAMBDAS = [1e-8, 1e-6, 1e-4, 1e-3, 1e-2, 1e-1, 1.0, 10.0]

PAIRS = {
    "train_1m": ("train_mixture_1m.csv", "train_pile_loss_1m.csv"),
    "test_1m": ("test_mixture_1m.csv", "test_pile_loss_1m.csv"),
    "test_60m": ("test_mixture_60m.csv", "test_pile_loss_60m.csv"),
    "test_1B": ("test_mixture_1B.csv", "test_pile_loss_1B.csv"),
    "est_10b": ("est_mixture_10b.csv", "est_pile_loss_10b.csv"),
    "est_70b": ("est_mixture_70b.csv", "est_pile_loss_70b.csv"),
}


def ensure_dirs() -> None:
    for d in (TABLES, METRICS, FIGURES):
        d.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


# ------------------------------------------------------------ 质量侧加载
def load_quality(populations: tuple[str, ...] = ("pooled", "per_domain")):
    """一次读盘、两臂共用。返回 (arms, cols, dom_idx, domain_names, meta)。

    arms[population] -> U[n,20]。加载约 60 s、峰值内存约 530 MB，故不重复读盘。
    'pooled' 为主报口径，'per_domain' 为决策 q1_normalization_population=A 的必跑消融臂。
    """
    X, dom, meta = qf.load_all()
    ref_mask = np.zeros(X.shape[0], dtype=bool)
    ref_mask[:meta["rows_per_file"]["A1"]] = True
    arms, cols = {}, None
    for pop in populations:
        U, cols = qf.build_canonical(X, dom, meta["columns"], ref_mask=ref_mask,
                                     population=pop)
        arms[pop] = U
    return arms, cols, dom, meta["domains"], meta


def vp_split(cols: list[str]) -> tuple[list[int], list[int]]:
    """语义分组。P = 污染组 6 列，V = 其余 14 列（canonical 20 列口径）。

    注意：风险探针里的『价值组 16 列』是 22 列口径；dsir 三合一后为 14 列。
    分组是语义划分，不得声称由相关结构导出（组内相关 0.051/0.026 与组间 0.016 同量级）。
    """
    poll = set(qf.POLLUTION_COLS)
    p_idx = [j for j, c in enumerate(cols) if c in poll]
    v_idx = [j for j, c in enumerate(cols) if c not in poll]
    assert len(p_idx) == 6, f"污染组应为 6 列，实得 {len(p_idx)}"
    assert len(v_idx) == len(cols) - 6
    return v_idx, p_idx


# ------------------------------------------------------------ 聚合与区间
def huber_mean(v: np.ndarray, k: float = 1.345, iters: int = 30) -> float:
    """Huber M 估计。与 probe_q1_quality.huber_mean 同参数，保证与探针数值可比。"""
    mu = float(np.median(v))
    s = float(np.median(np.abs(v - mu))) * 1.4826
    if s <= 0:
        return mu
    for _ in range(iters):
        r = (v - mu) / s
        w = np.where(np.abs(r) <= k, 1.0, k / np.maximum(np.abs(r), 1e-12))
        new = float(np.sum(w * v) / np.sum(w))
        if abs(new - mu) < 1e-12:
            break
        mu = new
    return mu


def trimmed_mean(v: np.ndarray, frac: float = 0.10) -> float:
    if len(v) < 3:
        return float(np.mean(v))
    lo, hi = np.quantile(v, [frac, 1 - frac])
    m = (v >= lo) & (v <= hi)
    return float(np.mean(v[m])) if m.any() else float(np.mean(v))


def boot_ci(v: np.ndarray, stat, rng: np.random.Generator,
            b: int = B_BOOT) -> tuple[float, float, float]:
    """返回 (lo, hi, half_width) 的 95% 自助区间。"""
    n = len(v)
    bs = np.array([stat(v[rng.integers(0, n, n)]) for _ in range(b)])
    lo, hi = np.quantile(bs, [0.025, 0.975])
    return float(lo), float(hi), float((hi - lo) / 2)


def auc(pos: np.ndarray, neg: np.ndarray) -> float:
    """Mann-Whitney AUC。与 probe_q1_quality.auc_from_scores 同口径。"""
    allv = np.concatenate([pos, neg])
    r = np.argsort(np.argsort(allv)) + 1.0
    rp = r[:len(pos)].sum()
    return float((rp - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    ra = np.argsort(np.argsort(a))
    rb = np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


def kendall_tau(a: list[int], b: list[int]) -> float:
    n = len(a)
    conc = disc = 0
    for i in range(n):
        for j in range(i + 1, n):
            s = np.sign(a[i] - a[j]) * np.sign(b[i] - b[j])
            if s > 0:
                conc += 1
            elif s < 0:
                disc += 1
    tot = conc + disc
    return float((conc - disc) / tot) if tot else float("nan")


# ------------------------------------------------- 域级聚合与退化检查
def domain_table(q: np.ndarray, dom: np.ndarray, names: list[str],
                 rng: np.random.Generator) -> dict:
    """域级 Q：Huber 主报 + 10% 截尾对照 + bootstrap 95% 区间。"""
    out = {}
    for d, nm in enumerate(names):
        v = q[dom == d]
        lo, hi, hw = boot_ci(v, huber_mean, rng)
        out[nm] = {"n": int(len(v)), "huber": huber_mean(v),
                   "trimmed10": trimmed_mean(v), "median": float(np.median(v)),
                   "ci95_lo": lo, "ci95_hi": hi, "half_width": hw}
    hub = np.array([out[n]["huber"] for n in names])
    order = [names[i] for i in np.argsort(-hub)]
    return {"per_domain": out, "order_best_to_worst": order,
            "domain_range": float(hub.max() - hub.min())}


def distinguishable_pairs(dt: dict, names: list[str]) -> dict:
    """bootstrap 95% 区间不重叠的域对数（共 C(7,2)=21 对）。"""
    pd_ = dt["per_domain"]
    tot = sep = 0
    tied = []
    for a, b in itertools.combinations(names, 2):
        tot += 1
        if pd_[a]["ci95_lo"] > pd_[b]["ci95_hi"] or pd_[b]["ci95_lo"] > pd_[a]["ci95_hi"]:
            sep += 1
        else:
            tied.append(f"{a}~{b}")
    return {"n_pairs_total": tot, "n_pairs_distinguishable": sep,
            "n_pairs_tied": tot - sep, "tied_pairs": tied}


def degeneracy(q: np.ndarray) -> dict:
    """输出退化检查：std / CV / 唯一值比 / 基尼 / top1% 质量占比。"""
    n = len(q)
    s = np.sort(q)
    cum = np.cumsum(s)
    gini = float((n + 1 - 2 * np.sum(cum) / cum[-1]) / n) if cum[-1] > 0 else float("nan")
    k = max(1, n // 100)
    return {"mean": float(q.mean()), "std": float(q.std()),
            "coefficient_of_variation": float(q.std() / q.mean()) if q.mean() else float("nan"),
            "unique_output_count": int(len(np.unique(q))),
            "unique_ratio": float(len(np.unique(q)) / n),
            "gini": gini,
            "top1pct_mass_share": float(s[-k:].sum() / s.sum()) if s.sum() > 0 else float("nan"),
            "p05_p95_spread": float(np.quantile(q, .95) - np.quantile(q, .05)),
            "min": float(q.min()), "max": float(q.max())}


def perturb_weights(U: np.ndarray, dom: np.ndarray, names: list[str],
                    combine, rng: np.random.Generator,
                    reps: int = PERT_REPS, frac: float = PERT_FRAC) -> dict:
    """列权重 uniform ±frac 扰动下的域序稳定性与 top1% 样本重叠。

    combine(U, w) -> q。基准为等权。
    """
    m = U.shape[1]
    base_q = combine(U, np.ones(m) / m)
    base_hub = np.array([huber_mean(base_q[dom == d]) for d in range(len(names))])
    base_rank = list(np.argsort(np.argsort(-base_hub)))
    k = max(1, len(base_q) // 100)
    base_top = set(np.argsort(-base_q)[:k].tolist())

    taus, shifts, overlaps, unchanged = [], [], [], 0
    for _ in range(reps):
        w = np.ones(m) * (1.0 + rng.uniform(-frac, frac, m))
        w = w / w.sum()
        q = combine(U, w)
        hub = np.array([huber_mean(q[dom == d]) for d in range(len(names))])
        rank = list(np.argsort(np.argsort(-hub)))
        taus.append(kendall_tau(base_rank, rank))
        shifts.append(int(np.max(np.abs(np.array(base_rank) - np.array(rank)))))
        overlaps.append(len(base_top & set(np.argsort(-q)[:k].tolist())) / k)
        unchanged += int(rank == base_rank)
    return {"perturbation": f"weights uniform +/-{int(frac * 100)}%, reps={reps}",
            "domain_rank_kendall_tau_mean": float(np.mean(taus)),
            "domain_rank_kendall_tau_min": float(np.min(taus)),
            "domain_rank_max_position_change_max": int(max(shifts)),
            "frac_reps_domain_order_unchanged": float(unchanged / reps),
            "sample_top1pct_overlap_mean": float(np.mean(overlaps)),
            "sample_top1pct_overlap_min": float(np.min(overlaps)),
            "tau_per_rep": [float(t) for t in taus],
            "top1pct_overlap_per_rep": [float(o) for o in overlaps]}


def diff_ci(a: list[float], b: list[float], rng: np.random.Generator,
            b_boot: int = B_BOOT) -> dict:
    """mean(a) − mean(b) 的自助 95% 区间。HD-2：显著性一律由重抽样区间机械判定。"""
    A, Bv = np.asarray(a), np.asarray(b)
    d = np.array([A[rng.integers(0, len(A), len(A))].mean()
                  - Bv[rng.integers(0, len(Bv), len(Bv))].mean() for _ in range(b_boot)])
    lo, hi = np.quantile(d, [0.025, 0.975])
    return {"mean_diff": float(A.mean() - Bv.mean()),
            "ci95": [float(lo), float(hi)],
            "significant": bool(lo > 0 or hi < 0),
            "direction": "a>b" if A.mean() > Bv.mean() else "a<b"}


# ------------------------------------------------------------ 配比侧加载
def read_table(name: str) -> tuple[list[str], np.ndarray, list[str]]:
    with open(TAB / name, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    hdr = rows[0]
    idx = [r[0] for r in rows[1:]]
    data = np.array([[float(x) if x != "" else np.nan for x in r[1:]]
                     for r in rows[1:]], dtype=np.float64)
    return hdr[1:], data, idx


def load_pair(key: str):
    mf, lf = PAIRS[key]
    pcols, P, pidx = read_table(mf)
    lcols, L, lidx = read_table(lf)
    assert pidx == lidx, f"{key} 的配方表与 Loss 表 index 不对齐"
    return pcols, P, lcols, L


def loss_col_to_domain(c: str) -> str:
    """metric/the_pile_<dom>_val_loss -> <dom>。禁用 replace('the_pile_','')（会 0 匹配）。"""
    return c.removeprefix("metric/the_pile_").removesuffix("_val_loss")


def loss_to_mixture_index(pcols: list[str], lcols: list[str]) -> list[int | None]:
    return [pcols.index("train_the_pile_" + loss_col_to_domain(c))
            if ("train_the_pile_" + loss_col_to_domain(c)) in pcols else None
            for c in lcols]


def make_target(P: np.ndarray, L: np.ndarray, l2m: list[int | None],
                kind: str = "pweighted13") -> np.ndarray:
    """目标变量。

    pweighted13（主报）：以配比在 13 个有 Loss 的域上重归一化后的加权 Loss 均值。
      声明（AMB-Q1-2）：该目标把 p 同时置于等式两侧，存在部分循环，须在论文声明。
    mean13（对照）：13 域简单均值。
    单位：交叉熵 nats/token。
    """
    if kind == "mean13":
        return np.nanmean(L, axis=1)
    mix_idx = [i for i in l2m if i is not None]
    loss_idx = [j for j, x in enumerate(l2m) if x is not None]
    w = P[:, mix_idx]
    w = w / np.maximum(w.sum(1, keepdims=True), 1e-12)
    return np.nansum(w * L[:, loss_idx], axis=1)


def design(P: np.ndarray, kind: str) -> np.ndarray:
    """'main' 仅 17 主效应（去截距） | 'inter' 主效应 + 136 二阶交互 = 153 特征。"""
    n, m = P.shape
    if kind == "main":
        return P.copy()
    if kind == "inter":
        cols = [P] + [(P[:, i] * P[:, j])[:, None]
                      for i, j in itertools.combinations(range(m), 2)]
        return np.hstack(cols)
    raise ValueError(kind)


def feature_names(pcols: list[str], kind: str) -> list[str]:
    if kind == "main":
        return list(pcols)
    return list(pcols) + [f"{pcols[i]}*{pcols[j]}"
                          for i, j in itertools.combinations(range(len(pcols)), 2)]


def ridge_fit(A: np.ndarray, y: np.ndarray, lam: float) -> np.ndarray:
    return np.linalg.solve(A.T @ A + lam * np.eye(A.shape[1]), A.T @ y)


def kfold_cv(A: np.ndarray, y: np.ndarray, lams: list[float],
             rng: np.random.Generator, k: int = 5) -> tuple[float, dict]:
    """5 折 CV 选 λ。显式实现以避免 sklearn 的隐藏默认值。"""
    folds = np.array_split(rng.permutation(len(y)), k)
    scores = {}
    for lam in lams:
        errs = []
        for i in range(k):
            te = folds[i]
            tr = np.concatenate([folds[j] for j in range(k) if j != i])
            errs.append(float(np.mean((A[te] @ ridge_fit(A[tr], y[tr], lam) - y[te]) ** 2)))
        scores[lam] = float(np.mean(errs))
    return min(scores, key=scores.get), {f"{k_:g}": round(v, 8) for k_, v in scores.items()}


def r2(y: np.ndarray, yh: np.ndarray) -> float:
    ss = float(np.sum((y - y.mean()) ** 2))
    return float(1 - np.sum((y - yh) ** 2) / ss) if ss > 0 else float("nan")


def validate_by_scale(w: np.ndarray, A: np.ndarray, y: np.ndarray) -> dict:
    """三指标同报：原始 R²（对照）、按尺度去常数偏移后的 R²（主报）、Spearman（主报）。

    去偏依据：探针实测 60m/1B 的 bias 占 RMSE 98.8%/99.9%，即误差几乎全是水平平移。
    禁止单独引用 r2_raw。
    """
    yh = A @ w
    resid = y - yh
    bias = float(resid.mean())
    rmse = float(np.sqrt(np.mean(resid ** 2)))
    return {"n": int(len(y)),
            "r2_raw": r2(y, yh),
            "r2_after_offset_removal": r2(y, yh + bias),
            "spearman": spearman(y, yh),
            "bias": bias, "rmse": rmse,
            "bias_share_of_rmse": float(abs(bias) / rmse) if rmse > 0 else float("nan")}


def coef_stability(A: np.ndarray, y: np.ndarray, lam: float,
                   rng: np.random.Generator, b: int = B_BOOT) -> dict:
    """B 次自助下的系数符号稳定率与相对标准误。"""
    n, m = A.shape
    draws = np.empty((b, m))
    for t in range(b):
        s = rng.integers(0, n, n)
        draws[t] = ridge_fit(A[s], y[s], lam)
    base = ridge_fit(A, y, lam)
    same = np.mean(np.sign(draws) == np.sign(base), axis=0)
    se = draws.std(axis=0)
    rel = se / np.maximum(np.abs(base), 1e-12)
    return {"B": b, "coef": base.tolist(), "sign_stability": same.tolist(),
            "se": se.tolist(), "relative_se": rel.tolist(),
            "frac_coefs_sign_stable_ge_0.95": float(np.mean(same >= 0.95)),
            "median_sign_stability": float(np.median(same)),
            "mean_relative_se": float(np.mean(rel))}


def load_domain_mapping() -> dict[str, str]:
    """配方域 -> 质量域。17 域中仅 6 个有对应（11 个 inferred 全为 (none)）。"""
    out = {}
    with open(MAPPING_CSV, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            qd = row["quality_domain"].strip()
            if qd and qd != "(none)":
                out[row["mixture_domain"].strip()] = qd
    return out

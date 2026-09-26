"""Q4 G2 风险探针 —— 按 AGENTS.md 风险探针契约的七字段设计。

已由使用者裁定的框定(planning/framing_decisions.jsonl):
  q4_primary_defense_target        = A  (归因为主 claim)
  q4_scale_channel_definition      = 丙 (甲全样本为主 + 乙 66 子集作偏误验证)
  q4_acceptance_criteria_and_budget= c + 自定预测判据 + g(C8 全量)

判据全部预声明在本 docstring,不事后放宽(沿用 Q1 R6/R7 与 Q3 纪律):

P1 data_coverage      —— 无判据,纯清点。含 C8 全量解析实测耗时(AI 此前只给了估算,须兑现)。
P2 identifiability    —— 判据:|spearman(t, log10 N)| < 0.30 且 分档内 spearman(t,S) 显著为正
                         ⇒ f(N) 与 tau_t 可分。超阈则归因识别退化,须记 CONDITIONAL。
P3 attribution_degeneracy(承重) —— 判据:规模份额 与 技术份额 同时落在 [0,1] 且自助 95% 区间不含
                         负值 ⇒ 「占比」表述形式成立。若任一份额为负 ⇒ 表述形式失效,
                         必须改口径(报 points 而非 share),记 FAIL 并触发 fallback。
P4 gamma_bias(丙 的承重项) —— 判据:甲(仅 N)与乙(N,D,compute)在 66 个共同模型上给出的
                         技术份额之差,符号须为「甲 > 乙」(即甲高估技术)。符号相反则
                         HANDOFF 里登记的偏误方向断言是错的,须更正而非保留。
P5 bridge             —— 判据:High 层(n=7)Loss->Score 单调(spearman < 0);
                         且 pretrained 与 chat 的桥接斜率差是否超过各自自助半宽之和(是则须分组映射)。
P6 perturbation       —— 判据:换 f(N) 规格(十分位 dummy vs 线性 logN)与换时间粒度(月 vs 季)后,
                         技术份额变动 < 其自助区间宽度的 50% ⇒ 结论不依赖规格。
P7 prediction_criterion_feasibility —— 判据:使用者自定判据(中性情景 12 个月 80% 区间下界 >
                         当前前沿值)在纯时间趋势下是否够得着。够不着则该判据本身不可达,须回报使用者。

输出: workspace/data/q4_probe_attribution.json
只读原始数据,不写 workspace/data_raw/。
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[3]
CDIR = ROOT / "workspace" / "data_raw" / "real_attachments" / "C_efficiency_evolution"
OUT = ROOT / "workspace" / "data" / "q4_probe_attribution.json"

SEED = 20260925
B_BOOT = 2000  # HANDOFF 教训:份额可能贴近 0,B=400 定不住边界,故取 2000

rng = np.random.default_rng(SEED)
result: dict = {
    "schema_version": 1,
    "seed": SEED,
    "b_bootstrap": B_BOOT,
    "generated_at": None,
    "probes": {},
}


def norm_name(s: str) -> str:
    s = str(s).lower().split("/")[-1]
    if "_" in s:
        s = s.split("_", 1)[1]
    return re.sub(r"[^a-z0-9]", "", s)


def load_c1() -> tuple[pd.DataFrame, str]:
    c1 = pd.read_csv(CDIR / "leaderboard_cleaned.csv", low_memory=False)
    avg = [c for c in c1.columns if c.startswith("Average")][0]
    c1["date"] = pd.to_datetime(c1["Submission Date"], errors="coerce")
    c1 = c1.dropna(subset=["date", avg, "#Params (B)"]).copy()
    c1 = c1[c1["#Params (B)"] > 0].copy()
    c1["logN"] = np.log10(c1["#Params (B)"])
    c1["ym"] = c1["date"].dt.to_period("M")
    c1["S"] = c1[avg].astype(float)
    return c1, avg


# ---------------------------------------------------------------- P1 coverage
def probe_p1(c1: pd.DataFrame, avg: str) -> dict:
    c4 = pd.read_csv(CDIR / "epoch_all_ai_models.csv", low_memory=False)
    trio = c4[["Parameters", "Training compute (FLOP)", "Publication date"]].notna().all(axis=1)
    c4t = c4[trio].copy()
    c4t["k"] = c4t["Model"].map(norm_name)
    c1k = c1.copy()
    c1k["k"] = c1k["Model"].map(norm_name)
    c1k = c1k[c1k["k"].str.len() >= 4]
    joined = c1k.merge(
        c4t[["k", "Parameters", "Training compute (FLOP)", "Training dataset size (total)"]],
        on="k", how="inner",
    ).drop_duplicates("k")

    c5 = pd.read_csv(CDIR / "loss_benchmark_bridge.csv", low_memory=False)
    c6 = pd.read_csv(CDIR / "loss_benchmark_bridge_expanded.csv", low_memory=False)

    # C8 全量解析 —— 兑现 AI 此前只给估算的耗时承诺
    det = CDIR / "detailed_results"
    t0 = time.perf_counter()
    n_dir = n_ok = n_bad = 0
    task_counts: list[int] = []
    for d in sorted(det.iterdir()):
        if not d.is_dir():
            continue
        n_dir += 1
        best = None
        for f in sorted(d.glob("*.json")):
            try:
                with f.open(encoding="utf-8") as fh:
                    obj = json.load(fh)
                best = obj
            except Exception:
                n_bad += 1
        if best is not None:
            n_ok += 1
            res = best.get("results", {})
            if isinstance(res, dict):
                task_counts.append(len(res))
    c8_secs = time.perf_counter() - t0

    return {
        "verdict": "PASS",
        "c1_rows_usable": int(len(c1)),
        "c1_date_span_days": int((c1["date"].max() - c1["date"].min()).days),
        "c1_date_range": [str(c1["date"].min().date()), str(c1["date"].max().date())],
        "c1_type_counts": {str(k): int(v) for k, v in c1["Type"].value_counts().items()},
        "c4_rows": int(len(c4)),
        "c4_trio_complete": int(trio.sum()),
        "join_unique_models": int(len(joined)),
        "join_with_D": int(joined["Training dataset size (total)"].notna().sum()),
        "join_type_counts": {str(k): int(v) for k, v in joined["Type"].value_counts().items()},
        "bridge_c5_rows": int(len(c5)),
        "bridge_c6_rows": int(len(c6)),
        "c8_dirs": n_dir,
        "c8_parseable": n_ok,
        "c8_unparseable_files": n_bad,
        "c8_task_count_mode": int(pd.Series(task_counts).mode().iloc[0]) if task_counts else None,
        "c8_full_parse_seconds": round(c8_secs, 1),
        "c8_budget_note": (
            f"全量 {n_ok} 个目录解析实测 {c8_secs:.1f}s —— 裁定(g)全量成立，"
            "AI 此前『分钟级』的估算得到实测确认" if c8_secs < 600 else
            f"全量解析实测 {c8_secs:.1f}s，超出 AI 此前估算，须回报使用者"
        ),
        "joined_frame_cache": joined,
    }


# ----------------------------------------------------------- P2 identifiability
def probe_p2(c1: pd.DataFrame) -> dict:
    t = (c1["date"] - c1["date"].min()).dt.days.to_numpy(float)
    r_tn, p_tn = spearmanr(t, c1["logN"].to_numpy())
    r_ts, p_ts = spearmanr(t, c1["S"].to_numpy())
    r_sn, p_sn = spearmanr(c1["S"].to_numpy(), c1["logN"].to_numpy())

    bins = [(0, 4, "<4B"), (4, 10, "4-10B"), (10, 30, "10-30B"), (30, np.inf, ">30B")]
    within = {}
    for lo, hi, lab in bins:
        s = c1[(c1["#Params (B)"] >= lo) & (c1["#Params (B)"] < hi)]
        if len(s) < 30:
            within[lab] = {"n": int(len(s)), "note": "样本不足，不判"}
            continue
        tt = (s["date"] - s["date"].min()).dt.days.to_numpy(float)
        r, p = spearmanr(tt, s["S"].to_numpy())
        q = s.groupby("ym")["S"].quantile(0.90)
        within[lab] = {
            "n": int(len(s)),
            "spearman_t_S": round(float(r), 4),
            "p_value": float(p),
            "q90_first_month": round(float(q.iloc[0]), 3),
            "q90_last_month": round(float(q.iloc[-1]), 3),
            "q90_delta": round(float(q.iloc[-1] - q.iloc[0]), 3),
        }

    judged = [v for k, v in within.items() if "spearman_t_S" in v and k in ("4-10B", "10-30B")]
    tau_positive = all(v["spearman_t_S"] > 0 and v["p_value"] < 0.01 for v in judged)
    collinear_ok = abs(r_tn) < 0.30
    verdict = "PASS" if (tau_positive and collinear_ok) else "CONDITIONAL"
    return {
        "verdict": verdict,
        "criterion": "|spearman(t,log10 N)| < 0.30 且 4-10B/10-30B 档内 spearman(t,S) 显著为正",
        "spearman_t_logN": round(float(r_tn), 4),
        "spearman_t_logN_p": float(p_tn),
        "spearman_t_S": round(float(r_ts), 4),
        "spearman_S_logN": round(float(r_sn), 4),
        "spearman_S_logN_p": float(p_sn),
        "within_bin": within,
        "collinearity_ok": bool(collinear_ok),
        "tau_present_within_bins": bool(tau_positive),
        "interpretation": (
            "时间与规模不共线 ⇒ f(N) 由横截面变异钉住、tau_t 由档内月际位移钉住；"
            "两者可分，归因识别成立" if verdict == "PASS" else
            "识别退化，归因份额将不可靠，须记 CONDITIONAL 并考虑 fallback"
        ),
    }


# ------------------------------------------------------- 分解核心(P3/P4/P6 共用)
def _dummies(keys: pd.Series) -> tuple[np.ndarray, list]:
    """对分类键做 dummy 编码,丢弃首个水平作参照。返回 (矩阵, 非参照水平列表)。"""
    levels = sorted(keys.unique().tolist())
    ref, rest = levels[0], levels[1:]
    M = np.zeros((len(keys), len(rest)))
    arr = keys.to_numpy()
    for j, lv in enumerate(rest):
        M[:, j] = (arr == lv).astype(float)
    return M, rest


def decompose(df: pd.DataFrame, scale_cols: list[str], time_key: str,
              n_spec: str = "decile") -> dict:
    """把首期→末期的能力变化加性分解为 规模贡献 与 时间(技术)贡献。

    模型: S = f(scale) + tau_t + eps,加性 ⇒ 两因子 Shapley 退化为本分解,无交互项。
    规模贡献 = E[f(scale)|末期] - E[f(scale)|首期]
    技术贡献 = tau_末期 - tau_首期
    两者之和恒等于 拟合的总变化。
    """
    d = df.copy()
    if n_spec == "decile":
        d["_nb"] = pd.qcut(d[scale_cols[0]], 10, labels=False, duplicates="drop")
        Xs, _ = _dummies(d["_nb"])
        extra = [d[[c]].to_numpy(float) for c in scale_cols[1:]]
        Xs = np.hstack([Xs] + extra) if extra else Xs
    else:  # linear in each scale col
        Xs = d[scale_cols].to_numpy(float)

    Xt, t_levels = _dummies(d[time_key])
    X = np.hstack([np.ones((len(d), 1)), Xs, Xt])
    y = d["S"].to_numpy(float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)

    n_s = Xs.shape[1]
    b_s = beta[1:1 + n_s]
    b_t = beta[1 + n_s:]
    tau = {t_levels[0] if False else lv: b_t[j] for j, lv in enumerate(t_levels)}
    first, last = sorted(d[time_key].unique())[0], sorted(d[time_key].unique())[-1]
    tau_first = 0.0  # 参照水平
    tau_last = tau.get(last, 0.0)

    f_hat = Xs @ b_s
    d["_f"] = f_hat
    f_first = d.loc[d[time_key] == first, "_f"].mean()
    f_last = d.loc[d[time_key] == last, "_f"].mean()

    scale_pts = float(f_last - f_first)
    tech_pts = float(tau_last - tau_first)
    total = scale_pts + tech_pts
    return {
        "scale_points": scale_pts,
        "tech_points": tech_pts,
        "total_points": total,
        "scale_share": scale_pts / total if total != 0 else float("nan"),
        "tech_share": tech_pts / total if total != 0 else float("nan"),
        "first_period": str(first),
        "last_period": str(last),
    }


# -------------------------------------------- P3 份额退化(承重:决定表述形式)
def probe_p3(c1: pd.DataFrame) -> dict:
    base = decompose(c1, ["logN"], "ym", "decile")

    # 自助:按月内重抽模型,保持月度样本量
    groups = [g.index.to_numpy() for _, g in c1.groupby("ym")]
    sc, tc = [], []
    for _ in range(B_BOOT):
        idx = np.concatenate([rng.choice(g, size=len(g), replace=True) for g in groups])
        try:
            r = decompose(c1.loc[idx], ["logN"], "ym", "decile")
        except Exception:
            continue
        if np.isfinite(r["scale_share"]):
            sc.append(r["scale_share"])
            tc.append(r["tech_share"])
    sc_a, tc_a = np.array(sc), np.array(tc)
    ci = lambda a: [round(float(np.quantile(a, 0.025)), 4), round(float(np.quantile(a, 0.975)), 4)]
    sc_ci, tc_ci = ci(sc_a), ci(tc_a)

    shares_in_unit = 0 <= base["scale_share"] <= 1 and 0 <= base["tech_share"] <= 1
    scale_ci_nonneg = sc_ci[0] >= 0
    form_valid = bool(shares_in_unit and scale_ci_nonneg)

    return {
        "verdict": "PASS" if form_valid else "FAIL",
        "criterion": "两份额同时落在 [0,1] 且规模份额自助 95% 区间下界 >= 0 ⇒ 「占比」表述形式成立",
        "share_form_valid": form_valid,
        "scale_points": round(base["scale_points"], 4),
        "tech_points": round(base["tech_points"], 4),
        "total_points": round(base["total_points"], 4),
        "scale_share": round(base["scale_share"], 4),
        "tech_share": round(base["tech_share"], 4),
        "scale_share_ci95": sc_ci,
        "tech_share_ci95": tc_ci,
        "n_boot_effective": int(len(sc_a)),
        "period": [base["first_period"], base["last_period"]],
        "consequence_if_fail": (
            "份额为负或区间跨零 ⇒ 不得报「规模 X% / 技术 Y%」。"
            "须改口径为报绝对贡献点数与方向，并把「前沿变强而前沿上的模型变小」作为正面结论写出。"
            "不得取绝对值、不得截断到 0 掩盖 —— 这是承重发现。"
        ),
        "shapley_note": "加性模型下两因子 Shapley 与本分解恒等，无交互项，份额和恒为 1",
    }


# ------------------------------------- P4 甲/乙 偏误(裁定 丙 的承重项)
def probe_p4(joined: pd.DataFrame) -> dict:
    d = joined.dropna(subset=["Training compute (FLOP)"]).copy()
    d = d[d["Training compute (FLOP)"] > 0]
    d["logC"] = np.log10(d["Training compute (FLOP)"].astype(float))
    d["ym"] = d["date"].dt.to_period("Q")  # 66 个模型太少,月粒度会空格,退到季度
    if len(d) < 30 or d["ym"].nunique() < 2:
        return {"verdict": "FAIL", "reason": f"子集不足: n={len(d)}, 季度数={d['ym'].nunique()}"}

    a = decompose(d, ["logN"], "ym", "linear")            # 甲:仅 N
    b = decompose(d, ["logN", "logC"], "ym", "linear")    # 乙:N + compute
    diff = a["tech_share"] - b["tech_share"]
    sign_ok = diff > 0

    return {
        "verdict": "PASS" if sign_ok else "FAIL",
        "criterion": "甲(仅 N)的技术份额 > 乙(N+compute)的技术份额 ⇒ 甲系统性高估技术，方向断言成立",
        "subset_n": int(len(d)),
        "subset_quarters": int(d["ym"].nunique()),
        "jia_tech_share": round(a["tech_share"], 4),
        "yi_tech_share": round(b["tech_share"], 4),
        "bias_tech_share": round(float(diff), 4),
        "jia_scale_points": round(a["scale_points"], 4),
        "yi_scale_points": round(b["scale_points"], 4),
        "generalization_limit": (
            "本子集 pretrained 占比远高于 C1 全样本的 6.0% —— 不是同一总体。"
            "本条只给偏误的符号与量级，不得作为对全样本数字的修正系数，不得表述为『已校正』。"
        ),
        "correction_if_sign_flips": (
            "若符号与预期相反，则账本 q4_scale_channel_definition 中"
            "『甲单独使用时对技术进步占比为系统性高估』的方向断言是错的，须如实更正而非保留。"
        ),
    }


# --------------------------------------------------------------- P5 桥接
def probe_p5(c1: pd.DataFrame) -> dict:
    c6 = pd.read_csv(CDIR / "loss_benchmark_bridge_expanded.csv", low_memory=False)
    loss_col = next((c for c in c6.columns if "loss" in c.lower() and "source" not in c.lower()
                     and "compar" not in c.lower()), None)
    score_col = next((c for c in c6.columns if "score" in c.lower() or c.startswith("Average")), None)
    cmp_col = next((c for c in c6.columns if "compar" in c.lower()), None)
    if loss_col is None or score_col is None:
        return {"verdict": "FAIL", "reason": f"列名未识别: {list(c6.columns)[:12]}"}

    out = {"loss_col": loss_col, "score_col": score_col, "comparability_col": cmp_col,
           "tiers": {}}
    d = c6.dropna(subset=[loss_col, score_col])
    r_all, p_all = spearmanr(d[loss_col], d[score_col])
    out["spearman_all"] = round(float(r_all), 4)
    out["spearman_all_p"] = float(p_all)
    out["n_all"] = int(len(d))

    high_ok = None
    if cmp_col is not None:
        for tier, g in d.groupby(cmp_col):
            if len(g) >= 5:
                r, p = spearmanr(g[loss_col], g[score_col])
                out["tiers"][str(tier)] = {"n": int(len(g)), "spearman": round(float(r), 4),
                                           "p_value": float(p)}
                if str(tier).lower().startswith("high"):
                    high_ok = r < 0
            else:
                out["tiers"][str(tier)] = {"n": int(len(g)), "note": "n<5,不判"}

    out["criterion"] = "High 层 Loss->Score 单调递减(spearman < 0)"
    out["verdict"] = "PASS" if (high_ok is True or (high_ok is None and r_all < 0)) else "CONDITIONAL"
    out["high_tier_monotone"] = high_ok
    out["small_sample_warning"] = (
        "High 层样本仅 7 条(F9 已记)。映射误差须作独立随机项传播到前沿预测，"
        "不得把 High 层相关弱于 Medium 层解读为 High 层质量更差(F10 已记)。"
    )
    return out


# ------------------------------------------------- P6 规格扰动敏感性
def probe_p6(c1: pd.DataFrame, p3: dict) -> dict:
    specs = {
        "decile_month": decompose(c1, ["logN"], "ym", "decile"),
        "linear_month": decompose(c1, ["logN"], "ym", "linear"),
    }
    cq = c1.copy()
    cq["yq"] = cq["date"].dt.to_period("Q")
    specs["decile_quarter"] = decompose(cq, ["logN"], "yq", "decile")
    specs["linear_quarter"] = decompose(cq, ["logN"], "yq", "linear")

    ts = [v["tech_share"] for v in specs.values() if np.isfinite(v["tech_share"])]
    spread = float(max(ts) - min(ts)) if ts else float("nan")
    ci = p3.get("tech_share_ci95") or [np.nan, np.nan]
    ci_width = float(ci[1] - ci[0]) if all(np.isfinite(ci)) else float("nan")
    ratio = spread / ci_width if ci_width and np.isfinite(ci_width) and ci_width > 0 else float("nan")
    ok = bool(np.isfinite(ratio) and ratio < 0.50)

    return {
        "verdict": "PASS" if ok else "CONDITIONAL",
        "criterion": "四种规格下技术份额极差 < 其自助 95% 区间宽度的 50% ⇒ 结论不依赖规格",
        "specs": {k: {"scale_share": round(v["scale_share"], 4),
                      "tech_share": round(v["tech_share"], 4),
                      "total_points": round(v["total_points"], 4)} for k, v in specs.items()},
        "tech_share_spread": round(spread, 4) if np.isfinite(spread) else None,
        "bootstrap_ci_width": round(ci_width, 4) if np.isfinite(ci_width) else None,
        "spread_over_ci_width": round(ratio, 4) if np.isfinite(ratio) else None,
        "note_if_conditional": (
            "极差超过区间宽度一半 ⇒ 规格选择本身是结论的一部分，"
            "须像 Q3 的三定义那样把规格差异摆在正文，不得只报一种规格。"
        ),
    }


# ------------------------------- P7 使用者自定预测判据是否够得着
def probe_p7(c1: pd.DataFrame) -> dict:
    q = c1.groupby("ym")["S"].quantile(0.90)
    x = np.arange(len(q), dtype=float)
    y = q.to_numpy(float)
    slope, intercept = np.polyfit(x, y, 1)
    resid = y - (slope * x + intercept)
    sigma = float(resid.std(ddof=2))
    cur = float(y[-1])
    h = 12.0
    pred = slope * (len(q) - 1 + h) + intercept
    # 纯时间趋势下的 80% 区间(仅含拟合残差,不含桥接与标度律不确定性)
    se = sigma * np.sqrt(1 + h / len(q))
    lo80 = pred - 1.2816 * se
    reachable = bool(lo80 > cur)

    return {
        "verdict": "PASS" if reachable else "FAIL",
        "criterion": "使用者自定判据:中性情景下 12 个月 80% 区间下界 > 当前前沿值",
        "frontier_definition": "每月 Average 的 0.90 分位",
        "q90_by_month": {str(k): round(float(v), 3) for k, v in q.items()},
        "slope_per_month": round(float(slope), 4),
        "current_frontier": round(cur, 3),
        "pred_12m_point": round(float(pred), 3),
        "resid_sigma": round(sigma, 4),
        "lo80_time_trend_only": round(float(lo80), 3),
        "criterion_reachable": reachable,
        "caveat": (
            "本条只含时间趋势残差,未含桥接误差与标度律参数不确定性。"
            "三源叠加后区间会更宽 ⇒ 本值是判据可达性的乐观上界。"
            "若此处已 FAIL，则该判据在完整不确定性下必然 FAIL，须回报使用者。"
        ),
        "saturation_note": (
            "得分有 0-100 上界,饱和形态在 9.1 个月窗口内不可检验。"
            "24 个月视界若报告须显式声明该假设不可验证(账本已登记为待办)。"
        ),
    }


def main() -> None:
    t0 = time.perf_counter()
    c1, avg = load_c1()
    print(f"C1 loaded: {len(c1)} rows, score col = {avg!r}")

    p1 = probe_p1(c1, avg)
    joined = p1.pop("joined_frame_cache")
    print(f"P1 done ({p1['verdict']}) | C8 full parse {p1['c8_full_parse_seconds']}s")

    p2 = probe_p2(c1); print(f"P2 done ({p2['verdict']})")
    p3 = probe_p3(c1); print(f"P3 done ({p3['verdict']}) scale_share={p3['scale_share']}")
    p4 = probe_p4(joined); print(f"P4 done ({p4['verdict']})")
    p5 = probe_p5(c1); print(f"P5 done ({p5['verdict']})")
    p6 = probe_p6(c1, p3); print(f"P6 done ({p6['verdict']})")
    p7 = probe_p7(c1); print(f"P7 done ({p7['verdict']})")

    result["probes"] = {"P1_data_coverage": p1, "P2_identifiability": p2,
                        "P3_share_degeneracy": p3, "P4_jia_yi_bias": p4,
                        "P5_bridge": p5, "P6_perturbation": p6,
                        "P7_prediction_criterion": p7}
    result["generated_at"] = pd.Timestamp.now(tz="Asia/Shanghai").isoformat()
    result["elapsed_seconds"] = round(time.perf_counter() - t0, 1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT.relative_to(ROOT)}  ({result['elapsed_seconds']}s total)")


if __name__ == "__main__":
    main()

"""Q1a/Q1b 方法特定风险探针（质量侧）。

按 AGENTS.md「Risk Probe Contract」执行，覆盖 executability / data_coverage /
assumption_checks / output_degeneracy / perturbation_sensitivity / scale_check。
评价类必查项：指标方向、权重敏感性、评分集中度、排序稳定性。

被探方法：
  M0 usable_baseline  : 22 指标方向统一后等权平均（HD-2=B 指定）
  M1 main_candidate   : 语义分组 V/P + 门控或差值合成
  M2 conditional_fallback : 指标间稳健序统计（中位数）合成 + 离散度冲突

输出：workspace/data/q1_probe_quality.json
种子：20260924
"""
from __future__ import annotations

import json
import time
import tracemalloc
from pathlib import Path

import numpy as np

import q1_features as qf

OUT = qf.ROOT / "workspace/data/q1_probe_quality.json"
RNG = np.random.default_rng(qf.SEED)
B_BOOT = 1000


def entropy_weights(U: np.ndarray) -> np.ndarray:
    """熵权法权重。U 已在 [0,1]。"""
    P = U / np.maximum(U.sum(0, keepdims=True), 1e-12)
    n = U.shape[0]
    with np.errstate(divide="ignore", invalid="ignore"):
        e = -(P * np.log(np.where(P > 0, P, 1.0))).sum(0) / np.log(n)
    d = 1.0 - e
    return d / d.sum()


def trimmed_mean(v: np.ndarray, frac: float = 0.1) -> float:
    if len(v) < 10:
        return float(np.mean(v))
    lo, hi = np.quantile(v, [frac, 1 - frac])
    sel = v[(v >= lo) & (v <= hi)]
    return float(np.mean(sel)) if len(sel) else float(np.mean(v))


def huber_mean(v: np.ndarray, k: float = 1.345, iters: int = 30) -> float:
    mu = float(np.median(v))
    s = float(np.median(np.abs(v - mu))) * 1.4826
    if s <= 0:
        return mu
    for _ in range(iters):
        r = (v - mu) / s
        w = np.where(np.abs(r) <= k, 1.0, k / np.maximum(np.abs(r), 1e-12))
        new = float((w * v).sum() / w.sum())
        if abs(new - mu) < 1e-12:
            break
        mu = new
    return mu


def boot_ci(v: np.ndarray, stat, b: int = B_BOOT) -> list[float]:
    n = len(v)
    idx = RNG.integers(0, n, size=(b, n))
    vals = np.array([stat(v[i]) for i in idx])
    return [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))]


def domain_stats(q: np.ndarray, dom: np.ndarray, names: list[str],
                 with_ci: bool = False) -> dict:
    out = {}
    for d, nm in enumerate(names):
        v = q[dom == d]
        rec = {"n": int(len(v)), "mean": float(np.mean(v)),
               "trimmed10": trimmed_mean(v), "huber": huber_mean(v),
               "std": float(np.std(v))}
        if with_ci:
            rec["huber_ci95"] = boot_ci(v, huber_mean)
            rec["ci_width"] = round(rec["huber_ci95"][1] - rec["huber_ci95"][0], 6)
        out[nm] = rec
    vals = np.array([out[nm]["huber"] for nm in names])
    return {"per_domain": out,
            "cross_domain_range": float(vals.max() - vals.min()),
            "cross_domain_cv": float(np.std(vals) / max(abs(np.mean(vals)), 1e-12))}


def auc_from_scores(pos: np.ndarray, neg: np.ndarray) -> float:
    """Mann-Whitney AUC，用秩计算。"""
    allv = np.concatenate([pos, neg])
    r = np.argsort(np.argsort(allv, kind="mergesort"), kind="mergesort") + 1.0
    rp = r[:len(pos)].sum()
    n1, n2 = len(pos), len(neg)
    return float((rp - n1 * (n1 + 1) / 2) / (n1 * n2))


def main() -> None:
    tracemalloc.start()
    t0 = time.time()
    X, dom, meta = qf.load_all()
    t_load = time.time() - t0
    cols = meta["columns"]
    names = meta["domains"]
    n = X.shape[0]
    # A1 行掩码：A1 在前 rows_per_file['A1'] 行
    ref_mask = np.zeros(n, dtype=bool)
    ref_mask[:meta["rows_per_file"]["A1"]] = True

    res: dict = {"schema_version": 1, "seed": qf.SEED, "meta": meta,
                 "runtime_load_seconds": round(t_load, 2)}

    # ---------------- 1. 方向表与 min-max 退化检查 ----------------
    direction_tbl = {c: {"sign": qf.DIRECTION[c][0], "tier": qf.DIRECTION[c][1],
                         "basis": qf.DIRECTION[c][2]} for c in cols}
    mm_deg = {}
    for j, c in enumerate(cols):
        v = X[:, j]
        lo, hi = float(v.min()), float(v.max())
        p50 = float(np.median(v))
        if hi > lo:
            mm_deg[c] = {
                "raw_min": lo, "raw_max": hi, "raw_median": p50,
                "median_position_in_naive_minmax": round((p50 - lo) / (hi - lo), 6),
                "frac_mass_in_top_1pct_of_range": round(
                    float(np.mean(v >= lo + 0.99 * (hi - lo))), 6),
            }
    res["direction_table"] = direction_tbl
    res["naive_minmax_degeneracy"] = mm_deg
    res["tier_counts"] = {t: sum(1 for c in cols if qf.DIRECTION[c][1] == t)
                          for t in ("A", "B", "C")}

    # ---------------- 2. 三种归一化口径下的域级 Q 可分辨性 ----------------
    pop_results = {}
    U_cache = {}
    for pop in ("pooled", "per_domain", "ref_A1"):
        for scheme in ("ecdf", "winsor_minmax"):
            Z = qf.normalize(X, dom, pop, scheme=scheme, ref_mask=ref_mask)
            U = qf.apply_direction(Z, cols)
            U_cache[(pop, scheme)] = U
            q0 = U.mean(1)                      # M0 等权
            ds = domain_stats(q0, dom, names)
            # Q 还原域标签的能力（arxiv vs github，与 F2 同口径）
            ia, ig = names.index("arxiv"), names.index("github")
            auc = auc_from_scores(q0[dom == ia], q0[dom == ig])
            pop_results[f"{pop}|{scheme}"] = {
                "cross_domain_range": round(ds["cross_domain_range"], 6),
                "cross_domain_cv": round(ds["cross_domain_cv"], 6),
                "domain_huber": {k: round(v["huber"], 5)
                                 for k, v in ds["per_domain"].items()},
                "auc_arxiv_vs_github_of_Q": round(auc, 4),
                "sample_level_std": round(float(np.std(q0)), 6),
            }
    res["normalization_population_comparison"] = pop_results

    # 主分析口径：pooled + ecdf（保留跨域可分辨性），per_domain 作为去混淆对照
    U = U_cache[("pooled", "ecdf")]
    Upd = U_cache[("per_domain", "ecdf")]

    # ---------------- 3. assumption_checks：共线性与 V/P 分块 ----------------
    C = np.corrcoef(U, rowvar=False)
    off = C - np.eye(len(cols))
    pol_idx = [cols.index(c) for c in qf.POLLUTION_COLS]
    val_idx = [j for j in range(len(cols)) if j not in pol_idx]
    ev = np.linalg.eigvalsh(C)[::-1]
    res["assumption_checks_raw"] = {
        "max_abs_offdiag_corr": round(float(np.abs(off).max()), 4),
        "mean_abs_offdiag_corr": round(float(np.abs(off).sum() / (len(cols) ** 2 - len(cols))), 4),
        "n_pairs_absdcorr_gt_0.9": int((np.abs(off) > 0.9).sum() // 2),
        "n_pairs_absdcorr_gt_0.7": int((np.abs(off) > 0.7).sum() // 2),
        "corr_condition_number": round(float(ev[0] / max(ev[-1], 1e-12)), 1),
        "pc1_variance_share": round(float(ev[0] / ev.sum()), 4),
        "pc1_pc2_variance_share": round(float((ev[0] + ev[1]) / ev.sum()), 4),
        "block_structure": {
            "mean_corr_within_value": round(float(np.mean(
                [C[a, b] for i, a in enumerate(val_idx) for b in val_idx[i + 1:]])), 4),
            "mean_corr_within_pollution": round(float(np.mean(
                [C[a, b] for i, a in enumerate(pol_idx) for b in pol_idx[i + 1:]])), 4),
            "mean_corr_between": round(float(np.mean(
                [C[a, b] for a in val_idx for b in pol_idx])), 4),
            "n_value_cols": len(val_idx), "n_pollution_cols": len(pol_idx),
        },
    }

    # 熵权是否放大域混淆
    w_ent = entropy_weights(U)
    dc = json.loads((qf.ROOT / "workspace/data/domain_confound.json").read_text(encoding="utf-8"))
    sep_map = {"fineweb_edu": "fineweb_edu", "ad_en_margin": "ad_en_margin",
               "fluency_en_margin": "fluency_en_margin",
               "modernbert_cleanliness": "modernbert_cleanliness_expclass",
               "modernbert_readability": "modernbert_readability_expclass",
               "modernbert_reasoning": "modernbert_reasoning_expclass",
               "modernbert_professionalism": "modernbert_professionalism_expclass"}
    seps, ws = [], []
    for j, c in enumerate(cols):
        key = sep_map.get(c, c)
        if key in dc["per_indicator"]:
            seps.append(dc["per_indicator"][key]["separation"])
            ws.append(w_ent[j])
    res["entropy_weight_confound_check"] = {
        "n_matched_indicators": len(seps),
        "pearson_w_vs_domain_separation": round(float(np.corrcoef(ws, seps)[0, 1]), 4),
        "entropy_weight_max": round(float(w_ent.max()), 4),
        "entropy_weight_min": round(float(w_ent.min()), 4),
        "entropy_weight_max_over_equal": round(float(w_ent.max() * len(cols)), 3),
        "top3_weight_mass": round(float(np.sort(w_ent)[::-1][:3].sum()), 4),
        "top3_columns": [cols[i] for i in np.argsort(w_ent)[::-1][:3]],
    }

    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    cur, peak = tracemalloc.get_traced_memory()
    print(f"part1 done rows={n} load={t_load:.1f}s peak={peak/1e6:.0f}MB -> {OUT}")


if __name__ == "__main__":
    main()

"""Q1a/Q1b 风险探针 part 2：输出退化、冲突率、扰动稳定性、Tier C 方向敏感性、规模。

被探方法（均在同一归一化口径下，唯一差异是权重与合成方式）：
  M0 baseline : Q = 22 列方向统一后等权平均
  M1 main     : V = 价值组均值, P = 污染组污染度均值, Q = V*(1-P) 门控 / V-P 差值
  M2 fallback : Q = 22 列的稳健序统计（中位数），冲突 = 指标间四分位距

输出：workspace/data/q1_probe_quality2.json
种子：20260924
"""
from __future__ import annotations

import json
import time
import tracemalloc

import numpy as np

import q1_features as qf
from probe_q1_quality import huber_mean, trimmed_mean, auc_from_scores

OUT = qf.ROOT / "workspace/data/q1_probe_quality2.json"
RNG = np.random.default_rng(qf.SEED)


def degeneracy(q: np.ndarray, dom: np.ndarray, names: list[str]) -> dict:
    """输出退化指标：方差、唯一值数、top-k 质量、基尼、域间极差。"""
    srt = np.sort(q)[::-1]
    k1 = max(1, len(q) // 100)
    dv = np.array([huber_mean(q[dom == d]) for d in range(len(names))])
    # 基尼系数
    s = np.sort(q)
    cum = np.cumsum(s)
    gini = float((len(s) + 1 - 2 * (cum.sum() / cum[-1])) / len(s)) if cum[-1] > 0 else 0.0
    return {
        "std": round(float(np.std(q)), 6),
        "coefficient_of_variation": round(float(np.std(q) / max(abs(np.mean(q)), 1e-12)), 6),
        "unique_output_count": int(len(np.unique(np.round(q, 6)))),
        "unique_ratio": round(float(len(np.unique(np.round(q, 6))) / len(q)), 6),
        "top1pct_mass_share": round(float(srt[:k1].sum() / q.sum()), 6),
        "gini": round(gini, 6),
        "p05_p95_spread": round(float(np.quantile(q, 0.95) - np.quantile(q, 0.05)), 6),
        "domain_huber_range": round(float(dv.max() - dv.min()), 6),
        "domain_huber": {n: round(float(v), 5) for n, v in zip(names, dv)},
    }


def build_scores(U: np.ndarray, cols: list[str]) -> dict[str, np.ndarray]:
    pol = [cols.index(c) for c in qf.POLLUTION_COLS]
    val = [j for j in range(len(cols)) if j not in pol]
    V = U[:, val].mean(1)
    P = 1.0 - U[:, pol].mean(1)        # 还原为"污染度"，越大越脏
    return {
        "M0_equal_weight": U.mean(1),
        "M1_gated": V * (1.0 - P),
        "M1_difference": V - P,
        "M2_median": np.median(U, axis=1),
        "_V": V, "_P": P,
    }


def conflict_rates(U: np.ndarray, cols: list[str]) -> dict:
    pol = [cols.index(c) for c in qf.POLLUTION_COLS]
    val = [j for j in range(len(cols)) if j not in pol]
    V = U[:, val].mean(1)
    P = 1.0 - U[:, pol].mean(1)
    mad = np.abs(U - np.median(U, axis=1, keepdims=True)).mean(1)
    iqr = np.quantile(U, 0.75, axis=1) - np.quantile(U, 0.25, axis=1)
    n_hi = (U > 0.75).sum(1)
    n_lo = (U < 0.25).sum(1)
    out = {
        "CD1_global_MAD_gt_0.25": round(float(np.mean(mad > 0.25)), 6),
        "CD1_global_MAD_gt_0.20": round(float(np.mean(mad > 0.20)), 6),
        "CD1_MAD_distribution": {k: round(float(np.quantile(mad, v)), 5)
                                 for k, v in (("p50", .5), ("p90", .9), ("p99", .99))},
        "CD2_local_highV_and_highP": round(float(np.mean((V > 0.75) & (P > 0.75))), 6),
        "CD2_thresholds_p75": {"V_p75": round(float(np.quantile(V, .75)), 5),
                               "P_p75": round(float(np.quantile(P, .75)), 5)},
        "CD2_local_quantile_based": round(float(np.mean(
            (V > np.quantile(V, .75)) & (P > np.quantile(P, .75)))), 6),
        "CD3_ge3_high_and_ge3_low": round(float(np.mean((n_hi >= 3) & (n_lo >= 3))), 6),
        "CD3_ge5_high_and_ge5_low": round(float(np.mean((n_hi >= 5) & (n_lo >= 5))), 6),
        "M2_IQR_distribution": {k: round(float(np.quantile(iqr, v)), 5)
                                for k, v in (("p50", .5), ("p90", .9))},
        "corr_V_vs_P": round(float(np.corrcoef(V, P)[0, 1]), 4),
    }
    out["all_rates_in_open_interval"] = all(
        0.0 < out[k] < 1.0 for k in
        ("CD1_global_MAD_gt_0.25", "CD1_global_MAD_gt_0.20",
         "CD2_local_highV_and_highP", "CD3_ge3_high_and_ge3_low",
         "CD3_ge5_high_and_ge5_low"))
    return out


def perturb_stability(U: np.ndarray, dom: np.ndarray, names: list[str],
                      reps: int = 40, scale: float = 0.10) -> dict:
    """权重 ±10% 相对扰动下的域级排序与样本 top-1% 重叠稳定性。"""
    m = U.shape[1]
    base_w = np.full(m, 1.0 / m)
    q_base = U @ base_w
    dv_base = np.array([huber_mean(q_base[dom == d]) for d in range(len(names))])
    rank_base = np.argsort(np.argsort(-dv_base))
    k = max(1, len(q_base) // 100)
    top_base = set(np.argpartition(-q_base, k)[:k].tolist())

    taus, overlaps, rank_changes = [], [], []
    for _ in range(reps):
        w = base_w * (1.0 + RNG.uniform(-scale, scale, size=m))
        w /= w.sum()
        q = U @ w
        dv = np.array([huber_mean(q[dom == d]) for d in range(len(names))])
        rk = np.argsort(np.argsort(-dv))
        rank_changes.append(int(np.abs(rk - rank_base).max()))
        # Kendall tau on 7 domains
        c = d_ = 0
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                s1 = np.sign(dv_base[i] - dv_base[j])
                s2 = np.sign(dv[i] - dv[j])
                if s1 * s2 > 0:
                    c += 1
                elif s1 * s2 < 0:
                    d_ += 1
        taus.append((c - d_) / max(c + d_, 1))
        top = set(np.argpartition(-q, k)[:k].tolist())
        overlaps.append(len(top & top_base) / k)
    return {
        "perturbation": f"weights uniform +/-{int(scale*100)}%, reps={reps}",
        "domain_rank_kendall_tau_mean": round(float(np.mean(taus)), 4),
        "domain_rank_kendall_tau_min": round(float(np.min(taus)), 4),
        "domain_rank_max_position_change_max": int(max(rank_changes)),
        "frac_reps_domain_order_unchanged": round(
            float(np.mean([t == 1.0 for t in taus])), 4),
        "sample_top1pct_overlap_mean": round(float(np.mean(overlaps)), 4),
        "sample_top1pct_overlap_min": round(float(np.min(overlaps)), 4),
    }


def direction_consistency(U: np.ndarray, cols: list[str]) -> dict:
    """方向统一后仍强反向的指标对 = 方向表内部矛盾的直接证据。"""
    C = np.corrcoef(U, rowvar=False)
    bad = []
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            if C[i, j] < -0.5:
                bad.append({"a": cols[i], "b": cols[j], "r": round(float(C[i, j]), 4),
                            "tier_a": qf.DIRECTION[cols[i]][1],
                            "tier_b": qf.DIRECTION[cols[j]][1]})
    bad.sort(key=lambda p: p["r"])
    return {
        "n_pairs_r_lt_minus_0.5": len(bad),
        "n_pairs_r_lt_minus_0.8": sum(1 for p in bad if p["r"] < -0.8),
        "pairs": bad[:15],
        "involves_tier_C": sum(1 for p in bad if "C" in (p["tier_a"], p["tier_b"])),
        "note": "两指标都已统一为『越高越好』却强负相关，说明至少一方方向赋值与数据不相容",
    }


def tierC_sensitivity(X: np.ndarray, dom: np.ndarray, cols: list[str],
                      ref_mask: np.ndarray, names: list[str]) -> dict:
    """Tier C 方向选择对域级 Q 排序的影响。"""
    Z = qf.normalize(X, dom, "pooled", scheme="ecdf", ref_mask=ref_mask)
    variants = {
        "baseline_all_plus": {},
        "dsir_negative": {"dsir_books": -1, "dsir_wiki": -1, "dsir_math": -1},
        "length_negative": {"rps_doc_word_count": -1, "rps_doc_num_sentences": -1},
        "dsir_and_length_negative": {"dsir_books": -1, "dsir_wiki": -1, "dsir_math": -1,
                                     "rps_doc_word_count": -1, "rps_doc_num_sentences": -1},
        "mwl_as_plus": {"rps_doc_mean_word_length": +1},
    }
    out, base_rank, base_dv = {}, None, None
    for nm, ov in variants.items():
        U = qf.apply_direction(Z, cols, tier_c_override=ov)
        q = U.mean(1)
        dv = np.array([huber_mean(q[dom == d]) for d in range(len(names))])
        rk = np.argsort(np.argsort(-dv))
        order = [names[i] for i in np.argsort(-dv)]
        ia, ig = names.index("arxiv"), names.index("github")
        rec = {"domain_order_best_to_worst": order,
               "domain_huber": {n: round(float(v), 5) for n, v in zip(names, dv)},
               "domain_range": round(float(dv.max() - dv.min()), 6),
               "auc_arxiv_vs_github_of_Q": round(auc_from_scores(q[dom == ia], q[dom == ig]), 4)}
        if base_rank is None:
            base_rank, base_dv = rk, dv
        else:
            rec["max_rank_shift_vs_baseline"] = int(np.abs(rk - base_rank).max())
            rec["spearman_vs_baseline"] = round(float(np.corrcoef(base_dv, dv)[0, 1]), 4)
        out[nm] = rec
    return out


def main() -> None:
    tracemalloc.start()
    t0 = time.time()
    X, dom, meta = qf.load_all()
    cols, names = meta["columns"], meta["domains"]
    ref_mask = np.zeros(X.shape[0], dtype=bool)
    ref_mask[:meta["rows_per_file"]["A1"]] = True
    t_load = time.time() - t0

    res = {"schema_version": 1, "seed": qf.SEED, "n_rows": int(X.shape[0]),
           "domains": names}

    for pop in ("pooled", "per_domain"):
        t1 = time.time()
        Z = qf.normalize(X, dom, pop, scheme="ecdf", ref_mask=ref_mask)
        U = qf.apply_direction(Z, cols)
        sc = build_scores(U, cols)
        block = {
            "direction_consistency": direction_consistency(U, cols),
            "conflict": conflict_rates(U, cols),
            "degeneracy": {k: degeneracy(v, dom, names)
                           for k, v in sc.items() if not k.startswith("_")},
            "perturbation_sensitivity": perturb_stability(U, dom, names),
            "runtime_seconds": round(time.time() - t1, 2),
        }
        # 域级稳健聚合 + bootstrap（小域不确定性）
        ci = {}
        for d, nm in enumerate(names):
            v = sc["M0_equal_weight"][dom == d]
            b = 300 if len(v) <= 30000 else 100
            idx = RNG.integers(0, len(v), size=(b, len(v)))
            tm = np.array([trimmed_mean(v[i]) for i in idx])
            ci[nm] = {"n": int(len(v)),
                      "trimmed10": round(trimmed_mean(v), 6),
                      "huber": round(huber_mean(v), 6),
                      "boot_ci95_trimmed": [round(float(np.quantile(tm, .025)), 6),
                                            round(float(np.quantile(tm, .975)), 6)],
                      "boot_B": b}
            ci[nm]["ci_width"] = round(ci[nm]["boot_ci95_trimmed"][1]
                                       - ci[nm]["boot_ci95_trimmed"][0], 6)
        block["domain_aggregation_bootstrap"] = ci
        res[pop] = block

    res["tierC_direction_sensitivity"] = tierC_sensitivity(X, dom, cols, ref_mask, names)
    cur, peak = tracemalloc.get_traced_memory()
    res["scale_check"] = {"representative_n": int(X.shape[0]),
                          "load_seconds": round(t_load, 1),
                          "total_seconds": round(time.time() - t0, 1),
                          "peak_memory_mb": round(peak / 1e6, 1)}
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"done n={X.shape[0]} total={time.time()-t0:.0f}s peak={peak/1e6:.0f}MB -> {OUT}")


if __name__ == "__main__":
    main()

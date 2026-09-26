"""裁定 1 选项 B 授权的两项补算。均不改动主结论，也不改 R4/R6 的 FAIL 判定。

B-1  R6 的 M1_pooled @ test_1B 一格，把自助次数由 B=400 提到 B=40000，并跨 8 个独立 RNG
     种子重复，判定「增量 95% 区间上界」的符号是真信号还是蒙特卡洛噪声。
     round1 该格上界 +1.5e-5、R6 重跑 -3.8e-6，点估计逐位一致 -0.00081873，n=64。
     **预先声明的读法**（执行前写定，不事后改）：
       - 若 B=40000 下 8 个种子的上界符号全部一致 -> 该格归类已定，按该符号表述；
       - 若仍出现符号分歧 -> 上界在蒙特卡洛精度内与零重合，表述为
         「无证据显示 Q 带来正增量；1B 尺度上区间上界在自助精度内与零不可区分，n=64」。
     两种情形都不改 R6 的 FAIL（预声明判据是 12 格全含 0，实测 11 格，不放宽）。

B-2  给 R4 的 base + 8 个变体补记域级点估计与自助区间（B=400，与 R1 同口径以便可比），
     回答「被推翻的 3 个变体中 c4 反超 arxiv 是否统计可分」。
     只补描述性证据，不改 R4 的预声明判据与 FAIL 状态。

输出 robustness/Q1/q1_supplementary_b1_b2.json
种子 20260924（B-1 另用 8 个显式种子）
"""
from __future__ import annotations

import json
import time

import numpy as np

import q1_common as C
import q1_quality_main as M1
from q1_mixture_baseline import build_Q_corpus, fit_no_intercept

OUT = C.ROOT / "robustness/Q1"
B1_SEEDS = [20260924, 1, 7, 42, 2026, 99, 12345, 777]
B1_GRID = [400, 4000, 40000]
B1_SCALE = "test_1B"
B1_SOURCE = ("M1_pooled", "q1_quality_M1.json", "pooled")
REVERSE_MOVES = ["rps_lines_ending_with_terminal_punctution_mark", "modernbert_cleanliness"]
DOMS_OF_INTEREST = ("arxiv", "c4", "commoncrawl")


# ----------------------------------------------------------------------- B-1
def b1_bootstrap_depth() -> dict:
    pcols, Ptr, lcols, Ltr = C.load_pair("train_1m")
    l2m = C.loss_to_mixture_index(pcols, lcols)
    ytr = C.make_target(Ptr, Ltr, l2m, "pweighted13")
    mapping = C.load_domain_mapping()

    j = json.loads((C.METRICS / B1_SOURCE[1]).read_text(encoding="utf-8"))
    dq = {d: v["huber"] for d, v in j["arms"][B1_SOURCE[2]]["domain"]["per_domain"].items()}

    # 与 R6 完全同口径地拟合 w_A / w_B
    Qc_tr, vtr, _ = build_Q_corpus(Ptr, pcols, dq, mapping)
    Pv, yv, Qv = Ptr[vtr], ytr[vtr], Qc_tr[vtr]
    w_A = fit_no_intercept(C.design(Pv, "main"), yv)
    w_B = fit_no_intercept(np.hstack([Pv, Qv[:, None]]), yv)

    pc, P, lc, L = C.load_pair(B1_SCALE)
    y = C.make_target(P, L, C.loss_to_mixture_index(pc, lc), "pweighted13")
    Qc, v, _ = build_Q_corpus(P, pc, dq, mapping)
    Pt, yt, Qt = P[v], y[v], Qc[v]
    AA, AB = C.design(Pt, "main"), np.hstack([Pt, Qt[:, None]])
    n = len(yt)
    point = (C.validate_by_scale(w_B, AB, yt)["r2_after_offset_removal"]
             - C.validate_by_scale(w_A, AA, yt)["r2_after_offset_removal"])

    grid = {}
    for b in B1_GRID:
        per_seed = {}
        for sd in B1_SEEDS:
            rng = np.random.default_rng(sd)
            d = np.empty(b)
            for t in range(b):
                s = rng.integers(0, n, n)
                d[t] = (C.validate_by_scale(w_B, AB[s], yt[s])["r2_after_offset_removal"]
                        - C.validate_by_scale(w_A, AA[s], yt[s])["r2_after_offset_removal"])
            lo, hi = (float(x) for x in np.quantile(d, [0.025, 0.975]))
            per_seed[f"seed_{sd}"] = {
                "ci95": [lo, hi], "upper_sign": "neg" if hi < 0 else "pos_or_zero",
                "contains_zero": bool(lo <= 0 <= hi)}
        uppers = [v["ci95"][1] for v in per_seed.values()]
        signs = {v["upper_sign"] for v in per_seed.values()}
        grid[f"B_{b}"] = {
            "per_seed": per_seed,
            "upper_bound_min": min(uppers), "upper_bound_max": max(uppers),
            "upper_bound_spread": max(uppers) - min(uppers),
            "upper_sign_unanimous": len(signs) == 1,
            "n_seeds_contains_zero": sum(v["contains_zero"] for v in per_seed.values()),
            "n_seeds": len(per_seed)}

    fin = grid[f"B_{B1_GRID[-1]}"]
    if fin["upper_sign_unanimous"]:
        verdict = ("upper_bound_sign_resolved_negative" if fin["upper_bound_max"] < 0
                   else "upper_bound_sign_resolved_nonnegative")
        wording = ("1B 尺度上增量区间整体位于零点下方（B=40000，8 个种子一致）；"
                   "方向与『Q 带来正增量』相反") if fin["upper_bound_max"] < 0 else \
                  "1B 尺度上区间含 0（B=40000，8 个种子一致）"
    else:
        verdict = "upper_bound_coincides_with_zero_within_mc_precision"
        wording = ("无证据显示 Q 带来正增量；1B 尺度上区间上界在自助精度内与零不可区分，n=64")
    return {
        "check_id": "B1_bootstrap_depth_at_1B",
        "purpose": "判定 R6 的 M1_pooled@test_1B 一格上界符号是真信号还是蒙特卡洛噪声",
        "authorized_by": "methods/Q1/q1_decisions.jsonl#q1_result_verdict (choice B)",
        "does_not_relax_predeclared_criterion": (
            "R6 的预声明判据是 12 格全含 0，实测 11 格 -> FAIL 不变。本项只定这一格的事实。"),
        "point_estimate": point, "n_used": n,
        "round1_reported_ci_upper": 1.5e-5,
        "r6_rerun_ci_upper": -3.831432666817703e-06,
        "predeclared_reading_rule": (
            "B=40000 下 8 种子上界符号全一致 -> 按该符号表述；否则表述为上界在自助精度内与零重合"),
        "grid": grid,
        "verdict": verdict,
        "resulting_wording_for_paper": wording,
    }


# ----------------------------------------------------------------------- B-2
def b2_r4_margins(U, cols, dom, names, v_idx, p_idx) -> dict:
    def tbl_for(nv, np_):
        q = M1.gated(U, np.ones(U.shape[1]), nv, np_)
        rng = np.random.default_rng(C.SEED)
        t = {}
        for d, nm in enumerate(names):
            vals = q[dom == d]
            lo, hi, hw = C.boot_ci(vals, C.huber_mean, rng)
            t[nm] = {"n": int(len(vals)), "point": float(C.huber_mean(vals)),
                     "ci95_lo": lo, "ci95_hi": hi, "half_width": hw}
        return t

    def pair_gap(t, a, b):
        """返回 (点差, 半宽和, 倍数, 是否可分)。点差为正表示 a 高于 b。"""
        gap = t[a]["point"] - t[b]["point"]
        hw = t[a]["half_width"] + t[b]["half_width"]
        return {"higher": a if gap > 0 else b, "abs_gap": abs(gap),
                "half_width_sum": hw, "ratio": abs(gap) / hw if hw > 0 else float("inf"),
                "distinguishable": bool(abs(gap) > hw)}

    configs = [("base", v_idx, p_idx)]
    for j in p_idx:
        configs.append((f"P_to_V:{cols[j]}", sorted(v_idx + [j]), [k for k in p_idx if k != j]))
    for c in REVERSE_MOVES:
        j = cols.index(c)
        configs.append((f"V_to_P:{c}", [k for k in v_idx if k != j], sorted(p_idx + [j])))

    obs = {}
    for tag, nv, np_ in configs:
        t = tbl_for(nv, np_)
        order = sorted(names, key=lambda n: -t[n]["point"])
        obs[tag] = {
            "order": order,
            "top3": order[:3],
            "arxiv_rank": order.index("arxiv") + 1,
            "per_domain": {k: t[k] for k in DOMS_OF_INTEREST},
            "pair_arxiv_vs_c4": pair_gap(t, "arxiv", "c4"),
            "pair_c4_vs_commoncrawl": pair_gap(t, "c4", "commoncrawl"),
        }

    breakers = [k for k, v in obs.items() if k != "base" and v["arxiv_rank"] != 1]
    resolved = {k: obs[k]["pair_arxiv_vs_c4"]["distinguishable"] for k in breakers}
    return {
        "check_id": "B2_r4_variant_margins",
        "purpose": "回答『被推翻的 3 个变体中 c4 反超 arxiv 是否统计可分』",
        "authorized_by": "methods/Q1/q1_decisions.jsonl#q1_result_verdict (choice B)",
        "does_not_change_r4": "R4 的预声明判据（claim 保持）与 FAIL 状态不变；本项只补描述性证据",
        "bootstrap": f"B={C.B_BOOT}，Huber，与 R1 同口径以便可比",
        "observed": obs,
        "summary": {
            "breaking_variants": breakers,
            "c4_over_arxiv_statistically_distinguishable": resolved,
            "top3_set_invariant": len({frozenset(v["top3"]) for v in obs.values()}) == 1,
            "top3_set": sorted(obs["base"]["top3"]),
        },
    }


def main() -> None:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    print("B-1 开始（配比侧，n=64，B 网格 400/4000/40000 × 8 种子）...", flush=True)
    b1 = b1_bootstrap_depth()
    print(f"  B-1 完成 {time.time()-t0:.1f}s | verdict={b1['verdict']}", flush=True)

    t1 = time.time()
    print("B-2 开始（质量侧，载入全量 272k 行约 60 s）...", flush=True)
    arms, cols, dom, names, meta = C.load_quality(populations=("pooled",))
    v_idx, p_idx = C.vp_split(cols)
    b2 = b2_r4_margins(arms["pooled"], cols, dom, names, v_idx, p_idx)
    print(f"  B-2 完成 {time.time()-t1:.1f}s", flush=True)

    res = {"schema_version": 1, "question": "Q1", "round_under_test": C.ROUND,
           "seed": C.SEED, "rigor_profile": "lean",
           "authorized_by": "methods/Q1/q1_decisions.jsonl#q1_result_verdict (choice B)",
           "scope": "裁定 1 选项 B 的两项补算；不改动主结论，不改 R4/R6 的 FAIL 判定",
           "checks": {b1["check_id"]: b1, b2["check_id"]: b2},
           "execution_time_seconds": round(time.time() - t0, 1)}
    C.write_json(OUT / "q1_supplementary_b1_b2.json", res)

    print()
    print("=" * 72)
    print("B-1 结论:", b1["verdict"])
    print("  点估计", f"{b1['point_estimate']:+.8f}", "| n =", b1["n_used"])
    for k, g in b1["grid"].items():
        print(f"  {k:9s} 上界 [{g['upper_bound_min']:+.3e}, {g['upper_bound_max']:+.3e}]"
              f" 极差 {g['upper_bound_spread']:.3e}"
              f" | 符号一致 {g['upper_sign_unanimous']}"
              f" | 含0 {g['n_seeds_contains_zero']}/{g['n_seeds']}")
    print("  论文表述:", b1["resulting_wording_for_paper"])
    print()
    print("B-2 结论:")
    s = b2["summary"]
    print("  top3 集合不变:", s["top3_set_invariant"], s["top3_set"])
    print("  破 arxiv 居首的变体:", s["breaking_variants"])
    for k, v in b2["observed"].items():
        p = v["pair_arxiv_vs_c4"]
        print(f"    {k:52s} arxiv#{v['arxiv_rank']} | 高者 {p['higher']:6s}"
              f" 差 {p['abs_gap']:.5f} 半宽和 {p['half_width_sum']:.5f}"
              f" ({p['ratio']:.2f}x) 可分 {p['distinguishable']}")
    print("=" * 72)
    print("输出 robustness/Q1/q1_supplementary_b1_b2.json")


if __name__ == "__main__":
    main()

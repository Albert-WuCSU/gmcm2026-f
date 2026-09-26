"""Q1 稳健性检查（配比侧）—— R6、R7。

判据在执行前声明，由既有结论的适用范围导出。

| 检查 | 承重声明 | 预声明判据 |
| R6 | 「Q 增量为零结果」只用过一个 Q 源（M1 pooled Huber） | 全部 Q 源下三尺度增量区间均含 0 |
| R7 | 目标口径 pweighted13 有部分循环（AMB-Q1-2），仅比过训练 R² | mean13 下 M0c 系数符号一致率 >=0.8 且三尺度去偏 R² 仍为正 |

R6 是三条「必须带走的结论」中最脆的一条：零结果要作为对题目「是否引入 Q 由参赛队伍
论证」的有证据回答写入论文，但其证据此前只有单一 Q 源。

输出 robustness/Q1/q1_robustness_mixture.json
种子 20260924
"""
from __future__ import annotations

import json
import time

import numpy as np

import q1_common as C
from q1_mixture_baseline import build_Q_corpus, fit_no_intercept

OUT = C.ROOT / "robustness/Q1"
SCALES = ("test_1m", "test_60m", "test_1B")

# Q 源：(标签, 指标文件, 归一化臂)。原始 round1 用的是 M1/pooled
Q_SOURCES = [("M1_pooled", "q1_quality_M1.json", "pooled"),
             ("M0_pooled", "q1_quality_M0.json", "pooled"),
             ("M1_per_domain", "q1_quality_M1.json", "per_domain"),
             ("M0_per_domain", "q1_quality_M0.json", "per_domain")]

SIGN_AGREE_MIN_R7 = 0.8


def domain_Q_from(metrics_file: str, arm: str) -> dict[str, float]:
    j = json.loads((C.METRICS / metrics_file).read_text(encoding="utf-8"))
    return {d: v["huber"] for d, v in j["arms"][arm]["domain"]["per_domain"].items()}


def increment_for_source(domain_Q: dict, mapping: dict, Ptr, ytr, pcols) -> dict:
    """与 q1_mixture_baseline 的嵌套检验同口径，只换 Q 源。"""
    rng = np.random.default_rng(C.SEED)
    Qc_tr, vtr, info = build_Q_corpus(Ptr, pcols, domain_Q, mapping)
    Pv, yv, Qv = Ptr[vtr], ytr[vtr], Qc_tr[vtr]
    A_A = C.design(Pv, "main")
    A_B = np.hstack([Pv, Qv[:, None]])
    w_A, w_B = fit_no_intercept(A_A, yv), fit_no_intercept(A_B, yv)
    out = {"domain_Q_used": domain_Q,
           "mapped_mass_median": info["mapped_mass_median"],
           "n_train_used": int(vtr.sum()),
           "train_r2_A": C.r2(yv, A_A @ w_A), "train_r2_B": C.r2(yv, A_B @ w_B),
           "by_scale": {}}
    for key in SCALES:
        pc, P, lc, L = C.load_pair(key)
        y = C.make_target(P, L, C.loss_to_mixture_index(pc, lc), "pweighted13")
        Qc, v, _ = build_Q_corpus(P, pc, domain_Q, mapping)
        Pt, yt, Qt = P[v], y[v], Qc[v]
        AA, AB = C.design(Pt, "main"), np.hstack([Pt, Qt[:, None]])
        vA = C.validate_by_scale(w_A, AA, yt)
        vB = C.validate_by_scale(w_B, AB, yt)
        n = len(yt)
        d = np.empty(C.B_BOOT)
        for t in range(C.B_BOOT):
            s = rng.integers(0, n, n)
            d[t] = (C.validate_by_scale(w_B, AB[s], yt[s])["r2_after_offset_removal"]
                    - C.validate_by_scale(w_A, AA[s], yt[s])["r2_after_offset_removal"])
        lo, hi = np.quantile(d, [0.025, 0.975])
        out["by_scale"][key] = {
            "n_used": n,
            "p_only_r2_deoffset": vA["r2_after_offset_removal"],
            "p_plus_Q_r2_deoffset": vB["r2_after_offset_removal"],
            "increment": vB["r2_after_offset_removal"] - vA["r2_after_offset_removal"],
            "increment_ci95": [float(lo), float(hi)],
            "ci_contains_zero": bool(lo <= 0 <= hi),
            "significant": bool(lo > 0 or hi < 0)}
    return out


# --------------------------------------------------------------------- R6
def r6_q_source_swap(Ptr, ytr, pcols) -> dict:
    mapping = C.load_domain_mapping()
    obs, ok = {}, True
    for tag, f, arm in Q_SOURCES:
        dq = domain_Q_from(f, arm)
        r = increment_for_source(dq, mapping, Ptr, ytr, pcols)
        r["q_range_across_domains"] = float(max(dq.values()) - min(dq.values()))
        obs[tag] = r
        ok = ok and all(v["ci_contains_zero"] for v in r["by_scale"].values())
    return {
        "check_id": "R6_q_source_swap",
        "tested_claim": ("『17 维 p 加入域级 Q_corpus 后三尺度增量的 95% 区间均含 0』"
                         "不依赖 Q 的来源方法与归一化臂"),
        "why_load_bearing": ("该零结果要作为对题目『是否以及如何引入质量评分 Q 由参赛队伍论证』"
                            "的有证据回答写入论文，但 round1 只用了 M1 pooled Huber 一个 Q 源；"
                            "若换源后出现显著增量，则论文结论须改写"),
        "sources": ["results/Q1/experiments/round1/metrics/q1_mixture_M0c.json#q_increment_test",
                    "results/Q1/experiments/round1/metrics/q1_quality_M0.json",
                    "results/Q1/experiments/round1/metrics/q1_quality_M1.json"],
        "perturbation": ("域级 Q 的来源 ∈ {M1,M0} × {pooled, per_domain}，"
                         "其余口径（目标 pweighted13、同子集拟合、B=400）不变"),
        "predeclared_criterion": "全部 4 个 Q 源下，三个尺度的增量 95% 区间均含 0",
        "observed": obs,
        "status": "PASS" if ok else "FAIL",
        "limitation": ("per_domain 臂的域级 Q 近乎恒等（极差约 0.003/0.012），"
                       "其零增量部分是恒等输入的必然结果，不构成独立证据；"
                       "构造性相关（Q_corpus 由 6/17 映射域的 p 加权而成）在所有源下同样存在"),
        "fallback_relevance": "不涉及 M2 触发条件",
    }


# --------------------------------------------------------------------- R7
def r7_target_definition(Ptr, Ltr, l2m, pcols) -> dict:
    """目标口径替换。pweighted13 把 p 置于等式两侧（AMB-Q1-2），此前只比过训练 R²。"""
    A_tr = C.design(Ptr, "main")
    obs = {}
    for kind in ("pweighted13", "mean13"):
        y = C.make_target(Ptr, Ltr, l2m, kind)
        w = fit_no_intercept(A_tr, y)
        val = {}
        for key in SCALES:
            pc, P, lc, L = C.load_pair(key)
            yt = C.make_target(P, L, C.loss_to_mixture_index(pc, lc), kind)
            val[key] = C.validate_by_scale(w, C.design(P, "main"), yt)
        st = C.coef_stability(A_tr, y, 0.0, np.random.default_rng(C.SEED))
        obs[kind] = {
            "train_r2": C.r2(y, A_tr @ w),
            "coef": {pcols[j]: w[j] for j in range(len(pcols))},
            "frac_coefs_sign_stable_ge_0.95": st["frac_coefs_sign_stable_ge_0.95"],
            "mean_relative_se": st["mean_relative_se"],
            "validation_by_scale": {k: {"r2_after_offset_removal": v["r2_after_offset_removal"],
                                       "spearman": v["spearman"],
                                       "bias_share_of_rmse": v["bias_share_of_rmse"]}
                                    for k, v in val.items()}}
    wp = np.array([obs["pweighted13"]["coef"][c] for c in pcols])
    wm = np.array([obs["mean13"]["coef"][c] for c in pcols])
    agree = float(np.mean(np.sign(wp) == np.sign(wm)))
    pos = all(v["r2_after_offset_removal"] > 0
              for v in obs["mean13"]["validation_by_scale"].values())
    obs["comparison"] = {
        "coef_sign_agreement": agree,
        "n_coefs": len(pcols),
        "n_sign_flipped": int(np.sum(np.sign(wp) != np.sign(wm))),
        "flipped_domains": [pcols[j] for j in range(len(pcols))
                            if np.sign(wp[j]) != np.sign(wm[j])],
        "spearman_between_coef_vectors": C.spearman(wp, wm),
        "mean13_all_scales_r2_positive": bool(pos)}
    ok = agree >= SIGN_AGREE_MIN_R7 and pos
    return {
        "check_id": "R7_target_definition_swap",
        "tested_claim": ("M0c 的 17 个系数所表达的域效应方向，不是目标口径 pweighted13 "
                         "的部分循环所造出来的"),
        "why_load_bearing": ("AMB-Q1-2：pweighted13 把 p 同时置于等式两侧，须在论文声明；"
                            "round1 只比了训练 R²（0.896 vs 0.296），未检验系数方向与跨尺度表现"),
        "sources": ["results/Q1/experiments/round1/metrics/q1_mixture_M0c.json"
                    "#target_comparison_mean13",
                    "code/Q1/q1_common.py#make_target"],
        "perturbation": "目标变量由 pweighted13 换为 mean13（13 域简单均值），其余不变",
        "predeclared_criterion": (f"两口径的系数符号一致率 >= {SIGN_AGREE_MIN_R7}，"
                                  "且 mean13 下三尺度去偏 R² 仍全为正"),
        "observed": obs,
        "status": "PASS" if ok else "FAIL",
        "limitation": ("mean13 不含配比权重，故其自身不是可主报的目标（训练 R² 仅 0.296）；"
                       "本检查只用它作方向一致性的独立对照，不作为替代主报口径"),
        "fallback_relevance": "不涉及 M2 触发条件",
    }


def main() -> None:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    pcols, Ptr, lcols, Ltr = C.load_pair("train_1m")
    l2m = C.loss_to_mixture_index(pcols, lcols)
    assert sum(x is not None for x in l2m) == 13, "Loss 列应 13/13 匹配"
    ytr = C.make_target(Ptr, Ltr, l2m, "pweighted13")

    checks = [r6_q_source_swap(Ptr, ytr, pcols),
              r7_target_definition(Ptr, Ltr, l2m, pcols)]

    res = {"schema_version": 1, "question": "Q1", "side": "mixture",
           "round_under_test": C.ROUND, "seed": C.SEED,
           "n_train_rows": int(Ptr.shape[0]),
           "criteria_predeclared_before_execution": True,
           "checks": {c["check_id"]: c for c in checks},
           "execution_time_seconds": round(time.time() - t0, 1)}
    C.write_json(OUT / "q1_robustness_mixture.json", res)

    print(f"配比侧稳健性完成 {res['execution_time_seconds']}s")
    for c in checks:
        print(f"  {c['check_id']}: {c['status']}")
    print("  R6 各 Q 源的三尺度增量:")
    for tag, r in res["checks"]["R6_q_source_swap"]["observed"].items():
        parts = [f"{k.replace('test_','')} {v['increment']:+.5f}"
                 f"[{v['increment_ci95'][0]:+.5f},{v['increment_ci95'][1]:+.5f}]"
                 f"{'含0' if v['ci_contains_zero'] else '**不含0**'}"
                 for k, v in r["by_scale"].items()]
        print(f"    {tag:14s} Q极差 {r['q_range_across_domains']:.4f} | " + " | ".join(parts))
    cmp_ = res["checks"]["R7_target_definition_swap"]["observed"]["comparison"]
    print(f"  R7 系数符号一致率 {cmp_['coef_sign_agreement']:.4f} "
          f"（翻转 {cmp_['n_sign_flipped']}/{cmp_['n_coefs']}: {cmp_['flipped_domains']}）"
          f" | 系数向量 Spearman {cmp_['spearman_between_coef_vectors']:.4f}"
          f" | mean13 三尺度 R² 全正={cmp_['mean13_all_scales_r2_positive']}")


if __name__ == "__main__":
    main()

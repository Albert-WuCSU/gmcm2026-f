"""Q1 稳健性检查（质量侧）—— R1..R5。

对应 AGENTS.md 的 robustness-checker 契约：按承重假设选检查，不凑清单。
**判据一律在看到结果前声明，且由既有人工决策的 claim scope 导出，不事后发明。**

| 检查 | 承重声明 | 预声明判据 |
| R1 | 域序（域级聚合估计量是自由参数，方法卡只声明 Huber 主报 / 截尾对照） | 三项 claim 判据保持 |
| R2 | 可分辨 21/21 与扰动 τ 全部出自单一种子 | 同种子下 M1 可分辨对数 >= M0 |
| R3 | M1>M0 仅在 ±10% 一个幅度上验证过 | ±20% 下 τ 差区间不含 0 |
| R4 | V/P 语义分组无相关内聚性（M1 唯一无数据支撑的假设） | 域序判据保持 且 CD2 率仍在 (0.01,0.50) |
| R5 | 「book 区间宽是 n 导致」从未做等 n 对照 | book 半宽落入大域降采样分布内 |

claim 判据的来源：决策 q1a_book_wikipedia_claim_scope 已裁定 book~wikipedia 统计上不可
区分、方向可变，故**二者互换不计为失败**；c4~commoncrawl 裕度 4.4 倍、照常报方向，故计入。
CD2 的 (0.01,0.50) 是 methods/Q1/q1_method_card.md 记录的 M2 fallback 触发区间。

输出 robustness/Q1/q1_robustness_quality.json
种子 20260924（R2 另用 5 个显式种子）
"""
from __future__ import annotations

import time

import numpy as np

import q1_common as C
import q1_quality_main as M1

OUT = C.ROOT / "robustness/Q1"

# 主实验已报的域序（results/Q1/experiments/round1/run_summary.json）
REPORTED_ORDER = {
    "M0": ["arxiv", "c4", "commoncrawl", "stackexchange", "wikipedia", "book", "github"],
    "M1": ["arxiv", "c4", "commoncrawl", "stackexchange", "book", "wikipedia", "github"],
}
SEEDS_R2 = [20260924, 1, 7, 42, 2026]
AMPLITUDES_R3 = [0.20, 0.30]
EQN_R5 = 171          # book 的样本量
EQN_REPS_R5 = 40
FALLBACK_BAND = (0.01, 0.50)

ESTIMATORS = {
    "huber": C.huber_mean,                        # 主报
    "trimmed10": C.trimmed_mean,                  # 方法卡已列为对照
    "median": lambda v: float(np.median(v)),
    "mean": lambda v: float(np.mean(v)),
}


# ------------------------------------------------------------------ 判据
def claim_components(order: list[str]) -> dict:
    """三项 claim 判据。book~wikipedia 互换不计为失败（已由决策裁定为不可区分）。"""
    ok_arxiv = order[0] == "arxiv"
    ok_github = order[-1] == "github"
    ok_c4 = order.index("c4") < order.index("commoncrawl")
    return {"arxiv_rank1": bool(ok_arxiv), "github_rank_last": bool(ok_github),
            "c4_above_commoncrawl": bool(ok_c4),
            "all_hold": bool(ok_arxiv and ok_github and ok_c4),
            "order": order,
            "book_wikipedia_swapped_vs_reported": None}


def tau_vs(order_a: list[str], order_b: list[str]) -> float:
    """两个域序的 Kendall tau（按名次向量计算，与 C.kendall_tau 同口径）。"""
    names = sorted(order_a)
    ra = [order_a.index(n) for n in names]
    rb = [order_b.index(n) for n in names]
    return C.kendall_tau(ra, rb)


def order_by(q: np.ndarray, dom: np.ndarray, names: list[str], est) -> tuple[list[str], float]:
    v = np.array([est(q[dom == d]) for d in range(len(names))])
    return [names[i] for i in np.argsort(-v)], float(v.max() - v.min())


def combines(cols: list[str], v_idx: list[int], p_idx: list[int]) -> dict:
    """两方法的合成函数，签名统一为 (U, w) -> q。"""
    return {"M0": lambda U, w: U @ (w / w.sum()),
            "M1": lambda U, w: M1.gated(U, w, v_idx, p_idx)}


# --------------------------------------------------------------------- R1
def r1_estimator_swap(qs: dict, dom: np.ndarray, names: list[str]) -> dict:
    """域级聚合估计量替换。域序与可分辨对数同报（后者是 Q1a 的预声明比较指标）。"""
    obs = {}
    for mid, q in qs.items():
        per_est = {}
        for ename, est in ESTIMATORS.items():
            rng = np.random.default_rng(C.SEED)     # 每个估计量用同一种子，差异只来自估计量
            tbl = {}
            for d, nm in enumerate(names):
                v = q[dom == d]
                lo, hi, hw = C.boot_ci(v, est, rng)
                tbl[nm] = {"n": int(len(v)), "point": float(est(v)),
                           "ci95_lo": lo, "ci95_hi": hi, "half_width": hw}
            pts = np.array([tbl[n]["point"] for n in names])
            order = [names[i] for i in np.argsort(-pts)]
            dist = C.distinguishable_pairs({"per_domain": tbl}, names)
            cc = claim_components(order)
            cc["book_wikipedia_swapped_vs_reported"] = bool(
                (order.index("book") < order.index("wikipedia"))
                != (REPORTED_ORDER[mid].index("book") < REPORTED_ORDER[mid].index("wikipedia")))
            per_est[ename] = {
                "claim": cc, "domain_range": float(pts.max() - pts.min()),
                "tau_vs_reported_order": tau_vs(order, REPORTED_ORDER[mid]),
                "n_pairs_distinguishable": dist["n_pairs_distinguishable"],
                "tied_pairs": dist["tied_pairs"],
                "point_by_domain": {n: tbl[n]["point"] for n in names},
                "half_width_by_domain": {n: tbl[n]["half_width"] for n in names}}
        obs[mid] = per_est
    m1_all = all(v["claim"]["all_hold"] for v in obs["M1"].values())
    return {
        "check_id": "R1_domain_aggregator_swap",
        "tested_claim": ("Q1a 报告的域序（arxiv 最高、github 最低、c4>commoncrawl）"
                         "不依赖域级聚合估计量的选择"),
        "why_load_bearing": ("方法卡只声明 Huber 主报 + 10% 截尾对照，估计量是未被检验的自由参数；"
                            "域序是 Q1a 的必交产出，也是 Q2 的输入"),
        "sources": ["results/Q1/experiments/round1/metrics/q1_quality_M0.json",
                    "results/Q1/experiments/round1/metrics/q1_quality_M1.json",
                    "code/Q1/q1_common.py#huber_mean,trimmed_mean,boot_ci"],
        "perturbation": "域级聚合估计量 ∈ {Huber(k=1.345), 10% 截尾均值, 中位数, 算术均值}",
        "predeclared_criterion": ("M1 在全部 4 个估计量下 arxiv 居首 ∧ github 居末 ∧ "
                                  "c4 优于 commoncrawl；book~wikipedia 互换不计为失败"
                                  "（决策 q1a_book_wikipedia_claim_scope 已裁定其不可区分）"),
        "observed": obs,
        "status": "PASS" if m1_all else "FAIL",
        "limitation": ("可分辨对数随估计量变化属预期（区间宽度依估计量而变），"
                       "本检查只以 claim 判据判定，不把可分辨对数的变化计为失败"),
        "fallback_relevance": "不涉及 M2 触发条件",
    }


# --------------------------------------------------------------------- R2
def r2_seed_stability(U: np.ndarray, dom: np.ndarray, names: list[str],
                      comb: dict) -> dict:
    """种子替换。主实验的 21/21 与扰动 τ 全部出自单一种子 20260924。"""
    obs, ok = {}, True
    for sd in SEEDS_R2:
        per_m = {}
        for mid, fn in comb.items():
            q = fn(U, np.ones(U.shape[1]))
            dt = C.domain_table(q, dom, names, np.random.default_rng(sd))
            dist = C.distinguishable_pairs(dt, names)
            pert = C.perturb_weights(U, dom, names, fn, np.random.default_rng(sd))
            per_m[mid] = {
                "n_pairs_distinguishable": dist["n_pairs_distinguishable"],
                "tied_pairs": dist["tied_pairs"],
                "domain_range": dt["domain_range"],
                "claim": claim_components(dt["order_best_to_worst"]),
                "kendall_tau_mean": pert["domain_rank_kendall_tau_mean"],
                "kendall_tau_min": pert["domain_rank_kendall_tau_min"],
                "frac_order_unchanged": pert["frac_reps_domain_order_unchanged"]}
        ge = per_m["M1"]["n_pairs_distinguishable"] >= per_m["M0"]["n_pairs_distinguishable"]
        per_m["M1_ge_M0_distinguishable"] = bool(ge)
        ok = ok and ge and per_m["M1"]["claim"]["all_hold"]
        obs[f"seed_{sd}"] = per_m
    return {
        "check_id": "R2_seed_stability",
        "tested_claim": "M1 可分辨 21/21 与扰动 τ=0.9976 不是单一种子的产物",
        "why_load_bearing": ("round1 的 bootstrap 区间、权重扰动、自助显著性全部只用了种子 "
                            "20260924；HD-2 的显著性判定依赖重抽样，种子敏感则判定本身不可靠"),
        "sources": ["results/Q1/experiments/round1/run_summary.json",
                    "code/Q1/q1_common.py#boot_ci,perturb_weights"],
        "perturbation": f"bootstrap 与扰动的随机种子 ∈ {SEEDS_R2}（B=400、reps=40 不变）",
        "predeclared_criterion": ("每个种子下 M1 的可分辨域对数 >= M0 的，"
                                  "且 M1 的三项 claim 判据保持"),
        "observed": obs,
        "status": "PASS" if ok else "FAIL",
        "limitation": "只换种子，未换 B 与 reps；区间宽度本身的蒙特卡洛误差未单独量化",
        "fallback_relevance": "不涉及 M2 触发条件",
    }


# --------------------------------------------------------------------- R3
def r3_amplitude(U: np.ndarray, dom: np.ndarray, names: list[str], comb: dict) -> dict:
    """扰动幅度阶梯。M1>M0 此前只在 ±10% 一个幅度上验证过。"""
    obs = {}
    for amp in AMPLITUDES_R3:
        rng = np.random.default_rng(C.SEED)
        per_m = {mid: C.perturb_weights(U, dom, names, fn, rng, frac=amp)
                 for mid, fn in comb.items()}
        d = C.diff_ci(per_m["M1"]["tau_per_rep"], per_m["M0"]["tau_per_rep"],
                      np.random.default_rng(C.SEED))
        obs[f"pm{int(amp * 100)}pct"] = {
            "M0": {k: v for k, v in per_m["M0"].items() if not k.endswith("_per_rep")},
            "M1": {k: v for k, v in per_m["M1"].items() if not k.endswith("_per_rep")},
            "tau_diff_M1_minus_M0": d,
            "role": "confirmatory" if amp == 0.20 else "exploratory"}
    ok = obs["pm20pct"]["tau_diff_M1_minus_M0"]["significant"] and \
        obs["pm20pct"]["tau_diff_M1_minus_M0"]["direction"] == "a>b"
    return {
        "check_id": "R3_perturbation_amplitude",
        "tested_claim": "M1 在排序稳定性上超过 M0，不只在 ±10% 这一个扰动幅度上成立",
        "why_load_bearing": ("HD-2 要求超出幅度大于重抽样噪声；±10% 是唯一测过的幅度，"
                            "若优势随幅度消失则该结论的适用范围须收窄"),
        "sources": ["results/Q1/experiments/round1/run_summary.json"
                    "#comparison.quality_side.significance_tests"],
        "perturbation": "列权重 uniform ±20%（确认性）与 ±30%（探索性），reps=40",
        "predeclared_criterion": ("±20% 下 τ(M1)−τ(M0) 的自助 95% 区间不含 0 且方向为 M1>M0；"
                                  "±30% 仅作探索性报告，不参与判定"),
        "observed": obs,
        "status": "PASS" if ok else "FAIL",
        "limitation": ("±30% 已超出「小扰动」的合理范围，故预先标为探索性；"
                       "均匀分布扰动不覆盖结构化的权重误指定"),
        "fallback_relevance": "不涉及 M2 触发条件",
    }


# --------------------------------------------------------------------- R4
# 反向移组候选：语义上可被论证为「整洁度/格式」类，其补集可读作污染
REVERSE_MOVES = ["rps_lines_ending_with_terminal_punctution_mark", "modernbert_cleanliness"]


def _cd2(V: np.ndarray, P: np.ndarray) -> float:
    return float(np.mean((V > np.quantile(V, 0.75)) & (P > np.quantile(P, 0.75))))


def r4_vp_regroup(U: np.ndarray, cols: list[str], dom: np.ndarray, names: list[str],
                  v_idx: list[int], p_idx: list[int]) -> dict:
    """V/P 分组扰动。分组无相关内聚性（组内 0.051/0.026 vs 组间 0.016），是 M1 唯一无数据支撑的假设。"""
    base_V, base_P = M1.vp_parts(U, v_idx, p_idx)
    obs = {"base": {"claim": claim_components(order_by(
        M1.gated(U, np.ones(U.shape[1]), v_idx, p_idx), dom, names, C.huber_mean)[0]),
        "cd2_p75": _cd2(base_V, base_P), "n_value": len(v_idx), "n_pollution": len(p_idx)}}
    variants, ok = {}, True
    moves = [("P_to_V", cols[j], j) for j in p_idx] + \
            [("V_to_P", c, cols.index(c)) for c in REVERSE_MOVES]
    for kind, cname, j in moves:
        if kind == "P_to_V":
            nv, np_ = sorted(v_idx + [j]), [k for k in p_idx if k != j]
        else:
            nv, np_ = [k for k in v_idx if k != j], sorted(p_idx + [j])
        q = M1.gated(U, np.ones(U.shape[1]), nv, np_)
        Vv, Pv = M1.vp_parts(U, nv, np_)
        order, rng_ = order_by(q, dom, names, C.huber_mean)
        cc = claim_components(order)
        cd2 = _cd2(Vv, Pv)
        in_band = FALLBACK_BAND[0] < cd2 < FALLBACK_BAND[1]
        variants[f"{kind}:{cname}"] = {
            "claim": cc, "domain_range": rng_, "cd2_p75": cd2,
            "cd2_in_fallback_band": bool(in_band),
            "tau_vs_reported_order": tau_vs(order, REPORTED_ORDER["M1"]),
            "n_value": len(nv), "n_pollution": len(np_)}
        ok = ok and cc["all_hold"] and in_band
    obs["variants"] = variants
    return {
        "check_id": "R4_vp_regrouping",
        "tested_claim": ("域序与 CD2 冲突率不依赖 V/P 语义分组的单列归属"),
        "why_load_bearing": ("M1 的分组是纯语义划分，代码注释明确『不得声称由相关结构导出』"
                            "（组内 0.051/0.026 与组间 0.016 同量级）；"
                            "ad_en_margin 归入污染组尤其可争（其 margin 已是『不像广告』）"),
        "sources": ["code/Q1/q1_common.py#vp_split",
                    "workspace/code/scripts/q1_features.py#POLLUTION_COLS",
                    "results/Q1/experiments/round1/metrics/q1_quality_M1.json#group_cohesion"],
        "perturbation": ("污染组 6 列逐列移入价值组（留一）；"
                         f"另将 {REVERSE_MOVES} 由价值组移入污染组"),
        "predeclared_criterion": ("全部 8 个变体下三项 claim 判据保持，"
                                  f"且 CD2@p75 仍落在 M2 触发区间 {FALLBACK_BAND} 内"),
        "observed": obs,
        "status": "PASS" if ok else "FAIL",
        "limitation": ("只做单列移动，未穷举分组划分；CD1/CD3 不随分组变化故不列入"),
        "fallback_relevance": ("直接对应 M2 的触发条件 2（冲突率落到 (0.01,0.50) 之外）；"
                               "任一变体越界即须提交使用者决定是否激活 M2"),
    }


# --------------------------------------------------------------------- R5
def r5_equal_n(qs: dict, dom: np.ndarray, names: list[str]) -> dict:
    """等 n 对照。「book 区间宽是 n=171 导致」此前无对照，只是推断。"""
    obs = {}
    for mid, q in qs.items():
        rng = np.random.default_rng(C.SEED)
        bi = names.index("book")
        book_hw = C.boot_ci(q[dom == bi], C.huber_mean, rng)[2]
        sub = {}
        for d, nm in enumerate(names):
            if d == bi:
                continue
            pool = q[dom == d]
            hws = [C.boot_ci(pool[rng.choice(len(pool), EQN_R5, replace=False)],
                             C.huber_mean, rng)[2] for _ in range(EQN_REPS_R5)]
            sub[nm] = {"n_full": int(len(pool)), "hw_mean": float(np.mean(hws)),
                       "hw_min": float(np.min(hws)), "hw_max": float(np.max(hws))}
        lo = min(v["hw_min"] for v in sub.values())
        hi = max(v["hw_max"] for v in sub.values())
        obs[mid] = {"book_half_width_observed": book_hw, "book_n": EQN_R5,
                    "equal_n_subsample_half_width": sub,
                    "envelope": [lo, hi], "book_inside_envelope": bool(lo <= book_hw <= hi)}
    ok = all(v["book_inside_envelope"] for v in obs.values())
    return {
        "check_id": "R5_equal_n_interval_width",
        "tested_claim": "book 的 bootstrap 区间宽（github 的 29.6 倍）由 n=171 解释，而非 book 域本身异常",
        "why_load_bearing": ("该归因是『book~wikipedia 不可区分』与『book 域级 Q 供 Q2 时须标注不可靠』"
                            "两条结论的理由；若区间宽并非 n 所致，则须改归因为域内异质"),
        "sources": ["results/Q1/experiments/round1/tables/q1a_domain_quality.csv",
                    "workspace/data/data_report.md#F3"],
        "perturbation": f"其余 6 域各无放回降采样至 n={EQN_R5}，重复 {EQN_REPS_R5} 次后重算半宽",
        "predeclared_criterion": "book 的实测半宽落在等 n 降采样半宽的 [min, max] 包络内",
        "observed": obs,
        "status": "PASS" if ok else "FAIL",
        "limitation": ("包络是 6 域 × 40 次的经验极值，非正式检验；"
                       "落在包络内只说明 n 足以解释宽度，不排除同时存在域内异质"),
        "fallback_relevance": "不涉及 M2 触发条件",
    }


def main() -> None:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)

    # 只加载主口径：per_domain 消融臂已证域级 Q 近乎恒等（极差 0.003），不是备选主口径
    arms, cols, dom, names, meta = C.load_quality(populations=("pooled",))
    U = arms["pooled"]
    assert len(cols) == 20, f"canonical 应为 20 列，实得 {len(cols)}"
    v_idx, p_idx = C.vp_split(cols)
    comb = combines(cols, v_idx, p_idx)
    qs = {mid: fn(U, np.ones(U.shape[1])) for mid, fn in comb.items()}

    # R5 的等 n 对照要求其余域样本量 >= book
    ns = {nm: int((dom == d).sum()) for d, nm in enumerate(names)}
    assert min(v for k, v in ns.items() if k != "book") >= EQN_R5, f"等 n 对照不可行：{ns}"

    checks = [r1_estimator_swap(qs, dom, names),
              r2_seed_stability(U, dom, names, comb),
              r3_amplitude(U, dom, names, comb),
              r4_vp_regroup(U, cols, dom, names, v_idx, p_idx),
              r5_equal_n(qs, dom, names)]

    res = {"schema_version": 1, "question": "Q1", "side": "quality",
           "round_under_test": C.ROUND, "seed": C.SEED,
           "n_rows": int(meta["n_rows"]), "columns": cols,
           "domain_sample_sizes": ns,
           "population": "pooled+ecdf（主报口径）",
           "criteria_predeclared_before_execution": True,
           "checks": {c["check_id"]: c for c in checks},
           "execution_time_seconds": round(time.time() - t0, 1)}
    C.write_json(OUT / "q1_robustness_quality.json", res)

    print(f"质量侧稳健性完成 {res['execution_time_seconds']}s")
    for c in checks:
        print(f"  {c['check_id']}: {c['status']}")
    r1 = res["checks"]["R1_domain_aggregator_swap"]["observed"]["M1"]
    print("  R1 M1 各估计量域序:")
    for e, v in r1.items():
        print(f"    {e:10s} {' > '.join(v['claim']['order'])} | 可分辨 "
              f"{v['n_pairs_distinguishable']}/21 | claim {v['claim']['all_hold']}")
    r3 = res["checks"]["R3_perturbation_amplitude"]["observed"]
    for k, v in r3.items():
        d = v["tau_diff_M1_minus_M0"]
        print(f"  R3 {k}: tau差 {d['mean_diff']:+.4f} CI [{d['ci95'][0]:+.4f},"
              f"{d['ci95'][1]:+.4f}] 显著={d['significant']} ({v['role']})")
    r4 = res["checks"]["R4_vp_regrouping"]["observed"]
    print(f"  R4 base CD2 {r4['base']['cd2_p75']:.4f}；变体:")
    for k, v in r4["variants"].items():
        print(f"    {k:55s} CD2 {v['cd2_p75']:.4f} band={v['cd2_in_fallback_band']} "
              f"claim={v['claim']['all_hold']}")
    r5 = res["checks"]["R5_equal_n_interval_width"]["observed"]["M1"]
    print(f"  R5 M1 book 半宽 {r5['book_half_width_observed']:.5f} | 等n包络 "
          f"[{r5['envelope'][0]:.5f}, {r5['envelope'][1]:.5f}] | 内={r5['book_inside_envelope']}")


if __name__ == "__main__":
    main()

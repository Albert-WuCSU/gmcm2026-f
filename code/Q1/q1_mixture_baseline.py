"""M0c — 配比侧 usable_baseline（HD-2=B 指定）。

方法：17 维配比 p 的线性回归，**显式去截距**；目标为配比加权 13 域 Loss（pweighted13）。
  不得依赖 Σp=1 的千分位舍入来辨识截距（cond 61 -> 4773，×78，该系数无实质解释）。
  同时记录「指定参照域」变体作等价性对照。

验证口径（硬性）：每个检验集同时报 原始 R²（对照，禁止单独引用）、
  **按尺度去常数偏移后的 R²（主报）**、**Spearman（主报）**，并给出 bias_share_of_rmse
  以说明原始 R² 为负的成因是水平平移。

est_10b/est_70b **仅作定性讨论**（GC5）：A12/A14 配比行与训练集重复率 1.0，
  不能检验配比泛化。

另含 Q1c 的 Q 增量嵌套检验：17 维 p vs 17 维 p + Q_corpus（决策 q1_normalization_population=A
  的附带要求；题目原文要求「是否以及如何引入质量评分 Q，由参赛队伍论证」）。

输出：tables/q1c_coefficients.csv、tables/q1c_validation_by_scale.csv、
      tables/q1c_q_increment_test.csv、metrics/q1_mixture_M0c.json
种子 20260924。
"""
from __future__ import annotations

import json
import time

import numpy as np

import q1_common as C

SCALES = ("test_1m", "test_60m", "test_1B")
EXTRAP = ("est_10b", "est_70b")


def fit_no_intercept(A: np.ndarray, y: np.ndarray) -> np.ndarray:
    w, *_ = np.linalg.lstsq(A, y, rcond=None)
    return w


def fit_reference_domain(P: np.ndarray, y: np.ndarray, ref: int) -> np.ndarray:
    """等价性对照：去掉参照域列 + 加截距。与去截距版在 Σp=1 下数学等价。"""
    keep = [j for j in range(P.shape[1]) if j != ref]
    A = np.hstack([np.ones((len(y), 1)), P[:, keep]])
    w, *_ = np.linalg.lstsq(A, y, rcond=None)
    return w


def build_Q_corpus(P: np.ndarray, pcols: list[str], domain_Q: dict[str, float],
                   mapping: dict[str, str]) -> tuple[np.ndarray, dict]:
    """语料级 Q = Σ_{i∈mapped} p_i·Q_i / Σ_{i∈mapped} p_i（6 域重归一化）。

    17 配方域中仅 6 个有质量域对应（11 个 inferred 全为 (none)）。
    """
    idx, qv = [], []
    for j, c in enumerate(pcols):
        dom = c.removeprefix("train_the_pile_")
        if dom in mapping and mapping[dom] in domain_Q:
            idx.append(j)
            qv.append(domain_Q[mapping[dom]])
    idx = np.array(idx)
    qv = np.array(qv)
    w = P[:, idx]
    mass = w.sum(1)
    valid = mass > 1e-12
    Qc = np.where(valid, (w @ qv) / np.maximum(mass, 1e-12), np.nan)
    info = {"n_mapped_domains": int(len(idx)),
            "mapped": [pcols[j].removeprefix("train_the_pile_") for j in idx],
            "mapped_mass_median": float(np.median(mass)),
            "mapped_mass_min": float(mass.min()), "mapped_mass_max": float(mass.max()),
            "n_rows_with_zero_mapped_mass": int((~valid).sum()),
            "n_rows_total": int(len(mass)),
            "zero_mass_handling": ("该类行在 6 个映射域上配比质量全为 0，无任何质量信息；"
                                  "不作插补，嵌套检验限定在 mass>0 的同一子集上（A/B 同行，保持可比）")}
    return Qc, valid, info


def main() -> None:
    t0 = time.time()
    C.ensure_dirs()
    rng = np.random.default_rng(C.SEED)

    pcols, Ptr, lcols, Ltr = C.load_pair("train_1m")
    l2m = C.loss_to_mixture_index(pcols, lcols)
    assert sum(x is not None for x in l2m) == 13, "Loss 列应 13/13 匹配"
    ytr = C.make_target(Ptr, Ltr, l2m, "pweighted13")

    res = {
        "schema_version": 1, "method_id": "M0c", "role": "usable_baseline",
        "subtasks": ["Q1c"], "seed": C.SEED,
        "definition": "17 维 p 线性回归，显式去截距；目标 pweighted13",
        "baseline_source": "HD-2=B 指定",
        "target_declaration": {
            "primary": "pweighted13",
            "circularity_warning": "该目标把 p 同时置于等式两侧，存在部分循环，须在论文声明（AMB-Q1-2）",
            "unit": "交叉熵 nats/token"},
        "mixture_domains": pcols, "loss_domains": lcols,
        "n_train_rows": int(Ptr.shape[0]),
    }

    # ---- 主拟合：显式去截距
    A_tr = C.design(Ptr, "main")
    w = fit_no_intercept(A_tr, ytr)
    res["train"] = {"r2": C.r2(ytr, A_tr @ w), "n": int(len(ytr))}

    # 单纯形共线性监测
    res["probe_monitors"] = {
        "simplex_induced_singularity": {
            "cond_main_17_no_intercept": float(np.linalg.cond(A_tr)),
            "cond_with_intercept_18": float(np.linalg.cond(np.hstack([np.ones((len(ytr), 1)), Ptr]))),
            "rowsum_max_deviation": float(np.abs(Ptr.sum(1) - 1).max()),
            "intercept_explicitly_removed": True},
    }

    # 等价性对照：指定参照域（取占比均值最大的域为参照）
    ref = int(np.argmax(Ptr.mean(0)))
    w_ref = fit_reference_domain(Ptr, ytr, ref)
    keep = [j for j in range(Ptr.shape[1]) if j != ref]
    A_ref_tr = np.hstack([np.ones((len(ytr), 1)), Ptr[:, keep]])
    res["reference_domain_variant"] = {
        "reference_domain": pcols[ref], "train_r2": C.r2(ytr, A_ref_tr @ w_ref),
        "note": "与去截距版在 Σp=1 下数学等价；列此以示不依赖千分位舍入"}

    # ---- 三尺度验证 + 外推（仅定性）
    val, extrap = {}, {}
    for key in SCALES:
        pc, P, lc, L = C.load_pair(key)
        y = C.make_target(P, L, C.loss_to_mixture_index(pc, lc), "pweighted13")
        val[key] = C.validate_by_scale(w, C.design(P, "main"), y)
    for key in EXTRAP:
        pc, P, lc, L = C.load_pair(key)
        y = C.make_target(P, L, C.loss_to_mixture_index(pc, lc), "pweighted13")
        extrap[key] = C.validate_by_scale(w, C.design(P, "main"), y)
        extrap[key]["qualitative_only"] = True
        extrap[key]["reason"] = "A12/A14 配比行与训练集重复率 1.0，只能检验 Loss 外推（GC5）"
    res["validation_by_scale"] = val
    res["extrapolation_qualitative_only"] = extrap

    # ---- 目标口径对照：mean13（不作主报，支撑 AMB-Q1-2 的声明）
    y_mean = C.make_target(Ptr, Ltr, l2m, "mean13")
    w_mean = fit_no_intercept(A_tr, y_mean)
    res["target_comparison_mean13"] = {
        "train_r2": C.r2(y_mean, A_tr @ w_mean),
        "note": "对照口径。pweighted13 的 R² 显著更高，是选它的依据；但循环性须声明"}

    # ---- 系数稳定性（B=400 自助）
    st = C.coef_stability(A_tr, ytr, 0.0, rng)
    res["coef_stability"] = {k: v for k, v in st.items()
                             if k not in ("coef", "sign_stability", "se", "relative_se")}
    res["coefficients"] = [
        {"feature": pcols[j], "coef": st["coef"][j], "sign_stability": st["sign_stability"][j],
         "se": st["se"][j], "relative_se": st["relative_se"][j]}
        for j in range(len(pcols))]

    # ---- Q 增量嵌套检验（须 M1 的域级 Q）
    qpath = C.METRICS / "q1_quality_M1.json"
    if qpath.exists():
        qj = json.loads(qpath.read_text(encoding="utf-8"))
        domain_Q = {d: v["huber"] for d, v
                    in qj["arms"]["pooled"]["domain"]["per_domain"].items()}
        mapping = C.load_domain_mapping()
        Qc_tr, vtr, info = build_Q_corpus(Ptr, pcols, domain_Q, mapping)
        # A 与 B 在同一子集上拟合，保证嵌套比较可比
        Ptr_v, ytr_v, Qtr_v = Ptr[vtr], ytr[vtr], Qc_tr[vtr]
        A_A_tr = C.design(Ptr_v, "main")
        A_B_tr = np.hstack([Ptr_v, Qtr_v[:, None]])
        w_A = fit_no_intercept(A_A_tr, ytr_v)
        w_B = fit_no_intercept(A_B_tr, ytr_v)

        inc = {"mapping_info": info, "domain_Q_source": "M1 pooled Huber",
               "fit_subset": {"n_train_used": int(vtr.sum()),
                              "n_train_dropped_zero_mass": int((~vtr).sum()),
                              "note": "A（仅 p）与 B（p+Q）在同一子集上拟合与评估"},
               "cond_17": float(np.linalg.cond(A_A_tr)),
               "cond_18_with_Q": float(np.linalg.cond(A_B_tr)),
               "train_r2_A": C.r2(ytr_v, A_A_tr @ w_A),
               "train_r2_B": C.r2(ytr_v, A_B_tr @ w_B),
               "constructive_correlation_note":
                   "Q_corpus 由 6 个已映射域的 p 加权构成，与 p 存在构造性相关，须在论文声明",
               "by_scale": {}}
        for key in SCALES:
            pc, P, lc, L = C.load_pair(key)
            y = C.make_target(P, L, C.loss_to_mixture_index(pc, lc), "pweighted13")
            Qc, v, _ = build_Q_corpus(P, pc, domain_Q, mapping)
            Pv, yv, Qv = P[v], y[v], Qc[v]
            AA, AB = C.design(Pv, "main"), np.hstack([Pv, Qv[:, None]])
            vA = C.validate_by_scale(w_A, AA, yv)
            vB = C.validate_by_scale(w_B, AB, yv)
            # 增量显著性：对 (A,B) 同步自助，取去偏 R² 之差的 95% 区间
            n = len(yv)
            d = np.empty(C.B_BOOT)
            for t in range(C.B_BOOT):
                s = rng.integers(0, n, n)
                d[t] = (C.validate_by_scale(w_B, AB[s], yv[s])["r2_after_offset_removal"]
                        - C.validate_by_scale(w_A, AA[s], yv[s])["r2_after_offset_removal"])
            lo, hi = np.quantile(d, [0.025, 0.975])
            inc["by_scale"][key] = {
                "n_used": n, "n_dropped_zero_mass": int((~v).sum()),
                "p_only_r2_deoffset": vA["r2_after_offset_removal"],
                "p_plus_Q_r2_deoffset": vB["r2_after_offset_removal"],
                "increment": vB["r2_after_offset_removal"] - vA["r2_after_offset_removal"],
                "increment_ci95": [float(lo), float(hi)],
                "significant": bool(lo > 0 or hi < 0),
                "p_only_spearman": vA["spearman"], "p_plus_Q_spearman": vB["spearman"]}
        res["q_increment_test"] = inc
    else:
        res["q_increment_test"] = {"status": "SKIPPED", "reason": "需先运行 q1_quality_main.py"}
        res.setdefault("warnings", []).append("Q 增量检验被跳过：缺 M1 域级 Q")

    res.setdefault("warnings", [])
    res["execution_time_seconds"] = round(time.time() - t0, 1)
    C.write_json(C.METRICS / "q1_mixture_M0c.json", res)

    C.write_csv(C.TABLES / "q1c_coefficients.csv",
                ["method", "feature", "coef", "sign_stability", "se", "relative_se", "reported"],
                [["M0c", c["feature"], round(c["coef"], 6), round(c["sign_stability"], 4),
                  round(c["se"], 6), round(c["relative_se"], 4), "yes"]
                 for c in res["coefficients"]])

    C.write_csv(C.TABLES / "q1c_validation_by_scale.csv",
                ["method", "scale", "n", "r2_raw", "r2_after_offset_removal", "spearman",
                 "bias", "rmse", "bias_share_of_rmse", "qualitative_only"],
                [["M0c", k, v["n"], round(v["r2_raw"], 5),
                  round(v["r2_after_offset_removal"], 5), round(v["spearman"], 5),
                  round(v["bias"], 5), round(v["rmse"], 5),
                  round(v["bias_share_of_rmse"], 5), v.get("qualitative_only", False)]
                 for k, v in list(val.items()) + list(extrap.items())])

    if "by_scale" in res["q_increment_test"]:
        C.write_csv(C.TABLES / "q1c_q_increment_test.csv",
                    ["scale", "p_only_r2_deoffset", "p_plus_Q_r2_deoffset", "increment",
                     "ci95_lo", "ci95_hi", "significant", "p_only_spearman", "p_plus_Q_spearman"],
                    [[k, round(v["p_only_r2_deoffset"], 5), round(v["p_plus_Q_r2_deoffset"], 5),
                      round(v["increment"], 5), round(v["increment_ci95"][0], 5),
                      round(v["increment_ci95"][1], 5), v["significant"],
                      round(v["p_only_spearman"], 5), round(v["p_plus_Q_spearman"], 5)]
                     for k, v in res["q_increment_test"]["by_scale"].items()])

    print(f"M0c 完成 {res['execution_time_seconds']}s | train R² {res['train']['r2']:.5f}")
    for k, v in val.items():
        print(f"  {k}: R²_raw {v['r2_raw']:9.4f} | 去偏 R² {v['r2_after_offset_removal']:.4f} "
              f"| Spearman {v['spearman']:.4f} | bias占RMSE {v['bias_share_of_rmse']:.4f}")
    print(f"  系数符号稳定率≥0.95 占比 {res['coef_stability']['frac_coefs_sign_stable_ge_0.95']:.3f}"
          f" | 平均相对SE {res['coef_stability']['mean_relative_se']:.4f}")
    if "by_scale" in res["q_increment_test"]:
        mi = res["q_increment_test"]["mapping_info"]
        fs = res["q_increment_test"]["fit_subset"]
        print(f"  Q 增量检验（映射域 {mi['n_mapped_domains']}/17，配比质量中位 "
              f"{mi['mapped_mass_median']:.4f}，训练用 {fs['n_train_used']} 行、"
              f"剔除零质量 {fs['n_train_dropped_zero_mass']} 行）:")
        for k, v in res["q_increment_test"]["by_scale"].items():
            print(f"    {k}: {v['p_only_r2_deoffset']:.4f} -> {v['p_plus_Q_r2_deoffset']:.4f} "
                  f"(增量 {v['increment']:+.4f}, CI [{v['increment_ci95'][0]:+.4f},"
                  f"{v['increment_ci95'][1]:+.4f}], 显著={v['significant']})")


if __name__ == "__main__":
    main()

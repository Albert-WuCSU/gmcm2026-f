"""Q2 风险探针（G2）。只查承重风险，判据在执行前写入本 docstring，不事后调整。

| 探针 | 承重风险 | 预声明判据 |
| P1 | 跨来源能否共享不可约损失 E（B1/B4/B5 的 val_loss 下界差异明显） | 三源各自拟合的 E 极差 < 0.15 才可共享 |
| P2 | p 与 (N,D) 是否在同一尺度区间联合观测 | A 侧三尺度全部落入 B1 的 N 区间才算可直接联合 |
| P3 | Q 进入方式：加性独立项 vs 乘性作用于 D_eff | 两式在 B6 上的 RMSE 相对差 > 10% 才算可区分 |
| P4 | D_eff = D·Q^γ 的 β/γ 可辨识性（评审 3.2 的必查项） | 沿 βγ=const 重参数化后预测最大变化 < 1e-8 即确认不可分辨 |
| P5 | B8 的 extrapolated 半数是否与 calibrated 半数同律 | 用 calibrated 拟合去预测 extrapolated，偏差占 RMSE < 50% 才算同律 |
| P6 | Q 是设计因子还是测量值（数据审计 F8）；B6/B7 是否嵌套 | Q 取值数 <= 20 即判为离散设计网格 |
| P7 | B9/B10 的可用性（B9 无 val_loss；B10 为估算值） | 仅记录事实，不设通过判据 |

输出 workspace/data/q2_probe_scaling.json
种子 20260924
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "workspace/data_raw"
OUT = ROOT / "workspace/data/q2_probe_scaling.json"
SEED = 20260924

FILES = {
    "B1": "pythia_training_log_existing.csv",
    "B2": "cerebras_training_log.csv",
    "B4": "scaling_baseline.csv",
    "B5": "published_scaling_data.csv",
    "B6": "supplementary_NQ_experiment.csv",
    "B7": "supplementary_NQ_experiment_expanded.csv",
    "B8": "supplementary_NQ_experiment_large.csv",
    "B9": "supplementary_large_models.csv",
    "B10": "supplementary_large_baseline.csv",
}
A_SCALES_N_B = {"1m": 0.001, "60m": 0.060, "1B": 1.0}


def load(tag: str) -> dict[str, np.ndarray]:
    path = next(RAW.rglob(FILES[tag]))
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    out = {}
    for k in rows[0]:
        vals = [r[k] for r in rows]
        try:
            out[k] = np.array([float(v) if v not in ("", "NA", "nan") else np.nan
                               for v in vals])
        except ValueError:
            out[k] = np.array(vals, dtype=object)
    out["__n__"] = len(rows)
    return out


def fit_classic(N, D, L, n_start: int = 12):
    """L = E + A·N^-alpha + B·D^-beta。对数域参数化保正。返回最优解。"""
    def resid(th):
        E, lA, la, lB, lb = th
        return E + np.exp(lA) * N ** (-np.exp(la)) + np.exp(lB) * D ** (-np.exp(lb)) - L

    rng = np.random.default_rng(SEED)
    best = None
    for _ in range(n_start):
        th0 = np.array([float(L.min()) * rng.uniform(0.3, 0.95),
                        rng.uniform(-1, 2), np.log(rng.uniform(0.1, 0.6)),
                        rng.uniform(-1, 2), np.log(rng.uniform(0.1, 0.6))])
        try:
            r = least_squares(resid, th0, method="trf",
                              bounds=([0, -20, -5, -20, -5], [float(L.max()), 20, 2, 20, 2]),
                              max_nfev=4000)
        except Exception:
            continue
        if best is None or r.cost < best.cost:
            best = r
    E, lA, la, lB, lb = best.x
    pred = best.fun + L
    ss = float(np.sum((L - L.mean()) ** 2))
    return {"E": float(E), "A": float(np.exp(lA)), "alpha": float(np.exp(la)),
            "B": float(np.exp(lB)), "beta": float(np.exp(lb)),
            "rmse": float(np.sqrt(np.mean(best.fun ** 2))),
            "r2": float(1 - np.sum(best.fun ** 2) / ss) if ss > 0 else float("nan"),
            "n": int(len(L)),
            "E_at_lower_bound": bool(E < 1e-6),
            "val_loss_min": float(L.min())}


def valid(*arrs):
    m = np.ones(len(arrs[0]), bool)
    for a in arrs:
        m &= np.isfinite(a) & (a > 0)
    return m


# ------------------------------------------------------------------ P1
def p1_shared_E() -> dict:
    per = {}
    for tag in ("B1", "B4", "B5"):
        d = load(tag)
        N, D, L = d["N_params_B"], d["D_tokens_B"], d["val_loss"]
        m = valid(N, D, L)
        per[tag] = fit_classic(N[m], D[m], L[m])
    Es = [v["E"] for v in per.values()]
    mins = {k: v["val_loss_min"] for k, v in per.items()}
    spread = max(Es) - min(Es)
    return {
        "probe_id": "P1_cross_source_shared_E",
        "load_bearing_risk": ("B1/B4/B5 的 val_loss 下界分别约 2.09/1.71/1.47，"
                              "若强行共享不可约损失 E，跨源拟合会把来源差异吸收进 E 或 alpha/beta"),
        "predeclared_criterion": "三源各自拟合的 E 极差 < 0.15 才可共享",
        "per_source": per,
        "E_by_source": {k: v["E"] for k, v in per.items()},
        "val_loss_min_by_source": mins,
        "E_spread": float(spread),
        "shared_E_admissible": bool(spread < 0.15),
        "verdict": "PASS" if spread < 0.15 else "FAIL",
    }


# ------------------------------------------------------------------ P2
def p2_scale_overlap() -> dict:
    d = load("B1")
    N = d["N_params_B"]
    N = N[np.isfinite(N)]
    lo, hi = float(N.min()), float(N.max())
    inside = {k: bool(lo <= v <= hi) for k, v in A_SCALES_N_B.items()}
    return {
        "probe_id": "P2_p_and_ND_joint_scale_overlap",
        "load_bearing_risk": ("11 个 B 文件逐列核验均无配比列 —— p 只能由 Q1（附件 A 侧）引入。"
                              "若 A 侧尺度不落在 B 侧区间内，L(N,D,Q,p) 在任何单一来源上都不可辨识"),
        "predeclared_criterion": "A 侧三尺度全部落入 B1 的 N 区间才算可直接联合",
        "B_files_with_mixture_columns": 0,
        "B_files_checked": 11,
        "B1_N_range_B": [lo, hi],
        "A_side_scales_N_B": A_SCALES_N_B,
        "A_scale_inside_B1_range": inside,
        "n_inside": int(sum(inside.values())),
        "direct_joint_identifiable": bool(all(inside.values())),
        "consequence": ("跨来源统一假设是承重假设，非可选设计（对应 AMB-Q2-2）。"
                        "Q1 已实测的跨尺度可分性 L(p,scale) ~ f(p)+g(scale)（去偏后 R² 0.771/0.705、"
                        "Spearman 0.922/0.887）可作为该假设的经验支撑 —— 属 AI 意见，采纳由使用者在 G2.5 裁定"),
        "verdict": "FAIL" if not all(inside.values()) else "PASS",
    }


# ------------------------------------------------------------------ P3
def p3_Q_entry_form() -> dict:
    d = load("B6")
    N, D, Q, L = d["N_params_B"], d["D_tokens_B"], d["Q_score"], d["val_loss"]
    m = valid(N, D, Q, L)
    N, D, Q, L = N[m], D[m], Q[m], L[m]
    rng = np.random.default_rng(SEED)

    def fit(resid, nth, lo, hi):
        best = None
        for _ in range(12):
            th0 = np.array([rng.uniform(l, h) for l, h in zip(lo, hi)])
            try:
                r = least_squares(resid, th0, bounds=(lo, hi), max_nfev=4000)
            except Exception:
                continue
            if best is None or r.cost < best.cost:
                best = r
        ss = float(np.sum((L - L.mean()) ** 2))
        return {"rmse": float(np.sqrt(np.mean(best.fun ** 2))),
                "r2": float(1 - np.sum(best.fun ** 2) / ss),
                "params": [float(x) for x in best.x]}

    # 加性独立项：L = E + A N^-a + B D^-b + C Q^-c
    add = fit(lambda t: (t[0] + np.exp(t[1]) * N ** (-np.exp(t[2]))
                         + np.exp(t[3]) * D ** (-np.exp(t[4]))
                         + np.exp(t[5]) * Q ** (-np.exp(t[6])) - L),
              7, [0, -20, -5, -20, -5, -20, -5], [float(L.max()), 20, 2, 20, 2, 20, 2])
    # 乘性 D_eff：L = E + A N^-a + B (D·Q^g)^-b
    mul = fit(lambda t: (t[0] + np.exp(t[1]) * N ** (-np.exp(t[2]))
                         + np.exp(t[3]) * (D * Q ** np.exp(t[4])) ** (-np.exp(t[5])) - L),
              6, [0, -20, -5, -20, -5, -5], [float(L.max()), 20, 2, 20, 2, 2])

    rel = abs(add["rmse"] - mul["rmse"]) / max(add["rmse"], mul["rmse"])
    return {
        "probe_id": "P3_Q_entry_additive_vs_multiplicative",
        "load_bearing_risk": "Q 的进入方式决定边际效用与替代率的函数形式，题目要求自行设计并论证",
        "predeclared_criterion": "两式在 B6 上的 RMSE 相对差 > 10% 才算可区分",
        "additive_independent_term": add,
        "multiplicative_D_eff": mul,
        "rmse_relative_difference": float(rel),
        "distinguishable_on_B6": bool(rel > 0.10),
        "better_fit": "additive" if add["rmse"] < mul["rmse"] else "multiplicative_D_eff",
        "verdict": "CONDITIONAL",
        "note": ("两式若不可区分，则形式选择须靠机理论证与下游可用性（Q3 需要 dL=0 的可解替代率），"
                 "不能只靠 B6 拟合优度。选择权属使用者"),
    }


# ------------------------------------------------------------------ P4
def p4_beta_gamma_identifiability() -> dict:
    rng = np.random.default_rng(SEED)
    N = rng.uniform(0.1, 10, 200)
    D = rng.uniform(10, 600, 200)
    Q = rng.uniform(0.1, 1.0, 200)
    E, A, a, B, be, g = 1.8, 0.4, 0.34, 0.9, 0.28, 2.0

    def L_of(be_, g_):
        return E + A * N ** (-a) + B * (D * Q ** g_) ** (-be_)

    base = L_of(be, g)
    tests = []
    for s in (0.5, 0.8, 1.25, 2.0, 4.0):
        be2, g2 = be * s, g / s          # 保持 be*g 不变
        d = float(np.max(np.abs(L_of(be2, g2) - base)))
        tests.append({"scale": s, "beta": be2, "gamma": g2,
                      "beta_times_gamma": float(be2 * g2), "max_abs_pred_diff": d})
    worst = max(t["max_abs_pred_diff"] for t in tests)

    # 弹性比：沿 Q 与沿 D 的对数导数之比
    eD = -be * B * (D * Q ** g) ** (-be)
    eQ = -be * g * B * (D * Q ** g) ** (-be)
    ratio = eQ / eD
    return {
        "probe_id": "P4_beta_gamma_identifiability",
        "load_bearing_risk": ("评审 3.2 的必查项：D_eff = D·Q^γ 形式下 Q 与 D 的弹性比恒等于 γ，"
                              "沿 Q 方向只能辨识乘积 βγ"),
        "predeclared_criterion": "沿 βγ=const 重参数化后预测最大变化 < 1e-8 即确认 β 与 γ 不可分辨",
        "reparameterizations": tests,
        "worst_max_abs_pred_diff": worst,
        "beta_gamma_separately_identifiable": bool(worst > 1e-8),
        "elasticity_ratio_Q_over_D": {"min": float(ratio.min()), "max": float(ratio.max()),
                                      "constant": bool(np.ptp(ratio) < 1e-12),
                                      "value": float(ratio[0])},
        "required_estimation_order": ("β 必须先由 B1 真实数据（无 Q 变化，Q 视为常数）钉住，"
                                     "再用 B6-B8 估 γ；不得在含 Q 数据上同时自由估 β 与 γ"),
        "prohibited_claim": "不得在采用该形式的同时声称『Q 与 D 的替代率随位置变化』—— 该比值恒为 γ",
        "verdict": "CONDITIONAL",
    }


# ------------------------------------------------------------------ P5
def p5_B8_extrapolated() -> dict:
    d = load("B8")
    N, D, Q, L = d["N_params_B"], d["D_tokens_B"], d["Q_score"], d["val_loss"]
    dt = d["data_type"].astype(str)
    m = valid(N, D, Q, L)
    rng = np.random.default_rng(SEED)

    def fit_deff(N_, D_, Q_, L_):
        def resid(t):
            return (t[0] + np.exp(t[1]) * N_ ** (-np.exp(t[2]))
                    + np.exp(t[3]) * (D_ * Q_ ** np.exp(t[4])) ** (-np.exp(t[5])) - L_)
        best = None
        for _ in range(12):
            th0 = np.array([float(L_.min()) * rng.uniform(0.3, 0.95), rng.uniform(-1, 2),
                            np.log(rng.uniform(0.1, 0.6)), rng.uniform(-1, 2),
                            np.log(rng.uniform(0.5, 3)), np.log(rng.uniform(0.1, 0.6))])
            try:
                r = least_squares(resid, th0, bounds=([0, -20, -5, -20, -5, -5],
                                                      [float(L_.max()), 20, 2, 20, 2, 2]),
                                  max_nfev=4000)
            except Exception:
                continue
            if best is None or r.cost < best.cost:
                best = r
        return best

    cal = m & (dt == "calibrated")
    ext = m & (dt == "extrapolated")
    fit = fit_deff(N[cal], D[cal], Q[cal], L[cal])
    th = fit.x
    pred_ext = (th[0] + np.exp(th[1]) * N[ext] ** (-np.exp(th[2]))
                + np.exp(th[3]) * (D[ext] * Q[ext] ** np.exp(th[4])) ** (-np.exp(th[5])))
    res = pred_ext - L[ext]
    rmse = float(np.sqrt(np.mean(res ** 2)))
    bias = float(np.mean(res))
    share = abs(bias) / rmse if rmse > 0 else float("nan")
    return {
        "probe_id": "P5_B8_extrapolated_consistency",
        "load_bearing_risk": ("B8 的 extrapolated 半数 N 上到 700B、val_loss 低至 0.5，"
                              "低于自然语言熵下界的常见量级；若与 calibrated 不同律，"
                              "混入拟合会污染参数（GC5 亦禁止表述为直接观测）"),
        "predeclared_criterion": "用 calibrated 拟合去预测 extrapolated，偏差占 RMSE < 50% 才算同律",
        "n_calibrated": int(cal.sum()), "n_extrapolated": int(ext.sum()),
        "calibrated_fit": {"rmse": float(np.sqrt(np.mean(fit.fun ** 2))),
                           "E": float(th[0]), "gamma": float(np.exp(th[4])),
                           "beta": float(np.exp(th[5]))},
        "extrapolated_prediction": {"rmse": rmse, "bias": bias,
                                    "bias_share_of_rmse": share},
        "val_loss_range": {"calibrated": [float(L[cal].min()), float(L[cal].max())],
                           "extrapolated": [float(L[ext].min()), float(L[ext].max())]},
        "N_range_B": {"calibrated": [float(N[cal].min()), float(N[cal].max())],
                      "extrapolated": [float(N[ext].min()), float(N[ext].max())]},
        "same_law": bool(share < 0.50),
        "verdict": "PASS" if share < 0.50 else "FAIL",
    }


# ------------------------------------------------------------------ P6
def p6_Q_design_factor() -> dict:
    out = {}
    for tag in ("B6", "B7", "B8"):
        d = load(tag)
        Q = d["Q_score"]
        Q = Q[np.isfinite(Q)]
        u = np.unique(np.round(Q, 6))
        out[tag] = {"n_rows": int(d["__n__"]), "n_unique_Q": int(len(u)),
                    "Q_values": [float(x) for x in u[:25]],
                    "Q_min": float(u.min()), "Q_max": float(u.max()),
                    "is_discrete_grid": bool(len(u) <= 20)}
    b6, b7 = load("B6"), load("B7")

    def keyset(d):
        return {(round(float(a), 6), round(float(b), 6), round(float(c), 6))
                for a, b, c in zip(d["N_params_B"], d["D_tokens_B"], d["Q_score"])}
    k6, k7 = keyset(b6), keyset(b7)
    return {
        "probe_id": "P6_Q_is_design_factor_and_B6_B7_nesting",
        "load_bearing_risk": ("数据审计 F8：B6-B8 的 Q_score 是实验设计因子（离散刻度），"
                              "Q1 产出的 Q 是连续经验值且受域混淆（AUC 0.95-0.97）。"
                              "二者不是同类对象 —— 对应 AMB-Q2-3"),
        "predeclared_criterion": "Q 取值数 <= 20 即判为离散设计网格",
        "per_file": out,
        "B6_B7_nesting": {"n_B6": len(k6), "n_B7": len(k7),
                          "B6_subset_of_B7": bool(k6 <= k7),
                          "n_shared": len(k6 & k7)},
        "consequence": "Q1->Q2 是尺度校准问题，不是直接代入；须建立对齐规则并声明假设",
        "verdict": "CONDITIONAL",
    }


# ------------------------------------------------------------------ P7
def p7_B9_B10() -> dict:
    b9, b10 = load("B9"), load("B10")
    d9 = b9["D_tokens_B"]
    return {
        "probe_id": "P7_B9_B10_usability",
        "load_bearing_risk": "B9 无 val_loss 列、B10 的 val_loss 是估算值（GC5）",
        "predeclared_criterion": "仅记录事实，不设通过判据",
        "B9": {"n_rows": int(b9["__n__"]), "columns": list(b9.keys() - {"__n__"}),
               "has_val_loss": "val_loss" in b9,
               "D_tokens_zero_or_missing": int(np.sum(~np.isfinite(d9) | (d9 <= 0))),
               "N_range_B": [float(np.nanmin(b9["N_params_B"])), float(np.nanmax(b9["N_params_B"]))]},
        "B10": {"n_rows": int(b10["__n__"]), "has_val_loss": "val_loss" in b10,
                "val_loss_range": [float(np.nanmin(b10["val_loss"])), float(np.nanmax(b10["val_loss"]))],
                "provenance": "估算值，非观测（GC5）"},
        "permitted_use": "仅用于百亿参数以上外推的可信度讨论，不进主拟合",
        "verdict": "CONDITIONAL",
    }


def main() -> None:
    probes = [p1_shared_E(), p2_scale_overlap(), p3_Q_entry_form(),
              p4_beta_gamma_identifiability(), p5_B8_extrapolated(),
              p6_Q_design_factor(), p7_B9_B10()]
    res = {"schema_version": 1, "question": "Q2", "seed": SEED,
           "scope": "G2 风险探针：只查承重风险；判据在执行前写入脚本 docstring",
           "criteria_predeclared_before_execution": True,
           "probes": {p["probe_id"]: p for p in probes}}
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")

    print("=" * 74)
    p1 = probes[0]
    print("P1 跨源共享 E:", p1["verdict"])
    for k, v in p1["E_by_source"].items():
        print(f"    {k}: E={v:.4f}  val_loss_min={p1['val_loss_min_by_source'][k]:.4f}")
    print(f"    E 极差 {p1['E_spread']:.4f} | 可共享 {p1['shared_E_admissible']}")
    p2 = probes[1]
    print("P2 尺度重叠:", p2["verdict"], "| B1 N 区间", [round(x, 4) for x in p2["B1_N_range_B"]])
    print("    A 侧落入:", p2["A_scale_inside_B1_range"])
    p3 = probes[2]
    print("P3 Q 进入方式:", p3["verdict"],
          f"| 加性 RMSE {p3['additive_independent_term']['rmse']:.5f}"
          f" / 乘性 {p3['multiplicative_D_eff']['rmse']:.5f}"
          f" | 相对差 {p3['rmse_relative_difference']:.4f} | 可区分 {p3['distinguishable_on_B6']}")
    p4 = probes[3]
    print("P4 β/γ 可辨识:", p4["verdict"],
          f"| 重参数化最大预测差 {p4['worst_max_abs_pred_diff']:.3e}"
          f" | 可分辨 {p4['beta_gamma_separately_identifiable']}"
          f" | 弹性比恒定 {p4['elasticity_ratio_Q_over_D']['constant']}"
          f" = {p4['elasticity_ratio_Q_over_D']['value']:.4f}")
    p5 = probes[4]
    print("P5 B8 外推同律:", p5["verdict"],
          f"| n cal/ext {p5['n_calibrated']}/{p5['n_extrapolated']}"
          f" | 预测 RMSE {p5['extrapolated_prediction']['rmse']:.4f}"
          f" bias 占比 {p5['extrapolated_prediction']['bias_share_of_rmse']:.4f}")
    print("    val_loss 范围 cal", [round(x, 3) for x in p5["val_loss_range"]["calibrated"]],
          "ext", [round(x, 3) for x in p5["val_loss_range"]["extrapolated"]])
    p6 = probes[5]
    print("P6 Q 设计因子:", p6["verdict"])
    for k, v in p6["per_file"].items():
        print(f"    {k}: {v['n_rows']} 行, Q 取值 {v['n_unique_Q']} 个"
              f" [{v['Q_min']}, {v['Q_max']}], 离散网格 {v['is_discrete_grid']}")
    print("    B6 ⊆ B7:", p6["B6_B7_nesting"]["B6_subset_of_B7"],
          "| 共享点", p6["B6_B7_nesting"]["n_shared"])
    p7 = probes[6]
    print("P7 B9/B10:", p7["verdict"], "| B9 有 val_loss", p7["B9"]["has_val_loss"],
          "| B9 的 D 缺失/零", p7["B9"]["D_tokens_zero_or_missing"])
    print("=" * 74)
    print("输出", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()

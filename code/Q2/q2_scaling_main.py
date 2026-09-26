"""M1s（main）：L = E_s + A*N^-alpha + B*(D*Q^gamma*exp(b^T z_p))^-beta

落地 6 条裁定（methods/Q2/q2_decisions.jsonl）：
  1A  p 经 exp(b^T z_p) 进入；B 侧 z_p=0（无配比列）
  2A  Q 经乘性 D_eff = D*Q^gamma；beta 先由 B1 钉住再估 gamma
  3B  半合成以更大 sigma 参与（异方差 WLS）；sigma 取值方式可切换、须记录
  4   B1 = 退化检验（阈 1e-6）；B7 = 超越性比较（自助区间）
  5   fallback 读「或」，条件2 已移到 B7
  6   kappa 主线声明不可辨识、只报比值；敏感性臂须带参照点

用法：python q2_scaling_main.py [--sigma-mode residual|p5_anchor]
"""
from __future__ import annotations

import argparse
import json
import time

import numpy as np
from scipy.stats import spearmanr

import q2_common as C

OUT = C.ROOT / "results/Q2/experiments/round1"
B_BOOT = 400
P5_ANCHOR_SIGMA = 0.6293200406951934      # P5 实测 calibrated->extrapolated 转移 RMSE


def sigma_spec(mode: str, b1, b7, p0) -> dict:
    """sigma_s 的取值方式。**未经使用者裁定**，故参数化 + 记录 + 可否决。"""
    s1 = p0["rmse"]
    if mode == "residual":
        pg = C.fit_gamma_on_b7(b7["N"], b7["D"], b7["Q"], b7["L"], p0["beta"])
        s7 = pg["rmse"]
        how = "各来源拟合残差分层估计"
    elif mode == "p5_anchor":
        s7 = P5_ANCHOR_SIGMA
        how = "半合成 sigma 锚定 P5 样本外转移 RMSE 0.6293"
    else:
        raise SystemExit(f"unknown sigma-mode: {mode}")
    ratio = (s1 / s7) ** 2
    share = b7["n"] * ratio / (b1["n"] + b7["n"] * ratio)
    return {"mode": mode, "how": how, "sigma_B1": float(s1), "sigma_B7": float(s7),
            "per_point_weight_ratio_B7_over_B1": float(ratio),
            "B7_total_weight_share": float(share),
            "status": "AI_PROPOSAL_UNCONFIRMED — 取值方式未经使用者裁定，可被否决",
            "consequence": ("共享参数几乎纯由 B1 决定、gamma 几乎纯由 B7 内部结构决定；"
                            "该事实与 sigma 取值方式无关，两种 mode 下同量级")}


def b_direction(beta, B, D_ref) -> dict:
    """裁定 6：b = kappa*(w - wbar)。主线只报比值与方向；敏感性臂带参照点。"""
    w, cols = C.load_q1_w()
    w_c = w - w.mean()
    order = np.argsort(-w_c)                       # w 高 = 域级 Loss 高
    # 主线 (a)：比值，kappa 无关
    i_hi, i_lo = int(order[0]), int(order[-1])
    ratios = {cols[i]: float(w_c[i] / w_c[i_hi]) for i in order}   # 以最高者为基准，kappa 约掉
    # 敏感性臂 (b)：kappa = -1/(beta*G)，G = B*D^-beta，须带参照点
    G = B * D_ref ** (-beta)
    kappa = -1.0 / (beta * G)
    b_vec = kappa * w_c
    # 符号自洽：高 Loss 域 w_i>wbar => b_i<0 => D_eff 小 => L 上升
    sign_ok = bool(b_vec[i_hi] < 0 and b_vec[i_lo] > 0)
    dL_1pp = float(-beta * (b_vec[i_hi] - b_vec[i_lo]) * 0.01 * G)
    return {
        "main_line_a": {
            "kappa_status": "B 侧严格不可辨识（实测 RMSE 随 kappa 变化 = 0.0）",
            "reported": "b_i/b_j 比值与方向（kappa 在比值中约掉）",
            "w_source": "Q1c 的 M0c 17 维系数（results/Q1/.../q1c_coefficients.csv）",
            "highest_loss_domain": cols[i_hi], "lowest_loss_domain": cols[i_lo],
            "ratio_to_highest": ratios,
        },
        "sensitivity_arm_b": {
            "assumption": "A 侧与 B 侧在指定参照点上 dL/dp_i 相等（承重假设，已声明）",
            "reference_point": {"D_tokens_B": float(D_ref), "note": "量级必须与该参照点一同报出"},
            "G_at_reference": float(G), "kappa": float(kappa),
            "b_range": [float(b_vec.min()), float(b_vec.max())],
            "dL_for_1pp_shift_lowest_to_highest_w": dL_1pp,
            "caveat": "G 随 D 变 ⇒ kappa 随参照点变（B1 的 1B run 内可差 8.7 倍），不存在普适 kappa",
        },
        "sign_coherence_ok": sign_ok,
    }


def q2c_one_side(A, al, B, be, g, N_ref, D_ref, Q_ref) -> dict:
    """在给定一侧形状参数上算 Q2c。全部 kappa 无关。"""
    dL_dN = -A * al * N_ref ** (-al - 1)
    dL_dD = -B * be * (D_ref * Q_ref ** g) ** (-be - 1) * Q_ref ** g
    dL_dQ = -B * be * g * (D_ref * Q_ref ** g) ** (-be - 1) * D_ref * Q_ref ** (g - 1)
    # 弹性（对数导数）
    e_N = dL_dN * N_ref
    e_D = dL_dD * D_ref
    e_Q = dL_dQ * Q_ref
    # Q<->D 弹性比：P4 证明恒为 gamma
    ratio_QD = float(e_Q / e_D) if e_D != 0 else float("nan")
    # dL=0 沿 (N,Q)：dN/dQ
    dN_dQ = -dL_dQ / dL_dN
    # Q 提升 0.1 等价的 N 增量：沿等 Loss 面积分（数值）
    qs = np.linspace(Q_ref, Q_ref + 0.1, 64)
    Ns = [N_ref]
    for i in range(1, len(qs)):
        Nc, Qc = Ns[-1], qs[i - 1]
        d1 = -A * al * Nc ** (-al - 1)
        d2 = -B * be * g * (D_ref * Qc ** g) ** (-be - 1) * D_ref * Qc ** (g - 1)
        Ns.append(Nc + (-d2 / d1) * (qs[i] - qs[i - 1]))
    dN_for_dQ01 = float(Ns[-1] - N_ref)
    return {
        "marginal": {"dL_dN": float(dL_dN), "dL_dD": float(dL_dD), "dL_dQ": float(dL_dQ)},
        "elasticity": {"N": float(e_N), "D": float(e_D), "Q": float(e_Q)},
        "elasticity_ratio_Q_over_D": ratio_QD,
        "elasticity_ratio_equals_gamma": bool(abs(ratio_QD - g) < 1e-9),
        "substitution_dN_dQ": float(dN_dQ),
        "dN_for_Q_plus_0.1": dN_for_dQ01,
        "signs_ok": bool(dL_dN < 0 and dL_dD < 0 and dL_dQ < 0),
    }


def q2c_outputs(m1, N_ref, D_ref, Q_ref) -> dict:
    """Q2c 按参数来源拆开报（P8 后的必要修正）。

    形状参数来源专属 ⇒ 不同侧给出的量级差达 24.5%(dL/dN) ~ 31.8%(dN/dQ)。
    主报用 B1 侧（真实数据支撑，Q=1 时精确退化为 B1 的真实拟合）；B7 侧作敏感性臂。
    """
    be, g = m1["beta"], m1["gamma"]
    prim = q2c_one_side(m1["A_B1"], m1["alpha_B1"], m1["B_B1"], be, g, N_ref, D_ref, Q_ref)
    sens = q2c_one_side(m1["A_B7"], m1["alpha_B7"], m1["B_B7"], be, g, N_ref, D_ref, Q_ref)
    diffs = {}
    for k, pa, sa in (("dL_dN", prim["marginal"]["dL_dN"], sens["marginal"]["dL_dN"]),
                      ("dL_dD", prim["marginal"]["dL_dD"], sens["marginal"]["dL_dD"]),
                      ("dL_dQ", prim["marginal"]["dL_dQ"], sens["marginal"]["dL_dQ"]),
                      ("substitution_dN_dQ", prim["substitution_dN_dQ"], sens["substitution_dN_dQ"]),
                      ("dN_for_Q_plus_0.1", prim["dN_for_Q_plus_0.1"], sens["dN_for_Q_plus_0.1"])):
        diffs[k] = {"B1_side": pa, "B7_side": sa,
                    "relative_difference": float(abs(pa - sa) / max(abs(pa), 1e-30))}
    return {
        "reference_point": {"N_params_B": float(N_ref), "D_tokens_B": float(D_ref), "Q": float(Q_ref)},
        "primary_B1_side": prim,
        "sensitivity_B7_side": sens,
        "cross_side_difference": diffs,
        "provenance": {
            "beta": "B1 真实（B7 权重份额 ~1.6e-6，实质纯 B1）",
            "gamma": "B7 半合成 —— B1 上 Q=1，对 gamma 零信息。不可避免，按 GC5 披露",
            "A_alpha_B_B1_side": "B1 真实：1176 行、8 个 N、D 跨 0.1-299.9B",
            "A_alpha_B_B7_side": "B7 半合成：450 行、9 个 N、D 仅 5 个取值",
            "real_data_supported": ["dL_dN", "dL_dD", "elasticity_N", "elasticity_D"],
            "irreducibly_semisynthetic": ["dL_dQ", "elasticity_Q", "substitution_dN_dQ",
                                          "dN_for_Q_plus_0.1", "elasticity_ratio_Q_over_D"],
            "why_split": ("形状参数经 P8 判定不可跨源共享，故 N/D 的边际效用应由 B1 真实数据支撑；"
                          "用 B7 侧参数计算它们会把可避免的半合成依赖引入本可由真实数据回答的量"),
        },
        "prohibited_claim_reminder": ("Q<->D 弹性比恒为 gamma（P4：ptp<1e-12）⇒ "
                                      "不得声称『Q 与 D 的替代率随位置变化』；仅 Q<->N 随位置变化"),
    }


def validate_transfer(p, codes=("B4", "B5", "B2")) -> dict:
    """真实/轨迹数据上的迁移验证。P1：禁止报跨源未去偏 R²，用 Spearman。"""
    out = {}
    for code in codes:
        d = C.load_nd(code)
        # 用共享形状参数 + 该源自有截距（去源偏）：E_s 由该源残差中位数吸收
        # 用 B1 侧形状参数（真实数据支撑）+ 该源自有截距（去源偏）
        core = p["A_B1"] * d["N"] ** (-p["alpha_B1"]) + p["B_B1"] * d["D"] ** (-p["beta"])
        E_s = float(np.median(d["L"] - core))
        pred = E_s + core
        rho, pv = spearmanr(pred, d["L"])
        out[code] = {
            "n": d["n"], "E_s_deoffset": E_s,
            "spearman": float(rho), "spearman_p": float(pv),
            "rmse_after_deoffset": float(np.sqrt(np.mean((pred - d["L"]) ** 2))),
            "note": "禁止报跨源未去偏 R²（P1：E 极差 1.6898）；此处仅报秩相关与去源偏后 RMSE",
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sigma-mode", default="residual", choices=["residual", "p5_anchor"])
    args = ap.parse_args()
    t0 = time.time()
    (OUT / "metrics").mkdir(parents=True, exist_ok=True)

    b1, b7 = C.load_nd("B1"), C.load_b7()

    # ---- 阶段 1：beta 由 B1 钉住 ----
    p0 = C.fit_classic(b1["N"], b1["D"], b1["L"])
    beta_fixed = p0["beta"]

    # ---- 阶段 2：gamma 在 B7 上（beta 固定）----
    pg = C.fit_gamma_on_b7(b7["N"], b7["D"], b7["Q"], b7["L"], beta_fixed)
    rng = np.random.default_rng(C.SEED)
    g_boot = []
    for _ in range(B_BOOT):
        idx = C.boot_indices(np.arange(b7["n"]), rng, "row")
        try:
            q = C.fit_gamma_on_b7(b7["N"][idx], b7["D"][idx], b7["Q"][idx], b7["L"][idx],
                                  beta_fixed, seed=int(rng.integers(1e9)))
            g_boot.append(q["gamma"])
        except Exception:
            continue
    gamma_ci = C.ci95(np.array(g_boot))

    # ---- 阶段 3：来源分层 WLS，形状参数**来源专属**（P8 判 FAIL 后的修正）----
    ss = sigma_spec(args.sigma_mode, b1, b7, p0)
    m1 = C.fit_joint_wls_source_shape(b1, b7, ss["sigma_B1"], ss["sigma_B7"], with_Q=True)
    m0j = C.fit_joint_wls_source_shape(b1, b7, ss["sigma_B1"], ss["sigma_B7"], with_Q=False)

    # 裁定 4：B1 退化检验（阈 1e-6）
    rel_b1 = abs(m1["rmse_B1"] - p0["rmse"]) / max(p0["rmse"], 1e-30)
    degeneracy = {"criterion": "M1s 与 M0s 在 B1 上 RMSE 相对差 < 1e-6",
                  "M0s_rmse_B1": p0["rmse"], "M1s_rmse_B1": m1["rmse_B1"],
                  "relative_difference": float(rel_b1), "passed": bool(rel_b1 < 1e-6),
                  "doubles_as": "题目要求的『Q=1 退化为经典形式』依据"}

    # 裁定 4：B7 超越性（自助区间）
    diffs = []
    rng2 = np.random.default_rng(C.SEED + 7)
    for _ in range(B_BOOT):
        idx = C.boot_indices(np.arange(b7["n"]), rng2, "row")
        sub = {"N": b7["N"][idx], "D": b7["D"][idx], "Q": b7["Q"][idx], "L": b7["L"][idx],
               "n": len(idx), "source": "B7"}
        try:
            a = C.fit_joint_wls_source_shape(b1, sub, ss["sigma_B1"], ss["sigma_B7"], True,
                                             seed=int(rng2.integers(1e9)), n_start=4)
            b = C.fit_joint_wls_source_shape(b1, sub, ss["sigma_B1"], ss["sigma_B7"], False,
                                             seed=int(rng2.integers(1e9)), n_start=4)
            diffs.append(b["rmse_B7"] - a["rmse_B7"])      # >0 表示 M1s 更优
        except Exception:
            continue
    d_ci = C.ci95(np.array(diffs))
    superiority = {"criterion": "M1s 在 B7 上 RMSE 优于 M0s_joint，差值自助 95% 区间不含 0",
                   "M0s_joint_rmse_B7": m0j["rmse_B7"], "M1s_rmse_B7": m1["rmse_B7"],
                   "rmse_reduction": float(m0j["rmse_B7"] - m1["rmse_B7"]),
                   "ci95_of_reduction": d_ci, "n_boot_ok": len(diffs),
                   "passed": bool(d_ci[0] > 0),
                   "nested_note": ("M0s_joint 在 B7 上另设自有截距 E_B7，与 M1s 仅差 gamma 一个参数。"
                                   "这是 P1『E 跨源不可共享』的机械后果；若用 B1 截距预测 B7 会把"
                                   "截距失配算成 Q 通道的功劳"),
                   "gc5_disclosure": ("超越性证据完全建立在半合成 B7 上 —— B 侧仅 B6/B7/B8 含 Q 变化"
                                      "且全部半合成。按 GC5 须披露，该结论带『补充分析』属性")}

    # 阶段 4：b 的方向（裁定 6）。用 B1 侧 B（真实数据支撑）
    D_ref = float(b1["D"][np.argmax(b1["D"])])
    bdir = b_direction(m1["beta"], m1["B_B1"], D_ref)
    if not bdir["sign_coherence_ok"]:
        raise SystemExit("符号自洽检查失败：高 Loss 域应得 b_i<0。不得静默继续")

    # Q2c
    N_ref, Q_ref = 1.0, 0.5
    q2c = q2c_outputs(m1, N_ref, float(np.median(b7["D"])), Q_ref)
    if not q2c["primary_B1_side"]["signs_ok"]:
        raise SystemExit("弹性符号检查失败（B1 侧主报）。不得静默继续")
    transfer = validate_transfer(m1)

    # 裁定 5：fallback 读「或」
    fb = {"fallback_id": "M2s",
          "condition": "gamma_ci95 包含 0  或  M1s 在 B7 上 RMSE 不优于 M0s_joint（自助区间判）",
          "gamma_ci95": gamma_ci, "cond1_gamma_ci_contains_zero": bool(gamma_ci[0] <= 0 <= gamma_ci[1]),
          "cond2_not_better_on_B7": bool(not superiority["passed"]),
          "observed": bool((gamma_ci[0] <= 0 <= gamma_ci[1]) or (not superiority["passed"])),
          "evidence": "results/Q2/experiments/round1/metrics/q2_M1s.json"}

    res = {"schema_version": 1, "method_id": "M1s", "role": "main",
           "form": "L = E_s + A*N^-alpha + B*(D*Q^gamma*exp(b^T z_p))^-beta",
           "approved_decision_ids": ["q2_p_entry_form", "q2_Q_entry_form",
                                     "q2_semisynthetic_fit_participation",
                                     "q2_baseline_comparison_venue",
                                     "q2_fallback_trigger_logic", "q2_kappa_treatment"],
           "stage1_beta_from_B1": {"beta": beta_fixed, "params": {k: v for k, v in p0.items() if k != "rmse"}},
           "stage2_gamma_on_B7": {"gamma": pg["gamma"], "gamma_ci95": gamma_ci,
                                  "n_boot_ok": len(g_boot), "rmse": pg["rmse"],
                                  "note": "beta 固定；z_p=0（B7 无配比列）⇒ exp(b^T z_p)=1"},
           "stage3_joint_wls": {
               "sigma_spec": ss, "M1s_params": m1, "M0s_joint_params": m0j,
               "shape_params_source_specific": True,
               "p8_basis": "workspace/data/q2_probe_shape_sharing.json",
               "p8_finding": ("强制共享 A/alpha/B 造成 gamma 位移 0.1691 = 其自助区间宽度的 98.5%，"
                              "判 FAIL ⇒ 形状参数来源专属"),
               "structural_consequence": ("B1 上 Q=1 ⇒ gamma 仅受 B7 约束；beta 因 B1 权重压倒性优势"
                                          "实质由 B1 决定。本式数值上等价于两段式（实测 gamma 差 1.03e-7、"
                                          "beta 差 6.86e-8）⇒ 裁定3=B 的 WLS 被忠实实现但在该参数结构下"
                                          "无实质作用，须如实说明，不得表述为『联合拟合提升了估计』")},
           "degeneracy_check_B1": degeneracy,
           "superiority_check_B7": superiority,
           "stage4_b_direction": bdir,
           "q2c": q2c,
           "transfer_validation": transfer,
           "fallback_trigger": fb,
           "amb_q2_3_scale_alignment": {
               "q1_empirical_domain_Q_range": [min(C.load_q1_domain_Q().values()),
                                               max(C.load_q1_domain_Q().values())],
               "b7_design_grid_Q_levels": b7["Q_levels"],
               "status": "尺度不同，对齐规则须显式声明；本轮不做静默映射",
           },
           "runtime_seconds": round(time.time() - t0, 2)}
    (OUT / "metrics/q2_M1s.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n",
                                             encoding="utf-8")
    print(json.dumps({"gamma": pg["gamma"], "gamma_ci95": gamma_ci,
                      "joint_gamma": m1["gamma"],
                      "degeneracy_passed": degeneracy["passed"], "rel_diff_B1": degeneracy["relative_difference"],
                      "superiority_passed": superiority["passed"],
                      "rmse_B7_M0s_joint": m0j["rmse_B7"], "rmse_B7_M1s": m1["rmse_B7"],
                      "ci95_reduction": d_ci, "fallback_observed": fb["observed"],
                      "elast_ratio_Q_over_D": q2c["primary_B1_side"]["elasticity_ratio_Q_over_D"],
                      "dN_for_Q01_B1side": q2c["primary_B1_side"]["dN_for_Q_plus_0.1"],
                      "dN_for_Q01_B7side": q2c["sensitivity_B7_side"]["dN_for_Q_plus_0.1"],
                      "signs_ok_B1side": q2c["primary_B1_side"]["signs_ok"],
                      "runtime_s": res["runtime_seconds"]},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

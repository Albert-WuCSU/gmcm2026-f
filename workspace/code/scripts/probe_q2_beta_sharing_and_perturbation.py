"""Q2 G4 补算(裁定 q2_result_verdict = 1B / q2_stability_verdict = 2B)。

两件：
  (1) P9 —— beta 跨源可共享性探针。评审 F4 记为 OPEN：P8 只查了 A/alpha/B，P1 只查了 E，
      beta 当前作跨源共享参数使用（实质由 B1 决定）而**从未检验**。
  (2) 实验四件套缺项的补齐：参数扰动 + 消融 + M0s 同口径扰动。

预声明判据（**执行前写定，不事后放宽**）：
  P9 判据：强制 beta 由 B1 共享（B7 不自估）造成的 gamma 位移，
           若 < gamma 自助 95% 区间宽度的 50% 则共享可接受；否则 beta 亦须来源专属。
  理由与 P8 同构：gamma 是本问核心可报量，判据挂在它的不确定性尺度上。

  P9a 判据：beta 在 B7 上自估的 95% 自助区间若覆盖 B1 的 beta 点估计，
            则「beta 跨源共享」不被数据拒绝；否则拒绝。
  P9b 判据：自助 B 由 400 提到 1000，gamma 的 95% 区间端点相对变化 < 10% 判稳。
  P9c 判据：B1 留一 N 组后 beta 的极差 < B1 beta 自助区间宽度判稳。
  P9d 判据（扰动）：B1 权重整体缩放 lambda ∈ {0.5, 1.0, 2.0}，gamma 位移
            < gamma 自助区间宽度判稳。此项直接服务于使用者挂起的约束「但B1的处理要谨慎」。
  P9e 判据（消融）：sigma_s 取值方式由 residual 换为 p5_anchor，gamma 位移
            < gamma 自助区间宽度判稳（该取值方式为 AI_PROPOSAL_UNCONFIRMED，可否决）。
  P9f 判据（M0s 同口径扰动）：M0s 留一 N 组后 beta 极差 < 其自助区间宽度判稳。
  P9g（消融）：关闭 Q 通道 -> 应退化为 M0s（已知）；移除 B7 -> gamma 应不可辨识。

只写新文件，不改任何已评审代码。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "code/Q2"))
import q2_common as C  # noqa: E402

OUT_SUPP = ROOT / "robustness/Q2/q2_robustness_supplement.json"
OUT_P9 = ROOT / "workspace/data/q2_probe_beta_sharing.json"
B_BOOT = 400
B_BOOT_BIG = 1000


def fit_b7_free_beta(N, D, Q, L, seed=C.SEED):
    """B7 上 E/A/alpha/B/beta/gamma 全自由(P8 后形状参数已来源专属,这里再加 beta 自由)。

    注意 (D*Q^gamma)^(-beta) = D^(-beta)*Q^(-beta*gamma)：beta 由 D 变化辨识、
    乘积 beta*gamma 由 Q 变化辨识。B7 的 D 取值很少,故 beta 的辨识强度本身就是探针要测的东西。
    """
    def resid(th):
        E, A, a, Bc, b, g = th
        return E + A * N ** (-a) + Bc * (D * Q ** g) ** (-b) - L
    r = C._multistart(resid, [0, 0, 1e-4, 0, 1e-4, 1e-4], [5, 50, 2, 50, 2, 10], seed=seed)
    p = dict(zip(["E_B7", "A", "alpha", "B", "beta", "gamma"], map(float, r.x)))
    p["rmse"] = float(np.sqrt(np.mean(r.fun ** 2)))
    return p


def fit_joint_srcshape_lambda(b1, b7, s1, s7, lam, seed=C.SEED):
    """来源专属形状 + 共享 beta/gamma 的联合 WLS，但 B1 权重整体乘 lam。"""
    w1, w7 = lam / s1 ** 2, 1.0 / s7 ** 2

    def resid(th):
        E1, A1, a1, B1c, E7, A7, a7, B7c, b, g = th
        r1 = E1 + A1 * b1["N"] ** (-a1) + B1c * b1["D"] ** (-b) - b1["L"]
        r7 = E7 + A7 * b7["N"] ** (-a7) + B7c * (b7["D"] * b7["Q"] ** g) ** (-b) - b7["L"]
        return np.concatenate([r1 * np.sqrt(w1), r7 * np.sqrt(w7)])

    lo = [0, 0, 1e-4, 0, 0, 0, 1e-4, 0, 1e-4, 1e-4]
    hi = [5, 50, 2, 50, 5, 50, 2, 50, 2, 10]
    r = C._multistart(resid, lo, hi, seed=seed)
    keys = ["E_B1", "A_B1", "alpha_B1", "B_B1", "E_B7", "A_B7", "alpha_B7", "B_B7", "beta", "gamma"]
    p = dict(zip(keys, map(float, r.x)))
    return p


def main() -> None:
    t0 = time.perf_counter()
    b1, b7 = C.load_nd("B1"), C.load_b7()
    p0 = C.fit_classic(b1["N"], b1["D"], b1["L"])          # M0s / B1 侧
    beta_b1 = float(p0["beta"])
    beta_b1_ci = json.loads((ROOT / "results/Q2/experiments/round1/metrics/q2_M0s.json")
                            .read_text(encoding="utf-8"))["bootstrap"]["by_mode"]["grouped"]["beta"]["ci95"]

    # ---- 路线 A：beta 由 B1 共享（现行生产口径）
    pa = C.fit_gamma_on_b7(b7["N"], b7["D"], b7["Q"], b7["L"], beta_b1)
    rng = np.random.default_rng(C.SEED)
    ga = []
    for _ in range(B_BOOT):
        idx = C.boot_indices(np.arange(b7["n"]), rng, "row")
        try:
            ga.append(C.fit_gamma_on_b7(b7["N"][idx], b7["D"][idx], b7["Q"][idx], b7["L"][idx],
                                        beta_b1, seed=int(rng.integers(1e9)))["gamma"])
        except Exception:
            continue
    ci_a = C.ci95(np.array(ga))
    width = float(ci_a[1] - ci_a[0])

    # ---- 路线 B：beta 在 B7 上自估（与 gamma 联立）
    pb = fit_b7_free_beta(b7["N"], b7["D"], b7["Q"], b7["L"])
    rng2 = np.random.default_rng(C.SEED)
    gb, bb = [], []
    for _ in range(B_BOOT):
        idx = C.boot_indices(np.arange(b7["n"]), rng2, "row")
        try:
            f = fit_b7_free_beta(b7["N"][idx], b7["D"][idx], b7["Q"][idx], b7["L"][idx],
                                 seed=int(rng2.integers(1e9)))
            gb.append(f["gamma"]); bb.append(f["beta"])
        except Exception:
            continue
    ci_b = C.ci95(np.array(gb))
    beta_b7_ci = C.ci95(np.array(bb))

    shift = abs(pa["gamma"] - pb["gamma"])
    frac = shift / width if width > 0 else float("nan")
    thresh = 0.5 * width
    # P9a：B7 自估 beta 的区间是否覆盖 B1 的 beta 点估计
    covers = bool(beta_b7_ci[0] <= beta_b1 <= beta_b7_ci[1])

    p9 = {
        "schema_version": 1,
        "probe_id": "P9_beta_cross_source_sharing",
        "load_bearing_risk": ("评审 F4：beta 当前作跨源共享参数使用（实质由 B1 决定，B7 权重份额约 1.6e-6），"
                              "但从未检验。P8 只查了 A/alpha/B，P1 只查了 E。"),
        "predeclared_criterion": "强制 beta 由 B1 共享造成的 gamma 位移 < gamma 自助 95% 区间宽度的 50% 才可共享",
        "route_A_beta_shared_from_B1": {
            "gamma": pa["gamma"], "gamma_ci95": ci_a, "ci_width": width,
            "E_B7": pa["E_B7"], "A": pa["A"], "alpha": pa["alpha"], "B": pa["B"],
            "rmse_B7": pa["rmse"], "n_boot_ok": len(ga),
        },
        "route_B_beta_free_on_B7": {
            "gamma": pb["gamma"], "gamma_ci95": ci_b,
            "beta": pb["beta"], "beta_ci95": beta_b7_ci,
            "E_B7": pb["E_B7"], "A": pb["A"], "alpha": pb["alpha"], "B": pb["B"],
            "rmse_B7": pb["rmse"], "n_boot_ok": len(gb),
        },
        "beta_b1_point": beta_b1,
        "beta_b1_ci95_grouped": beta_b1_ci,
        "p9a_b1_beta_inside_b7_beta_ci": covers,
        "gamma_shift": float(shift),
        "threshold": float(thresh),
        "shift_as_fraction_of_ci_width": float(frac),
        "beta_shift": float(abs(beta_b1 - pb["beta"])),
        "rmse_B7_penalty": float(pb["rmse"] - pa["rmse"]),
        "betas_agree_within_ci": covers,
        "verdict": "PASS" if (frac == frac and frac < 0.5) else "FAIL",
        "consequence": ("若 PASS：beta 跨源共享不被数据拒绝，F4 由 OPEN 转为已检验，"
                        "但须注意 beta 在 B7 上的辨识强度（B7 的 D 取值少）。"
                        "若 FAIL：beta 亦须来源专属，则『形状参数来源专属』扩及全部指数参数，"
                        "M1s 的跨源共享仅剩 gamma 一项。"),
    }
    OUT_P9.write_text(json.dumps(p9, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"P9: gamma_A={pa['gamma']:.6f} gamma_B={pb['gamma']:.6f} shift={shift:.6f} "
          f"frac={frac:.4f} verdict={p9['verdict']} b1_inside_b7_ci={covers}")
    print(f"    beta_B1={beta_b1:.6f} beta_B7={pb['beta']:.6f} beta_B7_ci={[round(x,6) for x in beta_b7_ci]}")

    # ---- P9b 自助 B 稳定性（主路线）
    rng3 = np.random.default_rng(C.SEED)
    gbig = []
    for _ in range(B_BOOT_BIG):
        idx = C.boot_indices(np.arange(b7["n"]), rng3, "row")
        try:
            gbig.append(C.fit_gamma_on_b7(b7["N"][idx], b7["D"][idx], b7["Q"][idx], b7["L"][idx],
                                          beta_b1, seed=int(rng3.integers(1e9)))["gamma"])
        except Exception:
            continue
    ci_big = C.ci95(np.array(gbig))
    rel = [abs(ci_big[i] - ci_a[i]) / max(abs(ci_a[i]), 1e-12) for i in (0, 1)]

    # ---- P9c B1 留一 N 组（beta 稳定性）
    groups = np.unique(b1["group"])
    beta_loo, gamma_loo = [], []
    for g in groups:
        m = b1["group"] != g
        try:
            f = C.fit_classic(b1["N"][m], b1["D"][m], b1["L"][m])
            beta_loo.append(f["beta"])
            gamma_loo.append(C.fit_gamma_on_b7(b7["N"], b7["D"], b7["Q"], b7["L"], f["beta"])["gamma"])
        except Exception:
            continue
    beta_loo = np.array(beta_loo)
    beta_width_b1 = beta_b1_ci[1] - beta_b1_ci[0]

    # ---- P9d B1 权重扰动（直接服务于挂起约束「但B1的处理要谨慎」）
    s1 = pa["rmse"]
    lam_res = {}
    for lam in (0.5, 1.0, 2.0):
        f = fit_joint_srcshape_lambda(b1, b7, s1, pa["rmse"], lam)
        lam_res[str(lam)] = {"beta": f["beta"], "gamma": f["gamma"],
                             "gamma_shift_vs_routeA": abs(f["gamma"] - pa["gamma"])}

    # ---- P9e sigma_s 消融（AI_PROPOSAL_UNCONFIRMED，可否决）
    f_p5 = C.fit_joint_wls_source_shape(b1, b7, s1, 0.6293200406951934, with_Q=True)
    gamma_p5 = f_p5["gamma"]

    # ---- P9f M0s 同口径扰动（留一 N 组）
    m0_beta_loo = []
    for g in groups:
        m = b1["group"] != g
        try:
            m0_beta_loo.append(C.fit_classic(b1["N"][m], b1["D"][m], b1["L"][m])["beta"])
        except Exception:
            continue
    m0_beta_loo = np.array(m0_beta_loo)

    supp = {
        "schema_version": 1,
        "question_id": "Q2",
        "gate": "G4",
        "purpose": "兑现裁定 q2_result_verdict=1B 与 q2_stability_verdict=2B 的补算要求",
        "seed": C.SEED,
        "inputs": {
            "B1": "workspace/data_raw/real_attachments/B_scaling_laws/pythia_training_log_existing.csv",
            "B7": "workspace/data_raw/real_attachments/B_scaling_laws/supplementary_NQ_experiment_expanded.csv",
            "metrics": "results/Q2/experiments/round1/metrics/q2_M0s.json",
        },
        "P9_beta_sharing": {k: p9[k] for k in (
            "gamma_shift", "threshold", "shift_as_fraction_of_ci_width", "beta_b1_point",
            "beta_b1_ci95_grouped", "p9a_b1_beta_inside_b7_beta_ci", "beta_shift",
            "rmse_B7_penalty", "verdict")},
        "P9b_bootstrap_B_stability": {
            "b_small": B_BOOT, "b_big": B_BOOT_BIG,
            "ci95_at_400": ci_a, "ci95_at_1000": ci_big,
            "relative_endpoint_change": rel,
            "max_relative_endpoint_change": float(max(rel)),
            "criterion": "端点相对变化 < 10% 判稳",
            "verdict": "PASS" if max(rel) < 0.10 else "FAIL",
            "n_boot_ok_big": len(gbig),
        },
        "P9c_B1_leave_one_N_group_out": {
            "n_groups": int(len(groups)), "n_ok": int(beta_loo.size),
            "beta_min": float(beta_loo.min()), "beta_max": float(beta_loo.max()),
            "beta_range": float(beta_loo.max() - beta_loo.min()),
            "beta_ci_width_grouped": float(beta_width_b1),
            "gamma_min": float(np.min(gamma_loo)), "gamma_max": float(np.max(gamma_loo)),
            "gamma_range": float(np.max(gamma_loo) - np.min(gamma_loo)),
            "criterion": "beta 极差 < B1 beta 自助区间宽度判稳",
            "verdict": "PASS" if (beta_loo.max() - beta_loo.min()) < beta_width_b1 else "FAIL",
        },
        "P9d_B1_weight_perturbation": {
            "lambda_values": [0.5, 1.0, 2.0],
            "results": lam_res,
            "gamma_ci_width_routeA": width,
            "criterion": "gamma 位移 < gamma 自助区间宽度判稳",
            "max_gamma_shift": float(max(v["gamma_shift_vs_routeA"] for v in lam_res.values())),
            "verdict": "PASS" if max(v["gamma_shift_vs_routeA"] for v in lam_res.values()) < width else "FAIL",
            "note": "直接服务于使用者挂起的约束「但B1的处理要谨慎」：量化结论对 B1 权重的依赖程度",
        },
        "P9e_sigma_s_ablation": {
            "gamma_residual_mode": pa["gamma"],
            "gamma_p5_anchor_mode": float(gamma_p5),
            "gamma_shift": float(abs(gamma_p5 - pa["gamma"])),
            "gamma_ci_width_routeA": width,
            "criterion": "gamma 位移 < gamma 自助区间宽度判稳",
            "verdict": "PASS" if abs(gamma_p5 - pa["gamma"]) < width else "FAIL",
            "note": "sigma_s 取值方式为 AI_PROPOSAL_UNCONFIRMED（可否决）；本项量化其影响",
        },
        "P9f_M0s_same_caliber_perturbation": {
            "n_groups": int(len(groups)), "n_ok": int(m0_beta_loo.size),
            "beta_min": float(m0_beta_loo.min()), "beta_max": float(m0_beta_loo.max()),
            "beta_range": float(m0_beta_loo.max() - m0_beta_loo.min()),
            "beta_ci_width_grouped": float(beta_width_b1),
            "criterion": "beta 极差 < 其自助区间宽度判稳",
            "verdict": "PASS" if (m0_beta_loo.max() - m0_beta_loo.min()) < beta_width_b1 else "FAIL",
        },
        "P9g_ablation": {
            "disable_Q_channel": {
                "note": "关闭 Q 通道即 M0s；预声明指标 1（B1 退化）已实测相对差 "
                        "1.0122362405611505e-08 < 1e-6，本项不重复计算",
                "status": "covered_by_predeclared_metric_1",
            },
            "drop_B7": {
                "note": "移除 B7 后 gamma 无任何数据约束（B1 上 Q=1）⇒ 不可辨识；"
                        "这正是『gamma 完全由半合成 B7 决定』的机械含义",
                "status": "structurally_unidentifiable",
            },
        },
        "elapsed_seconds": None,
    }
    supp["elapsed_seconds"] = round(time.perf_counter() - t0, 1)
    OUT_SUPP.write_text(json.dumps(supp, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"P9b max rel endpoint change = {max(rel):.4f} ({supp['P9b_bootstrap_B_stability']['verdict']})")
    print(f"P9c beta range={supp['P9c_B1_leave_one_N_group_out']['beta_range']:.3e} "
          f"ci_width={beta_width_b1:.3e} ({supp['P9c_B1_leave_one_N_group_out']['verdict']})")
    print(f"P9d max gamma shift={supp['P9d_B1_weight_perturbation']['max_gamma_shift']:.6f} "
          f"width={width:.6f} ({supp['P9d_B1_weight_perturbation']['verdict']})")
    print(f"P9e gamma p5={gamma_p5:.6f} shift={supp['P9e_sigma_s_ablation']['gamma_shift']:.6f} "
          f"({supp['P9e_sigma_s_ablation']['verdict']})")
    print(f"P9f M0s beta range={supp['P9f_M0s_same_caliber_perturbation']['beta_range']:.3e} "
          f"({supp['P9f_M0s_same_caliber_perturbation']['verdict']})")
    print(f"elapsed {supp['elapsed_seconds']}s")
    print("WROTE", OUT_P9.relative_to(ROOT), "|", OUT_SUPP.relative_to(ROOT))


if __name__ == "__main__":
    main()

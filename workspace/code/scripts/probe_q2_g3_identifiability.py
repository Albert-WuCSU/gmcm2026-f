"""G3 开工前的两项可辨识性核查。判据在执行前写死在本 docstring。

起因：裁定1=A（p 经 exp(b^T z_p) 进入）+ 裁定2=A（乘性 D_eff）落地时，
两条预声明指标与 fallback 触发条件可能在 B1 上退化。须在写代码计划前证伪或确认。

--- 核查 1：M1s 在 B1 上是否与 M0s 同构 ---
B1 无配比列（P2 实测 0/11）⇒ 全部 B1 行取基准配比 ⇒ z_p = 0 ⇒ exp(b^T z_p) = 1。
B1 亦无 Q 变化 ⇒ Q = Q0 常数。
故 M1s 在 B1 上为 L = E + A·N^-a + (B·Q0^(-b*g))·D^-b，与 M0s 的
L = E + A·N^-a + B·D^-b 函数形式相同、自由参数个数相同。
判据：两式在 B1 上各自最优拟合的 RMSE 相对差 < 1e-6 即判定「同构、不可比较」。
后果（若成立）：预声明指标 1「B1 留出集 RMSE」无法区分 M1s 与 M0s；
fallback 触发条件 2「M1s 在 B1 留出集 RMSE 不优于 M0s」会平凡成立。

--- 核查 2：b 的尺度因子 kappa 是否可辨识 ---
记 b = kappa * (w - mean(w))，w 为 Q1c 的 M0c 系数（17 维，域级 Loss 水平）。
Sum(p)=1 ⇒ 仅 w 的差分有意义 ⇒ 必须中心化。
B 侧 z_p=0 ⇒ B 侧似然对 kappa 的导数恒为 0。
判据：在 B1 上把 kappa 从 0 扫到 10，若预测最大变化 < 1e-12 即判定
「kappa 在 B 侧严格不可辨识」。
后果（若成立）：b_i/b_j（域间替代比）与 kappa 无关、可报；
但 ∂L/∂p_i 的绝对量级随 kappa 线性缩放、不可辨识，须另设假设或只报相对量。
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parents[3]
B1 = ROOT / "workspace/data_raw/real_attachments/B_scaling_laws/pythia_training_log_existing.csv"
Q1COEF = ROOT / "results/Q1/experiments/round1/tables/q1c_coefficients.csv"
MIX1B = ROOT / "workspace/data_raw/real_attachments/A_data_value/regmix_tables/test_mixture_1B.csv"
OUT = ROOT / "workspace/data/q2_probe_g3_identifiability.json"
SEED = 20260924


def load_b1():
    rows = list(csv.DictReader(B1.open(encoding="utf-8-sig")))
    N = np.array([float(r["N_params_B"]) for r in rows])
    D = np.array([float(r["D_tokens_B"]) for r in rows])
    L = np.array([float(r["val_loss"]) for r in rows])
    return N, D, L


def fit_classic(N, D, L):
    """M0s: L = E + A*N^-a + B*D^-b"""
    def resid(th):
        E, A, a, Bc, b = th
        return E + A * N ** (-a) + Bc * D ** (-b) - L
    best = None
    rng = np.random.default_rng(SEED)
    for _ in range(12):
        x0 = np.array([rng.uniform(0, 2), rng.uniform(0.1, 3), rng.uniform(0.05, 0.6),
                       rng.uniform(0.1, 3), rng.uniform(0.05, 0.6)])
        r = least_squares(resid, x0, bounds=([0, 0, 1e-4, 0, 1e-4], [5, 50, 2, 50, 2]),
                          max_nfev=20000)
        if best is None or r.cost < best.cost:
            best = r
    rmse = float(np.sqrt(np.mean(best.fun ** 2)))
    return dict(zip(["E", "A", "alpha", "B", "beta"], map(float, best.x))), rmse


def fit_m1s_on_b1(N, D, L, Q0=1.0, kappa=0.0, zp_norm=0.0):
    """M1s 在 B1 上：L = E + A*N^-a + B*(D*Q0^g*exp(kappa*zp))^-b
    B1 上 zp=0、Q=Q0 常数。自由参数 (E,A,a,B,b,g)，其中 g 与 B 通过 Q0^(-b*g) 共线。"""
    def resid(th):
        E, A, a, Bc, b, g = th
        D_eff = D * (Q0 ** g) * np.exp(kappa * zp_norm)
        return E + A * N ** (-a) + Bc * D_eff ** (-b) - L
    best = None
    rng = np.random.default_rng(SEED)
    for _ in range(12):
        x0 = np.array([rng.uniform(0, 2), rng.uniform(0.1, 3), rng.uniform(0.05, 0.6),
                       rng.uniform(0.1, 3), rng.uniform(0.05, 0.6), rng.uniform(0.1, 4)])
        r = least_squares(resid, x0,
                          bounds=([0, 0, 1e-4, 0, 1e-4, 1e-4], [5, 50, 2, 50, 2, 10]),
                          max_nfev=20000)
        if best is None or r.cost < best.cost:
            best = r
    rmse = float(np.sqrt(np.mean(best.fun ** 2)))
    return dict(zip(["E", "A", "alpha", "B", "beta", "gamma"], map(float, best.x))), rmse


def main() -> None:
    N, D, L = load_b1()
    res = {"schema_version": 1, "question": "Q2", "scope": "G3 开工前可辨识性核查",
           "seed": SEED, "criteria_predeclared_before_execution": True}

    # ---- 核查 1：同构性 ----
    p0, r0 = fit_classic(N, D, L)
    p1, r1 = fit_m1s_on_b1(N, D, L)
    rel = abs(r1 - r0) / max(r0, 1e-30)
    res["check1_M1s_vs_M0s_on_B1"] = {
        "predeclared_criterion": "两式在 B1 上最优拟合 RMSE 相对差 < 1e-6 即判定同构、不可比较",
        "M0s_params": p0, "M0s_rmse": r0,
        "M1s_params_on_B1": p1, "M1s_rmse": r1,
        "rmse_relative_difference": float(rel),
        "isomorphic_on_B1": bool(rel < 1e-6),
        "consequence": ("若同构：预声明指标 1『B1 留出集 RMSE』无法区分 M1s 与 M0s；"
                        "fallback 触发条件 2『M1s 不优于 M0s』平凡成立。"
                        "须由使用者裁定如何修改比较口径 —— AI 不得自行放宽或改写判据"),
    }

    # ---- 核查 2：kappa 可辨识性 ----
    coef = {r["feature"]: float(r["coef"]) for r in
            csv.DictReader(Q1COEF.open(encoding="utf-8-sig")) if r["method"] == "M0c"}
    mix = list(csv.DictReader(MIX1B.open(encoding="utf-8-sig")))
    pcols = [c for c in mix[0] if c.startswith("train_the_pile_")]
    w = np.array([coef[c] for c in pcols])
    w_c = w - w.mean()

    # B 侧 zp 恒为 0（无配比列 ⇒ 取基准配比）
    preds = []
    for kappa in [0.0, 0.5, 1.0, 2.0, 5.0, 10.0]:
        _, rk = fit_m1s_on_b1(N, D, L, kappa=kappa, zp_norm=0.0)
        preds.append({"kappa": kappa, "rmse": rk})
    spread = max(p["rmse"] for p in preds) - min(p["rmse"] for p in preds)
    res["check2_kappa_identifiability_on_B"] = {
        "predeclared_criterion": "kappa 从 0 扫到 10，B1 上预测最大变化 < 1e-12 即判定严格不可辨识",
        "zp_on_B_side": 0.0,
        "zp_reason": "B 侧 11 个文件零配比列（P2 实测）⇒ 全部 B 行取基准配比 ⇒ z_p = 0",
        "sweep": preds,
        "rmse_spread_over_kappa": float(spread),
        "kappa_identifiable_from_B": bool(spread >= 1e-12),
        "w_centered_range": [float(w_c.min()), float(w_c.max())],
        "w_centered_abs_max": float(np.abs(w_c).max()),
        "ratio_b_i_over_b_j_invariant_to_kappa": True,
        "consequence": ("b 的方向（域间替代比 b_i/b_j）与 kappa 无关、可报且可继承 Q1c；"
                        "但 ∂L/∂p_i 的绝对量级随 kappa 线性缩放，B 侧无信息。"
                        "Q2c 的域间替代/互补判定不受影响；p 的绝对边际效用须另设假设或只报相对量。"
                        "如何处置属使用者裁定"),
    }

    # A 侧与 B1 的口径差（供裁定时参考，不作判据）
    P = np.array([[float(r[c]) for c in pcols] for r in mix])
    res["scale_gap_A_vs_B1"] = {
        "A_side_implied_loss_range": [float((P @ w).min()), float((P @ w).max())],
        "A_side_implied_loss_mean": float((P @ w).mean()),
        "B1_val_loss_range": [float(L.min()), float(L.max())],
        "B1_val_loss_mean": float(L.mean()),
        "note": "同为交叉熵但口径不同（A 侧为 pweighted13 域级 Loss，B1 为单一 val_loss）；P1 已证 E 跨源不可共享",
    }

    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({
        "check1_isomorphic_on_B1": res["check1_M1s_vs_M0s_on_B1"]["isomorphic_on_B1"],
        "check1_M0s_rmse": r0, "check1_M1s_rmse": r1, "check1_rel_diff": rel,
        "check2_kappa_identifiable_from_B": res["check2_kappa_identifiability_on_B"]["kappa_identifiable_from_B"],
        "check2_rmse_spread": spread,
    }, ensure_ascii=False, indent=1))
    print("WROTE", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()

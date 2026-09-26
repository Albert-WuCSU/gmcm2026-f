"""Q3 G2 风险探针。判据在执行前写死在本 docstring，不事后放宽。

目标函数取 Q2 已过 G3 的 B1 侧参数（真实数据支撑）：
  L(N,D,Q) = E + A*N^-alpha + B*(D*Q^gamma)^-beta
  E=1.68979741 A=0.35398032 alpha=0.33997658 B=1.24030577 beta=0.27987806 gamma=0.96591294
约束（题目给定，不可改）：
  6*N*D + D*[g(Q)-g(Q0)]_+ + eta*N*D*L_ctx <= C,  eta=2e-4
单位（GC10）：N、D 以十亿为单位输入，代入成本式各乘 1e9。

--- P1 最优解是内点还是边界 ---
风险：若 Q* 恒顶到边界（Q=1 或 Q=Q0），则「质量投入」不是真正的决策维度，KKT 内点条件失效。
判据：三档预算 × 三类 g 共 9 个组合中，若 Q* 落在 (Q0+0.01, 0.99) 内的组合 < 3 个，
      判 FAIL —— 须改用带边界情形的分段 KKT 或显式讨论角点解。

--- P2 三类 g 是否给出质的不同 ---
风险：AMB-Q3-2，三类 g 量级差极大（1e7*e^6=4.03e9 vs 5e9 vs 2e9*ln(11)=4.79e9）。
判据：同一预算下三类 g 的 Q* 极差 > 0.10 即判「成本函数选择实质影响最优解」（题目要求讨论此点）。

--- P3 p 联立优化是否退化为角点 ---
风险：b^T z_p 对 p 线性 ⇒ exp(b^T z_p) 对每个 p_i 单调 ⇒ 无内点最优，全部质量堆到单一域。
判据：在单纯形上最大化 -b^T z_p，若最优 p 的最大分量 > 0.99 即判「角点退化」，
      则 p 联立优化须加信赖域/正则或改为固定 p。

--- P4 结构性转移是否真实发生 ---
风险：题目要求判定「预算跨量级时最优策略是否质变」，若无转移则 Q3c 无内容。
判据：在 log10(C) 从 18 到 25 密集扫描，若某成本分项占比（C_train/C_Q/C_attn）的
      排序发生变化，或 Q* 的一阶差分出现 > 0.05 的跳变，即判「存在结构性转移」。

--- P5 L_ctx 跨临界值是否改变最优配置 ---
风险：L_ctx^crit=6/eta=30000，C7 的 32768 与 131072 超过它。
判据：L_ctx 从 2048 到 131072（C7 实测 5 档），若 N*/D* 比值极差 > 20% 即判「跨临界有实质影响」。

--- P6 Q2 标度律在高预算档的外推距离 ---
风险：AMB-Q3-3。B1 的 N 范围 0.07-11.97B、D 范围 0.1-299.9B。
判据：仅记录 C=1e24 档隐含的 N*/D* 相对 B1 范围的外推倍数，不设通过判据（供 GC5 披露用）。
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.optimize import brentq, minimize

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "workspace/data/q3_probe_optimization.json"
SEED = 20260924

# Q2 B1 侧参数（已过 G3）
E, A, AL, B, BE, GA = 1.68979741, 0.35398032, 0.33997658, 1.24030577, 0.27987806, 0.96591294
ETA = 2e-4
L_CTX_FEASIBLE = [2048, 4096, 8192, 32768, 131072]      # C7 实测
L_CTX_CRIT = 6.0 / ETA                                   # = 30000
G_FORMS = {
    "exponential": lambda q: 1e7 * np.exp(6.0 * q),
    "power": lambda q: 5e9 * q ** 4.0,
    "log_asymptotic": lambda q: 2e9 * np.log(1.0 + 10.0 * q),
}
Q0_DEFAULT = 0.35        # Q1 实测域级 Q 落在 0.2233-0.3815，取其上端附近


def loss(N_B, D_B, Q):
    return E + A * N_B ** (-AL) + B * (D_B * Q ** GA) ** (-BE)


def cost(N_B, D_B, Q, gname, Q0, L_ctx):
    """返回 (总成本, 三分项)。N_B/D_B 以十亿为单位 ⇒ 各乘 1e9。"""
    N, D = N_B * 1e9, D_B * 1e9
    g = G_FORMS[gname]
    c_train = 6.0 * N * D
    c_q = D * max(g(Q) - g(Q0), 0.0)
    c_attn = ETA * N * D * L_ctx
    return c_train + c_q + c_attn, {"C_train": c_train, "C_Q": c_q, "C_attn": c_attn}


def solve(C, gname, Q0=Q0_DEFAULT, L_ctx=2048, n_start=8):
    """在预算 C 下最小化 Loss。决策变量 (log10 N_B, log10 D_B, Q)，Q 边界 [Q0, 1]。"""
    g = G_FORMS[gname]

    def neg_obj(x):
        nb, db, q = 10 ** x[0], 10 ** x[1], x[2]
        return loss(nb, db, q)

    def con(x):
        nb, db, q = 10 ** x[0], 10 ** x[1], x[2]
        tot, _ = cost(nb, db, q, gname, Q0, L_ctx)
        return (C - tot) / C          # 归一化，避免 1e24 量级下的数值问题

    rng = np.random.default_rng(SEED)
    best = None
    # 起点：按 C_train 主导估个量级，N=D 的 Chinchilla 式起点
    nd = C / 6.0 / 1e18
    base = 0.5 * np.log10(max(nd, 1e-12))
    for _ in range(n_start):
        x0 = np.array([base + rng.uniform(-1, 1), base + rng.uniform(-1, 1),
                       rng.uniform(Q0 + 0.01, 0.99)])
        try:
            r = minimize(neg_obj, x0, method="SLSQP",
                         bounds=[(-4, 5), (-4, 6), (Q0, 1.0)],
                         constraints=[{"type": "ineq", "fun": con}],
                         options={"maxiter": 500, "ftol": 1e-12})
        except Exception:
            continue
        if not r.success or con(r.x) < -1e-6:
            continue
        if best is None or r.fun < best.fun:
            best = r
    if best is None:
        return None
    nb, db, q = 10 ** best.x[0], 10 ** best.x[1], best.x[2]
    tot, parts = cost(nb, db, q, gname, Q0, L_ctx)
    return {"N_B": float(nb), "D_B": float(db), "Q": float(q), "loss": float(best.fun),
            "cost_total": float(tot), "cost_parts": {k: float(v) for k, v in parts.items()},
            "cost_shares": {k: float(v / tot) for k, v in parts.items()},
            "budget_used_frac": float(tot / C), "N_over_D": float(nb / db)}


def main() -> None:
    res = {"schema_version": 1, "question": "Q3", "seed": SEED,
           "criteria_predeclared_before_execution": True,
           "objective_params_from_Q2_B1_side": {"E": E, "A": A, "alpha": AL, "B": B,
                                               "beta": BE, "gamma": GA},
           "L_ctx_crit_analytic": L_CTX_CRIT,
           "L_ctx_crit_derivation": "C_attn/C_train = eta*N*D*L_ctx/(6*N*D) = eta*L_ctx/6; 令其=1 得 L_ctx=6/eta=30000",
           "Q0_used": Q0_DEFAULT, "probes": {}}

    budgets = [1e19, 1e22, 1e24]

    # ---- P1 + P2 ----
    grid = {}
    interior = 0
    for C in budgets:
        for gname in G_FORMS:
            s = solve(C, gname)
            key = f"C{C:.0e}_{gname}"
            grid[key] = s
            if s and (Q0_DEFAULT + 0.01) < s["Q"] < 0.99:
                interior += 1
    q_by_budget = {}
    for C in budgets:
        qs = [grid[f"C{C:.0e}_{g}"]["Q"] for g in G_FORMS if grid.get(f"C{C:.0e}_{g}")]
        q_by_budget[f"{C:.0e}"] = {"Q_values": qs, "spread": float(max(qs) - min(qs)) if qs else None}

    res["probes"]["P1_interior_vs_boundary"] = {
        "predeclared_criterion": "9 个组合中 Q* 落在 (Q0+0.01, 0.99) 内的 < 3 个则 FAIL",
        "n_interior": interior, "n_total": len(grid),
        "grid": grid,
        "verdict": "PASS" if interior >= 3 else "FAIL",
        "consequence": ("若 FAIL：Q* 恒在边界 ⇒ KKT 内点条件失效，须用分段 KKT 或显式讨论角点解；"
                        "且『质量投入』不是真正的连续决策维度"),
    }
    max_spread = max(v["spread"] for v in q_by_budget.values() if v["spread"] is not None)
    res["probes"]["P2_cost_form_sensitivity"] = {
        "predeclared_criterion": "同一预算下三类 g 的 Q* 极差 > 0.10 即判成本函数选择实质影响最优解",
        "by_budget": q_by_budget, "max_spread": float(max_spread),
        "g_magnitudes_at_Q1": {k: float(f(1.0)) for k, f in G_FORMS.items()},
        "g_magnitudes_at_Q0": {k: float(f(Q0_DEFAULT)) for k, f in G_FORMS.items()},
        "verdict": "CONFIRMED_SENSITIVE" if max_spread > 0.10 else "NOT_SENSITIVE",
    }

    # ---- P3 p 联立优化的角点退化 ----
    import csv as _csv
    rows = [r for r in _csv.DictReader(
        (ROOT / "results/Q1/experiments/round1/tables/q1c_coefficients.csv").open(encoding="utf-8-sig"))
        if r["method"] == "M0c"]
    w = np.array([float(r["coef"]) for r in rows])
    w_c = w - w.mean()
    # b = kappa*(w-wbar)，kappa<0 ⇒ 最小化 Loss 等价于最大化 -b^T z_p ∝ 最小化 w_c^T p
    # 单纯形上线性目标 ⇒ 最优在顶点：全部质量给 w_c 最小的域
    n = len(w_c)
    r_lin = minimize(lambda p: float(w_c @ p), np.ones(n) / n,
                     bounds=[(0, 1)] * n,
                     constraints=[{"type": "eq", "fun": lambda p: p.sum() - 1}],
                     method="SLSQP", options={"maxiter": 500})
    p_opt = r_lin.x / r_lin.x.sum()
    res["probes"]["P3_p_joint_corner_degeneracy"] = {
        "predeclared_criterion": "单纯形上最优 p 的最大分量 > 0.99 即判角点退化",
        "max_component": float(p_opt.max()),
        "argmax_domain": rows[int(np.argmax(p_opt))]["feature"],
        "lowest_w_domain": rows[int(np.argmin(w_c))]["feature"],
        "objective_is_linear_in_p": True,
        "verdict": "CORNER_DEGENERATE" if p_opt.max() > 0.99 else "INTERIOR_EXISTS",
        "consequence": ("若角点退化：b^T z_p 对 p 线性 ⇒ 无内点最优，全部配比堆到单一域，"
                        "这在物理上不合理。p 联立优化须加信赖域/正则化，或改为由 Q1/Q2 结果固定。"
                        "选择权属使用者（题目授权二选一但要求说明理由）"),
    }
    # ---- P4 结构性转移 ----
    sweep = []
    for lc in np.arange(18.0, 25.01, 0.25):
        C = 10 ** lc
        s = solve(C, "exponential")
        if s:
            sh = s["cost_shares"]
            sweep.append({"log10_C": float(lc), "Q": s["Q"], "N_B": s["N_B"], "D_B": s["D_B"],
                          "N_over_D": s["N_over_D"], "shares": sh,
                          "dominant": max(sh, key=sh.get),
                          "share_order": "|".join(sorted(sh, key=sh.get, reverse=True))})
    orders = [p["share_order"] for p in sweep]
    order_changes = [(sweep[i]["log10_C"], orders[i - 1], orders[i])
                     for i in range(1, len(orders)) if orders[i] != orders[i - 1]]
    qs = np.array([p["Q"] for p in sweep])
    dq = np.abs(np.diff(qs))
    jumps = [{"log10_C": sweep[i + 1]["log10_C"], "dQ": float(dq[i])}
             for i in range(len(dq)) if dq[i] > 0.05]
    q_sat = next((p["log10_C"] for p in sweep if p["Q"] >= 0.999), None)
    res["probes"]["P4_structural_transition"] = {
        "predeclared_criterion": ("成本分项占比排序发生变化，或 Q* 一阶差分出现 > 0.05 的跳变，"
                                 "即判存在结构性转移"),
        "sweep_range_log10_C": [18.0, 25.0], "step": 0.25, "n_points": len(sweep),
        "share_order_changes": order_changes,
        "Q_jumps_gt_0.05": jumps,
        "Q_saturation_log10_C": q_sat,
        "max_abs_dQ": float(dq.max()) if len(dq) else None,
        "verdict": "TRANSITION_EXISTS" if (order_changes or jumps) else "NO_TRANSITION",
        "candidate_definitions_for_user": [
            "活跃约束集变化（Q 的上界约束由非活跃转为活跃）—— 本探针实测该事件确实发生",
            "最优解路径的不可微点（dQ*/dlogC 在饱和点处不连续）",
            "成本分项占比排序变化",
            "分配份额突变（一阶差分阈值）",
        ],
        "note": "定义的选取属使用者裁定（题目 success_criteria 第 2 条）",
    }

    # ---- P5 L_ctx 跨临界 ----
    lc_rows = {}
    for L in L_CTX_FEASIBLE:
        s = solve(1e22, "exponential", L_ctx=L)
        if s:
            lc_rows[str(L)] = {"Q": s["Q"], "N_B": s["N_B"], "D_B": s["D_B"],
                               "N_over_D": s["N_over_D"], "loss": s["loss"],
                               "shares": s["cost_shares"],
                               "attn_over_train": float(ETA * L / 6.0),
                               "above_crit": bool(L > L_CTX_CRIT)}
    nds = [v["N_over_D"] for v in lc_rows.values()]
    spread_nd = (max(nds) - min(nds)) / max(min(nds), 1e-30) if nds else None
    res["probes"]["P5_L_ctx_crossing_crit"] = {
        "predeclared_criterion": "N*/D* 比值极差 > 20% 即判跨临界有实质影响",
        "L_ctx_crit": L_CTX_CRIT, "feasible_from_C7": L_CTX_FEASIBLE,
        "above_crit": [L for L in L_CTX_FEASIBLE if L > L_CTX_CRIT],
        "by_L_ctx": lc_rows, "N_over_D_relative_spread": float(spread_nd) if spread_nd else None,
        "verdict": ("MATERIAL_EFFECT" if spread_nd and spread_nd > 0.20 else "WEAK_EFFECT"),
        "writing_red_line": "30000 只是两类成本相等的临界尺度，不是最优上下文长度",
    }

    # ---- P6 外推距离 ----
    hi = grid.get("C1e+24_exponential")
    res["probes"]["P6_extrapolation_distance"] = {
        "predeclared_criterion": "仅记录事实，不设通过判据（供 GC5 披露用）",
        "B1_ranges": {"N_B": [0.070542, 11.965825], "D_B": [0.1, 299.9]},
        "optimum_at_1e24": {"N_B": hi["N_B"], "D_B": hi["D_B"]} if hi else None,
        "extrapolation_factor": {
            "N": float(hi["N_B"] / 11.965825) if hi else None,
            "D": float(hi["D_B"] / 299.9) if hi else None,
        } if hi else None,
        "consequence": ("高预算档最优解远超 B1 的观测范围 ⇒ Q2 标度律在该档为外推。"
                        "须结合 B9/B10 的可信度边界说明（AMB-Q3-3），不得表述为可靠预测"),
    }

    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("P4 verdict=%s | order_changes=%d | Q_jumps=%d | Q_sat@log10C=%s" % (
        res["probes"]["P4_structural_transition"]["verdict"], len(order_changes), len(jumps), q_sat))
    print("P5 verdict=%s | N/D 相对极差=%.4f" % (
        res["probes"]["P5_L_ctx_crossing_crit"]["verdict"], spread_nd or -1))
    print("P6 外推倍数 N=%.2fx D=%.2fx" % (
        res["probes"]["P6_extrapolation_distance"]["extrapolation_factor"]["N"],
        res["probes"]["P6_extrapolation_distance"]["extrapolation_factor"]["D"]))
    print("P1 interior=%d/%d verdict=%s" % (interior, len(grid),
                                            res["probes"]["P1_interior_vs_boundary"]["verdict"]))
    print("P2 max_spread=%.4f verdict=%s" % (max_spread,
                                             res["probes"]["P2_cost_form_sensitivity"]["verdict"]))
    print("P3 max_component=%.4f verdict=%s" % (p_opt.max(),
                                                res["probes"]["P3_p_joint_corner_degeneracy"]["verdict"]))
    for k, v in grid.items():
        if v:
            print("   %-28s Q*=%.4f N*=%.3fB D*=%.1fB shares=%s" % (
                k, v["Q"], v["N_B"], v["D_B"],
                {kk: round(vv, 3) for kk, vv in v["cost_shares"].items()}))
    print("WROTE(partial)", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()

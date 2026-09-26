"""M1o:main。三分支 KKT + log C 密集扫描 + 结构性转移识别 + L_ctx 敏感性。

裁定 2 = A_main_plus_D_reported_as_contrast:
  主定义 A = 活跃约束集变化(离散事件,不依赖阈值/步长/数值微分)
  D 定义一并报(含三步长对比),C 定义记录位置。
裁定 3 = C:KKT 为硬判据;Chinchilla 对照仅参考,不作 pass/fail。
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import brentq

from q3_common import (BUDGET_ANCHORS, ETA, G_SPECS, L_CTX_CRIT, L_CTX_DEFAULT,
                       L_CTX_FEASIBLE, Model, g_prime)

D_THRESHOLD = 0.05          # 裁定2 的 D 定义阈值(预声明,与探针一致)
SWEEP_STEPS = [0.5, 0.25, 0.125]
SWEEP_MAIN_STEP = 0.125
SWEEP_RANGE = (18.0, 25.0)


def sweep(model: Model, step: float, lo=SWEEP_RANGE[0], hi=SWEEP_RANGE[1]) -> list:
    pts = []
    for lc in np.arange(lo, hi + 1e-9, step):
        best, _ = model.solve_kkt(10.0 ** lc)
        if best is None:
            continue
        pts.append({"log10_C": float(lc), "Q": best["Q"], "N_B": best["N_B"],
                    "D_B": best["D_B"], "N_over_D": best["N_over_D"],
                    "branch": best["branch"], "active_set": best["active_set"],
                    "loss": best["loss"], "cost_shares": best["cost_shares"],
                    "share_order": "|".join(sorted(best["cost_shares"],
                                                   key=best["cost_shares"].get, reverse=True)),
                    "kkt_passed": best["kkt_passed"],
                    "mu_upper": best["multipliers"]["mu_upper"]})
    return pts


def locate_active_set_change(model: Model, lo: float, hi: float, tol=1e-4) -> float:
    """二分定位活跃约束集变化点(裁定2 主定义 A 的识别方法)。

    判别函数取「Q_le_1 是否在活跃集内」,离散 ⇒ 用二分而非数值微分。
    """
    def has_upper(lc):
        best, _ = model.solve_kkt(10.0 ** lc)
        return best is not None and "Q_le_1" in best["active_set"]

    a, b = lo, hi
    if has_upper(a) == has_upper(b):
        return float("nan")
    while b - a > tol:
        m = 0.5 * (a + b)
        if has_upper(m) == has_upper(a):
            a = m
        else:
            b = m
    return float(0.5 * (a + b))


def definition_A(model: Model, pts: list) -> dict:
    """活跃约束集变化。返回位置与 verdict。"""
    changes = []
    for i in range(1, len(pts)):
        if pts[i]["active_set"] != pts[i - 1]["active_set"]:
            loc = locate_active_set_change(model, pts[i - 1]["log10_C"], pts[i]["log10_C"])
            changes.append({"bracket": [pts[i - 1]["log10_C"], pts[i]["log10_C"]],
                            "located_log10_C": loc,
                            "from": pts[i - 1]["active_set"], "to": pts[i]["active_set"]})
    return {
        "definition": ("结构性转移 := 最优解处的活跃约束集 A(C) 发生变化。"
                       "本问中 A 的可变元素为 {Q ≤ 1}"),
        "identification": ("沿 log10 C 扫描活跃集与互补松弛乘子 mu;转移点 = mu 由 0 转正"
                           "(等价地 Q* 触及 1)的位置,用二分定位到 1e-4"),
        "depends_on_threshold": False,
        "depends_on_grid_step": False,
        "needs_numerical_differentiation": False,
        "changes": changes,
        "verdict": "TRANSITION_EXISTS" if changes else "NO_TRANSITION",
    }


def definition_C(pts: list) -> dict:
    """成本分项占比排序变化。"""
    ch = [{"at_log10_C": pts[i]["log10_C"], "from": pts[i - 1]["share_order"],
           "to": pts[i]["share_order"]}
          for i in range(1, len(pts)) if pts[i]["share_order"] != pts[i - 1]["share_order"]]
    return {"definition": "成本分项占比(C_train/C_Q/C_attn)的排序发生变化",
            "changes": ch, "n_changes": len(ch),
            "verdict": "TRANSITION_EXISTS" if ch else "NO_TRANSITION"}


def definition_D(model: Model, steps=SWEEP_STEPS) -> dict:
    """分配份额突变(一阶差分超阈)。**结论随步长翻转,故不作主定义。**"""
    table, cache = [], {}
    for st in steps:
        pts = sweep(model, st, 18.0, 22.0)      # 与 AI 意见支撑算例同范围,便于核对
        cache[st] = pts
        q = np.array([p["Q"] for p in pts])
        dq = np.abs(np.diff(q)) if len(q) > 1 else np.array([0.0])
        i = int(dq.argmax())
        table.append({"step": st, "n_points": len(pts),
                      "max_abs_dQ": float(dq.max()),
                      "at_log10_C": pts[i + 1]["log10_C"] if len(pts) > i + 1 else None,
                      "n_jumps_over_threshold": int((dq > D_THRESHOLD).sum()),
                      "verdict": ("TRANSITION_EXISTS" if dq.max() > D_THRESHOLD
                                  else "NO_TRANSITION")})
    return {
        "definition": f"若相邻扫描点间 |ΔQ*| 超过阈值 delta = {D_THRESHOLD},则判发生转移",
        "threshold": D_THRESHOLD,
        "grid_sensitivity_table": table,
        "verdict_at_main_step": next(
            (t["verdict"] for t in table if t["step"] == SWEEP_MAIN_STEP), None),
        "why_not_main_definition": (
            "结论是扫描步长的函数:饱和前 Q* 光滑上升且斜率稳定(约 +0.149),"
            "一阶差分 ≈ 斜率 × 步长,与固定阈值比较不是网格不变量"),
    }, cache


def derivative_at_saturation(pts: list, sat_log10_C: float, window=0.6) -> dict:
    """饱和点附近 dQ*/dlogC 的序列与符号(计划 §6.4:上游写成『由负转零』是符号错误)。"""
    seq = []
    for i in range(1, len(pts)):
        lo_i, hi_i = pts[i - 1]["log10_C"], pts[i]["log10_C"]
        if not np.isnan(sat_log10_C) and abs(hi_i - sat_log10_C) > window:
            continue
        d = (pts[i]["Q"] - pts[i - 1]["Q"]) / (hi_i - lo_i)
        # 跨越饱和点的区间:差商既非左导数也非右导数,须单列不参与符号判定
        straddles = (not np.isnan(sat_log10_C)) and (lo_i < sat_log10_C < hi_i)
        seq.append({"log10_C": hi_i, "Q": pts[i]["Q"], "dQ_dlogC": float(d),
                    "interval": [lo_i, hi_i], "straddles_saturation": bool(straddles)})
    before = [s["dQ_dlogC"] for s in seq
              if not s["straddles_saturation"] and s["interval"][1] <= sat_log10_C]
    after = [s["dQ_dlogC"] for s in seq
             if not s["straddles_saturation"] and s["interval"][0] >= sat_log10_C]
    sign = "undetermined"
    if before and after:
        if min(before) > 0 and max(np.abs(np.array(after))) < 1e-12:
            sign = "positive_to_zero"
        elif max(before) < 0 and max(np.abs(np.array(after))) < 1e-12:
            sign = "negative_to_zero"
    return {"sequence": seq, "sign_at_saturation": sign,
            "left_derivative_range": [float(min(before)), float(max(before))] if before else None,
            "right_derivative_max_abs": float(max(np.abs(np.array(after)))) if after else None,
            "straddling_interval_excluded": next(
                (s for s in seq if s["straddles_saturation"]), None),
            "upstream_card_said": "negative_to_zero",
            "upstream_card_is_wrong": sign == "positive_to_zero",
            "note": ("方法卡与选择卡称『由负转零』;实测为由正转零。论文不得沿用错误表述。"
                     "跨越饱和点的那个区间(部分步长差商)已单列排除,不参与符号判定")}


def anchors(model: Model, budgets=BUDGET_ANCHORS) -> list:
    """三档报告锚点精确求解(不复用扫描网格点)。"""
    out = []
    for C in budgets:
        best, cands = model.solve_kkt(C)
        if best is None:
            out.append({"C": C, "status": "no_solution",
                        "n_branch_candidates": len(cands)})
            continue
        num = model.solve_numeric(C)
        rec = dict(best)
        rec["C"] = C
        rec["branch_candidates"] = [
            {"branch": c["branch"], "Q": c["Q"], "loss": c["loss"],
             "kkt_passed": c["kkt_passed"],
             "budget_violation_rel": c["budget_violation_rel"]} for c in cands]
        if num is not None:
            gap = (best["loss"] - num["loss"]) / max(abs(num["loss"]), 1e-300)
            rec["numeric_check"] = {
                "numeric_loss": num["loss"], "kkt_loss": best["loss"],
                "loss_relative_gap": float(gap),
                "numeric_better_by_rel": float(max(gap, 0.0)),
                "active_set_agreement": sorted(num["active_set"]) == sorted(best["active_set"]),
                "numeric_active_set": num["active_set"],
                "purpose": "仅用于 fallback 触发判定,不作结果报出",
            }
        out.append(rec)
    return out


def cost_form_comparison(law, Q0, L_ctx=L_CTX_DEFAULT, budgets=BUDGET_ANCHORS) -> dict:
    """Q3b:三类 g × 三档预算 = 9 组合。"""
    grid, by_budget = {}, {}
    for C in budgets:
        qs = []
        for form in G_SPECS:
            m = Model(law, Q0=Q0, L_ctx=L_ctx, form=form)
            best, _ = m.solve_kkt(C)
            key = f"C{C:.0e}_{form}"
            if best is None:
                grid[key] = None
                continue
            grid[key] = {"Q": best["Q"], "N_B": best["N_B"], "D_B": best["D_B"],
                         "loss": best["loss"], "branch": best["branch"],
                         "cost_shares": best["cost_shares"],
                         "kkt_passed": best["kkt_passed"]}
            qs.append(best["Q"])
        by_budget[f"{C:.0e}"] = {"Q_values": qs,
                                 "spread": float(max(qs) - min(qs)) if qs else None}
    spreads = {k: v["spread"] for k, v in by_budget.items() if v["spread"] is not None}
    return {
        "grid": grid, "by_budget": by_budget,
        "max_spread": float(max(spreads.values())) if spreads else None,
        "spread_concentrated_at": max(spreads, key=spreads.get) if spreads else None,
        "answer_to_problem_question": (
            "成本函数选择的影响集中在预算紧张时;高预算档三类 g 给出一致的 Q*"),
        "prohibited_claim": ("不得笼统写『各档预算最优质量恒为 1』—— 低预算档明确不是。"
                             "该笼统说法亦为隐藏文本伪造断言之一,本结果是其反证"),
        "improvement_not_done": ("本轮未新增第四类 g(时间预算不允许),如实记录"),
    }


def lctx_sensitivity(law, Q0, C=1e22, form="exponential") -> dict:
    """Q3d:L_ctx^crit 复算 + C7 五档敏感性。"""
    rows = {}
    for L in L_CTX_FEASIBLE:
        m = Model(law, Q0=Q0, L_ctx=L, form=form)
        best, _ = m.solve_kkt(C)
        if best is None:
            continue
        rows[str(L)] = {"Q": best["Q"], "N_B": best["N_B"], "D_B": best["D_B"],
                        "N_over_D": best["N_over_D"], "loss": best["loss"],
                        "cost_shares": best["cost_shares"],
                        "attn_over_train": float(ETA * L / 6.0),
                        "above_crit": bool(L > L_CTX_CRIT),
                        "branch": best["branch"]}
    nds = [v["N_over_D"] for v in rows.values()]
    ns = [v["N_B"] for v in rows.values()]
    ds = [v["D_B"] for v in rows.values()]
    return {
        "L_ctx_crit_analytic": L_CTX_CRIT,
        "L_ctx_crit_derivation": ("C_attn/C_train = eta*N*D*L_ctx/(6*N*D) = eta*L_ctx/6;"
                                  "令其=1 得 L_ctx = 6/eta = 30000"),
        "L_ctx_crit_recomputed": float(6.0 / ETA),
        "feasible_from_C7": L_CTX_FEASIBLE,
        "above_crit": [L for L in L_CTX_FEASIBLE if L > L_CTX_CRIT],
        "by_L_ctx": rows,
        "N_over_D_relative_spread": float((max(nds) - min(nds)) / min(nds)) if nds else None,
        "N_B_change_pct": float((ns[-1] - ns[0]) / ns[0] * 100.0) if ns else None,
        "D_B_change_pct": float((ds[-1] - ds[0]) / ds[0] * 100.0) if ds else None,
        "accurate_statement": "跨临界显著压缩可负担规模,几乎不改变相对配比",
        "writing_red_lines": [
            "L_ctx_crit = 30000 仅为两类成本相等的临界尺度,不是最优上下文长度",
            "准确表述为『跨临界显著压缩可负担规模,几乎不改变相对配比』,而非『最优配置显著偏移』",
            "AI 曾断言『L_ctx 只等价于预算缩放』,实测仅近似且随 L_ctx 失效"
            "(N:D 相对差 1.97e-2 → 3.34e-1),强版本不得入论文",
        ],
    }


def chinchilla_reference(model: Model, budgets=BUDGET_ANCHORS) -> dict:
    """裁定3=C:Chinchilla 对照仅作参考,不作 pass/fail。"""
    al, be, A, B, ga, Q0 = model.al, model.be, model.A, model.B, model.ga, model.Q0
    rows = {}
    for C in budgets:
        # 无质量投入(Δg=0)时本律自身的最优 D/N:alpha*A*N^-alpha = beta*B*(D*Q0^ga)^-beta
        c18 = C / model.k / 1e18
        def f(lnN):
            N = np.exp(lnN)
            D = c18 / N
            return al * A * N ** (-al) - be * B * (D * Q0 ** ga) ** (-be)
        try:
            lnN = brentq(f, np.log(1e-6), np.log(1e6), xtol=1e-14, maxiter=300)
        except Exception:
            continue
        N = float(np.exp(lnN))
        rows[f"{C:.0e}"] = {"N_B": N, "D_B": float(c18 / N),
                            "implied_D_over_N": float(c18 / N / N)}
    return {
        "reference_only": True,
        "not_a_pass_fail_criterion": True,
        "law_implied_D_over_N_by_budget": rows,
        "drift_exponent_dlog_DN_dlogC": float((al - be) / (al + be)),
        "chinchilla_folklore_ratio": 20.0,
        "why_not_a_hard_criterion": (
            "本律隐含 D/N 随预算漂移而非常数 20(20 tokens/param 出自 Chinchilla "
            "Approach 1/2 的 a≈b≈0.5;本律用 Approach 3 的 alpha≠beta)。"
            "把 20 当硬判据会拒绝本律自身的真最优解"),
        "external_anchor_claim_is_void": (
            "本律 B1 侧参数与 Chinchilla Approach-3 常数按十亿单位折算后数值同一"
            "(相对差 9.4e-6 ~ 4.4e-4) ⇒ 以 Chinchilla 对照本律等于自证"),
        "constants_verified_against_paper": False,
        "caveat": "上述 Chinchilla 常数由 AI 凭记忆复现,引用前须核原文(Hoffmann et al. 2022)",
    }


def dldp_direction(model: Model, N_B: float, D_B: float, Q: float) -> dict:
    """裁定1 的 C 辅线:只报 dL/dp_i 的符号与域间排序(kappa 无关),不报 p*。"""
    import csv
    from q3_common import ROOT
    src = ROOT / "results/Q1/experiments/round1/tables/q1c_coefficients.csv"
    rows = [r for r in csv.DictReader(src.open(encoding="utf-8-sig"))
            if r["method"] == "M0c"]
    w = np.array([float(r["coef"]) for r in rows])
    feats = [r["feature"] for r in rows]
    w_c = w - w.mean()
    # b = kappa*(w - wbar),kappa < 0(Q2 q2_kappa_treatment)。dL/dp_i ∝ -b_i ∝ w_c_i
    order = np.argsort(-w_c)     # w_c 最大者 dL/dp_i 最大(增配该域最伤 Loss)
    hi, lo = feats[int(order[0])], feats[int(order[-1])]
    sign_ok = bool(w_c[int(order[0])] > 0 > w_c[int(order[-1])])
    return {
        "reported": "sign_and_ranking_only",
        "kappa_free": True,
        "w_source": str(src.relative_to(ROOT)).replace("\\", "/"),
        "n_domains": len(feats),
        "ranking_worst_to_best": [feats[int(i)] for i in order],
        "dL_dp_ratio_is_kappa_free": "dL/dp_i ÷ dL/dp_j = b_i/b_j",
        "highest_marginal_loss_domain": hi,
        "lowest_marginal_loss_domain": lo,
        "sign_coherence_ok": sign_ok,
        "p_star_not_reported": True,
        "absolute_magnitude_not_reported": True,
        "why_p_is_fixed": ("P3 实测角点退化:b^T z_p 对 p 线性 ⇒ 单纯形最优在顶点,"
                           "最大分量 1.0000(全给 dm_mathematics)。论证须本队自撰(GC9)"),
        "reference_point": {"N_B": N_B, "D_B": D_B, "Q": Q},
    }

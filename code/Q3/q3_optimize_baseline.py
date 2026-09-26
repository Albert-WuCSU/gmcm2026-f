"""M0o:usable_baseline(HD-2 已声明的 Chinchilla 经验配置)+ M0o' 诊断项。

M0o  固定 D/N = 20(Chinchilla Approach 1/2 的 ~20 tokens/param)、Q = Q0(不投质量)。
     **按方法卡定义原样实现,不改动**(baseline 由 HD-2 声明,改动须使用者裁定)。
M0o' 同 Q = Q0 但 D/N 自由。**诊断项,不得作为官方 baseline 报出**(计划 §5.3),
     仅用于把 M1o−M0o 的差距分解为「质量通道」与「比值被强制」两部分。
"""
from __future__ import annotations

import math

from q3_common import R_CHINCHILLA, Model


def solve_M0o(model: Model, C: float) -> dict:
    """D/N = R_CHINCHILLA, Q = Q0, Δg = 0 ⇒ k·N·D·1e18 = C 有闭式。"""
    N_B = math.sqrt(C / (R_CHINCHILLA * model.k * 1e18))
    D_B = R_CHINCHILLA * N_B
    Q = model.Q0
    parts = model.cost_parts(N_B, D_B, Q)
    tot = sum(parts.values())
    return {
        "method_id": "M0o", "role": "usable_baseline",
        "spec": "fixed D/N = 20 (Chinchilla Approach 1/2 empirical ratio), Q = Q0",
        "r_chinchilla": R_CHINCHILLA,
        "r_chinchilla_source": ("Hoffmann et al. 2022 Approach 1/2 的 ~20 tokens/param 经验比例;"
                               "与本律自身最优比值不同,见 chinchilla_reference"),
        "N_B": float(N_B), "D_B": float(D_B), "Q": float(Q),
        "loss": float(model.loss(N_B, D_B, Q)),
        "cost_total": float(tot),
        "cost_parts": {k: float(v) for k, v in parts.items()},
        "cost_shares": {k: float(v / tot) for k, v in parts.items()},
        "budget_violation_rel": float((tot - C) / C),
        "D_over_N": float(D_B / N_B),
        "has_quality_channel": False,
        "degeneracy_note": "无 Q 与 p 通道,退化是设计使然而非缺陷(方法卡 Baseline validity)",
    }


def solve_M0o_prime(model: Model, C: float) -> dict | None:
    """诊断项:Q = Q0 固定、D/N 自由。等价于 KKT 的下界段。"""
    cands = model.branch_lower(C)
    if not cands:
        return None
    r = min(cands, key=lambda x: x["loss"])
    return {
        "method_id": "M0o_prime", "role": "diagnostic_reference_NOT_baseline",
        "spec": "Q = Q0 fixed, D/N free (law's own no-quality optimum)",
        "N_B": r["N_B"], "D_B": r["D_B"], "Q": r["Q"], "loss": r["loss"],
        "cost_total": r["cost_total"], "cost_shares": r["cost_shares"],
        "budget_violation_rel": r["budget_violation_rel"],
        "D_over_N": r["D_over_N"],
        "must_not": "不得作为官方 baseline 报出(计划 §5.3);M0o 的定义是否改动属未裁定项",
    }


def gap_decomposition(loss_M1o: float, m0o: dict, m0o_p: dict | None) -> dict:
    """差距分解(计划 §5.3):三个数必须同时报,不得只报 gap_reported。"""
    out = {
        "gap_reported": float(m0o["loss"] - loss_M1o),
        "gap_quality_only": None,
        "gap_ratio_handicap": None,
        "handicap_share_of_reported_pct": None,
        "why": ("HD-2 为相对 baseline 制。M0o 的 D/N 被强制为 20,而本律自身的无质量投入最优比值不同,"
                "故 gap_reported 含一部分与质量通道无关的虚增"),
        "status": "M0o 定义未改动;是否改动属使用者未裁定项",
    }
    if m0o_p is not None:
        out["gap_quality_only"] = float(m0o_p["loss"] - loss_M1o)
        out["gap_ratio_handicap"] = float(m0o["loss"] - m0o_p["loss"])
        if out["gap_reported"] != 0.0:
            out["handicap_share_of_reported_pct"] = float(
                out["gap_ratio_handicap"] / out["gap_reported"] * 100.0)
    return out

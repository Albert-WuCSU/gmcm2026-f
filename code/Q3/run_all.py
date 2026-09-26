"""Q3 round1 装配:跑 M1o 与 M0o,写 tables / metrics / figures / run_summary.json。

用法:cd code/Q3 && PYTHONIOENCODING=utf-8 python run_all.py
"""
from __future__ import annotations

import csv
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import scipy

from q3_common import (BUDGET_ANCHORS, ETA, L_CTX_CRIT, L_CTX_DEFAULT, Model,
                       Q0_DEFAULT, R_CHINCHILLA, ROOT, SEED, load_law_params)
from q3_optimize_baseline import gap_decomposition, solve_M0o, solve_M0o_prime
from q3_optimize_main import (D_THRESHOLD, SWEEP_MAIN_STEP, SWEEP_RANGE, anchors,
                              chinchilla_reference, cost_form_comparison, definition_A,
                              definition_C, definition_D, derivative_at_saturation,
                              dldp_direction, lctx_sensitivity, sweep)

OUT = ROOT / "results/Q3/experiments/round1"
DECISION_IDS = ["q3_p_joint_optimization", "q3_structural_transition_definition",
                "q3_optimum_acceptability_criterion"]
Q0 = Q0_DEFAULT
FORM = "exponential"


def write_csv(path: Path, rows: list, cols: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c) for c in cols})


def main() -> None:
    t0 = time.time()
    warnings: list[str] = []
    for sub in ("tables", "metrics", "figures"):
        (OUT / sub).mkdir(parents=True, exist_ok=True)

    law = load_law_params()
    model = Model(law, Q0=Q0, L_ctx=L_CTX_DEFAULT, form=FORM)

    # ---- M1o ----
    t_m1 = time.time()
    anchor_rows = anchors(model)
    pts = sweep(model, SWEEP_MAIN_STEP)
    defA = definition_A(model, pts)
    defC = definition_C(pts)
    defD, d_cache = definition_D(model)
    sat = (defA["changes"][0]["located_log10_C"] if defA["changes"] else float("nan"))
    deriv = derivative_at_saturation(pts, sat)
    lctx = lctx_sensitivity(law, Q0)
    cforms = cost_form_comparison(law, Q0)
    chin = chinchilla_reference(model)
    a22 = next((a for a in anchor_rows if a.get("C") == 1e22 and "N_B" in a), None)
    dldp = (dldp_direction(model, a22["N_B"], a22["D_B"], a22["Q"]) if a22 else None)
    t_m1 = time.time() - t_m1

    if not all(p["kkt_passed"] for p in pts):
        n_bad = sum(1 for p in pts if not p["kkt_passed"])
        warnings.append(f"log C 扫描中有 {n_bad}/{len(pts)} 点未通过 KKT 硬判据")
    if dldp and not dldp["sign_coherence_ok"]:
        warnings.append("dL/dp 符号自洽检查未通过")
    if not deriv["upstream_card_is_wrong"]:
        warnings.append(f"饱和点导数符号判定为 {deriv['sign_at_saturation']},"
                        "与预期 positive_to_zero 不符,须人工核对")

    # ---- M0o + 诊断 ----
    t_m0 = time.time()
    m0_rows, m0p_rows, gaps = [], [], []
    for a in anchor_rows:
        C = a["C"]
        m = Model(law, Q0=Q0, L_ctx=L_CTX_DEFAULT, form=FORM)
        b0 = solve_M0o(m, C)
        b0p = solve_M0o_prime(m, C)
        m0_rows.append(dict(b0, C=C))
        if b0p:
            m0p_rows.append(dict(b0p, C=C))
        if "loss" in a:
            gaps.append(dict(gap_decomposition(a["loss"], b0, b0p), C=C))
    t_m0 = time.time() - t_m0

    # ---- 预声明指标 ----
    superiority = []
    for a, b in zip(anchor_rows, m0_rows):
        if "loss" not in a:
            continue
        superiority.append({"C": a["C"], "M1o_loss": a["loss"], "M0o_loss": b["loss"],
                            "M1o_better": bool(a["loss"] < b["loss"])})
    feasible_all = all(abs(a.get("budget_violation_rel", 1.0)) < 1e-6 for a in anchor_rows
                       if "budget_violation_rel" in a)
    stability = [{"C": a["C"], **a["numeric_check"]} for a in anchor_rows
                 if "numeric_check" in a]

    # ---- fallback 触发 ----
    trig_gap = [s for s in stability if s["numeric_better_by_rel"] > 1e-6]
    trig_set = [s for s in stability if not s["active_set_agreement"]]
    observed = bool(trig_gap or trig_set)
    fallback = {
        "fallback_id": "M2o", "implemented": False,
        "condition": ("分段 KKT 边界枚举不完备(数值解优于全部解析分支,Loss 相对差 > 1e-6)"
                      " 或 分段 KKT 与数值解给出不同活跃约束集"),
        "observed": observed,
        "evidence": {"loss_gap_violations": trig_gap, "active_set_mismatches": trig_set,
                     "max_numeric_advantage_rel": (max((s["numeric_better_by_rel"]
                                                        for s in stability), default=0.0)),
                     "all_active_sets_agree": all(s["active_set_agreement"]
                                                  for s in stability)},
    }
    if observed:
        warnings.append("M2o 触发条件成立 —— 须停下报使用者,不得自行切换")

    # ---- tables ----
    write_csv(OUT / "tables/q3_optimal_by_budget.csv",
              [{"C": f"{a['C']:.0e}", "branch": a.get("branch"),
                "N_B": a.get("N_B"), "D_B": a.get("D_B"), "Q": a.get("Q"),
                "D_over_N": a.get("D_over_N"), "loss": a.get("loss"),
                "share_C_train": (a.get("cost_shares") or {}).get("C_train"),
                "share_C_Q": (a.get("cost_shares") or {}).get("C_Q"),
                "share_C_attn": (a.get("cost_shares") or {}).get("C_attn"),
                "kkt_passed": a.get("kkt_passed"),
                "budget_violation_rel": a.get("budget_violation_rel")} for a in anchor_rows],
              ["C", "branch", "N_B", "D_B", "Q", "D_over_N", "loss", "share_C_train",
               "share_C_Q", "share_C_attn", "kkt_passed", "budget_violation_rel"])

    write_csv(OUT / "tables/q3_cost_form_comparison.csv",
              [{"key": k, "Q": (v or {}).get("Q"), "N_B": (v or {}).get("N_B"),
                "D_B": (v or {}).get("D_B"), "loss": (v or {}).get("loss"),
                "branch": (v or {}).get("branch")}
               for k, v in cforms["grid"].items()],
              ["key", "Q", "N_B", "D_B", "loss", "branch"])

    write_csv(OUT / "tables/q3_transition_definitions.csv", [
        {"definition": "A 活跃约束集变化", "verdict": defA["verdict"],
         "location_log10_C": (defA["changes"][0]["located_log10_C"] if defA["changes"] else None),
         "depends_on_threshold": False, "depends_on_grid_step": False},
        {"definition": "C 成本分项占比排序变化", "verdict": defC["verdict"],
         "location_log10_C": (defC["changes"][0]["at_log10_C"] if defC["changes"] else None),
         "depends_on_threshold": False, "depends_on_grid_step": True},
        {"definition": f"D 分配份额突变(delta={D_THRESHOLD})",
         "verdict": defD["verdict_at_main_step"], "location_log10_C": None,
         "depends_on_threshold": True, "depends_on_grid_step": True},
    ], ["definition", "verdict", "location_log10_C", "depends_on_threshold",
        "depends_on_grid_step"])

    write_csv(OUT / "tables/q3_lctx_sensitivity.csv",
              [{"L_ctx": k, "above_crit": v["above_crit"], "Q": v["Q"], "N_B": v["N_B"],
                "D_B": v["D_B"], "N_over_D": v["N_over_D"], "loss": v["loss"],
                "attn_over_train": v["attn_over_train"]}
               for k, v in lctx["by_L_ctx"].items()],
              ["L_ctx", "above_crit", "Q", "N_B", "D_B", "N_over_D", "loss",
               "attn_over_train"])

    write_csv(OUT / "tables/q3_chinchilla_reference.csv",
              [{"C": k, "law_implied_D_over_N": v["implied_D_over_N"],
                "chinchilla_ratio": R_CHINCHILLA, "reference_only": True}
               for k, v in chin["law_implied_D_over_N_by_budget"].items()],
              ["C", "law_implied_D_over_N", "chinchilla_ratio", "reference_only"])

    if dldp:
        write_csv(OUT / "tables/q3_dldp_direction.csv",
                  [{"rank": i + 1, "domain": d} for i, d in
                   enumerate(dldp["ranking_worst_to_best"])], ["rank", "domain"])

    write_csv(OUT / "tables/q3_baseline_gap_decomposition.csv",
              [{"C": f"{g['C']:.0e}", "gap_reported": g["gap_reported"],
                "gap_quality_only": g["gap_quality_only"],
                "gap_ratio_handicap": g["gap_ratio_handicap"],
                "handicap_share_pct": g["handicap_share_of_reported_pct"]} for g in gaps],
              ["C", "gap_reported", "gap_quality_only", "gap_ratio_handicap",
               "handicap_share_pct"])

    # ---- Type 1 诊断图(内部用,非论文图)----
    figs = []
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        lcs = [p["log10_C"] for p in pts]
        fig, ax = plt.subplots(3, 1, figsize=(7.2, 8.4), sharex=True)
        ax[0].plot(lcs, [p["Q"] for p in pts], lw=1.4)
        if not np.isnan(sat):
            for a_ in ax:
                a_.axvline(sat, ls="--", lw=1.0, color="crimson")
            ax[0].annotate(f"active-set change\nlog10C={sat:.4f}", (sat, 0.6),
                           xytext=(sat + 0.4, 0.55), fontsize=8, color="crimson")
        ax[0].set_ylabel("Q*")
        ax[1].semilogy(lcs, [p["N_B"] for p in pts], label="N* (B params)")
        ax[1].semilogy(lcs, [p["D_B"] for p in pts], label="D* (B tokens)")
        ax[1].legend(fontsize=8)
        ax[1].set_ylabel("scale")
        for key in ("C_train", "C_Q", "C_attn"):
            ax[2].plot(lcs, [p["cost_shares"][key] for p in pts], label=key)
        ax[2].legend(fontsize=8)
        ax[2].set_ylabel("cost share")
        ax[2].set_xlabel("log10 C (FLOPs)")
        ax[0].set_title("Q3 diagnostic (Type 1, not a paper figure): optimal path vs budget")
        fig.tight_layout()
        p1 = OUT / "figures/diag_q3_optimal_path.png"
        fig.savefig(p1, dpi=130)
        plt.close(fig)
        figs.append(str(p1.relative_to(ROOT)).replace("\\", "/"))

        fig, ax = plt.subplots(figsize=(7.2, 4.0))
        for st, cache_pts in d_cache.items():
            q = np.array([p["Q"] for p in cache_pts])
            x = [p["log10_C"] for p in cache_pts][1:]
            ax.plot(x, np.abs(np.diff(q)), marker="o", ms=3, lw=1.1, label=f"step={st}")
        ax.axhline(D_THRESHOLD, ls="--", color="crimson", lw=1.0,
                   label=f"threshold {D_THRESHOLD}")
        ax.set_xlabel("log10 C (FLOPs)")
        ax.set_ylabel("|dQ*| between adjacent points")
        ax.set_title("Q3 diagnostic (Type 1): definition-D verdict flips with grid step")
        ax.legend(fontsize=8)
        fig.tight_layout()
        p2 = OUT / "figures/diag_q3_definitionD_grid_sensitivity.png"
        fig.savefig(p2, dpi=130)
        plt.close(fig)
        figs.append(str(p2.relative_to(ROOT)).replace("\\", "/"))
    except Exception as e:                                    # noqa: BLE001
        warnings.append(f"诊断图未生成:{type(e).__name__}: {e}")

    # ---- metrics ----
    m1 = {"schema_version": 1, "method_id": "M1o", "role": "main",
          "approved_decision_ids": DECISION_IDS,
          "form": "min E + A*N^-alpha + B*(D*Q^gamma)^-beta s.t. k*N*D + D*dg(Q) <= C, k = 6 + eta*L_ctx",
          "z_p": 0, "decision_variables": ["N", "D", "Q"], "kkt_dimension": 3,
          "law_params": law, "anchors": anchor_rows,
          "sweep": {"range_log10_C": list(SWEEP_RANGE), "step": SWEEP_MAIN_STEP,
                    "n_points": len(pts), "points": pts},
          "structural_transition": {
              "main_definition_A": defA, "definition_C": defC, "definition_D": defD,
              "derivative_at_saturation": deriv,
              "joint_reading": (
                  "A 测『活跃约束集是否改变』⇒ 发生且位置明确;D 测『是否有突跳』⇒ 判不出。"
                  "两者合读:转移形态为连续饱和而非突跳。D 的结论随步长翻转,故不作主定义"),
              "three_definitions_three_answers": {
                  "A": (defA["changes"][0]["located_log10_C"] if defA["changes"] else None),
                  "C": (defC["changes"][0]["at_log10_C"] if defC["changes"] else None),
                  "D": defD["verdict_at_main_step"]},
          },
          "cost_form_comparison": cforms, "lctx_sensitivity": lctx,
          "chinchilla_reference": chin, "dldp_direction": dldp,
          "runtime_seconds": t_m1}
    (OUT / "metrics/q3_M1o.json").write_text(
        json.dumps(m1, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    m0 = {"schema_version": 1, "method_id": "M0o", "role": "usable_baseline",
          "approved_decision_ids": DECISION_IDS,
          "spec": "fixed D/N = 20 (Chinchilla empirical), Q = Q0; implemented as carded, unmodified",
          "by_budget": m0_rows, "diagnostic_M0o_prime": m0p_rows,
          "baseline_gap_decomposition": gaps, "runtime_seconds": t_m0}
    (OUT / "metrics/q3_M0o.json").write_text(
        json.dumps(m0, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    # ---- run_summary ----
    tables = sorted(str(p.relative_to(ROOT)).replace("\\", "/")
                    for p in (OUT / "tables").glob("*.csv"))
    summary = {
        "schema_version": 1, "question": "Q3", "round": "round1",
        "implementation_target": "python", "random_seed": SEED,
        "approved_decision_id": DECISION_IDS,
        "methods": [
            {"method_id": "M1o", "role": "main", "script": "code/Q3/q3_optimize_main.py",
             "status": "success", "execution_time_seconds": round(t_m1, 3),
             "input_files": [law["source"],
                             "results/Q1/experiments/round1/tables/q1c_coefficients.csv"],
             "output_files": tables + ["results/Q3/experiments/round1/metrics/q3_M1o.json"],
             "figure_files": figs,
             "metrics_summary": {
                 "anchor_Q": {f"{a['C']:.0e}": a.get("Q") for a in anchor_rows},
                 "anchor_loss": {f"{a['C']:.0e}": a.get("loss") for a in anchor_rows},
                 "transition_A_log10_C": (defA["changes"][0]["located_log10_C"]
                                          if defA["changes"] else None),
                 "transition_C_log10_C": (defC["changes"][0]["at_log10_C"]
                                          if defC["changes"] else None),
                 "transition_D_verdict": defD["verdict_at_main_step"],
                 "cost_form_max_spread": cforms["max_spread"]},
             "warnings": [], "errors": []},
            {"method_id": "M0o", "role": "usable_baseline",
             "script": "code/Q3/q3_optimize_baseline.py", "status": "success",
             "execution_time_seconds": round(t_m0, 3),
             "input_files": [law["source"]],
             "output_files": ["results/Q3/experiments/round1/metrics/q3_M0o.json"],
             "figure_files": [],
             "metrics_summary": {"loss": {f"{b['C']:.0e}": b["loss"] for b in m0_rows},
                                 "D_over_N": R_CHINCHILLA},
             "warnings": [], "errors": []},
        ],
        "comparison": {
            "predeclared_metric_1_optimal_loss": superiority,
            "predeclared_metric_2_feasibility": {
                "criterion": "(cost - C)/C < 1e-6", "all_passed": feasible_all},
            "predeclared_metric_3_stability": stability,
            "kkt_vs_numeric": {
                "max_loss_gap": max((s["numeric_better_by_rel"] for s in stability),
                                    default=0.0),
                "active_set_agreement": all(s["active_set_agreement"] for s in stability),
                "purpose": "仅用于 fallback 触发判定,不作结果报出"},
        },
        "fallback_trigger": fallback,
        "Q0_spec": {"value": Q0, "source": "Q1 实测域级 Q 范围 0.2233-0.3815 的上端附近",
                    "status": "未经使用者裁定,可被否决",
                    "amb_q2_3_note": ("Q1 经验域级 Q 与 B7 设计网格 Q(0.1-1.0)的尺度对齐未解决;"
                                      "gamma 的解释绑定在 B7 设计刻度上")},
        "baseline_gap_decomposition": gaps,
        "structural_transition": m1["structural_transition"],
        "kkt_audit": {"predeclared_tolerances": {"feasibility": Model.TOL_FEAS,
                                                 "stationarity_rel": Model.TOL_STAT,
                                                 "multiplier": Model.TOL_MULT},
                      "criterion_is_hard_pass_fail": True,
                      "anchors": [{"C": f"{a['C']:.0e}", "branch": a.get("branch"),
                                   "kkt_passed": a.get("kkt_passed"),
                                   "checks": a.get("kkt_checks"),
                                   "multipliers": a.get("multipliers"),
                                   "n_branch_candidates": a.get("n_branch_candidates")}
                                  for a in anchor_rows],
                      "sweep_all_passed": all(p["kkt_passed"] for p in pts)},
        "chinchilla_reference": chin,
        "lctx_sensitivity": {k: v for k, v in lctx.items() if k != "by_L_ctx"},
        "writing_red_lines": lctx["writing_red_lines"] + [
            cforms["prohibited_claim"],
            "饱和点处 dQ*/dlogC 为由正转零;方法卡与选择卡的『由负转零』是符号错误,不得沿用",
            "不得声称 Chinchilla 对照构成外部锚点(本律与其数值同一)",
        ],
        "extrapolation_disclosure": {
            "B1_observed_ranges": {"N_B": [0.070542, 11.965825], "D_B": [0.1, 299.9]},
            "extrapolation_factor": {
                f"{a['C']:.0e}": {"N": (a["N_B"] / 11.965825 if "N_B" in a else None),
                                  "D": (a["D_B"] / 299.9 if "D_B" in a else None)}
                for a in anchor_rows},
            "amb_q3_3": "高预算档为外推,须结合 B9/B10 可信度边界,不得表述为可靠预测"},
        "supersedes_upstream_numbers": {
            "why": ("探针与方法卡/选择卡引用的转移位置是 0.25 步长下的网格点;"
                    "本轮主定义 A 用二分定位到 1e-4,C 定义用 0.125 步长扫描,"
                    "两者均比上游更精。论文须用本轮数值,不得再引用网格值作为实测位置"),
            "definition_A_location": {
                "upstream_grid_value": 21.5,
                "this_round_bisected": (defA["changes"][0]["located_log10_C"]
                                        if defA["changes"] else None),
                "relation": "refinement_not_contradiction"},
            "definition_C_location": {
                "upstream_grid_value": 22.75,
                "this_round_finer_grid": (defC["changes"][0]["at_log10_C"]
                                          if defC["changes"] else None),
                "relation": "refinement_not_contradiction"},
            "decision_ledger_untouched": ("methods/Q3/q3_decisions.jsonl 的 rationale 为使用者原话,"
                                          "不因本轮数值细化而改动"),
        },
        "not_done_this_round": [
            "未新增第四类 g(Q)(题目『或改进』部分,时间预算不允许)",
            "figures 仅含 Type 1 诊断图,论文图留到装配阶段(figure-table-planner)",
            "Q0 取值未经使用者裁定",
            "M0o 定义是否改为本律自身最优比值,属使用者未裁定项",
        ],
        "environment": {"python": sys.version.split()[0], "numpy": np.__version__,
                        "scipy": scipy.__version__, "platform": platform.platform()},
        "total_runtime_seconds": round(time.time() - t0, 3),
        "warnings": warnings,
    }
    (OUT / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"M1o anchors: " + ", ".join(
        f"{a['C']:.0e}->Q={a.get('Q'):.4f}/{a.get('branch')}" for a in anchor_rows
        if "Q" in a))
    print(f"transition A: log10C={summary['methods'][0]['metrics_summary']['transition_A_log10_C']}"
          f" | C: {summary['methods'][0]['metrics_summary']['transition_C_log10_C']}"
          f" | D: {defD['verdict_at_main_step']}")
    print("derivative at saturation:", deriv["sign_at_saturation"])
    print("gap decomposition:", [(f"{g['C']:.0e}", round(g["gap_reported"], 6),
                                  round(g["gap_quality_only"] or 0, 6),
                                  round(g["gap_ratio_handicap"] or 0, 6)) for g in gaps])
    print("fallback observed:", fallback["observed"])
    print("warnings:", len(warnings))
    for w in warnings:
        print("  -", w)
    print(f"total {summary['total_runtime_seconds']}s -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

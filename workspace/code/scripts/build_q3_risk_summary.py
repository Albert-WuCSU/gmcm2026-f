"""把 Q3 探针原始输出装配为契约格式的 risk_probe_summary.json。

契约七字段（AGENTS.md Risk Probe Contract）：executability / data_coverage /
assumption_checks / output_degeneracy / perturbation_sensitivity / scale_check / verdict
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "workspace/data/q3_probe_optimization.json"
OUT = ROOT / "methods/Q3/probes/risk_probe_summary.json"
TS = "2026-09-25T15:45:00+08:00"


def main() -> None:
    d = json.loads(SRC.read_text(encoding="utf-8"))
    p = d["probes"]
    p1, p2, p3 = p["P1_interior_vs_boundary"], p["P2_cost_form_sensitivity"], p["P3_p_joint_corner_degeneracy"]
    p4, p5, p6 = p["P4_structural_transition"], p["P5_L_ctx_crossing_crit"], p["P6_extrapolation_distance"]

    common_assumptions = [
        {"check": "objective_from_Q2_is_differentiable", "status": "PASS",
         "evidence": "L = E + A*N^-alpha + B*(D*Q^gamma)^-beta 解析可导，满足 KKT 需求"},
        {"check": "Q2_params_are_B1_side_real_data", "status": "PASS",
         "evidence": "取 Q2 的 B1 侧参数（真实数据支撑）；gamma 仍为半合成来源，按 GC5 披露"},
        {"check": "constraint_set_nonempty", "status": "PASS",
         "evidence": "9/9 预算×成本函数组合均求得可行解，budget_used_frac 均 <= 1"},
        {"check": "L_ctx_exogenous_not_optimized", "status": "PASS",
         "evidence": "L_ctx 仅作参数扫描（C7 实测 5 档），未列为决策变量（题目硬性）"},
        {"check": "Q_upper_bound_active_in_most_regimes", "status": "FAIL",
         "evidence": "P1：9 组合中 7 个 Q*=1.0（边界），仅 2 个内点 ⇒ 内点 KKT 不足",
         "mitigation": "改用分段 KKT：Q<1 内点段 + Q=1 边界降维段"},
        {"check": "p_simplex_interior_optimum_exists", "status": "FAIL",
         "evidence": "P3：b^T z_p 对 p 线性 ⇒ 单纯形最优在顶点，实测最大分量 1.0000",
         "mitigation": "p 联立优化须加信赖域/正则化，或由 Q1/Q2 固定；属人工裁定"},
        {"check": "high_budget_within_observed_range", "status": "FAIL",
         "evidence": "P6：C=1e24 最优解 N*=40.755B / D*=3771.0B，相对 B1 上界外推 3.41x / 12.57x",
         "mitigation": "结合 B9/B10 可信度边界说明；不得表述为可靠预测（AMB-Q3-3）"},
    ]

    res = {
        "schema_version": 1, "question": "Q3", "gate": "G2", "seed": d["seed"],
        "criteria_predeclared_before_execution": True,
        "probe_evidence": "workspace/data/q3_probe_optimization.json",
        "probe_scripts": ["workspace/code/scripts/probe_q3_optimization.py",
                          "workspace/code/scripts/probe_q3_p5_supplement.py"],
        "upstream": {"Q2_gate": "G3", "objective_params": d["objective_params_from_Q2_B1_side"],
                     "L_ctx_crit_analytic": d["L_ctx_crit_analytic"],
                     "L_ctx_crit_derivation": d["L_ctx_crit_derivation"]},
        "methods": {
            "M1o": {
                "role": "main",
                "executability": {"status": "PASS",
                                  "evidence": "9/9 预算×成本函数组合收敛且可行；log C 扫描 29 点全部求解成功"},
                "data_coverage": {"budgets_probed": ["1e19", "1e22", "1e24"],
                                  "log10_C_sweep": [18.0, 25.0], "sweep_points": p4["n_points"],
                                  "cost_forms": list(p2["g_magnitudes_at_Q1"].keys()),
                                  "L_ctx_levels_from_C7": p5["feasible_from_C7"],
                                  "L_ctx_above_crit": p5["above_crit"]},
                "assumption_checks": common_assumptions,
                "output_degeneracy": {
                    "Q_at_upper_bound_fraction": f"{p1['n_total'] - p1['n_interior']}/{p1['n_total']}",
                    "Q_saturation_log10_C": p4["Q_saturation_log10_C"],
                    "p_joint_max_component": p3["max_component"],
                    "p_joint_verdict": p3["verdict"],
                    "N_over_D_relative_spread_across_L_ctx": p5["N_over_D_relative_spread"],
                    "note": "Q* 边界化与 p 角点退化均为结构性退化，须在实现中显式处理而非规避"},
                "perturbation_sensitivity": {
                    "cost_form_Q_spread_max": p2["max_spread"],
                    "cost_form_sensitivity_concentrated_at": "C=1e19（低预算档）；1e22/1e24 三类 g 的 Q* 全为 1.0",
                    "L_ctx_effect": ("跨 L_ctx_crit=30000 时 N* -54.8%、D* -53.4%，"
                                     "但 N:D 仅变 3.22% ⇒ 压缩规模而非重排配比"),
                    "structural_transition": {"verdict": p4["verdict"],
                                              "share_order_changes": len(p4["share_order_changes"]),
                                              "Q_jumps_gt_0.05": len(p4["Q_jumps_gt_0.05"]),
                                              "max_abs_dQ": p4["max_abs_dQ"]}},
                "scale_check": {"single_solve": "秒级（SLSQP，8 起点）",
                                "log_C_sweep_29_points": "分钟级",
                                "memory": "可忽略（无大矩阵）"},
                "verdict": "CONDITIONAL",
                "conditions_to_clear": [
                    "分段 KKT 须覆盖 Q=1 边界情形（P1 FAIL 的解除条件）",
                    "p 联立优化须经使用者裁定并在选定时加正则（P3 FAIL 的解除条件）",
                    "高预算档结论须附外推可信度边界（P6 的解除条件）"],
            },
            "M0o": {
                "role": "usable_baseline",
                "executability": {"status": "PASS",
                                  "evidence": "固定 N:D 与 Q=Q0 后为单变量预算分配，必有可行解"},
                "data_coverage": {"same_budgets_and_L_ctx_as_main": True},
                "assumption_checks": [
                    {"check": "chinchilla_ratio_transferable_to_this_law", "status": "NOT_CHECKED",
                     "evidence": "未检验。Chinchilla 比例由 N^-alpha 与 D^-beta 的经验平衡导出，"
                                 "本标度律的 alpha=0.3400 与 beta=0.2799 不必然给出同一比例",
                     "mitigation": "作为 baseline 的已声明简化假设，须在论文注明"},
                    {"check": "Q_fixed_at_Q0_means_no_quality_investment", "status": "PASS",
                     "evidence": "C_Q = D*[g(Q0)-g(Q0)]_+ = 0，baseline 不投质量，与 HD-2 声明一致"}],
                "output_degeneracy": {"note": "无 Q 与 p 通道，退化是设计使然而非缺陷"},
                "perturbation_sensitivity": {"status": "NOT_PROBED",
                                             "reason": "baseline，留到实验阶段与 main 同口径比较"},
                "scale_check": {"single_solve": "秒级"},
                "verdict": "CONDITIONAL",
                "conditions_to_clear": ["Chinchilla 比例的可迁移性须在论文声明为简化假设"],
            },
        },
        "fallback": {
            "M2o": {"role": "conditional_fallback",
                    "trigger": ["分段 KKT 的边界枚举被证明不完备（数值解优于全部解析分支，Loss 相对差 > 1e-6）",
                                "分段 KKT 与数值解给出不同的活跃约束集"],
                    "evidence_to_evaluate": ["results/Q3/experiments/round1/run_summary.json 的 "
                                             "kkt_vs_numeric.max_loss_gap 与 active_set_agreement"],
                    "credibility": "探针本身即用多起点 SLSQP 求解成功，故 M2o 的可执行性已有证据",
                    "implemented": False}},
        "criterion_self_audit": [
            {"item": "P5 的判据挂在 N:D 比值上，判 WEAK_EFFECT",
             "issue": "该判据错过了真实效应 —— N* 与 D* 各自腰斩（-54.8%/-53.4%），只是比值不变。"
                      "判据本身没错（问的是配比是否重排），但单看 verdict 会误读为『L_ctx 不重要』。"
                      "已在方法卡与本文件同时记录规模压缩效应，不事后改判据"},
            {"item": "AI 曾断言 L_ctx 等价于预算缩放",
             "issue": "实测仅近似且随 L_ctx 失效（相对差 1.97e-2 → 3.34e-1）。成因 C_Q 只随 D 标度。"
                      "该断言的强版本已更正，不得写入论文"},
        ],
        "human_verdict_required": [
            "p 是否联立优化（题目授权二选一但要求说明理由；P3 实测角点退化）",
            "结构性转移的数学定义（P4 四个候选，实测支持活跃约束集变化）",
            "最优解可接受性判据（是否要求满足 KKT、是否与 Chinchilla 经验比例对照）"],
        "built_at": TS,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    v = json.loads(OUT.read_text(encoding="utf-8"))
    print("methods:", list(v["methods"].keys()), "| fallback:", list(v["fallback"].keys()))
    for m, mm in v["methods"].items():
        need = ["executability", "data_coverage", "assumption_checks", "output_degeneracy",
                "perturbation_sensitivity", "scale_check", "verdict"]
        print(f"  {m}: 七字段齐备={all(k in mm for k in need)} verdict={mm['verdict']}")
    print("human_verdict_required:", len(v["human_verdict_required"]))
    print("SELF_CHECK_OK")


if __name__ == "__main__":
    main()

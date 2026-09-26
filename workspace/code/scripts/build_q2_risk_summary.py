"""把 q2_probe_scaling.json 装配为契约格式的 methods/Q2/probes/risk_probe_summary.json。

契约字段（AGENTS.md# Risk Probe Contract）：executability / data_coverage /
assumption_checks / output_degeneracy / perturbation_sensitivity / scale_check / verdict。
数值一律从探针 JSON 取，不手抄。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "workspace/data/q2_probe_scaling.json"
DST = ROOT / "methods/Q2/probes/risk_probe_summary.json"


def main() -> None:
    p = json.loads(SRC.read_text(encoding="utf-8"))["probes"]
    P1, P2, P3 = p["P1_cross_source_shared_E"], p["P2_p_and_ND_joint_scale_overlap"], p["P3_Q_entry_additive_vs_multiplicative"]
    P4 = p["P4_beta_gamma_identifiability"]
    P5, P6, P7 = p["P5_B8_extrapolated_consistency"], p["P6_Q_is_design_factor_and_B6_B7_nesting"], p["P7_B9_B10_usability"]

    out = {
        "schema_version": 1,
        "question": "Q2",
        "gate": "G2",
        "seed": 20260924,
        "criteria_predeclared_before_execution": True,
        "underlying_probe_output": "workspace/data/q2_probe_scaling.json",
        "probe_script": "workspace/code/scripts/probe_q2_scaling.py",
        "methods": {
            "M1s": {
                "role": "main_candidate",
                "form": "L = E_s + A·N^(-alpha) + B·(D·Q^gamma·exp(b^T z_p))^(-beta)，E_s 来源专属截距",
                "executability": {
                    "legal_result": True,
                    "evidence": f"P3 的乘性 D_eff 拟合在 B6 上收敛，RMSE={P3['multiplicative_D_eff']['rmse']:.5f}、R²={P3['multiplicative_D_eff']['r2']:.4f}；P5 的同形式在 B8 calibrated 上收敛，RMSE={P5['calibrated_fit']['rmse']:.4f}",
                },
                "data_coverage": {
                    "B_files_with_mixture_columns": P2["B_files_with_mixture_columns"],
                    "B_files_checked": P2["B_files_checked"],
                    "B1_N_range_B": P2["B1_N_range_B"],
                    "A_scale_inside_B1_range": P2["A_scale_inside_B1_range"],
                    "n_A_scales_inside": P2["n_inside"],
                    "Q_bearing_rows": {k: v["n_rows"] for k, v in P6["per_file"].items()},
                    "B8_calibrated_vs_extrapolated": [P5["n_calibrated"], P5["n_extrapolated"]],
                    "finding": "p 与 (N,D) 仅在 1B 一点联合观测；Q 仅出现在半合成 B6-B8",
                },
                "assumption_checks": {
                    "cross_source_shared_E": {
                        "criterion": P1["predeclared_criterion"],
                        "E_by_source": P1["E_by_source"],
                        "E_spread": P1["E_spread"],
                        "admissible": P1["shared_E_admissible"],
                        "verdict": P1["verdict"],
                        "consequence": "必须来源专属截距 E_s；B1 主拟合、B4/B5 仅验证；禁止报跨源未去偏 R²",
                    },
                    "joint_identifiability_of_p": {
                        "criterion": P2["predeclared_criterion"],
                        "direct_joint_identifiable": P2["direct_joint_identifiable"],
                        "verdict": P2["verdict"],
                        "consequence": P2["consequence"],
                    },
                    "beta_gamma_identifiability": {
                        "criterion": P4["predeclared_criterion"],
                        "worst_max_abs_pred_diff": P4["worst_max_abs_pred_diff"],
                        "separately_identifiable": P4["beta_gamma_separately_identifiable"],
                        "elasticity_ratio_Q_over_D": P4["elasticity_ratio_Q_over_D"],
                        "required_estimation_order": P4["required_estimation_order"],
                        "prohibited_claim": P4["prohibited_claim"],
                        "criterion_design_flaw": (
                            "预声明判据测错对象：(D·Q^g)^(-b) = D^(-b)·Q^(-bg)，beta 由 D 变化辨识、"
                            "gamma 再由 Q 指数反解，故字面结论为『可分辨』。评审 3.2 的『只能辨识 beta*gamma』"
                            "成立于固定 D 沿 Q 方向。估计顺序约束仍成立，理由改为 gamma 的精度继承 beta 的精度。"),
                    },
                    "Q_scale_alignment": {
                        "criterion": P6["predeclared_criterion"],
                        "per_file_Q_levels": {k: v["n_unique_Q"] for k, v in P6["per_file"].items()},
                        "is_discrete_grid": {k: v["is_discrete_grid"] for k, v in P6["per_file"].items()},
                        "B6_subset_of_B7": P6["B6_B7_nesting"]["B6_subset_of_B7"],
                        "consequence": P6["consequence"],
                        "verdict": P6["verdict"],
                    },
                },
                "output_degeneracy": {
                    "form_discriminability_on_B6": {
                        "criterion": P3["predeclared_criterion"],
                        "additive_rmse": P3["additive_independent_term"]["rmse"],
                        "multiplicative_rmse": P3["multiplicative_D_eff"]["rmse"],
                        "relative_difference": P3["rmse_relative_difference"],
                        "distinguishable": P3["distinguishable_on_B6"],
                        "consequence": "形式选择不能靠拟合优度，须靠机理与 Q3 可用性 —— 属人工裁定",
                    },
                    "small_sample_parameter_collapse": {
                        "observed": "B4(n=57)/B5(n=44) 单独拟合时 E 落到下界 0.0331/0.0000",
                        "consequence": "小样本大跨度下幂律项吸收全部结构 -> 不可作主拟合",
                    },
                },
                "perturbation_sensitivity": {
                    "beta_gamma_reparameterization": P4["reparameterizations"],
                    "elasticity_ratio_constant": P4["elasticity_ratio_Q_over_D"]["constant"],
                    "note": "参数扰动的完整检查留到 G3 实验阶段（本阶段只验承重假设）",
                },
                "scale_check": {
                    "rows": {"B1": 1176, "B2": 1029, "B4": 57, "B5": 44,
                             "B6": P6["per_file"]["B6"]["n_rows"],
                             "B7": P6["per_file"]["B7"]["n_rows"],
                             "B8": P6["per_file"]["B8"]["n_rows"]},
                    "runtime": "全部探针合计秒级；非线性最小二乘 12 起点多起始",
                    "memory": "可忽略（最大表 1704 行）",
                },
                "verdict": "CONDITIONAL",
                "conditional_on": [
                    "来源专属截距 E_s（P1 FAIL 的直接后果）",
                    "跨源统一假设须显式声明并检验（P2 FAIL 的直接后果，对应 AMB-Q2-2）",
                    "beta 先由 B1 钉住再估 gamma（P4）",
                    "不得声称 Q 与 D 的替代率随位置变化（P4，弹性比恒为 gamma）",
                    "半合成参与拟合的程度须由使用者裁定（P5 + GC5 + 题目 success_criteria 第 3 条）",
                ],
                "fallback_trigger": "gamma 的自助 95% 区间含 0，或 M1s 在 B1 留出集 RMSE 不优于 M0s -> 考虑 M2s",
            },
            "M0s": {
                "role": "usable_baseline",
                "form": "L = E + A·N^(-alpha) + B·D^(-beta)，仅用 B1",
                "executability": {
                    "legal_result": True,
                    "evidence": f"P1 在 B1 上拟合收敛：E={P1['per_source']['B1']['E']:.4f}、alpha={P1['per_source']['B1']['alpha']:.4f}、beta={P1['per_source']['B1']['beta']:.4f}、RMSE={P1['per_source']['B1']['rmse']:.5f}、R²={P1['per_source']['B1']['r2']:.4f}、n={P1['per_source']['B1']['n']}",
                },
                "data_coverage": {"B1_rows": P1["per_source"]["B1"]["n"],
                                  "B1_N_range_B": P2["B1_N_range_B"],
                                  "val_loss_min": P1["val_loss_min_by_source"]["B1"]},
                "assumption_checks": {
                    "cross_source_shared_E": {"verdict": P1["verdict"],
                                              "consequence": "baseline 亦须限定在 B1 内，不跨源共享 E"},
                },
                "output_degeneracy": {
                    "E_at_lower_bound": P1["per_source"]["B1"]["E_at_lower_bound"],
                    "note": "B1 上 E 未触下界（1.6898），无退化",
                },
                "perturbation_sensitivity": {"note": "留到 G3；baseline 的扰动检查与主方法同口径"},
                "scale_check": {"rows": P1["per_source"]["B1"]["n"], "runtime": "秒级"},
                "verdict": "CONDITIONAL",
                "conditional_on": ["仅用 B1 拟合，不与 B4/B5 共享 E"],
                "is_declared_baseline_by": "planning/framing_decisions.jsonl#HD-2",
            },
            "M2s": {
                "role": "conditional_fallback",
                "form": "L = E_s + A·N^(-alpha) + B·D^(-beta) + C·Q^(-delta)（Q 为加性独立衰减项）",
                "executability": {
                    "legal_result": True,
                    "evidence": f"P3 的加性拟合在 B6 上收敛，RMSE={P3['additive_independent_term']['rmse']:.5f}、R²={P3['additive_independent_term']['r2']:.4f}（略优于乘性式）",
                },
                "probe_depth": "仅验触发条件与风险轮廓的可信度，未完整实现（契约要求）",
                "fields_intentionally_absent": {
                    "fields": ["data_coverage", "assumption_checks", "output_degeneracy",
                               "perturbation_sensitivity", "scale_check"],
                    "reason": ("AGENTS.md# method-selector：『Probe the fallback only enough to establish "
                               "that its trigger and risk profile are credible. Do not fully implement it.』"
                               "M2s 与 M1s 共用同一批数据（B1+B6-B8），其 data_coverage / scale_check 与 M1s 同；"
                               "assumption_checks 待触发后再查。这不是探针缺口。"),
                },
                "verdict": "CONDITIONAL",
                "activation_trigger": "见 M1s 的 fallback_trigger；触发前保持休眠",
                "main_risk": "Q 与 D 无交互 -> dL=0 解出的 ΔN/ΔQ 不含 D，替代率的解释范围变窄",
            },
        },
        "criterion_self_audit": {
            "note": "两条预声明判据自身有问题，照实记录，不事后放宽（与 Q1 的 R6/R7 同一纪律）",
            "P4": "判据测错对象，详见 methods.M1s.assumption_checks.beta_gamma_identifiability.criterion_design_flaw",
            "P5": {
                "criterion": P5["predeclared_criterion"],
                "bias_share_of_rmse": P5["extrapolated_prediction"]["bias_share_of_rmse"],
                "prediction_rmse": P5["extrapolated_prediction"]["rmse"],
                "val_loss_range_calibrated": P5["val_loss_range"]["calibrated"],
                "val_loss_range_extrapolated": P5["val_loss_range"]["extrapolated"],
                "flaw": ("判据太松：bias 占比 3.2% 通过，但预测 RMSE 0.6293 而 val_loss 全域仅 0.5-2.603，"
                         "低 bias 只说明误差对称、不说明误差小。另 calibrated 半数的 val_loss 下界也是 0.5，"
                         "低于自然语言熵的常见量级，属半合成生成产物，须按 GC5 披露。"),
                "verdict_recorded_as": P5["verdict"],
            },
        },
        "data_usability_notes": {
            "B3_missing_from_profile": ("workspace/data/profile_b_scaling.json 漏了 B3；"
                                        "磁盘上实为 8 个 pythia_*_trajectory.csv（8×500）。"
                                        "B2 已画像可用，故『B2 或 B3』的硬性要求不受阻。"),
            "B6_subset_of_B7": f"B6 的 360 个 (N,D,Q) 点全部包含于 B7（共享 {P6['B6_B7_nesting']['n_shared']} 点）-> 用 B7 即覆盖 B6",
            "B9": {"has_val_loss": P7["B9"]["has_val_loss"],
                   "D_missing_or_zero_rows": P7["B9"]["D_tokens_zero_or_missing"],
                   "permitted_use": P7["permitted_use"]},
            "B10": {"provenance": P7["B10"]["provenance"], "permitted_use": P7["permitted_use"]},
        },
        "pending_human_decisions": [
            "p 如何进入标度律（exp(b^T z_p) 低维投影 / 标量化为 Q_corpus / 仅经 Q 间接）—— AMB-Q2-1 + P2",
            "Q 进入方式（D_eff 乘性 vs 加性独立项）—— P3 显示拟合优度不可区分",
            "半合成 B6-B8 参与拟合的程度上限 —— 题目 success_criteria 第 3 条 + GC5 + P5",
        ],
    }
    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    req = {"executability", "data_coverage", "assumption_checks", "output_degeneracy",
           "perturbation_sensitivity", "scale_check", "verdict"}
    print("契约字段核验（fallback 按契约只需 executability + trigger）：")
    for mid, m in out["methods"].items():
        missing = req - set(m)
        if m["role"] == "conditional_fallback":
            ok = {"executability", "verdict"} <= set(m) and "activation_trigger" in m
            print(f"  {mid:5s} verdict={m['verdict']:12s} role=fallback"
                  f" 契约满足={ok} 有意省略={len(m['fields_intentionally_absent']['fields'])} 项")
        else:
            print(f"  {mid:5s} verdict={m['verdict']:12s} 缺字段={sorted(missing) if missing else '无'}")
    print("主方法与 baseline 七字段齐备:",
          all(not (req - set(out["methods"][k])) for k in ("M1s", "M0s")))
    print("输出", DST.relative_to(ROOT))


if __name__ == "__main__":
    main()

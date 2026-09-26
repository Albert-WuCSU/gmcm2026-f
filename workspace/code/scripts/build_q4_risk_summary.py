"""把 Q4 两份真实探针输出装配为 AGENTS.md 风险探针契约的七字段格式。

设计约束:本脚本**不硬编码任何测量值**。所有数字从
  workspace/data/q4_probe_attribution.json
  workspace/data/q4_probe_bridge.json
读取。这样摘要里的数字不可能与探针输出不一致(上一轮 AI 编造数字的结构性防线)。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ATT = ROOT / "workspace" / "data" / "q4_probe_attribution.json"
BRI = ROOT / "workspace" / "data" / "q4_probe_bridge.json"
OUT = ROOT / "methods" / "Q4" / "probes" / "risk_probe_summary.json"

a = json.loads(ATT.read_text(encoding="utf-8"))["probes"]
b = json.loads(BRI.read_text(encoding="utf-8"))["probes"]

P1, P2, P3 = a["P1_data_coverage"], a["P2_identifiability"], a["P3_share_degeneracy"]
P4, P5, P6, P7 = a["P4_jia_yi_bias"], a["P5_bridge"], a["P6_perturbation"], a["P7_prediction_criterion"]
B1, B2, B3, B4, B5 = (b["B1_inventory"], b["B2_tier"], b["B3_monotone"],
                      b["B4_circularity"], b["B5_p4_total_sign"])

c6_high = B3["detail"]["C6"]["by::Loss_Comparability"]["High (same model, same validation set)"]
c6_med = B3["detail"]["C6"]["by::Loss_Comparability"]["Medium (different validation set, approximate)"]

summary = {
    "schema_version": 1,
    "question_id": "Q4",
    "gate": "G2",
    "generated_from": {
        "attribution_probe": str(ATT.relative_to(ROOT)).replace("\\", "/"),
        "bridge_probe": str(BRI.relative_to(ROOT)).replace("\\", "/"),
    },
    "approved_framing": {
        "primary_defense_target": "A 归因为主 claim",
        "scale_channel": "丙 甲(全样本)为主 + 乙(66 子集)作偏误验证",
        "fn_spec": "C 主口径 A(十分位 dummy) + B(线性 log N)作规格敏感性",
        "ledger": "planning/framing_decisions.jsonl",
    },

    "executability": {
        "verdict": "PASS",
        "main_candidate_M1a": (
            f"半参数归因可产出合法分解:规模 {P3['scale_points']} 点 / 技术 {P3['tech_points']} 点 / "
            f"合计 {P3['total_points']} 点,份额 {P3['scale_share']} / {P3['tech_share']}"
        ),
        "baseline_M0a": (
            f"纯时间趋势外推可运行:q90 斜率 {P7['slope_per_month']}/月,"
            f"12 个月点预测 {P7['pred_12m_point']}"
        ),
        "bridge": f"Loss->Score 桥接可运行,C6 全样本 spearman {B3['detail']['C6']['all']['spearman']}",
        "evidence": ["P3_share_degeneracy", "P7_prediction_criterion", "B3_monotone"],
    },

    "data_coverage": {
        "verdict": P1["verdict"],
        "c1_rows_usable": P1["c1_rows_usable"],
        "c1_date_span_days": P1["c1_date_span_days"],
        "c1_date_range": P1["c1_date_range"],
        "c1_type_counts": P1["c1_type_counts"],
        "c4_rows": P1["c4_rows"],
        "c4_trio_complete": P1["c4_trio_complete"],
        "join_unique_models": P1["join_unique_models"],
        "join_with_D": P1["join_with_D"],
        "join_type_counts": P1["join_type_counts"],
        "bridge_c5_rows": B1["C5"]["rows"],
        "bridge_c6_rows": B1["C6"]["rows"],
        "bridge_same_model_set": B1["same_model_set"],
        "bridge_tiers_c6": B2["observed_tiers"]["C6.Loss_Comparability"],
        "c8_dirs": P1["c8_dirs"],
        "c8_parseable": P1["c8_parseable"],
        "c8_full_parse_seconds": P1["c8_full_parse_seconds"],
        "imbalance_warnings": [
            f"pretrained 仅 {P1['c1_type_counts'].get('🟢 pretrained')} / {P1['c1_rows_usable']} "
            "⇒ 分组建模该组精度必然更低,须如实报告(F12)",
            f"C1xC4 连接子集 {P1['join_unique_models']} 个中 pretrained "
            f"{P1['join_type_counts'].get('🟢 pretrained')} 个 ⇒ 与全样本不是同一总体,"
            "偏误只给符号与量级,不得作修正系数",
            f"密集窗口 {P1['c1_date_span_days']} 天 < 24 个月预测窗口(F11)",
            f"桥接 High 层 n={c6_high['n']} ⇒ 映射误差须作独立随机项传播(F9)",
        ],
    },

    "assumption_checks": {
        "verdict": P2["verdict"],
        "identifiability_fn_vs_tau": {
            "criterion": P2["criterion"],
            "spearman_t_logN": P2["spearman_t_logN"],
            "spearman_S_logN": P2["spearman_S_logN"],
            "collinearity_ok": P2["collinearity_ok"],
            "tau_present_within_bins": P2["tau_present_within_bins"],
            "within_bin": P2["within_bin"],
            "conclusion": "时间与规模不共线;档内 tau 显著为正 ⇒ f(N) 与 tau_t 可分",
        },
        "bridge_monotonicity": {
            "verdict": B3["verdict"],
            "c6_all": B3["detail"]["C6"]["all"],
            "c6_high_tier": c6_high,
            "c6_medium_tier": c6_med,
            "note": (
                f"High 层 n={c6_high['n']},spearman {c6_high['spearman']} 但 p={c6_high['p']:.3f} "
                "⇒ 方向正确、统计不显著,纯样本量所致(F10 已记:不得据此认为 High 层质量更差)"
            ),
        },
        "no_circularity": {
            "verdict": B4["verdict"],
            "n_suspect_rows": B4["n_suspect"],
            "note": "Loss_Source 全为技术报告/训练日志,无标度律估算行 ⇒ 桥接拟合不构成循环论证",
        },
        "load_bearing": [
            "跨源统一假设:C1 得分与 C4 compute 经名称连接后视为同一模型(承重,AMB-Q4-3)",
            "tau_t 吸收未观测的数据质量变化 ⇒ 只能表述为「非规模技术/数据工程综合进步」",
            "C1 为投榜样本而非模型总体,tau 含 benchmark 过拟合成分",
        ],
    },

    "output_degeneracy": {
        "verdict": P3["verdict"],
        "share_form_valid_under_main_spec": P3["share_form_valid"],
        "scale_share": P3["scale_share"],
        "scale_share_ci95": P3["scale_share_ci95"],
        "tech_share": P3["tech_share"],
        "tech_share_ci95": P3["tech_share_ci95"],
        "n_boot": P3["n_boot_effective"],
        "period": P3["period"],
        "subset_share_not_interpretable": {
            "verdict": B5["verdict"],
            "p4_jia_total_points_implied": B5.get("p4_jia_total_points_implied"),
            "p4_yi_total_points_implied": B5.get("p4_yi_total_points_implied"),
            "consequence": B5["consequence"],
        },
    },

    "perturbation_sensitivity": {
        "verdict": P6["verdict"],
        "criterion": P6["criterion"],
        "specs": P6["specs"],
        "tech_share_spread": P6["tech_share_spread"],
        "bootstrap_ci_width": P6["bootstrap_ci_width"],
        "spread_over_ci_width": P6["spread_over_ci_width"],
        "jia_yi_bias": {
            "subset_n": P4["subset_n"],
            "jia_tech_share": P4["jia_tech_share"],
            "yi_tech_share": P4["yi_tech_share"],
            "bias_tech_share": P4["bias_tech_share"],
            "direction_holds": P4["verdict"] == "PASS",
            "caveat": "该子集 total 为负(见 output_degeneracy.subset_share_not_interpretable),"
                      "故只支持符号关系「甲 > 乙」,不支持把 share 数值当占比",
        },
        "conclusion": (
            f"技术份额极差 {P6['tech_share_spread']} 是自助区间宽度 {P6['bootstrap_ci_width']} 的 "
            f"{P6['spread_over_ci_width']} 倍 ⇒ 规格选择本身是结论的一部分。"
            "已由使用者裁定为 C:主口径 A,B 作规格敏感性一并报告。"
        ),
    },

    "scale_check": {
        "verdict": "PASS",
        "c8_full_parse_seconds": P1["c8_full_parse_seconds"],
        "attribution_probe_total_seconds": json.loads(ATT.read_text(encoding="utf-8")).get("elapsed_seconds"),
        "bootstrap_b": P3["n_boot_effective"],
        "note": f"C8 全量 {P1['c8_parseable']} 目录解析 {P1['c8_full_parse_seconds']}s ⇒ 裁定(g)全量成立,无需抽样",
    },

    "verdict": "CONDITIONAL",
    "verdict_basis": (
        "主方法可执行、识别条件实测成立、桥接单调且无循环论证;"
        f"但输出口径对 f(N) 规格敏感(P6 比值 {P6['spread_over_ci_width']} > 0.50 阈)。"
        "使用者已裁定 C(主口径 A + B 作敏感性),CONDITIONAL 的处置方式已确定,可进 G3。"
    ),
    "fallback_trigger_M2a": {
        "trigger": "所采用 f(N) 规格下 scale_share 的自助 95% 区间下界 < 0",
        "status_under_main_spec_A": (
            f"未触发(下界 {P3['scale_share_ci95'][0]} >= 0)"
            if P3["scale_share_ci95"][0] >= 0 else
            f"已触发(下界 {P3['scale_share_ci95'][0]} < 0)"
        ),
        "status_under_spec_B": (
            f"若采用线性 log N 则触发(scale_share {P6['specs']['linear_month']['scale_share']} < 0)"
        ),
        "action_when_triggered": "改报绝对贡献点数与方向,不得取绝对值或截断到 0 掩盖",
    },
    "record_corrections_this_round": [
        {
            "item": "AI 上一轮编造的 bridge 探针结论(B1-B5)",
            "status": "已作废",
            "detail": (
                "上一轮 AI 报告称 C6 仅 43 行、不存在 High 层、7 条『High』实为 proxy/interp 行、"
                "measured_pythia n=36 rho=-0.8863、3 条 estimated_from_scaling_law 行。"
                "该脚本与输出从未落盘,全部为凭空生成。"
            ),
            "truth": (
                f"C5 {B1['C5']['rows']} 行 / C6 {B1['C6']['rows']} 行,模型集不同;"
                f"High 层存在 n={c6_high['n']};Loss_Source 全为技术报告/训练日志,无估算行。"
                "data_report.md 的 F9 原文正确,不需更正。"
            ),
        },
        {
            "item": "P5_bridge 判 FAIL",
            "status": "SUPERSEDED by B1-B5",
            "detail": f"FAIL 原因是 AI 的列名匹配 bug(C6 得分列名为 LB_Average): {P5.get('reason')}",
        },
    ],
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print("WROTE", OUT.relative_to(ROOT))
for f in ("executability", "data_coverage", "assumption_checks", "output_degeneracy",
          "perturbation_sensitivity", "scale_check"):
    print(f"  {f}: {summary[f]['verdict']}")
print("  overall:", summary["verdict"])
print("  M2a:", summary["fallback_trigger_M2a"]["status_under_main_spec_A"])

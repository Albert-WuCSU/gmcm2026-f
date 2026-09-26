"""Q4 过 G4:登记两份工件、清两款 blocker、追加 gate_history、改写待办与 next_action。

依据:methods/Q4/q4_decisions.jsonl 六条人工裁定(result / stability / claim_scope 三类齐备)。
AI 只做机械更新,不新增或改写任何裁定文字。

幂等:blockers 清空;gate_history 按 (gate, result, at) 去重;artifacts 为赋值。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "planning/manifests/Q4.json"
TS = "2026-09-25T20:45:00+08:00"

ARTIFACTS = {
    "robustness_report": "robustness/Q4/q4_robustness_report.md",
    "final_result_analysis": "results/Q4/reports/q4_final_result_analysis.md",
    "supplementary_run": "results/Q4/experiments/round2/run_summary.json",
    "supplementary_metrics": "results/Q4/experiments/round2/metrics/q4_trend_method.json",
    "supplementary_tables": [
        "results/Q4/experiments/round2/tables/q4_endpoint_sensitivity.csv",
        "results/Q4/experiments/round2/tables/q4_N_and_frontier_by_month.csv",
        "results/Q4/experiments/round2/tables/q4_scenario_spread_scaling.csv",
    ],
    "supplementary_aux": "results/Q4/experiments/round2/n_frontier_meta.json",
    "number_provenance_check": "scratch/verify_q4_reports_numbers.py",
    "round2_reproducibility_check": "scratch/verify_q4_round2_values.py",
}

# 已清的 blocker:保留记录以便追溯(证据变更需留存)
RESOLVED = [
    {
        "id": "F-Q4-2",
        "resolved_at": TS,
        "resolved_by": "q4_scale_channel_bias_direction_correction",
        "resolution": "撤回实证方向断言、保留机制断言;现行表述为「重分配 0.2451 点、净效应方向随样本而定」",
        "recorded_in": "results/Q4/reports/q4_final_result_analysis.md §4",
    },
    {
        "id": "G4-verdicts",
        "resolved_at": TS,
        "resolved_by": "q4_result_verdict + q4_stability_verdict + q4_claim_scope + q4_horizon_scope",
        "resolution": "三类裁定齐备;另兑现 q4_result_verdict 的 supplementary_run_required(round2 已落盘)",
        "recorded_in": "results/Q4/reports/q4_final_result_analysis.md §11",
    },
]

G4_ENTRY = {
    "gate": "G4",
    "result": "PASSED",
    "at": TS,
    "basis": [
        "methods/Q4/q4_decisions.jsonl",
        "robustness/Q4/q4_robustness_report.md",
        "results/Q4/reports/q4_final_result_analysis.md",
        "results/Q4/experiments/round1/run_summary.json",
        "results/Q4/experiments/round2/run_summary.json",
        "code/Q4/reviews/q4_python_review.json",
    ],
    "verdicts": {
        "result": "accept_round1_with_claim_reframed_plus_supplementary_run",
        "stability": "keep_all_at_face_value_plus_new_endpoint_sensitivity",
        "claim_scope": "robust_direction_only_no_percentage_split",
        "horizon_scope": "h12_main_h24_not_main",
    },
    "note": "6 条裁定全部 DECIDED/by human;两款 blocker 已清;round2 补跑已落盘并逐字节复现",
}

G4_SUMMARY = {
    "main_claim": "窗口 2024-06->2025-03 能力提升约 5.4865-6.6592 点(四端点/规格算法极差);"
                  "非规模技术/数据工程综合进步主导;规模通道贡献与 0 不可区分",
    "main_claim_evidence": "round2 趋势法 scale_share=0.0911,CI95 [-0.1942,+0.2258] 含 0(B=1000);"
                           "端点定义使其极差 0.2875 且符号翻转;slope_tau/slope_f = 9.98",
    "withdrawn_claims": [
        "26%/74% 及任何百分比分割(端点敏感性极差 0.2875 > 主口径点值 0.2593,且符号翻转)",
        "甲单独使用时对技术进步占比系统性高估(66 子集 total 为负,判不了方向)",
    ],
    "checks": {
        "R1_spec_perturbation": "CONDITIONAL(极差 0.7565 = 区间宽 0.3796 的 1.9929 倍,阈 0.50)",
        "R2_endpoint_sensitivity": "FAIL(预声明判据外的新增项,主张已撤回)",
        "R3_trend_bootstrap": "PASS(CI 含 0)",
        "R4_prediction_criterion": "PASS(裕度 1.881;发现次序须披露)",
        "R5_prediction_vs_baseline": "FAIL(主 56.330 < 基线 60.290;预测非主 claim)",
        "R6_subgroup_share": "FAIL(pretrained total -3.5789,该组改报点数)",
    },
    "no_loosening": "预声明判据文字一律未改;端点为新增条目而非放宽既有阈",
    "must_write_limits": [
        "pretrained 组 total_points=-3.5789(负),只报绝对点数与方向,不得给占比",
        "chat_finetuned 组 scale_share CI95 [-0.0328,0.3567] 含 0,不得称规模贡献显著为正",
        "预测判据由 FAIL 翻 PASS 系修对象不一致缺陷所致,且缺陷在看到 FAIL 后才被发现,裕度仅 1.881",
        "乙侧偏误方向不成立,机制成立(重分配精确抵消 0.2451 点)",
        "预测表须同表列出 baseline 的 60.290,不得只报主方法中位数",
        "总提升区间是四端点/规格算法极差;趋势法 drop-last 给 5.3581,略低于下界",
        "N 下降倍数须写明端点比值 3.162 还是斜率隐含值 3.675",
    ],
    "open_wording_items_require_human": [
        "q4_claim_scope 原文写「下降约 3.7 倍」(对应斜率隐含值 3.675),"
        "落盘端点比值为 3.162;两者非同一量,AI 未改写账本",
    ],
}

TODOS = [
    "缺失 benchmark 用可比样本子集或层次模型，不得填 0",
    "贡献表述为“非规模技术/数据工程综合进步”，不过度因果化（时间项会吸收未观测的数据质量变化）",
    "桥接须对 pretrained / chat 分别检验是否需要不同映射；映射误差作为独立随机项传播到前沿预测",
    "前沿用 0.9/0.95 分位数定义；报告中位数与 80%/95% 区间，不给虚假精确点值",
    "Monte Carlo 同时抽取标度律参数、桥接误差与技术趋势三个不确定性来源",
    "每个数据编号增加 confidence_tier 与 fit_allowed 字段；禁止把半合成与真实观测等权拟合",
    "实验设计四件套：baseline + 主方法 + 消融 + 参数扰动",
    "不可行候选须记录违反了哪条约束及违反程度，而非只给极大惩罚值",
    "24 个月视界不作主报；若列出须声明饱和形态在 9.1 个月窗口内不可检验",
    "规格 B(线性 log N)的负份额须在正文作规格敏感性一并报告(裁定 C 的约定)",
    "F-Q4-1 pretrained 组 total_points 为负，只能报绝对点数与方向，不得给占比",
    "F-Q4-3 预测判据由 FAIL 翻 PASS 系 AI 修对象不一致缺陷所致，发现次序须披露，裕度仅 1.881 点",
    "F-Q4-6 chat_finetuned 组 scale_share 的 CI95 含 0，不得声称规模贡献显著为正",
    "F-Q4-2 已清：乙侧偏误只报机制与绝对点数差，不得表述为固定的「甲高估」",
    "26%/74% 及任何百分比分割已作废，不得进入论文",
    "预测维度主方法未打赢 baseline(56.330 < 60.290)，预测表须同表列出 baseline",
    "总提升区间 5.4865-6.6592 的准确表述是「四端点/规格算法极差」(趋势法 drop-last 给 5.3581)",
    "N 下降倍数须写明是端点比值 3.162 还是斜率隐含值 3.675",
    "AI 上一轮编造的 bridge 结论已作废;data_report.md 的 F9 原文正确,不需更正",
    "figures: round1/round2 均为空;论文图另在 paper/figures/ 制作(Q4 已有 fig_q4_frontier_vs_scale.tex)",
    "G5 前必须按模板目录内的修改说明把届数由第二十二届改为第二十三届",
    "Q4 侧 G4 已过，无阻塞项",
]

NEXT_ACTION = {
    "owner": "human",
    "skill": "modeler-decision-logger",
    "target": "Q3",
    "reason": "Q4 已过 G4 且 round1 已定为最终轮，Q4 侧无阻塞项（仅余论文图与一处措辞待办："
              "账本「下降约 3.7 倍」对应斜率隐含值 3.675，而落盘端点比值为 3.162，两者非同一量，"
              "须由使用者确认论文措辞）。按 HANDOFF §0.00000 的优先级，下一步是 Q3 的 G4"
              "（需三类人工裁定，参照 q4_decisions.jsonl 的 result/stability/claim_scope 先例）"
              "与 Q2 的 G4，随后是论文可视化。",
}


def main() -> None:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))

    missing = []
    for k, v in ARTIFACTS.items():
        for p in (v if isinstance(v, list) else [v]):
            if not (ROOT / p).exists():
                missing.append(p)
    if missing:
        raise SystemExit(f"拒绝写入：以下登记路径不存在 {missing}")

    m["current_gate"] = "G4"
    m["status"] = "g4_passed_round1_final_paper_figures_pending"
    m["artifacts"].update(ARTIFACTS)

    cleared = [b.get("id") for b in m.get("blockers", [])]
    m["blockers"] = []
    resolved_ids = {r["id"] for r in m.get("resolved_blockers", [])}
    m.setdefault("resolved_blockers", [])
    for r in RESOLVED:
        if r["id"] not in resolved_ids:
            m["resolved_blockers"].append(r)
    m["resolved_blockers_note"] = f"本轮清空的 blocker: {cleared}"

    hist = m.setdefault("gate_history", [])
    if not any(h.get("gate") == "G4" and h.get("result") == "PASSED" for h in hist):
        hist.append(G4_ENTRY)

    m["g4_summary"] = G4_SUMMARY
    m["carried_forward_todos"] = TODOS
    m["next_action"] = NEXT_ACTION
    m["updated_at"] = TS

    MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print("gate:", m["current_gate"], "| status:", m["status"])
    print("blockers:", m["blockers"])
    print("resolved:", [r["id"] for r in m["resolved_blockers"]])
    print("gate_history:", [(h["gate"], h["result"]) for h in hist])
    print("artifacts:", len(m["artifacts"]), "keys | todos:", len(TODOS))


if __name__ == "__main__":
    main()

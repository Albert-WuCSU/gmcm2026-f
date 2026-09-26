"""补记两条 G4 裁定（Q2 claim_scope 条件化修订 + Q3 第四类 g 处置）。

使用者原话（逐字）：
    Q2 claim_scope ：维持 3A 但条件化，同报两条路线；Q3 第四类 g(Q)：A，不采用候选，只作分析报告。
    记录我的决策，然后推进，然后更新交接文档。比赛还有4小时，我们得抓紧

q2_claim_scope 的修订按 Q1 先例处理：新记录 supersedes 旧记录，账本 append-only 不删原记录。
幂等：按 decision_id 去重。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TS = "2026-09-25T22:10:00+08:00"
FULL = ("Q2 claim_scope ：维持 3A 但条件化，同报两条路线；Q3 第四类 g(Q)：A，不采用候选，只作分析报告。"
        "记录我的决策，然后推进，然后更新交接文档。比赛还有4小时，我们得抓紧")

Q2_NEW = {
    "decision_id": "q2_claim_scope_conditioned_v2",
    "decision_type": "claim_scope",
    "choice": "keep_3A_but_condition_on_beta_report_both_routes",
    "choice_label": "维持 3A（绑定 B7 设计刻度主张 D_eff ≈ D·Q），但显式条件化于「beta 取自 B1」，"
                    "并在正文同报两条路线（gamma=0.965913 / 1.179781）",
    "supersedes": "q2_claim_scope",
    "supersede_scope": "替换 q2_claim_scope 的 binding_commitments；原记录保留（append-only）",
    "rationale": "Q2 claim_scope ：维持 3A 但条件化，同报两条路线；Q3 第四类 g(Q)：A，不采用候选，只作分析报告。",
    "triggered_by": "P9 判 FAIL：workspace/data/q2_probe_beta_sharing.json",
    "rejected_alternatives": [
        "B 收窄为只主张乘积 beta*gamma —— 实测该量同样路线依赖（beta*gamma：路线A 0.270396 vs 路线B 0.097985，"
        "差 2.76 倍），改报它并不能摆脱条件性，只是把条件性藏起来",
        "C 维持 3A 不变、P9 仅作附录敏感性臂 —— P9 判 FAIL 的是它自己的预声明判据，"
        "把判失败的预声明检验挪进附录属掩埋，与 Q1 R6/R7 及 Q3 P5 的纪律冲突",
    ],
    "binding_commitments": {
        "claim_retained_but_conditioned": "主张「在 B7 设计刻度上 D_eff ≈ D·Q」成立，"
                                          "但须显式条件化于「beta 取自 B1（0.279878）」这一承重假设",
        "p9_verdict_must_be_disclosed": "P9 预声明判据判 FAIL：gamma 位移 0.213868 = 其自助区间宽的 1.2457 倍（阈 0.5）；"
                                        "B1 的 beta 落在 B7 自估 beta 的区间之外。该结果必须在正文披露，不得只进附录",
        "both_routes_must_be_reported": "同报 gamma=0.965913（CI95 [0.883860, 1.055546]，含 1.0，beta 取自 B1）"
                                        "与 gamma=1.179781（CI95 [1.088441, 1.283359]，不含 1.0，beta 在 B7 上自由）",
        "why_b1_beta_is_taken": "B1 的 beta 辨识显著更强（CI 宽 1.16e-04，1176 行，D 跨 0.1-299.9B），"
                                "而 B7 仅 5 个不同 D 取值且 D 与 N 在设计上纠缠；且 beta=0.083 远离"
                                "Chinchilla Approach-3 的 0.28 与本律 B1 侧的 0.279878。"
                                "故取 B1 的 beta —— 但这只让结论有条件地成立，不构成 P9 未发生",
        "beta_status": "beta 跨源共享由「未检验的承重假设」升级为「已检验且被判据判 FAIL 的承重假设」",
        "perturbation_results": "其余扰动项全部 PASS：自助 B 400->1000 端点变化 0.0098；B1 留一 N 组 beta 极差 3.535e-05 "
                                "（< 区间宽 1.163e-04）；B1 权重缩放 lambda∈{0.5,1,2} 的 gamma 位移 0.039812"
                                "（< 宽 0.171686）；sigma_s 换 p5_anchor 位移 0.000341",
    },
    "evidence_refs": [
        "workspace/data/q2_probe_beta_sharing.json",
        "robustness/Q2/q2_robustness_supplement.json",
        "results/Q2/reports/q2_final_result_analysis.md",
    ],
    "ai_note": "使用者索取 AI 意见后自行决断。AI 建议中指出选项 B（只报 beta*gamma）并不更严谨，"
               "因 beta*gamma 实测同样路线依赖（0.270396 vs 0.097985），该论证为 AI 意见，不写入 rationale。",
}

Q3_NEW = {
    "decision_id": "q3_fourth_cost_form",
    "decision_type": "claim_scope",
    "choice": "no_candidate_adopted_report_analysis_only",
    "choice_label": "不采用任一候选第四类 g(Q)，只把三候选分析作为题目「或改进」的答案报出",
    "rationale": "Q3 第四类 g(Q)：A，不采用候选，只作分析报告。",
    "triggered_by": "results/Q3/experiments/round1/metrics/q3_supplement_Q0_and_4th_g.json",
    "rejected_alternatives": [
        "B 采用 C3（二次型）并扩展定义 A 的识别以处理双侧转移 —— 成本与收益不匹配："
        "C3 的左事件是 Q 触下界 Q0，而 Q0=0.35 本身未经使用者裁定、可被否决，"
        "该双侧结构的左支位置取决于一个未裁定参数",
        "C 采用有界型（C1 饱和指数 / C2 Hill） —— 实测两者均使 Q* ≡ 1、NO_TRANSITION，"
        "会消灭本问核心发现（三定义三答案 + 连续饱和），须同时重定 Q3 主 claim",
        "D 另提新形式 —— 使用者未提出，本轮不做",
    ],
    "binding_commitments": {
        "analysis_is_the_answer": "题目「或改进 g(Q)」的答案即三候选分析本身，"
                                  "不加第四类 g 进入主 claim；主张仍基于给定的三类 g",
        "must_report_findings": [
            "C1 饱和指数型 g=γ(1−e^(−λQ))（γ=1e7, λ=6.0）与 C2 Hill 型 g=γQ^λ/(1+Q^λ)（γ=1e7, λ=6.0）"
            "均为有界型 ⇒ Q* 在三档预算上恒为 1，结构性转移 NO_TRANSITION（消灭核心发现）",
            "C3 二次型 g=γQ²（γ=4.034287935e9，使 g(1) 与指数型 g(1) 相同）⇒ 出现双侧转移："
            "低预算 Q 触下界 Q0（Q*=0.35）、高预算 Q 触上界 1.0；定义 C 在 19.125 与 22.5 各一次翻转",
            "C3 的左事件依赖未裁定的 Q0，且定义 A 的单谓词二分定位不了它（返回 nan）",
        ],
        "prohibited": [
            "不得把任一候选的数值当作主结果报出（三候选均为探索性分析，未进入主 claim）",
            "不得声称『给定三类 g 是最优选择』—— 只能说它们不被这两个方向的改进所取代",
        ],
    },
    "evidence_refs": [
        "results/Q3/experiments/round1/metrics/q3_supplement_Q0_and_4th_g.json",
        "workspace/code/scripts/probe_q3_Q0_and_fourth_g.py",
        "results/Q3/reports/q3_final_result_analysis.md",
    ],
    "ai_note": "使用者索取 AI 意见后自行决断。AI 建议 A，理由（C1/C2 消灭转移、C3 左支依赖未裁定 Q0）为 AI 意见，"
               "不写入 rationale。",
}

Q3_STABILITY_V2 = {
    "decision_id": "q3_stability_verdict_v2",
    "decision_type": "stability_verdict",
    "choice": "add_Q0_sensitivity_result_not_load_bearing",
    "choice_label": "补记 Q0 敏感性实测结果：在 Q1 实测域级 Q 范围内 Q0 非承重",
    "supersedes": None,
    "rationale": "Q3 第四类 g(Q)：A，不采用候选，只作分析报告。",
    "adds_to": "q3_stability_verdict（其 binding_commitment 要求补做 Q0 敏感性）",
    "binding_commitments": {
        "Q0_scan": "Q0 扫 [0.223306, 0.25, 0.30, 0.35, 0.381496]（端点 = Q1 实测域级 Q 范围）",
        "result": "Q*_1e19 极差 0.011712（阈 0.10）；转移位置移动 0.005981 dex（阈 0.10）"
                  "⇒ 判 NOT_LOAD_BEARING_IN_TESTED_RANGE",
        "transition_locations": "21.400909 / 21.401581 / 21.403107 / 21.405182 / 21.406891",
        "consequence": "Q0 无需另立敏感性臂；但 Q0=0.35 未经使用者裁定的状态不变，仍须在论文声明",
    },
    "evidence_refs": [
        "results/Q3/experiments/round1/metrics/q3_supplement_Q0_and_4th_g.json",
    ],
    "ai_note": "本记录只补记实测结果，不改 q3_stability_verdict 的任何判据文字。",
}

TARGETS = [("Q2", [Q2_NEW]), ("Q3", [Q3_NEW, Q3_STABILITY_V2])]


def main() -> None:
    for q, recs in TARGETS:
        p = ROOT / f"methods/{q}/{q.lower()}_decisions.jsonl"
        existing = set()
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing.add(json.loads(line)["decision_id"])
        added = 0
        with p.open("a", encoding="utf-8", newline="\n") as f:
            for r in recs:
                if r["decision_id"] in existing:
                    print("  skip", r["decision_id"]); continue
                f.write(json.dumps({
                    "schema_version": 1, "status": "DECIDED", "decided_by": "human",
                    "captured_in_mode": "learning", "rationale_provenance": "verbatim_user_reply",
                    "option_content_authored_by": "ai",
                    "user_action": "reviewed_and_adopted_ai_recommendation",
                    "decided_at": TS, "user_reply_full": FULL, **r,
                }, ensure_ascii=False) + "\n")
                added += 1
        print(f"{q}: appended {added}, now {len(existing) + added}")


if __name__ == "__main__":
    main()

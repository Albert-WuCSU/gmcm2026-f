"""第二张决策卡的两条人工决策 -> methods/Q1/q1_decisions.jsonl（append-only）。

使用者原话（一次性给出两项）：
「1.CD2@p75 为主报，CD1/CD3 作已声明的敏感性臂；2.book~wikipedia：报统计上不可区分、
方向随合成方式而变。记录我的决策继续推进，另外判断是否需要换窗口，如果需要记得更新交接进度的文档」

rationale 一律为使用者原话照录，AI 不补写、不强化。
AI 曾提供三条量化理由与反方质疑点，标注为 AI 意见；使用者作出选择。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEDGER = ROOT / "methods/Q1/q1_decisions.jsonl"
TS = "2026-09-24T21:40:00+08:00"
VERBATIM = ("1.CD2@p75 为主报，CD1/CD3 作已声明的敏感性臂；2.book~wikipedia：报统计上不可区分、"
            "方向随合成方式而变。记录我的决策继续推进，另外判断是否需要换窗口，"
            "如果需要记得更新交接进度的文档")
NOTE = "使用者一次性给出两项选择，本条为该次回复的原话全文，未作拆分改写"
AI_NOTE = ("选项与其量化后果由 AI 构造并展示（含 AI 自陈的反方质疑点），使用者作出选择；"
           "本条 rationale 为使用者原话照录，AI 未补写或强化理由。"
           "注意 GC9：论文中的相应论证须由本队自行撰写，不得直接复制 AI 生成的方案表述。")

RECORDS = [
    {
        "decision_id": "q1b_conflict_criterion",
        "decision_type": "method_choice",
        "scope": "Q1b 冲突判据的主报口径与敏感性臂",
        "choice": "CD2@p75",
        "choice_label": "CD2（高价值 ∧ 高污染，各取 p75）为主报；CD1/CD3 作已声明的敏感性臂",
        "chosen_spec": {
            "primary": "CD2：V > p75(V) ∧ P > p75(P)，canonical/pooled 口径下冲突率 0.040824",
            "sensitivity_arms": "CD1（指标间 MAD>0.25）、CD3-5（≥5高∧≥5低）、CD3-3（≥3高∧≥3低）"
                                "须作为已声明的敏感性臂报告，不作主报",
            "anchor_sensitivity_required": "CD2 须同时报 p70/p75/p80 = 0.0687/0.0408/0.0208",
            "required_fix": "CD1 的 0.25 为固定阈、对锚点零响应（评审 F1），"
                            "作敏感性臂前须改为 MAD 自身分位数锚定，否则该臂为哑变量",
            "excluded": "绝对阈版 V>0.75 ∧ P>0.75 冲突率恰为 0.0，已据证据排除，不实现",
        },
        "evidence_refs": [
            "workspace/data/q1_probe_conflict_by_domain.json",
            "results/Q1/experiments/round1/tables/q1b_conflict_rates.csv",
            "results/Q1/experiments/round1/run_summary.json",
            "code/Q1/reviews/q1_python_review.json",
        ],
        "evidence_digest": {
            "domain_level_rates_p75": {
                "CD2": "stackexchange 0.174 / c4 0.004（43 倍差），book 0.035 居低位",
                "CD1": "book 0.994、arxiv 0.878 —— book 域近乎全判冲突",
                "CD3_ge5": "book 0.988",
                "CD3_ge3": "book 1.000、arxiv 0.958 —— book 域 171 条全部判为冲突（退化）"},
            "anchor_response": "CD2/CD3 随锚点单调变化；CD1 三锚点同值 0.303058（零响应）",
            "pairwise_jaccard_p75": "CD2 与其余三者 0.030~0.045（近乎独立子集）；"
                                    "CD1~CD3_ge5 为 0.512（实质同一子集的不同切法）",
            "CD2_indicator_profile": "冲突子集相对全体均值：readability +0.263、qurater +0.244、"
                                     "cleanliness +0.241；top_3gram −0.182、top_2gram −0.122、"
                                     "ad_en_margin −0.122 => 规整通顺但高度模板化且带推广性的文本",
            "why_not_CD1_CD3": "其域级冲突率把 book 顶到 0.99~1.00，实质在重复度量『该域相对"
                               "合并分布的异常度』，与已知域混淆（AUC 0.974）同源，非文档内部质量张力",
        },
    },
    {
        "decision_id": "q1a_book_wikipedia_claim_scope",
        "decision_type": "claim_scope",
        "scope": "Q1a 域序中 book 与 wikipedia 的表述口径",
        "choice": "report_indistinguishable",
        "choice_label": "报统计上不可区分、方向随合成方式而变",
        "chosen_spec": {
            "prohibited_claim": "不得声称 book > wikipedia 或 wikipedia > book",
            "required_statement": "报『二者在统计上不可区分，先后随合成方式而变』，"
                                 "并附 M0/M1 两法的相反方向与区间",
            "scope_limit": "该口径仅适用于 book~wikipedia；c4~commoncrawl 分离裕度 4.4 倍、"
                          "方向与 baseline 一致，照常报告方向",
            "downstream": "book 的域级 Q 供 Q2 使用时须显式标注不可靠，Q2 应设敏感性臂",
        },
        "evidence_refs": [
            "results/Q1/experiments/round1/run_summary.json",
            "results/Q1/experiments/round1/tables/q1a_domain_quality.csv",
            "methods/Q1/q1_method_card.md",
        ],
        "evidence_digest": {
            "M0": "wikipedia 0.53256 > book 0.52638，差 0.00617 < 半宽和 0.01098 => 并列",
            "M1": "book 0.26677 > wikipedia 0.25564，差 0.01113 > 半宽和 0.00996 => 仅超出 1.12 倍",
            "direction_reversed_between_methods": True,
            "book_n": 171,
            "consistency_with_method_card": "方法卡承重发现 #7 已记载二者不可区分，"
                                            "若结果部分改为有方向断言将内部不一致",
        },
    },
]


def main() -> None:
    existing = set()
    if LEDGER.exists():
        existing = {json.loads(l)["decision_id"]
                    for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()}
    n = 0
    with open(LEDGER, "a", encoding="utf-8") as f:
        for r in RECORDS:
            if r["decision_id"] in existing:
                print(f"已存在 {r['decision_id']}，跳过")
                continue
            rec = {"schema_version": 1, "decision_id": r["decision_id"],
                   "decision_type": r["decision_type"], "scope": r["scope"],
                   "status": "DECIDED", "decided_by": "human", "captured_in_mode": "learning",
                   "choice": r["choice"], "choice_label": r["choice_label"],
                   "rationale": VERBATIM, "rationale_provenance": "verbatim_user_reply",
                   "rationale_note": NOTE, "chosen_spec": r["chosen_spec"],
                   "evidence_refs": r["evidence_refs"],
                   "evidence_digest": r["evidence_digest"], "ai_note": AI_NOTE,
                   "decided_at": TS, "supersedes": None}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    print(f"appended {n} records -> {LEDGER}")


if __name__ == "__main__":
    main()

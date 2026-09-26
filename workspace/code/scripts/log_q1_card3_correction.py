"""追加一条 supersedes 记录，更正 q1a_domain_order_claim_scope 的 chosen_spec 归属划分。

更正内容（不改 choice，仍为 A，不改 rationale）：
把「本决策建立的口径」与「既有已报事实」分开，不让 AI 补充的两条断言看起来像是本次人工裁定的产物。

- 属本决策的：不对 arxiv 在最高一档内的位次作断言；档位含 3 个域（卡内 A 的正文已写明
  「按同一逻辑这一档得含 3 个域（7 域中的前 3）」，故三域档位不是超出 A）。
- 不属本决策、仅为既有已报事实：c4 > commoncrawl（round1 已报，裕度 4.4 倍）、github 居末。
  二者列为支撑证据，不作为本裁定新建立的断言。

append-only：不覆写第 9 条，新增第 10 条并以 supersedes 指向它。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEDGER = ROOT / "methods/Q1/q1_decisions.jsonl"
TS = "2026-09-24T23:10:00+08:00"
NEW_ID = "q1a_domain_order_claim_scope_v2"
OLD_ID = "q1a_domain_order_claim_scope"

VERBATIM_ORIGINAL = "根据我们的讨论以及你的补充算结果，我选择1B,2B,3A，请记录我们的决策，然后继续推进"
VERBATIM_CORRECTION = "修改的同时，请继续推进，现在进度有点慢了，我们需要快速开始Q2，不能在Q1一直打转了，我的比赛时间只剩一天了"

RECORD = {
    "schema_version": 1,
    "decision_id": NEW_ID,
    "decision_type": "claim_scope",
    "scope": "Q1a 域序头部（arxiv 头名）的表述口径 —— 归属划分更正版",
    "status": "DECIDED",
    "decided_by": "human",
    "captured_in_mode": "learning",
    "choice": "A",
    "choice_label": "收窄为最高一档，不对 arxiv 在该档内的位次作断言（choice 不变，仅更正 chosen_spec 的归属划分）",
    "rationale": VERBATIM_ORIGINAL,
    "rationale_provenance": "verbatim_user_reply",
    "correction_trigger": VERBATIM_CORRECTION,
    "correction_trigger_provenance": "verbatim_user_reply",
    "rationale_note": (
        "choice 与 rationale 沿用第 9 条（使用者原话全文，未改写）。本条只更正 chosen_spec 的归属划分："
        "AI 在上一版把两条既有已报事实（c4>commoncrawl、github 居末）写进了 required_statement，"
        "使其看似由本次人工裁定建立。经使用者要求修改，现将其降为支撑证据。"
        "三域档位不属超出选项 A —— 卡内 A 的正文已写明『按同一逻辑这一档得含 3 个域（7 域中的前 3）』。"),
    "chosen_spec": {
        "established_by_this_decision": [
            "不得声称 arxiv 是质量最高的域；不对 arxiv 在最高一档内的位次作断言",
            "最高一档按 R4 的 top-3 集合不变性报为 {arxiv, c4, commoncrawl}（9/9 配置下集合不变）",
            "须显式声明 arxiv 在该档内的位次依 V/P 分组的单列归属而变（实测取到 1/2/3）",
        ],
        "preexisting_reported_facts_not_established_here": [
            "c4 > commoncrawl —— round1 已报，分离裕度 4.4 倍、方向与 baseline 一致，照常报方向",
            "github 居末 —— round1 已报，9/9 配置下成立",
        ],
        "scope_limit": "本口径针对域序头部；book~wikipedia 另由 q1a_book_wikipedia_claim_scope 裁定",
        "downstream_Q2": "不影响 Q2 —— Q2 使用域级 Q 的数值与区间，不使用名次",
        "historical_record_must_not_change": "code/Q1/q1_robustness_quality.py 的 tested_claim / predeclared_criterion 是 R4 预声明判据的历史记录，不得据本决策改写；R4 的 FAIL 状态不变",
    },
    "evidence_refs": [
        "robustness/Q1/q1_robustness_summary.json",
        "results/Q1/reports/q1_final_result_analysis.md",
        "planning/choice_cards/q1_round1_verdict_card.md",
    ],
    "ai_note": (
        "本条由 AI 主动提出更正并经使用者指示『修改』后写入。更正的是 AI 自身在上一版的归属越界，"
        "非使用者改变选择。choice 与 rationale 未变。GC9 同前：论文论证须由本队自行撰写。"),
    "decided_at": TS,
    "supersedes": OLD_ID,
}


def main() -> None:
    lines = [ln for ln in LEDGER.read_text(encoding="utf-8").splitlines() if ln.strip()]
    ids = [json.loads(ln)["decision_id"] for ln in lines]
    if NEW_ID in ids:
        print("更正记录已存在，未重复追加。")
        return
    assert OLD_ID in ids, f"被更正的记录 {OLD_ID} 不在账本中"
    for p in RECORD["evidence_refs"]:
        if not (ROOT / p).exists():
            raise SystemExit(f"证据路径不存在 {p}")

    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(RECORD, ensure_ascii=False) + "\n")

    out = [json.loads(ln) for ln in LEDGER.read_text(encoding="utf-8").splitlines() if ln.strip()]
    print(f"账本现 {len(out)} 条（JSONL 全部可解析）")
    print("末条:", out[-1]["decision_id"], "| supersedes:", out[-1]["supersedes"])
    print("被更正条仍在（append-only）:", any(r["decision_id"] == OLD_ID for r in out))


if __name__ == "__main__":
    main()

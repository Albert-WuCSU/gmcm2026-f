"""G4 准备完成后更新 manifest：登记稳健性报告与最终结果分析，把状态改为「等待三条人工裁定」。

本轮不推进 gate（G4 未过 —— 账本缺 result_verdict / stability_verdict，且 R4 新暴露的
arxiv 头名依赖需要一条新的 claim_scope）。故 gate_history 不动，只改 status / blockers /
artifacts / next_action。

幂等：重复执行结果一致（blockers 按 id 去重，artifacts 为赋值）。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "planning/manifests/Q1.json"
TS = "2026-09-24T22:30:00+08:00"

BLOCKERS = [
    {
        "id": "q1_result_verdict",
        "type": "human_decision_required",
        "gate": "G4",
        "summary": "round1 结果裁定：接受 round1 为 Q1 最终轮 / 先补算两项再接受 / 下令 round2",
        "why_ai_cannot_decide": "AGENTS.md：AI 不得发起使用者的选择、理由、置信度裁定；G4 要求账本含 result 裁定",
        "already_mechanical_do_not_ask": "M1 在两项预声明指标上超过 M0（τ 差自助区间 [0.0190,0.0571] 不含 0）已由 HD-2 机械判定；M2 触发条件未成立故不激活；Q1c 主辅分工已由 q1c_interaction_tradeoff=C 决定",
        "card": "planning/choice_cards/q1_round1_verdict_card.md",
    },
    {
        "id": "q1_stability_verdict",
        "type": "human_decision_required",
        "gate": "G4",
        "summary": "稳定性裁定：7 项检查 4 PASS / 3 FAIL 的处置，含 R6 表述软化与 R7 判据失效",
        "why_ai_cannot_decide": "稳健性检查只产出证据与机械判定，不得由 AI 转换为置信度裁定",
        "card": "planning/choice_cards/q1_round1_verdict_card.md",
    },
    {
        "id": "q1a_arxiv_rank1_claim_scope",
        "type": "human_decision_required",
        "gate": "G4",
        "summary": "R4 暴露的 arxiv 头名依赖 V/P 分组单列归属，须裁定域序 claim 口径",
        "why_ai_cannot_decide": "claim 收窄属人工所有；既有 q1a_book_wikipedia_claim_scope 不覆盖头名情形",
        "card": "planning/choice_cards/q1_round1_verdict_card.md",
    },
]

ARTIFACTS = {
    "robustness_report": "robustness/Q1/q1_robustness_summary.json",
    "robustness_parts": [
        "robustness/Q1/q1_robustness_quality.json",
        "robustness/Q1/q1_robustness_mixture.json",
    ],
    "final_result_analysis": "results/Q1/reports/q1_final_result_analysis.md",
    "choice_card_round1_verdict": "planning/choice_cards/q1_round1_verdict_card.md",
}


def main() -> None:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))

    m["status"] = "g4_prepared_awaiting_three_human_verdicts"
    m["artifacts"].update(ARTIFACTS)

    existing = {b["id"] for b in m["blockers"] if isinstance(b, dict) and "id" in b}
    for b in BLOCKERS:
        if b["id"] not in existing:
            m["blockers"].append(b)

    m["updated_at"] = TS

    # 落盘前校验：每个登记路径都必须真实存在，否则状态源又会与实际不一致
    missing = []
    for k, v in ARTIFACTS.items():
        for p in (v if isinstance(v, list) else [v]):
            if not (ROOT / p).exists():
                missing.append(p)
    if missing:
        raise SystemExit(f"拒绝写入：以下登记路径不存在 {missing}")

    MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print("status:", m["status"])
    print("gate:", m["current_gate"], "(G4 未过，gate_history 未动)")
    print("blockers:", [b["id"] for b in m["blockers"]])
    print("artifacts:", len(m["artifacts"]), "keys")


if __name__ == "__main__":
    main()

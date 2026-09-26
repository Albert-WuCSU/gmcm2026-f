"""把 G2.5 的 f(N) 规格裁定写入 methods/Q4/q4_decisions.jsonl，并更新 manifest 过 G2 + G2.5。

使用者原话:「采用你的建议 C,主口径 A」
授权形式与 Q2 后三条一致(使用者主动采纳 AI 建议) ⇒
  option_content_authored_by=ai + user_action=reviewed_and_adopted_ai_recommendation

幂等:按 decision_id 去重;manifest 的 gate_history 不留重复记录。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEDGER = ROOT / "methods" / "Q4" / "q4_decisions.jsonl"
MANIFEST = ROOT / "planning" / "manifests" / "Q4.json"
SUMMARY = ROOT / "methods" / "Q4" / "probes" / "risk_probe_summary.json"

s = json.loads(SUMMARY.read_text(encoding="utf-8"))
P6 = s["perturbation_sensitivity"]
P3_ci = s["output_degeneracy"]["scale_share_ci95"]

VERBATIM = "采用你的建议 C,主口径 A"

record = {
    "schema_version": 1,
    "decision_id": "q4_fn_spec_and_method_choice",
    "decision_type": "method_choice",
    "status": "DECIDED",
    "decided_by": "human",
    "captured_in_mode": "learning",
    "choice": "C_main_spec_A",
    "choice_label": "主口径 A(十分位 dummy) + B(线性 log N)作规格敏感性一并报告",
    "rationale": VERBATIM,
    "rationale_provenance": "verbatim_user_reply",
    "option_content_authored_by": "ai",
    "user_action": "reviewed_and_adopted_ai_recommendation",
    "rejected_alternatives": [
        "A 单独(仅十分位 dummy):会埋掉「前沿变强而前沿上的模型在变小」这一实测事实",
        "B 单独(仅线性 log N):规模份额为负,占比口径破,须改报绝对点数",
    ],
    "approved_roles": {
        "main": "M1a 半参数归因(f(N) 十分位 dummy + 月度固定效应) + 分层桥接前沿预测",
        "usable_baseline": "M0a 纯时间趋势外推(HD-2 声明)",
        "conditional_fallback": "M2a 改报绝对贡献点数(休眠)",
    },
    "fallback_status": {
        "M2a_trigger": "所采用 f(N) 规格下 scale_share 自助 95% 区间下界 < 0",
        "status_under_approved_spec": s["fallback_trigger_M2a"]["status_under_main_spec_A"],
        "scale_share_ci95_lower": P3_ci[0],
    },
    "evidence_refs": [
        "methods/Q4/probes/risk_probe_summary.json",
        "workspace/data/q4_probe_attribution.json",
        "workspace/data/q4_probe_bridge.json",
        "methods/Q4/q4_method_card.md",
    ],
    "evidence_digest": {
        "P6_spread_over_ci_width": P6["spread_over_ci_width"],
        "P6_specs_scale_share": {k: v["scale_share"] for k, v in P6["specs"].items()},
        "P3_scale_share": s["output_degeneracy"]["scale_share"],
        "P3_tech_share": s["output_degeneracy"]["tech_share"],
    },
    "ai_note": (
        "选项与 AI 倾向(C,主口径 A)由 AI 构造,使用者主动索取意见后采纳,授权形式与 Q2 后三条一致。"
        "须记录:AI 在给出该倾向的同一轮里编造了 bridge 探针结论与 P4/P7 量级(见 "
        "risk_probe_summary.record_corrections_this_round)。但本裁定所依赖的证据是 P3 与 P6,"
        "两者均在真实落盘的 q4_probe_attribution.json 中、已独立核验,故裁定的证据基础未受污染。"
        "AI 当时用于修饰主 claim 的『约 18 个百分点』一句是编造值(真实 P4 差为 0.0539,"
        "且 B5 判 FAIL ⇒ 该子集份额不可当占比读),该句作废,不得写入论文。"
    ),
    "decided_at": "2026-09-25T17:15:00+08:00",
    "supersedes": None,
}


def main() -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    existing = set()
    if LEDGER.exists():
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing.add(json.loads(line)["decision_id"])
    if record["decision_id"] in existing:
        print(f"SKIP (exists): {record['decision_id']}")
    else:
        with LEDGER.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"appended: {record['decision_id']}")

    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    m["current_gate"] = "G2.5"
    m["status"] = "method_chosen_by_human_ready_for_code"
    m["artifacts"]["method_card"] = "methods/Q4/q4_method_card.md"
    m["artifacts"]["decision_ledger"] = "methods/Q4/q4_decisions.jsonl"
    m["artifacts"]["risk_probe"] = "methods/Q4/probes/risk_probe_summary.json"
    m["artifacts"]["choice_card"] = "planning/choice_cards/q4_framing_card.md"
    m["allowed"]["code_generation"] = True
    m["blockers"] = []
    m["next_action"] = {
        "owner": "ai",
        "skill": "model-code-analyzer",
        "reason": "G2 与 G2.5 均已过，可生成 M1a 主方法 + M0a baseline 代码",
    }
    m["updated_at"] = "2026-09-25T17:15:00+08:00"

    hist = [h for h in m.get("gate_history", []) if h["gate"] not in ("G2", "G2.5")]
    hist.append({
        "gate": "G2", "result": "PASSED_CONDITIONAL", "at": "2026-09-25T17:10:00+08:00",
        "basis": ["methods/Q4/q4_method_card.md",
                  "methods/Q4/probes/risk_probe_summary.json",
                  "workspace/data/q4_probe_attribution.json",
                  "workspace/data/q4_probe_bridge.json"],
        "condition": (
            f"P6 技术份额极差 / 自助区间宽 = {P6['spread_over_ci_width']} > 0.50 阈 ⇒ "
            "输出口径对 f(N) 规格敏感，处置方式由 G2.5 裁定"
        ),
    })
    hist.append({
        "gate": "G2.5", "result": "PASSED", "at": "2026-09-25T17:15:00+08:00",
        "basis": ["methods/Q4/q4_decisions.jsonl"],
        "decision": "q4_fn_spec_and_method_choice = C_main_spec_A",
    })
    m["gate_history"] = hist

    todos = m.get("carried_forward_todos", [])
    for t in [
        "P4 的份额不可当占比读(B5 FAIL, total 隐含 -4.55 点);甲/乙偏误须改报绝对点数差",
        "桥接 High 层 n=7 方向对但 p=0.148 不显著;按 F10 不得解读为 High 层质量更差",
        "24 个月视界是否一并报告未裁定,默认不作主报",
        "规格 B(线性 log N)的负份额须在正文作规格敏感性一并报告(裁定 C 的约定)",
        "AI 上一轮编造的 bridge 结论已作废;data_report.md 的 F9 原文正确,不需更正",
    ]:
        if t not in todos:
            todos.append(t)
    m["carried_forward_todos"] = todos

    MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    print("manifest updated")

    chk = json.loads(MANIFEST.read_text(encoding="utf-8"))
    print("  gate =", chk["current_gate"], "| codegen =", chk["allowed"]["code_generation"])
    print("  gate_history =", [(h["gate"], h["result"]) for h in chk["gate_history"]])
    lines = [l for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"  ledger records = {len(lines)}, all parse OK:",
          [json.loads(l)["decision_id"] for l in lines])


if __name__ == "__main__":
    main()

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MP = ROOT / "planning" / "manifests" / "Q4.json"
RV = ROOT / "code" / "Q4" / "reviews" / "q4_python_review.json"

m = json.loads(MP.read_text(encoding="utf-8"))
rv = json.loads(RV.read_text(encoding="utf-8"))

m["current_gate"] = "G3"
m["status"] = "code_and_experiment_reviewed_awaiting_human_g4_verdicts"
m["artifacts"]["latest_run"] = "results/Q4/experiments/round1/run_summary.json"
m["artifacts"]["code_review"] = "code/Q4/reviews/q4_python_review.json"
m["allowed"]["code_generation"] = True
m["allowed"]["freeze"] = False
m["allowed"]["paper_writing"] = False
m["updated_at"] = "2026-09-25T18:05:00+08:00"

m["blockers"] = [
    {
        "id": "F-Q4-2",
        "severity": "high",
        "class": "CANONICAL",
        "blocks": "G4",
        "issue": "账本 q4_scale_channel_definition 的 binding_commitments.known_bias_direction 在 66 子集上不可验证",
        "owner": "human",
    },
    {
        "id": "G4-verdicts",
        "severity": "high",
        "blocks": "G4",
        "issue": "缺 result_verdict / stability_verdict / claim_scope 三类人工裁定",
        "owner": "human",
    },
]

m["next_action"] = {
    "owner": "human",
    "skill": "modeler-decision-logger",
    "reason": "G3 已过。G4 需先处置 F-Q4-2，再给三类裁定",
}

hist = [h for h in m.get("gate_history", []) if h["gate"] != "G3"]
hist.append({
    "gate": "G3",
    "result": "PASSED_WITH_FINDINGS",
    "at": "2026-09-25T18:05:00+08:00",
    "basis": [
        "results/Q4/experiments/round1/run_summary.json",
        "code/Q4/reviews/q4_python_review.json",
    ],
    "checks": {k: v["result"] for k, v in rv["checks"].items()},
    "findings": [{"id": f["id"], "severity": f["severity"]} for f in rv["findings"]],
    "blocking": rv["blocking"],
    "reproducibility": "两次运行 q4_M1a.json 逐字节一致 sha256 a5cb20771e10af7f",
})
m["gate_history"] = hist

todos = m.get("carried_forward_todos", [])
new = [
    "F-Q4-1 pretrained 组 total_points 为负，只能报绝对点数与方向，不得给占比",
    "F-Q4-3 预测判据由 FAIL 翻 PASS 系 AI 修对象不一致缺陷所致，发现次序须披露，裕度仅 1.881 点",
    "F-Q4-6 chat_finetuned 组 scale_share 的 CI95 含 0，不得声称规模贡献显著为正",
    "figures 本轮为空，与 Q1/Q2 同为欠账",
    "G4 两份工件待写：robustness/Q4/q4_robustness_report.md、results/Q4/reports/q4_final_result_analysis.md",
]
for t in new:
    if t not in todos:
        todos.append(t)
m["carried_forward_todos"] = todos

MP.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")

chk = json.loads(MP.read_text(encoding="utf-8"))
print("gate =", chk["current_gate"])
print("history =", [(h["gate"], h["result"]) for h in chk["gate_history"]])
print("blockers =", [b["id"] for b in chk["blockers"]])
print("next_action.owner =", chk["next_action"]["owner"])
print("allowed =", chk["allowed"])
print("todos =", len(chk["carried_forward_todos"]))

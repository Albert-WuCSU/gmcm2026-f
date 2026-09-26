"""把质量侧与配比侧的稳健性结果装配为契约命名的汇总文件。

契约：robustness/Qx/qx_robustness_summary.json（.claude/skills/robustness-checker）
每条检查须含 tested claim、来源路径、扰动、预声明判据与阈值、观测值、
status、limitation、fallback 相关性 —— 字段由两个分侧文件原样带入，本脚本不改判定。

用法：python q1_robustness_assemble.py
"""
from __future__ import annotations

import json

import q1_common as C

OUT = C.ROOT / "robustness/Q1"
PARTS = ["q1_robustness_quality.json", "q1_robustness_mixture.json"]


def main() -> None:
    parts = [json.loads((OUT / p).read_text(encoding="utf-8")) for p in PARTS]
    checks = {}
    for p in parts:
        checks.update(p["checks"])

    by_status: dict[str, list[str]] = {}
    for cid, c in checks.items():
        by_status.setdefault(c["status"], []).append(cid)

    res = {
        "schema_version": 1,
        "question": "Q1",
        "round_under_test": C.ROUND,
        "seed": C.SEED,
        "rigor_profile": "lean",
        "criteria_predeclared_before_execution": True,
        "source_parts": {p["side"]: PARTS[i] for i, p in enumerate(parts)},
        "execution_time_seconds": {p["side"]: p["execution_time_seconds"] for p in parts},
        "n_checks": len(checks),
        "status_rollup": {k: sorted(v) for k, v in sorted(by_status.items())},
        "checks": checks,
        "human_verdict_required": {
            "reason": ("G4 要求账本含 result / stability / claim-scope 三类人工裁定。"
                       "稳健性检查只产出证据与机械判定，"
                       "不得由 AI 转换为置信度裁定或 claim 收窄决定"),
            "existing_ledger_records": "methods/Q1/q1_decisions.jsonl",
            "missing_decision_types": ["result_verdict", "stability_verdict"],
        },
    }
    C.write_json(OUT / "q1_robustness_summary.json", res)
    print(f"装配完成：{len(checks)} 项检查 -> robustness/Q1/q1_robustness_summary.json")
    for st, ids in res["status_rollup"].items():
        print(f"  {st}: {', '.join(ids)}")


if __name__ == "__main__":
    main()

"""把 code plan 落成 manifest 工件，并把 next_action 推到 python-model-code-generator。

不改 current_gate（G3 须待实验与评审完成才通过）。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "planning/manifests/Q1.json"
TS = "2026-09-24T20:30:00+08:00"


def main() -> None:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    m["artifacts"]["code_plan"] = "code/Q1/q1_code_plan.md"
    m["status"] = "code_plan_ready_for_generation"
    m["next_action"] = {
        "owner": "ai",
        "skill": "python-model-code-generator",
        "reason": "代码计划已就位（code/Q1/q1_code_plan.md）：范围为 M0/M1/M0c/M1c + per_domain 消融臂 "
                  "+ 五类参数扰动 + Q1c 的 Q 增量嵌套检验；M2 仅登记触发条件不实现。"
                  "生成后交 python-code-reviewer 产出 code/Q1/reviews/q1_python_review.json",
    }
    m["updated_at"] = TS
    MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("updated", MANIFEST)
    print("  code_plan:", m["artifacts"]["code_plan"])
    print("  status:", m["status"])
    print("  next:", m["next_action"]["skill"])


if __name__ == "__main__":
    main()

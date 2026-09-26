"""把 q1_frac_unique_words_treatment 决策落入 planning/manifests/Q1.json。

改动：
  1) carried_forward_todos 中「[新增·待查] rps_doc_frac_unique_words…」标记为已决
  2) 新增论文局限的必披露项
  3) probe_evidence 追加 q1_probe_unique_words_length.json
  4) decisions 追加该条
  5) next_action 改为 model-code-analyzer（G2.5 已过，代码生成已解锁）
  6) updated_at 刷新

不改 gate_history（本决策不构成新 gate）。不改 canonical_spec_summary（规格未变）。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "planning/manifests/Q1.json"
TS = "2026-09-24T20:10:00+08:00"

OLD_TODO_PREFIX = "[新增·待查] rps_doc_frac_unique_words"
NEW_TODO = (
    "[已决·不处置] rps_doc_frac_unique_words 的长度混淆：使用者决定不处置，CANONICAL 规格不变。"
    "探针判定其与 dsir 同属长度混淆族但机制不同（Heaps 估计量偏倚 β=0.785 vs dsir 的量纲错误），"
    "dsir 式除以 N 会把长度相关由 −0.85 恶化到 −0.99。见 q1_frac_unique_words_treatment"
)
NEW_DISCLOSURE = (
    "[新增·须披露] 论文局限须写成 rps_doc_frac_unique_words 与 rps_doc_unigram_entropy『这一对』"
    "受长度反向混淆（对 log N 的 Spearman 为 −0.85 与 +0.95），不得只点 frac_unique_words；"
    "canonical 保留的 3 对 r<−0.5 已判定为长度诱导的伪矛盾（双方去长度后相关 +0.92），非语义冲突"
)
NEW_PROBE = "workspace/data/q1_probe_unique_words_length.json"


def main() -> None:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))

    todos = m["carried_forward_todos"]
    hits = [i for i, t in enumerate(todos) if t.startswith(OLD_TODO_PREFIX)]
    if hits:
        todos[hits[0]] = NEW_TODO
    elif NEW_TODO not in todos:
        todos.append(NEW_TODO)
    if NEW_DISCLOSURE not in todos:
        todos.append(NEW_DISCLOSURE)

    probes = m["artifacts"].setdefault("probe_evidence", [])
    if NEW_PROBE not in probes:
        probes.append(NEW_PROBE)

    m["decisions"]["q1_frac_unique_words_treatment"] = "no_treatment"
    m["decisions"]["frac_unique_decided_at"] = TS

    m["next_action"] = {
        "owner": "ai",
        "skill": "model-code-analyzer",
        "reason": "G2.5 已过、code_generation 已解锁，且 rps_doc_frac_unique_words 的未决项已由使用者裁定"
                  "（不处置，规格不变）。下一步按交接文档 §5.1 做代码结构分析，"
                  "仅实现 M0/M1/M0c/M1c，M2 保持休眠",
    }
    m["updated_at"] = TS

    MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("updated", MANIFEST)
    print("  current_gate:", m["current_gate"], "| code_generation:", m["allowed"]["code_generation"])
    print("  decisions:", json.dumps(m["decisions"], ensure_ascii=False))
    print("  next_action.skill:", m["next_action"]["skill"])
    print("  todos:", len(todos))


if __name__ == "__main__":
    main()

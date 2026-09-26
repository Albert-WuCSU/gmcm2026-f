"""把 planning/manifests/Q1.json 推进到 G2.5（人工方法选择已记录，代码生成解锁）。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MF = ROOT / "planning/manifests/Q1.json"
TS = "2026-09-24T19:25:00+08:00"


def main() -> None:
    m = json.loads(MF.read_text(encoding="utf-8"))

    m["current_gate"] = "G2.5"
    m["status"] = "method_chosen_ready_for_code_analysis"
    m["artifacts"]["decision_ledger"] = "methods/Q1/q1_decisions.jsonl"
    m["artifacts"]["canonical_spec"] = "workspace/code/scripts/q1_features.py#CANONICAL"
    m["artifacts"]["canonical_verification"] = "workspace/data/q1_canonical_verification.json"
    m["allowed"]["code_generation"] = True
    m["blockers"] = []

    m["approved_methods"] = {
        "quality_side": {"main": "M1", "baseline": "M0", "fallback_dormant": "M2"},
        "mixture_side": {"main": "M1c", "baseline": "M0c"},
        "implement_only": ["M0", "M1", "M0c", "M1c"],
        "note": "M2 保持休眠，仅在其记录的触发条件成立时激活",
    }
    m["decisions"] = {
        "q1_tierC_direction": "D",
        "q1_normalization_population": "A",
        "q1c_interaction_tradeoff": "C",
        "decided_at": "2026-09-24T19:05:00+08:00",
        "ledger": "methods/Q1/q1_decisions.jsonl",
    }
    m["canonical_spec_summary"] = {
        "indicator_columns": 20,
        "dsir": "逐 token 归一化（除以 word_count）后三列合一为 dsir_prose_likeness，方向 +1",
        "length_indicators": "word_count / num_sentences / mean_word_length 非单调（1−2|z−0.5|）",
        "normalization_primary": "pooled + ecdf",
        "normalization_ablation": "per_domain + ecdf（必跑消融臂）",
        "verified": "canonical 复现探针 PT 配置：强矛盾对 0 / 域间极差 0.1757 / AUC 0.9741",
    }
    m["gate_history"].append({
        "gate": "G2.5", "result": "PASSED", "at": TS,
        "basis": ["methods/Q1/q1_decisions.jsonl"],
        "note": "三条 DECIDED 人工 method_choice 记录均为使用者原话、附证据引用、无占位符。"
                "决策引起的 CANONICAL 预处理变更已落入 q1_features.py 并通过范围内一致性核验。",
    })

    todos = m["carried_forward_todos"]
    todos.insert(0, "[G3 硬性] 实验设计四件套：M0/M1/M0c/M1c + 消融（per_domain 归一化臂）+ 参数扰动")
    todos.insert(1, "[G3 硬性] Q1c 须显式检验『加入域级 Q 是否优于仅用 17 维 p』——"
                    "决策 q1_normalization_population=A 的附带要求，无增量则如实写入")
    todos.insert(2, "[G3 硬性] 交互项仅报符号稳定率 >=0.95 者（已测：136 项中 69 项达标、53 项 >=0.99）")
    todos.insert(3, "[G3 硬性] A6–A11 验证须含按尺度截距或改用秩相关，禁止报未去偏原始 R²")
    todos.append("[新增·待查] rps_doc_frac_unique_words（类型-例符比）与 unigram_entropy 相关 −0.68，"
                 "疑同属长度效应（TTR 随文档变长机械下降）；量级远小于 dsir，未处理")
    m["carried_forward_todos"] = todos

    m["updated_at"] = TS
    MF.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    print("updated", MF)


if __name__ == "__main__":
    main()

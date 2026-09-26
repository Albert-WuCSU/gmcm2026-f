"""把使用者对 rps_doc_frac_unique_words 处置的决策追加写入 methods/Q1/q1_decisions.jsonl。

append-only。rationale 一律为使用者原话照录，AI 不补写、不强化。
使用者原始回复：「不处置rps_doc_frac_unique_words，记录我的决策后,继续推进下一步」

背景：该项为交接文档 §9.1 登记的未决事项。探针已判定它与 dsir 同属长度混淆族，
但机制不同（TTR 的 Heaps 估计量偏倚 vs dsir 的量纲错误），dsir 式处置会恶化。
使用者选择不处置，记入论文局限。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEDGER = ROOT / "methods/Q1/q1_decisions.jsonl"
TS = "2026-09-24T20:10:00+08:00"
VERBATIM = "不处置rps_doc_frac_unique_words，记录我的决策后,继续推进下一步"

RECORD = {
    "schema_version": 1,
    "decision_id": "q1_frac_unique_words_treatment",
    "decision_type": "preprocessing_spec",
    "scope": "Q1a 指标预处理：rps_doc_frac_unique_words 的长度混淆是否处置",
    "status": "DECIDED",
    "decided_by": "human",
    "captured_in_mode": "learning",
    "choice": "no_treatment",
    "choice_label": "不处置，保持 CANONICAL 规格不变，记入论文局限",
    "rationale": VERBATIM,
    "rationale_provenance": "verbatim_user_reply",
    "rationale_note": "使用者原话照录，未作拆分改写",
    "chosen_spec": {
        "canonical_change": "无。CANONICAL 规格（20 列 / pooled ecdf / dsir 逐 token 合一）保持不变",
        "rejected_option_2": "只残差化 frac_unique —— 会把复合 Q 的长度暴露由 0.499 抬到 0.579",
        "rejected_option_3": "frac_unique 与 unigram_entropy 一并对 log N 残差化 —— "
                             "矛盾对 3→0、长度暴露 0.499→0.488，但仅赚 0.011，不足以重开 CANONICAL",
        "required_disclosure": "论文局限须写成 rps_doc_frac_unique_words 与 rps_doc_unigram_entropy "
                               "『这一对』受长度反向混淆，不得只点 frac_unique_words —— "
                               "unigram_entropy 才是更大的长度载体（对 log N 的 Spearman +0.95 vs −0.85）",
        "retained_known_issue": "canonical 配置保留 3 对 r<−0.5 的弱矛盾，全部牵涉 frac_unique_words；"
                                "已判定为长度诱导的伪矛盾，非语义冲突",
    },
    "evidence_refs": [
        "methods/Q1/q1_method_card.md",
        "workspace/data/q1_probe_unique_words_length.json",
        "workspace/data/q1_probe_corr.json",
        "workspace/data/q1_canonical_verification.json",
    ],
    "evidence_digest": {
        "field_semantics": "frac_unique_words = 100·V/N（TTR，百分数刻度）；"
                           "去刻度后 V 在 89.3% 的行上为整数",
        "length_dependence": "Spearman vs word_count = −0.8546（dsir 为 −0.93，量级相当）",
        "heaps_law": "β=0.7848，R²=0.9737 → TTR ∝ N^−0.2152，属估计量偏倚而非量纲错误",
        "dsir_style_fix_falsified": "除以 N 后 Spearman vs word_count 由 −0.8546 恶化到 −0.9939",
        "direction_vs_fineweb_edu": "−0.471 → +0.058（残差化换来空信号；dsir 当时是 −0.499 → +0.374）",
        "spurious_contradiction": "与 unigram_entropy 原始 −0.6838；纯长度即可生成 −0.8138；"
                                  "双方去长度后为 +0.9213 强一致",
        "composite_length_exposure_Q_vs_logN": "canonical 0.4994 / 只修 fu 0.5788 / fu+ue 0.4884",
        "impact_if_treated": "行级 Q 秩相关 0.992（只修 fu）与 0.986（fu+ue）；域级最大位移 0.0217",
        "c4_vs_commoncrawl_tie": "canonical 下差值 bootstrap 区间 [−0.00179, +0.00320] 含 0，"
                                 "本就统计并列；故不存在被推翻的显著域序",
    },
    "ai_note": "AI 提供了三个选项与各自的量化后果，并给出标注为『AI 意见』的技术推荐（方案一）；"
               "使用者作出选择。本条 rationale 为使用者原话照录，AI 未补写或强化理由。"
               "注意 GC9：论文中该局限的表述须由本队自行撰写，不得直接复制 AI 生成的方案表述。",
    "decided_at": TS,
    "supersedes": None,
}


def main() -> None:
    if LEDGER.exists():
        existing = [json.loads(ln) for ln in
                    LEDGER.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if any(r.get("decision_id") == RECORD["decision_id"] for r in existing):
            print(f"已存在 {RECORD['decision_id']}，跳过（append-only，不重复写入）")
            return
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(RECORD, ensure_ascii=False) + "\n")
    print(f"appended 1 record ({RECORD['decision_id']}) -> {LEDGER}")


if __name__ == "__main__":
    main()

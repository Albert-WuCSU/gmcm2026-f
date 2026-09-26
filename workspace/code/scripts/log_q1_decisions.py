"""把使用者对 Q1 三项判断的选择追加写入 methods/Q1/q1_decisions.jsonl。

append-only。rationale 一律为使用者原话照录，AI 不补写、不强化。
使用者原始回复（一次性给出三项）：「1D2A3C，我认同你说的。」
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEDGER = ROOT / "methods/Q1/q1_decisions.jsonl"
TS = "2026-09-24T19:05:00+08:00"
VERBATIM = "1D2A3C，我认同你说的。"

AI_NOTE = ("选项内容与其论证由 AI 在决策卡中构造并展示，使用者作出选择并表示认同；"
           "本条 rationale 为使用者原话照录，AI 未补写或强化理由。"
           "AI 所述论证的证据基础见 evidence_refs 所列工件。"
           "注意 GC9：论文中的建模论证须由本队自行撰写，不得直接复制 AI 生成的方案表述。")

COMMON_EVIDENCE = [
    "methods/Q1/q1_method_card.md",
    "methods/Q1/probes/risk_probe_summary.json",
]

RECORDS = [
    {
        "decision_id": "q1_tierC_direction",
        "decision_type": "method_choice",
        "scope": "Q1a/Q1b 指标方向与预处理规格",
        "choice": "D",
        "choice_label": "补充约束：dsir 逐 token 归一化 + 三合一取正 + 长度类非单调",
        "chosen_spec": {
            "dsir_per_token_normalization": "dsir_books/wiki/math 各除以 rps_doc_word_count",
            "dsir_collapse": "逐 token 化后三列合为 1 个代表量 dsir_prose_likeness（互相关 0.996）",
            "dsir_direction": "+1（归一化后与 fineweb_edu 的 Spearman 为 +0.374）",
            "length_indicators": "rps_doc_word_count / rps_doc_num_sentences / "
                                 "rps_doc_mean_word_length 按非单调处理（sign=0，1−2|z−0.5|）",
            "resulting_columns": 20,
        },
        "evidence_refs": COMMON_EVIDENCE + [
            "workspace/data/q1_probe_dsir_length.json",
            "workspace/data/q1_probe_configs2.json",
        ],
        "evidence_digest": {
            "log_neg_dsir_vs_log_wordcount_pearson": "0.937~0.939",
            "spearman_vs_fineweb_edu_raw_to_pertoken": "-0.499 -> +0.374",
            "dsir_books_book_domain_rank_raw_to_pertoken": "7 -> 1",
            "direction_contradiction_pairs_lt_-0.8": "10 (配置A) -> 0 (配置PT)",
            "domain_range": "0.153 -> 0.176",
            "auc_Q_recovering_domain": "0.984 -> 0.974",
        },
    },
    {
        "decision_id": "q1_normalization_population",
        "decision_type": "method_choice",
        "scope": "Q1a 归一化总体口径",
        "choice": "A",
        "choice_label": "合并全体（pooled ecdf）为主报口径，按域口径作声明的消融臂",
        "chosen_spec": {
            "primary": "pooled + 经验分位数（ecdf）",
            "ablation_arm": "per_domain + ecdf（须在实验设计中作为消融对照实跑）",
            "mandatory_disclosure": "Q 还原域标签 AUC(arxiv:github)=0.974，须在论文显式披露",
            "required_followup_test": "在 Q1c 中显式检验『加入域级 Q 是否优于仅用 17 维 p』，"
                                      "若无增量则如实写入，作为对题目『是否引入 Q 由参赛队伍论证』的回答",
        },
        "evidence_refs": COMMON_EVIDENCE + [
            "workspace/data/q1_probe_quality.json",
            "workspace/data/q1_probe_transferability.json",
        ],
        "evidence_digest": {
            "pooled_ecdf": "域间极差 0.153 / AUC 0.984",
            "per_domain_ecdf": "域间极差 0.0028 / AUC 0.498（域级 Q 近乎恒等）",
            "why_per_domain_rejected": "语料级 Q=Σp_iQ_i 几乎不随配比变化，Q1c 的 Q 通道消失，"
                                       "Q2 无量可与 B6-B8 设计网格做尺度校准，"
                                       "且 Q1a 必交产出『域级 Q 与抽样集对照』无从对照",
            "transferability_weighted_variant": "已实跑并撤回：eta2<0.05 仅剩 2 个指标，"
                                                "阈值 0.05->0.20 域序翻转",
        },
    },
    {
        "decision_id": "q1c_interaction_tradeoff",
        "decision_type": "method_choice",
        "scope": "Q1c 主方法与交互项",
        "choice": "C",
        "choice_label": "M0c 与 M1c 都跑，论文以 M0c 为主、M1c 作组合效应的辅助证据",
        "chosen_spec": {
            "primary_model": "M0c 17 维主效应（去截距或指定参照域）",
            "auxiliary_model": "M1c 主效应 + 二阶交互 + 岭正则",
            "interaction_reporting_filter": "仅报符号稳定率 >= 0.95 的交互项",
            "stable_subset_size": "主效应 17/17 稳定；交互 136 项中 69 项 >=0.95、53 项 >=0.99"
                                  "（B=400 自助，lambda=0.001）",
            "validation_convention": "A6-A11 须含按尺度截距或改用秩相关；"
                                     "禁止报未去偏的原始 R²（60m/1B 为 -8.4/-173，"
                                     "bias 占 RMSE 98.8%/99.9%）",
            "prohibited_claim": "不得把单个二阶交互系数解释为域间替代/互补的定量结论，"
                                "除非该系数在稳定子集内",
        },
        "evidence_refs": COMMON_EVIDENCE + ["workspace/data/q1_probe_mixture.json"],
        "evidence_digest": {
            "M0c_pweighted13": "train R²=0.896；去偏后 test_1m/60m/1B = 0.913/0.771/0.705；"
                               "Spearman 0.953/0.922/0.887；系数符号稳定率 1.000",
            "M1c_pweighted13": "去偏后 test_1m/60m/1B = 0.983/0.766/0.658；"
                               "符号稳定率 0.549；平均相对 SE 1.514",
            "why_C": "题目要求『各领域及其组合对性能的影响』，组合为必交产出，M0c 单独无法交付；"
                     "M1c 在 1B 上劣于 baseline（0.658 < 0.705），不可单独作主模型",
        },
    },
]


def main() -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for r in RECORDS:
        rec = {
            "schema_version": 1,
            "decision_id": r["decision_id"],
            "decision_type": r["decision_type"],
            "scope": r["scope"],
            "status": "DECIDED",
            "decided_by": "human",
            "captured_in_mode": "learning",
            "choice": r["choice"],
            "choice_label": r["choice_label"],
            "rationale": VERBATIM,
            "rationale_provenance": "verbatim_user_reply",
            "rationale_note": "使用者一次性给出三项选择，本条为该次回复的原话全文，未作拆分改写",
            "chosen_spec": r["chosen_spec"],
            "evidence_refs": r["evidence_refs"],
            "evidence_digest": r["evidence_digest"],
            "ai_note": AI_NOTE,
            "decided_at": TS,
            "supersedes": None,
        }
        lines.append(json.dumps(rec, ensure_ascii=False))
    # append-only
    mode = "a" if LEDGER.exists() else "w"
    with open(LEDGER, mode, encoding="utf-8") as f:
        for ln in lines:
            f.write(ln + "\n")
    print(f"appended {len(lines)} records -> {LEDGER}")


if __name__ == "__main__":
    main()

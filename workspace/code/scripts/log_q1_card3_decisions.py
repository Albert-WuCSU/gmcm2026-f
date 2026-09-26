"""登记第三张决策卡的三条人工裁定（1B / 2B / 3A）到 methods/Q1/q1_decisions.jsonl。

按 .claude/skills/modeler-decision-logger/SKILL.md：
- rationale 只录使用者原话，不补写、不强化、不把 AI 意见写进 rationale；
- 三条出自同一次回复，故 rationale 相同，并以 rationale_note 说明未拆分改写；
- append-only，supersedes 为 null（三条均为新增，不推翻任何既有决策）；
- 落盘前校验 evidence_refs 路径存在、rationale 非空无占位符、JSONL 每行可解析。

幂等：若三个 decision_id 已存在则拒绝重复追加。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEDGER = ROOT / "methods/Q1/q1_decisions.jsonl"
TS = "2026-09-24T22:55:00+08:00"

# 使用者原话全文（一次性给出三项选择）。不得改写。
VERBATIM = "根据我们的讨论以及你的补充算结果，我选择1B,2B,3A，请记录我们的决策，然后继续推进"

RATIONALE_NOTE = ("使用者一次性给出三项选择，本条为该次回复的原话全文，未作拆分改写。"
                  "原话所称『补充算结果』指本轮已核验的 R4 top-3 集合不变性"
                  "（9 个配置下最高一档恒为 {arxiv,c4,commoncrawl}）；"
                  "裁定 1 选项 B 所含的 B-1/B-2 补算在本决策作出时尚未执行，由本决策授权执行。")

AI_NOTE = ("选项与其量化后果由 AI 构造并展示；使用者在讨论中主动索取 AI 技术意见，"
           "AI 给出的意见（1B/2B/3A）已明确标注为 AI 意见且不写入本 rationale。"
           "本条 rationale 为使用者原话照录，AI 未补写或强化理由。"
           "注意 GC9：论文中的相应论证须由本队自行撰写，不得直接复制 AI 生成的方案表述。")

RECORDS = [
    {
        "schema_version": 1,
        "decision_id": "q1_result_verdict",
        "decision_type": "result_verdict",
        "scope": "Q1 round1 结果裁定（是否接受 round1 为最终轮）",
        "status": "DECIDED",
        "decided_by": "human",
        "captured_in_mode": "learning",
        "choice": "B",
        "choice_label": "先做两项补算（B-1/B-2），两项均不改动主结论，之后接受 round1 为 Q1 最终轮",
        "rationale": VERBATIM,
        "rationale_provenance": "verbatim_user_reply",
        "rationale_note": RATIONALE_NOTE,
        "round_action": "accept_round1_as_final_after_two_supplementary_computations",
        "chosen_spec": {
            "B-1": ("R6 在 test_1B 格提高自助重抽样次数，判定该格增量区间是否真含 0。"
                    "卡内原写 B>=4000；AI 在意见中修正为 B=40000（理由：两个 RNG 状态的上界相差约 1.9e-5，"
                    "B=4000 的蒙特卡洛误差约 3e-6 与上界离零距离同量级，仍可能翻号）。"
                    "不放宽 R6 的预声明判据（12 格全含 0），R6 的 FAIL 状态不变"),
            "B-2": ("给 R4 的 8 个分组变体补记域级点估计与自助区间，"
                    "以回答『被推翻的 3 个变体中 c4 反超 arxiv 是否统计可分』。"
                    "不改 R4 的预声明判据与 FAIL 状态，仅补描述性证据"),
            "round2_not_ordered": "未下令 round2。三项预声明指标均已达标，R1/R2/R3 证明质量侧结论对聚合估计量、种子、扰动幅度稳健",
            "fallback_M2": "不激活。触发条件未成立（强矛盾对 r<-0.8 计数 0；CD2@p75 在 8 个分组变体下为 0.0236-0.0568，全部留在 (0.01,0.50) 内）",
        },
        "rejected_alternatives": {
            "A": "不补算直接接受 —— 会使裁定 3 在缺少各变体点估计的情况下作出",
            "C": "下令 round2 —— 未采纳",
        },
        "evidence_refs": [
            "results/Q1/reports/q1_final_result_analysis.md",
            "robustness/Q1/q1_robustness_summary.json",
            "results/Q1/experiments/round1/run_summary.json",
            "planning/choice_cards/q1_round1_verdict_card.md",
        ],
        "evidence_digest": {
            "predeclared_metrics_quality": "可分辨域对 19->21/21；扰动 τ 0.9595->0.9976，差的自助 95% 区间 [0.0190,0.0571] 不含 0",
            "mixture_gain_scale_local": "1m +0.0703 / 60m -0.0050 / 1B -0.0464",
            "disclosures_not_predeclared": "域间极差方向相反（M0 0.1757 > M1 0.1582）；top1% 样本重叠之差 [-0.0022,+0.0162] 含 0",
            "robustness_rollup": "7 项检查 4 PASS / 3 FAIL",
        },
        "ai_note": AI_NOTE,
        "decided_at": TS,
        "supersedes": None,
    },
    {
        "schema_version": 1,
        "decision_id": "q1_stability_verdict",
        "decision_type": "stability_verdict",
        "scope": "Q1 稳健性 7 项检查（4 PASS / 3 FAIL）的处置",
        "status": "DECIDED",
        "decided_by": "human",
        "captured_in_mode": "learning",
        "choice": "B",
        "choice_label": "三条 FAIL 按现状记录并各自保留其性质；R6 的 1B 表述待 B-1 补算后确定；不为 R7 事后新立判据",
        "rationale": VERBATIM,
        "rationale_provenance": "verbatim_user_reply",
        "rationale_note": RATIONALE_NOTE,
        "chosen_spec": {
            "R4": "保持 FAIL。真发现，claim 须收窄 —— 由 q1a_domain_order_claim_scope 裁定",
            "R6": ("保持 FAIL（预声明判据为 12 格全含 0，实测 11 格，不作事后放宽）。"
                   "1B 格的最终表述待 B-1 补算后确定；结论方向不变：无证据显示 Q 带来正增量，"
                   "唯一例外格的增量为负（方向与『Q 有帮助』相反）"),
            "R7": ("保持 FAIL 并记为『判据设计失效』。不新立事后判据。"
                   "真信息写入局限：域效应的量级排序依赖目标口径（两口径系数向量 Spearman -0.5809）。"
                   "AMB-Q1-2 的循环性声明据此由『须声明』加强为『量级排序依赖目标口径』"),
            "prohibited_statement": "不得把三条 FAIL 笼统表述为『稳健性检查通过/未通过』",
            "predeclared_criteria_not_relaxed": True,
        },
        "rejected_alternatives": {
            "A": "同 B 但 R6 表述立即定稿 —— 未采纳，等 B-1",
            "C": "为 R7 新立一条预声明判据重做检验 —— 未采纳",
        },
        "evidence_refs": [
            "robustness/Q1/q1_robustness_summary.json",
            "robustness/Q1/q1_robustness_quality.json",
            "robustness/Q1/q1_robustness_mixture.json",
            "results/Q1/reports/q1_final_result_analysis.md",
        ],
        "evidence_digest": {
            "PASS": "R1 聚合估计量 / R2 五种子 / R3 扰动幅度 / R5 等 n 对照",
            "R4": "8 变体中 3 个破 arxiv 居首（ad_en_margin / top_2gram / top_3gram），τ 0.714/0.810/0.905",
            "R6": "12 格中 11 格含 0；例外 M1_pooled@1B 上界 -3.8e-6，round1 同配置为 +1.5e-5，点估计逐位一致 -0.00081873，n=64",
            "R7": "符号一致率 1.000 是平凡结果（Loss 目标 + 去截距 + Σp=1 使 17 系数必然全正）；系数向量 Spearman -0.5809；philpapers 6.14->1.24、enron_emails 4.79->0.99；mean13 在 1B 去偏 R² -8.667",
        },
        "ai_note": AI_NOTE,
        "decided_at": TS,
        "supersedes": None,
    },
    {
        "schema_version": 1,
        "decision_id": "q1a_domain_order_claim_scope",
        "decision_type": "claim_scope",
        "scope": "Q1a 域序头部（arxiv 头名）的表述口径",
        "status": "DECIDED",
        "decided_by": "human",
        "captured_in_mode": "learning",
        "choice": "A",
        "choice_label": "收窄为最高一档，不对 arxiv 在该档内的位次作断言",
        "rationale": VERBATIM,
        "rationale_provenance": "verbatim_user_reply",
        "rationale_note": (RATIONALE_NOTE + " 选项 A 在卡内的措辞为『arxiv 与 c4 同属最高一档』"
                          "并已附注该档实含 3 个域；讨论中 AI 据 top-3 集合不变性将其精确化为下列 "
                          "chosen_spec（最高一档 = {arxiv,c4,commoncrawl}，档内 c4>commoncrawl，github 居末）。"
                          "本条按精确化后的口径登记；若使用者本意为更窄的两域表述，须追加一条 supersedes 记录更正。"),
        "chosen_spec": {
            "prohibited_claim": "不得声称 arxiv 是质量最高的域，不得对 arxiv 在最高一档内的位次作断言",
            "required_statement": [
                "最高一档为 {arxiv, c4, commoncrawl}（V/P 分组扰动下集合不变，9/9）",
                "该档内 c4 > commoncrawl（9/9）",
                "github 居末（9/9）",
                "arxiv 在该档内的位次依 V/P 分组的单列归属而变（实测取到 1/2/3），须显式声明该依赖",
            ],
            "scope_limit": "本口径针对域序头部；book~wikipedia 另由 q1a_book_wikipedia_claim_scope 裁定为统计上不可区分",
            "downstream_Q2": "不影响 Q2 —— Q2 使用域级 Q 的数值与区间，不使用名次。arxiv 的域级 Q 是 7 域中估计最精确者（半宽 0.00081，n=18942）",
            "historical_record_must_not_change": "code/Q1/q1_robustness_quality.py 的 tested_claim / predeclared_criterion 是 R4 预声明判据的历史记录，不得据本决策改写；R4 的 FAIL 状态不变",
        },
        "rejected_alternatives": {
            "B": "保留 arxiv 居首为主报断言 + 声明依赖 —— 未采纳",
            "C": "只报 github 居末与 c4>commoncrawl，头部整体不作断言 —— 未采纳",
        },
        "evidence_refs": [
            "robustness/Q1/q1_robustness_summary.json",
            "results/Q1/reports/q1_final_result_analysis.md",
            "results/Q1/experiments/round1/tables/q1a_domain_quality.csv",
            "methods/Q1/q1_method_card.md",
        ],
        "evidence_digest": {
            "top3_set_invariant": "9 个配置（base + 8 变体）下最高一档恒为 {arxiv, c4, commoncrawl}",
            "arxiv_rank_observed": "1 / 2 / 3（base 及 5 个变体为 1；top_2gram、top_3gram 为 2；ad_en_margin 为 3）",
            "github_last": "9/9",
            "c4_above_commoncrawl": "9/9",
            "base_separation_is_statistically_clear": "M1 Huber 下 arxiv 0.38150(±0.00081) vs c4 0.36381(±0.00193)，差 0.01769 = 半宽和的 6.5 倍 —— 故不稳固性来自规格依赖，非统计不可分",
            "mechanism": "Q=V·(1−P) 使一列在 V 中加性（权重 1/14）、在 P 中经 (1−P) 乘性门控（权重 1/6），归组即改变函数角色；而 V/P 为纯语义划分，组内相关 0.051/0.026 与组间 0.016 同量级",
            "evidence_count_not_overstated": "3 个破 claim 的列中 top_2gram 与 top_3gram 同属字符 n-gram 重复度，语义为一族 => 实为 2 类成因，非 3 份独立证据",
        },
        "ai_note": AI_NOTE,
        "decided_at": TS,
        "supersedes": None,
    },
]


def main() -> None:
    lines = [ln for ln in LEDGER.read_text(encoding="utf-8").splitlines() if ln.strip()]
    existing = {json.loads(ln)["decision_id"] for ln in lines}

    new = [r for r in RECORDS if r["decision_id"] not in existing]
    if not new:
        print("三条裁定已存在，未重复追加。现有：", sorted(existing))
        return

    # 校验
    for r in new:
        assert r["rationale"].strip() and "TODO" not in r["rationale"], r["decision_id"]
        assert r["rationale"] == VERBATIM, "rationale 必须是使用者原话全文"
        assert r["decided_by"] == "human" and r["status"] == "DECIDED"
        for p in r["evidence_refs"]:
            if not (ROOT / p).exists():
                raise SystemExit(f"拒绝写入：{r['decision_id']} 的证据路径不存在 {p}")

    with LEDGER.open("a", encoding="utf-8") as fh:
        for r in new:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 回读校验 JSONL 合法
    out = [ln for ln in LEDGER.read_text(encoding="utf-8").splitlines() if ln.strip()]
    ids = [json.loads(ln)["decision_id"] for ln in out]
    types = [json.loads(ln)["decision_type"] for ln in out]
    print(f"追加 {len(new)} 条，账本现共 {len(out)} 条（JSONL 全部可解析）")
    for i, (a, b) in enumerate(zip(ids, types), 1):
        print(f"  {i}. {a:34s} {b}")
    need = {"result_verdict", "stability_verdict", "claim_scope"}
    print("G4 要求的三类裁定齐备：", need <= set(types))


if __name__ == "__main__":
    main()

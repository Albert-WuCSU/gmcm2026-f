"""落 Q2/Q3 的 G4 裁定到各自账本(append-only)。

使用者原话(逐字)：
    Q2: 1B 2B 3A 4A
    Q3: F4-A 1B 2B 3A
    记录我的决策后继续推进，推进完Q2\\Q3的G4后后写交接文档，然后我开新窗口完成可视化

rationale 只录与本题相关的那一行原话；整条原话另存 user_reply_full 以便追溯。
option_content_authored_by=ai + user_action=reviewed_and_adopted_ai_recommendation，
与 Q2 后三条 / Q3 三条 / Q4 六条的处理一致（使用者主动索取 AI 意见后采纳）。

幂等：按 decision_id 去重，已存在则跳过。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TS = "2026-09-25T21:30:00+08:00"
FULL = ("Q2: 1B 2B 3A 4A\nQ3: F4-A 1B 2B 3A\n"
        "记录我的决策后继续推进，推进完Q2\\Q3的G4后后写交接文档，然后我开新窗口完成可视化")

Q2 = [
    {
        "decision_id": "q2_result_verdict",
        "decision_type": "result_verdict",
        "choice": "supplement_two_gaps_then_finalize",
        "choice_label": "接受 round1 的结论，但先补算两项再定稿：① beta 跨源共享同构探针；② 参数扰动/消融/M0s 同口径扰动",
        "rationale": "Q2: 1B 2B 3A 4A",
        "rejected_alternatives": [
            "A 接受 round1 为最终轮、两缺口仅作声明 —— 会留下 beta 未检验的 OPEN 项，且消融/参数扰动是本项目其他三问都做过的实验四件套之一",
            "C 下令 round2 重跑主实验 —— 无证据支持：三项预声明判据全 PASS，三项 FAIL 已通过改变模型结构消化",
        ],
        "binding_commitments": {
            "B1_beta_probe": "补做与 P8 同构的 beta 跨源共享探针；若判 FAIL 则 beta 同为来源专属，须重述其承重假设地位",
            "B2_perturbation_ablation": "补做参数扰动 + 消融 + M0s 同口径扰动，补齐实验四件套",
            "no_criterion_loosening": "补算不改动任何预声明判据文字；三项判据的 PASS 与 P1/P8/P2 的 FAIL 状态均不变",
            "claim_scope_is_provisional": "若补算结果使 gamma 区间或 B7 超越性降幅区间显著变化，3A 的口径须重述",
        },
        "evidence_refs": [
            "results/Q2/reports/q2_final_result_analysis.md",
            "robustness/Q2/q2_robustness_report.md",
            "code/Q2/reviews/q2_python_review.json",
        ],
        "ai_note": "选项与量化后果由 AI 构造；使用者主动索取 AI 建议（四个问题均答『给我你的选择建议，并附带理由』），"
                   "AI 给出建议后使用者采纳。按 AGENTS.md，AI 建议不写入 rationale。",
    },
    {
        "decision_id": "q2_stability_verdict",
        "decision_type": "stability_verdict",
        "choice": "supplement_beta_probe_then_restate",
        "choice_label": "13 项检查按现状记录、各保留其性质，但补做与 P8 同构的 beta 探针后按新证据重述稳定性结论",
        "rationale": "Q2: 1B 2B 3A 4A",
        "rejected_alternatives": [
            "A 仅按现状记录不补算 —— 浪费 beta 探针的产出（秒级成本）",
            "C 另为 P4 的判据设计失效新立一条判据重做 —— 该判据将在看到 worst=0.9944728324465535 之后设计，构成事后择判据",
        ],
        "binding_commitments": {
            "keep_natures_distinct": "P1/P8/P2 三项 FAIL 是真发现（已改变模型结构）；P4 判据测错对象、P5 判据太松属方法学问题（判据缺陷，非结论错误）；两类不得笼统合并表述",
            "no_post_hoc_loosening": "沿用 Q1 R6/R7 与 Q3 的纪律，不为新发现的脆弱性事后新立宽判据",
            "beta_status_after_probe": "探针结果决定 beta 是『已检验的跨源共享参数』还是『同为来源专属』，两种情形下论文表述不同",
        },
        "evidence_refs": [
            "robustness/Q2/q2_robustness_report.md",
            "methods/Q2/probes/risk_probe_summary.json",
            "code/Q2/reviews/q2_python_review.json",
        ],
        "ai_note": "同上：选项由 AI 构造，使用者索取并采纳 AI 建议；建议不写入 rationale。",
    },
    {
        "decision_id": "q2_claim_scope",
        "decision_type": "claim_scope",
        "choice": "bind_to_b7_design_scale",
        "choice_label": "主张「在 B7 设计刻度上 D_eff ≈ D·Q（质量按比例放大有效 token 数）」，并把三条边界写进正文",
        "rationale": "Q2: 1B 2B 3A 4A",
        "rejected_alternatives": [
            "B 只报 gamma 与区间、不作解释 —— 会把 Q2 最有价值的结构性结论降级为一句观察",
            "C 主张该比例放大关系跨刻度成立（也适用于 Q1 的经验 Q） —— 当前无证据支持：AMB-Q2-3 尺度对齐未建立，须先补刻度对齐并声明一项新的承重假设",
        ],
        "binding_commitments": {
            "claimable": [
                "gamma = 0.9659128363851796，自助 95% 区间 [0.8838599505464407, 1.055546203294626] 含 1.0",
                "在 B7 设计刻度上 D_eff ≈ D·Q，即质量按比例放大有效 token 数",
                "Q+0.1 等价 N 增量（参照点 N=1B, D=150B, Q=0.5；须带参照点且两侧同报）",
                "dL/dp 域比值排序（中心化 w 之比，kappa 无关）",
            ],
            "must_write_boundaries": [
                "gamma 完全由半合成 B7 决定（B1 上 Q=1，对 gamma 零信息），按 GC5 须披露",
                "AMB-Q2-3 尺度对齐未解决：Q1 经验 Q 落在 [0.223306, 0.381496]，B7 设计网格 Q 为 [0.1,...,1.0]，"
                "gamma 的解释绑定在 B7 设计刻度上，不得移植到 Q1 的经验 Q",
                "kappa 严格不可辨识且随参照点变（1B run 内 -14.215132486372847 到 -1.6413，差 8.7 倍），"
                "任何绝对量级须带参照点",
            ],
            "prohibited": [
                "不得同时声称「Q 与 D 的替代率随位置变化」（该弹性比恒为常数）",
                "不得陈述为「联合拟合提升了估计」（P8 后联合 WLS 实质退化为两段式）",
                "不得报跨源未去偏的 R²",
                "不得把 2.0000 当作本轮弹性比估计",
            ],
        },
        "evidence_refs": [
            "results/Q2/experiments/round1/metrics/q2_M1s.json",
            "results/Q2/reports/q2_final_result_analysis.md",
        ],
        "ai_note": "同上：选项由 AI 构造，使用者索取并采纳 AI 建议；建议不写入 rationale。",
    },
    {
        "decision_id": "q2_domain_ratio_reporting",
        "decision_type": "claim_scope",
        "choice": "full_table_with_semantic_disclaimer",
        "choice_label": "17 域比值表全部报出，并带 CSV 自带的语义声明「中心化 w 之比、非有界比例」",
        "rationale": "Q2: 1B 2B 3A 4A",
        "rejected_alternatives": [
            "B 只报 Loss 最高域与最低域两端 —— 会丢掉 17 域结果，且 Q3 的 dL/dp 排序线依赖该表",
        ],
        "binding_commitments": {
            "semantic_disclaimer_required": "该值为「中心化 w 之比，非有界比例」；负值表示 upweight 该域会降低 Loss；"
                                            "全表仅 train_the_pile_dm_mathematics 的 abs_gt_1 为 yes（-1.618816）",
            "no_independent_corroboration": "该排序与 Q3 的 dL/dp 线同源（两者都源自 Q1 的 q1c_coefficients），"
                                            "两处一致只作内部一致性检查，不构成独立佐证",
        },
        "evidence_refs": [
            "results/Q2/experiments/round1/tables/q2_domain_ratio.csv",
        ],
        "ai_note": "同上：选项由 AI 构造，使用者索取并采纳 AI 建议；建议不写入 rationale。",
    },
]

Q3 = [
    {
        "decision_id": "q3_baseline_definition_f4",
        "decision_type": "claim_scope",
        "choice": "keep_M0o_as_declared_baseline_report_three_numbers",
        "choice_label": "维持 M0o（D/N = 20）为官方 baseline，M0o′ 保持诊断项；论文三数同报",
        "rationale": "Q3: F4-A 1B 2B 3A",
        "supersedes": None,
        "rejected_alternatives": [
            "B 改官方 baseline 为 M0o′（Q=Q0、N:D 自由） —— 会让 baseline 依赖本律："
            "M0o′ 是本律自身的退化分支（其 loss 与 M1o 的 lower_Q_eq_Q0 分支全位相同），"
            "而 M0o 是独立于本律的外部经验配置；且 M0o′ 的 D/N=79.59104144631574~243.02074222002932 "
            "并非 Chinchilla 配置，以其充当 Chinchilla baseline 属名实不符",
            "C 双 baseline 正式并报 —— 仍属改动已声明 baseline 集合，且使预声明指标 1 的通过/不通过出现两个版本；"
            "三数同报已提供等价信息",
        ],
        "binding_commitments": {
            "three_numbers_mandatory": "gap_reported / gap_quality_only / gap_ratio_handicap 三数必须同时报，"
                                       "不得只报 gap_reported",
            "handicap_share": "handicap 占报告差距 32.10322783409671% (1e19) / 27.65840772632896% (1e22) / "
                              "34.00830933287415% (1e24)",
            "baseline_unmodified": "代码按卡上定义原样实现未改动；M0o′ 的 role 保持 "
                                   "diagnostic_reference_NOT_baseline，不得作为官方 baseline 报出",
            "disclosure_in_text": "正文须承认预声明指标 1 的差距含与质量通道无关的成分（27.65840772632896%~34.00830933287415%）",
        },
        "evidence_refs": [
            "results/Q3/experiments/round1/tables/q3_baseline_gap_decomposition.csv",
            "results/Q3/experiments/round1/metrics/q3_M0o.json",
            "code/Q3/reviews/q3_python_review.json",
            "planning/framing_decisions.jsonl",
        ],
        "ai_note": "F4 属 HD-2 范畴。AI 在建议中指出评审未提的两条事实：M0o 独立于本律、M0o′ 是本律自身退化；"
                   "以及 HD-2 卡原文只要求 N∝D。使用者采纳 A。建议不写入 rationale。",
    },
    {
        "decision_id": "q3_result_verdict",
        "decision_type": "result_verdict",
        "choice": "supplement_Q0_sensitivity_and_4th_cost_form_then_finalize",
        "choice_label": "接受 round1 的结论，但先补做两项再定稿：① Q0 敏感性（扫 Q1 实测域级 Q 范围）；② 新增第四类 g(Q)（题目「或改进」部分）",
        "rationale": "Q3: F4-A 1B 2B 3A",
        "rejected_alternatives": [
            "A 接受 round1 为最终轮、不补做 —— 会留下题目「或改进 g(Q)」这一处唯一的未答题，"
            "且 Q0=0.35 保持『未经裁定』状态",
            "C 下令 round2 重跑主实验 —— 无证据支持：三项预声明判据全过，KKT 五项硬判据在 57 点上全过并经三条独立路径复核",
        ],
        "binding_commitments": {
            "cost_is_negligible": "Q3 全量重跑仅 3.244 s，补做成本几乎为零",
            "B1_Q0_sensitivity": "在 Q1 实测域级 Q 范围 [0.223306, 0.381496] 上扫若干取值，"
                                 "看 Q*/loss/转移位置是否移动；纯机械，无需使用者裁定",
            "B2_fourth_cost_form": "第四类 g(Q) 的具体形式属建模判断，须由使用者裁定后实现",
            "transition_pos_may_move": "若 Q0 或 g 改变导致活跃集翻转点移动，"
                                       "claim_scope 中的转移位置 log10 C = 21.405181884765625 须相应更新",
        },
        "evidence_refs": [
            "results/Q3/reports/q3_final_result_analysis.md",
            "robustness/Q3/q3_robustness_report.md",
            "results/Q3/experiments/round1/metrics/q3_M1o.json",
        ],
        "ai_note": "选项由 AI 构造，使用者索取并采纳 AI 建议；建议不写入 rationale。",
    },
    {
        "decision_id": "q3_stability_verdict",
        "decision_type": "stability_verdict",
        "choice": "supplement_Q0_sensitivity_then_restate",
        "choice_label": "19 项检查按现状记录、各保留其性质，但补做 Q0 敏感性后重述稳定性结论",
        "rationale": "Q3: F4-A 1B 2B 3A",
        "rejected_alternatives": [
            "A 仅按现状记录不补做 —— Q0 是承重参数且文件明确标注『未经使用者裁定，可被否决』，其敏感性缺失是当前最实的短板",
            "C 另为「规模压缩」单独立一条预声明判据重做 —— 该判据将在看到 N* 变化 -54.83512125256155% 之后设计，构成事后择判据；"
            "且规模压缩幅度已量化，无需新判据",
        ],
        "binding_commitments": {
            "keep_natures_distinct": "P1/P3 两项 FAIL 是真发现（已改变求解结构：必须分段 KKT；p 不联立）；"
                                     "P5 的判据只问了较窄的问题（配比是否重排），属方法学问题，两类不得笼统合并",
            "p5_double_sided_reporting": "须同时报 P5 判 WEAK_EFFECT（N:D 极差 3.22%）与规模压缩（N* -54.83512125256155%、"
                                         "D* -53.37880146895937%），不得只引其一、不得把 WEAK_EFFECT 读成『L_ctx 不重要』",
            "upstream_number_discipline": "隐含 D/N 用本轮值 79.59104144631574/155.5004609503274/243.02074222002932"
                                          "（非上游 32.06/62.64/97.89）；N:D 相对变化用 3.22%（非 3.12%）",
            "no_post_hoc_loosening": "预声明判据文字一律不改",
        },
        "evidence_refs": [
            "robustness/Q3/q3_robustness_report.md",
            "workspace/data/q3_probe_optimization.json",
            "code/Q3/reviews/q3_python_review.json",
        ],
        "ai_note": "选项由 AI 构造，使用者索取并采纳 AI 建议；建议不写入 rationale。",
    },
    {
        "decision_id": "q3_claim_scope",
        "decision_type": "claim_scope",
        "choice": "claim_three_transition_scale_dldp",
        "choice_label": "主张三条：① 结构性转移（主定义位置 + 三定义并报 + 连续饱和形态）；② 跨 L_ctx^crit 压缩规模而非重排配比；③ dL/dp 只报符号与域间排序",
        "rationale": "Q3: F4-A 1B 2B 3A",
        "rejected_alternatives": [
            "B 只报转移的『存在与位置』与 KKT 全过，不主张形态；L_ctx 只列数值表 —— 会丢掉本问最有价值的发现（三定义三答案 + 连续饱和）",
            "C 另主张转移位置可作预算配置的定量阈值并据此给配置建议 —— 越界：把描述性结论变成规范性建议；"
            "1e22/1e24 的 Q*=1.0 中 1e24 落在外推区；且 1e19 下三类 g 给出三种不同 Q*，阈值建议不稳健",
        ],
        "binding_commitments": {
            "claimable": [
                "存在结构性转移；主定义（活跃约束集变化）位置 log10 C = 21.405181884765625，不依赖阈值与步长",
                "三定义三答案：A 21.405181884765625 / C 22.625 / D 判不出（NO_TRANSITION）",
                "转移形态为连续饱和而非突跳；饱和点 dQ*/dlogC 由正转零",
                "跨 L_ctx^crit 压缩规模而非重排配比（N* -54.83512125256155%、D* -53.37880146895937%，N:D 仅 3.22%）",
                "dL/dp 只报符号与域间排序（dL/dp_i ÷ dL/dp_j = b_i/b_j，kappa 无关）",
                "成本函数影响集中在低预算档（Q* 极差 0.46095601286892085 全来自 1e19）",
            ],
            "must_write_limits": [
                "L_ctx_crit = 30000 仅为两类成本相等的临界尺度，不是最优上下文长度",
                "不得笼统写「各档预算最优质量恒为 1」——低预算档明确不是（0.6460174872692858 / 0.5390439871310791）",
                "1e24 为外推：N 相对 B1 观测上界 3.4059903063249575×、D 12.574318155320217×，不得表述为可靠预测",
                "Q0 = 0.35 未经使用者裁定；Chinchilla 常数未经原文核验（constants_verified_against_paper=false）",
                "Chinchilla 对照不构成外部锚点",
            ],
            "prohibited": [
                "不得沿用『饱和点导数由负转零』（实测由正转零）",
                "不得声称 Chinchilla 对照构成外部锚点",
                "不得报 p* 或 dL/dp 的绝对量级",
            ],
        },
        "evidence_refs": [
            "results/Q3/experiments/round1/tables/q3_transition_definitions.csv",
            "results/Q3/experiments/round1/tables/q3_lctx_sensitivity.csv",
            "results/Q3/reports/q3_final_result_analysis.md",
        ],
        "ai_note": "选项由 AI 构造，使用者索取并采纳 AI 建议；建议不写入 rationale。",
    },
]


def append(q: str, records: list[dict]) -> None:
    p = ROOT / f"methods/{q}/{q.lower()}_decisions.jsonl"
    existing = set()
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing.add(json.loads(line).get("decision_id"))
    added = 0
    with p.open("a", encoding="utf-8", newline="\n") as f:
        for r in records:
            if r["decision_id"] in existing:
                print(f"  skip (exists): {r['decision_id']}")
                continue
            rec = {
                "schema_version": 1,
                "status": "DECIDED",
                "decided_by": "human",
                "captured_in_mode": "learning",
                "rationale_provenance": "verbatim_user_reply",
                "option_content_authored_by": "ai",
                "user_action": "reviewed_and_adopted_ai_recommendation",
                "decided_at": TS,
                "user_reply_full": FULL,
                **r,
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            added += 1
    print(f"{q}: appended {added}, now {len(existing) + added} records")


def main() -> None:
    append("Q2", Q2)
    append("Q3", Q3)


if __name__ == "__main__":
    main()

"""把 Q4 框定裁定(1A / 2丙 / 3c+自定预测判据+g)追加到 planning/framing_decisions.jsonl。

幂等:按 decision_id 去重,已存在则跳过。
rationale 只录使用者原话全文,不补写、不强化、不重解释。
选项内容由 AI 在 planning/choice_cards/q4_framing_card.md 中构造并在对话中给出倾向,
使用者审阅后采纳 ⇒ 记 option_content_authored_by=ai + user_action=reviewed_and_adopted_ai_recommendation。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEDGER = ROOT / "planning" / "framing_decisions.jsonl"

# 使用者原话全文(三条共用)
VERBATIM = (
    "我们决定了，就按这样来：:1A、2丙、3(c) + 自定的预测判据 + (g)，"
    "全力冲击一等奖。记录我的决策后，继续推进吧，争取两小时内完成Q4！"
)

DECIDED_AT = "2026-09-25T18:20:00+08:00"

COMMON = {
    "schema_version": 1,
    "decision_type": "framing",
    "status": "DECIDED",
    "decided_by": "human",
    "captured_in_mode": "learning",
    "rationale": VERBATIM,
    "rationale_provenance": "verbatim_user_reply",
    "option_content_authored_by": "ai",
    "user_action": "reviewed_and_adopted_ai_recommendation",
    "decided_at": DECIDED_AT,
    "supersedes": None,
}

CARD = "planning/choice_cards/q4_framing_card.md"

RECORDS = [
    {
        **COMMON,
        "decision_id": "q4_primary_defense_target",
        "choice": "A",
        "choice_label": "偏归因为主辩护对象（占比 X%/Y% 为主 claim）",
        "rejected_alternatives": [
            "B 偏预测（前沿值 + 区间为主 claim）",
            "C 双主（归因与预测同等严谨）",
        ],
        "binding_commitments": {
            "main_claim": "规模扩张与非规模技术/数据工程综合进步各自的贡献占比",
            "secondary_deliverable": "12/24 个月前沿预测仍为题目硬性交付，照常完成并出扇形图，但不作主 claim；宽区间可接受",
            "wording_red_line": "时间项须表述为「非规模技术/数据工程综合进步」，不得写成架构/算法进步，不过度因果化",
            "disclosure_required": [
                "C1 为投榜样本而非模型总体，tau 含「社区针对该 benchmark 调优」成分，含榜单过拟合风险",
                "每月 top10% 中位规模出现 14.77 连续 6 个月相同、8.03 反复出现的模态伪影，方向可信但数值须带此限制",
            ],
        },
        "ai_note": (
            "选项内容由 AI 构造；AI 应使用者主动索取给出了倾向(1A)，使用者审阅后采纳。"
            "AI 倾向的四条理由中最硬的一条是 HD-2 baseline 制下的可赢性："
            "主 claim 若为预测，baseline(纯时间趋势外推)在实测近线性的 q90 轨迹上很可能打赢主方法，"
            "触发 HD-2『如实承认 baseline 更优』条款；主 claim 若为归因，baseline 不产出归因，比较赢得干净。"
            "该理由为 AI 意见，不构成使用者的 rationale。"
        ),
        "evidence_refs": [
            CARD,
            "planning/HANDOFF.md#6",
            "planning/manifests/Q4.json",
        ],
        "evidence_pending_formalization": (
            "支持本条的档内 tau 诊断(4-10B: spearman(t,avg)=+0.3125, q90 +12.29; "
            "10-30B: +0.4827, q90 +19.61; spearman(t,logN)=-0.0615; "
            "spearman(Average,logN)=+0.6352; top10% 中位规模 68.98B->14.77B 同期中位得分 30.51->42.19) "
            "本轮为只读诊断、未落盘，须在 G2 风险探针中正式重跑并写入 "
            "methods/Q4/probes/risk_probe_summary.json 方成为工件证据。"
        ),
    },
    {
        **COMMON,
        "decision_id": "q4_scale_channel_definition",
        "choice": "丙",
        "choice_label": "甲(仅 N，全样本)为主 + 乙(N,D,compute 于 C1xC4 子集)作偏误验证",
        "rejected_alternatives": [
            "甲 仅参数量 N（4573 行，但 D/compute 增长会被系统性计入技术进步项）",
            "乙 仅 (N,D,compute) 连接子集（66 个模型，chat 组仅 3 个，违反 pretrained/chat 分组硬性要求）",
        ],
        "binding_commitments": {
            "headline_sample": "C1 全样本（#Params(B) 非空 4573），支持题目硬性的 pretrained/chat 分组对比",
            "bias_probe_sample": "C1xC4 名称连接后去重 66 个唯一模型（其中 D 非空 46）",
            "bias_quantity": "档内能力涨幅中可被 compute/D 增长解释的部分；甲与乙之差即偏误估计",
            "extrapolation_prohibition": (
                "66 个模型中 pretrained 占 84.8%，而 C1 全样本 pretrained 仅占 6.0% —— 不是同一总体。"
                "乙只给偏误的符号与量级，不得作为对全样本数字的修正系数，不得表述为『已校正』。"
            ),
            "known_bias_direction": "甲单独使用时对『技术进步』占比为系统性高估",
        },
        "ai_note": (
            "选项内容由 AI 构造并给出倾向(2丙)，使用者审阅后采纳。"
            "C1xC4 连接数 66 是 AI 在本轮修正后的值：首次归一化漏剥 org 前缀"
            "(C1 为 01-ai/Yi-1.5-34B，C4 为 Yi 1.5 34B)，误算为 1 行匹配。"
            "『C1 与 C4 无法连接』的说法已作废，不得沿用。"
        ),
        "evidence_refs": [
            CARD,
            "workspace/data/data_report.md#F12",
        ],
        "evidence_pending_formalization": (
            "连接统计(C1 命中 C4 108 行 / 命中三项齐全子集 74 行 / 去重 66 个唯一模型 / 含 D 者 46 / "
            "log10(compute) 20.46-24.90 / 类型构成 pretrained 56、fine-tuned 6、chat 3、multimodal 1) "
            "本轮为只读诊断、未落盘，须在 G2 风险探针中正式重跑。"
        ),
    },
    {
        **COMMON,
        "decision_id": "q4_acceptance_criteria_and_budget",
        "choice": "c + custom_prediction_criterion + g",
        "choice_label": "归因侧(c)；预测侧采用 AI 提出的自定判据；C8 预算(g)全量",
        "rejected_alternatives": [
            "归因侧(a) 占比区间跨越 50% 即视为失败 —— 会惩罚正确性：若真相接近 50/50，诚实报出区间的模型被自己的判据判死",
            "归因侧(b) 仅要求符号正确且和为 1 —— 和为 1 由 Shapley 构造强加，自动成立，测不到东西",
            "预测侧(d) 95% 区间宽度超过前沿当前值 ±20% 即视为无信息 —— ±20% 对应 41.4 的 ±8.3 点，三源不确定性叠加后很可能超过，等于预先承诺把硬性交付物判成无信息",
            "预测侧(e) 不设宽度上限、宽就如实报 —— 不含阈值，不构成判据",
            "C8 预算(h) 分层抽样 / (i) 先全量超时再退抽样",
        ],
        "binding_commitments": {
            "attribution_criterion": "允许占比不确定，但必须报出区间（判据测的是能否量化自身不确定性）",
            "prediction_criterion_main": (
                "中性情景下 12 个月的 80% 区间下界高于当前前沿值，即『进步会继续』这一断言可被主张"
            ),
            "prediction_criterion_reporting_only": (
                "95% 区间宽度如实报告，但不作通过/不通过的闸门"
            ),
            "prediction_criterion_rationale_note": (
                "该判据测的是：在算力放缓情景下能否区分『进步继续』与『进步停滞』。"
                "按实测 q90 约 +1.7/月 的斜率，该断言够得着。"
            ),
            "judged_horizon": "12 个月（判据按 12 个月的 80% 区间构造，故 12 个月为被判定的视界）",
            "c8_budget": "全量 1860 个可解析目录逐任务聚合，不抽样（抽样省不下有意义时间，却需额外论证抽样口径）",
            "no_post_hoc_loosening": (
                "本判据为预声明判据。沿用 Q1 R6/R7 与 Q3 的纪律：不得事后放宽，"
                "未达成即如实记为未达成。"
            ),
        },
        "ai_note": (
            "归因侧(c)为卡上既有选项；预测侧判据由 AI 在对话中新构造(卡上(f)其他项)，使用者采纳；"
            "(g)为卡上既有选项。AI 对 C8 全量耗时的『分钟级』判断是按 1958 文件/229MB、均值约 117KB 的估算，"
            "非实测，已在对话中如实标注。"
        ),
        "evidence_refs": [
            CARD,
            "workspace/data/data_report.md#F14",
        ],
        "carried_forward_open_items": [
            "24 个月视界是否一并报告（题目原文为『12 个月或 24 个月』，只报 12 个月即合规）"
            "未经使用者裁定。AI 曾建议作显式标注的外推(2.6 倍)，使用者未就此表态，"
            "故登记为待办而非已决；默认不作主报，正式报告前须确认。",
            "饱和形态（得分 0-100 上界）在 9.1 个月窗口内不可检验，若报 24 个月须显式声明该假设不可验证。",
        ],
    },
]


def main() -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    existing_ids = set()
    if LEDGER.exists():
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                existing_ids.add(json.loads(line)["decision_id"])

    appended = []
    with LEDGER.open("a", encoding="utf-8", newline="\n") as fh:
        for rec in RECORDS:
            if rec["decision_id"] in existing_ids:
                print(f"SKIP (exists): {rec['decision_id']}")
                continue
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            appended.append(rec["decision_id"])

    print(f"appended {len(appended)}: {appended}")

    # 落盘核验:逐行 json.load,不信写入回执
    lines = [l for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    ids = [json.loads(l)["decision_id"] for l in lines]
    print(f"ledger now has {len(lines)} records, all parse OK")
    for i in ids:
        print("  -", i)


if __name__ == "__main__":
    main()

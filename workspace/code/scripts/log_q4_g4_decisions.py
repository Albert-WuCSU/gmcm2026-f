"""把 Q4 的五条裁定写入 methods/Q4/q4_decisions.jsonl。

使用者原话(五条共用):
「经过讨论，我们决定先按照上面你的5个裁定和建议来推进，你现在先记录我的决策，
然后看看要不要及时更新一下交接文档换窗口跑，还是直接本窗口继续？」

五条的选项内容与建议全部由 AI 构造，使用者主动索取后采纳 ⇒
  option_content_authored_by=ai + user_action=reviewed_and_adopted_ai_recommendation

注意:q4_result_verdict 依赖的趋势法数字尚未落盘，标为 evidence_pending_persistence，
由补跑兑现后方可进入论文。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEDGER = ROOT / "methods" / "Q4" / "q4_decisions.jsonl"
M1A = ROOT / "results" / "Q4" / "experiments" / "round1" / "metrics" / "q4_M1a.json"

d = json.loads(M1A.read_text(encoding="utf-8"))
ms = d["attribution"]["main_spec_decile_month"]
yi = d["yi_bias_probe"]
fr = d["frontier"]
grp = d["attribution"]["by_type_group"]

VERBATIM = (
    "经过讨论，我们决定先按照上面你的5个裁定和建议来推进，你现在先记录我的决策，"
    "然后看看要不要及时更新一下交接文档换窗口跑，还是直接本窗口继续？"
)
AT = "2026-09-25T18:30:00+08:00"

COMMON = {
    "schema_version": 1,
    "status": "DECIDED",
    "decided_by": "human",
    "captured_in_mode": "learning",
    "rationale": VERBATIM,
    "rationale_provenance": "verbatim_user_reply",
    "option_content_authored_by": "ai",
    "user_action": "reviewed_and_adopted_ai_recommendation",
    "decided_at": AT,
}

ON_DISK = [
    "results/Q4/experiments/round1/metrics/q4_M1a.json",
    "results/Q4/experiments/round1/metrics/q4_M0a.json",
    "code/Q4/reviews/q4_python_review.json",
    "methods/Q4/probes/risk_probe_summary.json",
]

PENDING = (
    "端点敏感性与趋势法的数字(末2月合并 scale_share=+0.1811、末3月合并 -0.0282、"
    "去末月 +0.2205、趋势法 +0.0911 CI95 [-0.1942,+0.2258] B=1000、"
    "logN 中位月斜率 -0.00209、0.9 分位月斜率 -0.06281、"
    "slope_f=+0.0575 vs slope_tau=+0.574、情景极差随 scale_share 缩放 11.79->约4.14->0)"
    "本轮仅在 console 计算，尚未落盘。补跑写入 round2 metrics 后方可引用于论文。"
)

RECORDS = [
    {
        **COMMON,
        "decision_id": "q4_scale_channel_bias_direction_correction",
        "decision_type": "canonical_correction",
        "choice": "withdraw_empirical_keep_mechanism",
        "choice_label": "撤回实证方向断言，保留机制断言并改写为随样本而定",
        "supersedes": "q4_scale_channel_definition.binding_commitments.known_bias_direction",
        "supersede_scope": "仅替换该一个字段；原框定记录其余部分继续有效，账本 append-only 不删原记录",
        "was": "甲单独使用时对『技术进步』占比为系统性高估",
        "now": (
            "省略 compute 会在规模通道与技术通道之间重分配解释力，"
            "净效应的方向随样本而定，不是固定的高估。"
            f"在 66 子集上重分配量为 {abs(yi['tech_points_diff_jia_minus_yi'])} 点"
            f"(tech {yi['tech_points_diff_jia_minus_yi']:+.4f} / scale "
            f"{yi['scale_points_diff_jia_minus_yi']:+.4f}，精确抵消)。"
        ),
        "why_empirical_part_withdrawn": (
            "66 子集末期 2025Q1 仅 3 个模型、中位 logN 掉到 0.180(前三期 0.88-1.09)、"
            "S_mean 掉到 7.765 ⇒ total 为负是端点抽样假象，该子集判不了偏误方向。"
        ),
        "evidence_refs": ON_DISK,
        "evidence_pending_persistence": "66 子集季度构成表(n/S_mean/S_q90/logN_med/logC_med)未落盘",
    },
    {
        **COMMON,
        "decision_id": "q4_result_verdict",
        "decision_type": "result_verdict",
        "choice": "accept_round1_with_claim_reframed_plus_supplementary_run",
        "choice_label": "接受 round1 为最终轮，但主 claim 换成稳健版，并补跑一次把趋势法数字落盘",
        "rejected_alternatives": [
            "接受 round1 并沿用 26%/74% 作主 claim —— 该点值随末端定义摆动，趋势法区间含 0",
            "推翻 round1 重跑 —— total_points 在所有算法下稳定 5.4865-6.6592，模型本身无需重做",
        ],
        "binding_commitments": {
            "hard_result": (
                f"窗口 {ms['first_period']}->{ms['last_period']} 能力提升约 5.4865-6.6592 个点"
                "(四种端点/粒度算法下的极差)，该量稳健"
            ),
            "claim_replaced": "不再以 26%/74% 作主 claim",
            "new_main_claim": "非规模技术/数据工程综合进步主导；规模通道贡献与 0 不可区分",
            "supplementary_run_required": (
                "补跑一轮把趋势法与端点敏感性写入 metrics/tables，论文只能引落盘值"
            ),
            "m2a_status": f"未触发(主口径 scale_share CI 下界 {ms['scale_share_ci95'][0]} >= 0)",
        },
        "evidence_refs": ON_DISK,
        "evidence_pending_persistence": PENDING,
    },
    {
        **COMMON,
        "decision_id": "q4_stability_verdict",
        "decision_type": "stability_verdict",
        "choice": "keep_all_at_face_value_plus_new_endpoint_sensitivity",
        "choice_label": "三项各保留其性质不软化，并新增端点敏感性一项",
        "binding_commitments": {
            "P6_spec_sensitivity": (
                "CONDITIONAL 照原样保留：技术份额极差 "
                f"{fr and d['attribution']['sensitivity_specs'] and 0.7565} "
                "= 自助区间宽 0.3796 的 1.99 倍(阈 0.50)"
            ),
            "new_endpoint_sensitivity": (
                "自助区间只重抽模型、不重抽端点选择，故未覆盖末端定义造成的摆幅。"
                "该项须作为独立的稳健性条目记录。"
            ),
            "no_post_hoc_loosening": (
                "沿用 Q1 R6/R7 与 Q3 的纪律：不为本轮新发现的脆弱性事后新立宽判据。"
                "预声明判据文字一律不改。"
            ),
            "f_q4_3_disclosure": (
                "预测判据由 FAIL 翻 PASS 系 AI 修对象不一致缺陷所致(把均值层面 tau 斜率 "
                f"{fr['tau_slope_mean_level_for_reference']} 加到 q90 水平 "
                f"{fr['frontier_slope_per_month']} 上)，且缺陷是在看到 FAIL 之后才发现的。"
                f"发现次序须披露；PASS 裕度仅 "
                f"{round(fr['user_criterion']['lo80'] - fr['current_frontier'], 3)} 点。"
            ),
        },
        "evidence_refs": ON_DISK,
        "evidence_pending_persistence": PENDING,
    },
    {
        **COMMON,
        "decision_id": "q4_claim_scope",
        "decision_type": "claim_scope",
        "choice": "robust_direction_only_no_percentage_split",
        "choice_label": "只主张方向与量级，不主张任何百分比分割",
        "binding_commitments": {
            "population": "Open LLM Leaderboard 投榜模型(非模型总体)",
            "window": f"{ms['first_period']} -> {ms['last_period']}",
            "claimable": [
                "窗口内能力提升约 5.4865-6.6592 个点",
                "非规模技术/数据工程综合进步主导",
                "规模通道的贡献与 0 不可区分",
                "同期 N 的 0.9 分位下降约 3.7 倍(logN 0.9 分位月斜率 -0.06281，十个月累计 -0.565 dex)",
                "算力增长放缓对开源前沿的短期预测影响很小，因前沿推进本就不靠规模扩张",
            ],
            "not_claimable": [
                "任何具体百分比分割，含 26%/74%",
                f"pretrained 组的占比(该组 total_points={grp['pretrained']['total_points']:.4f} 为负)",
                f"chat_finetuned 组规模贡献显著为正(CI95 {grp['chat_finetuned']['scale_share_ci95']} 含 0)",
                "把 66 子集结论推广到全样本(该子集 pretrained 占比远高于全样本)",
                "tau 是架构/算法进步(它吸收未观测的数据质量变化与榜单过拟合)",
            ],
        },
        "evidence_refs": ON_DISK,
        "evidence_pending_persistence": PENDING,
    },
    {
        **COMMON,
        "decision_id": "q4_horizon_scope",
        "decision_type": "claim_scope",
        "choice": "h12_main_h24_not_main",
        "choice_label": "12 个月作主报，24 个月不作主报",
        "binding_commitments": {
            "judged_horizon": "12 个月",
            "h24_status": "不作主报；若列出须显式声明饱和形态不可检验",
            "reason_truncation_artifact": (
                f"optimistic h24 中位 {fr['scenarios']['optimistic']['h24']['median']} 逼近 0-100 上界，"
                f"其 95% 宽度 {fr['scenarios']['optimistic']['h24']['width95']} 反而窄于 h12 的 "
                f"{fr['scenarios']['optimistic']['h12']['width95']} —— 这是截断到 100 造成的假象，"
                "不是精度提高"
            ),
            "saturation_untestable": "得分 0-100 上界的饱和形态在 9.1 个月窗口内不可检验",
            "compliance": "题目原文为『12 个月或 24 个月』，只报 12 个月即合规",
        },
        "evidence_refs": ON_DISK,
    },
]


def main() -> None:
    existing = set()
    if LEDGER.exists():
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing.add(json.loads(line)["decision_id"])
    appended = []
    with LEDGER.open("a", encoding="utf-8", newline="\n") as fh:
        for r in RECORDS:
            if r["decision_id"] in existing:
                print("SKIP", r["decision_id"])
                continue
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            appended.append(r["decision_id"])
    print("appended", len(appended), appended)
    lines = [l for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    print("ledger records =", len(lines))
    for l in lines:
        print("  -", json.loads(l)["decision_id"])


if __name__ == "__main__":
    main()

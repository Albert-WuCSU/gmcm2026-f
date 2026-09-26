"""把 Q3 的三条人工裁定写入 methods/Q3/q3_decisions.jsonl。

rationale 只录使用者原话全文,不补写、不强化、不把 AI 论证并入。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "methods/Q3/q3_decisions.jsonl"

VERBATIM = "1.B+C，B为主，C为辅；2.A做主，D一并报告，加以对比辅证；3.C，记录我的决策后，继续往前推进吧，加快进度"
AT = "2026-09-25T16:40:00+08:00"

EVIDENCE = [
    "methods/Q3/q3_method_card.md",
    "methods/Q3/probes/risk_probe_summary.json",
    "planning/choice_cards/q3_method_card.md",
    "workspace/data/q3_probe_optimization.json",
]

AI_NOTE = (
    "选项内容与其量化后果由 AI 依据已落盘探针证据在决策卡中构造;使用者主动索取 AI 技术意见,"
    "AI 给出的倾向(1=B主+C辅、2=A主+D并报、3=C)已明确标注为 AI 意见。使用者本轮的三条裁定与该倾向一致,"
    "故按 option_content_authored_by=ai + user_action=reviewed_and_adopted_ai_recommendation 记录。"
    "rationale 为使用者原话照录,AI 未补写、未强化、未把 AI 论证并入 rationale。"
    "同轮 AI 主动更正三处自述:① 上一轮称裁定2选D『对阈值敏感』说轻了,实为对扫描步长敏感且结论会翻转"
    "(step=0.5 判 TRANSITION_EXISTS、0.25 与 0.125 判 NO_TRANSITION);"
    "② 选择卡与方法卡称饱和点处导数『由负转零』,实测为由正转零(+0.1500 → 0),符号写错;"
    "③ 选择卡与探针摘要称 Chinchilla 比例『可迁移性未检验』,实为已检验且本律 B1 侧参数与 Chinchilla "
    "Approach-3 常数按十亿单位折算后数值同一(五参数相对差 9.4e-6 ~ 4.4e-4)。"
    "GC9:论文中的建模论证须由本队自行撰写,不得直接复制 AI 生成的方案表述。"
)

AI_SUPPORT = {
    "script": "scratch/q3_opinion_support.py",
    "status": "AI 意见支撑算例,非交付物,不进论文、不作判据",
    "目标函数与成本式": "逐行照抄 workspace/code/scripts/probe_q3_optimization.py,仅改扫描步长",
}

DECISIONS = [
    {
        "decision_id": "q3_p_joint_optimization",
        "decision_type": "method_choice",
        "scope": "AMB-Q3-1 + 题目授权项:领域配比 p 是否作为联立决策变量(题目原文『可作联立决策变量,也可由前两问结果确定,但须说明理由』)",
        "choice": "B_main_plus_C_supplement",
        "choice_label": "B 为主:由 Q1/Q2 结果固定 p(z_p=0),只优化 (N,D,Q);C 为辅:另报 dL/dp_i 的符号与排序作补充分析",
        "chosen_spec": {
            "main_line_B": "p 取 Q1 基准配比,z_p = 0 ⇒ exp(b^T z_p) = 1。决策变量为 (N, D, Q),KKT 维度 3",
            "supplement_C": "另报 dL/dp_i 的符号与域间排序(与 kappa 无关,Q2 q2_kappa_treatment 已证),不报最优配比点 p*",
            "why_not_A": "P3 实测角点退化:b^T z_p 对 p 线性 ⇒ 单纯形上线性目标 ⇒ 最优必在顶点(最大分量 1.0000,全给 dm_mathematics)。A 需引入信赖域半径 r 或正则强度,数据无法定标,且与 Q2 已声明不可辨识的 kappa 纠缠",
            "reason_for_fixing_p_to_report": "P3 的角点退化实测即为题目要求的『理由』:联立优化在本模型下给出只训练单一域的不合理解,故 p 由前两问确定。该理由须由本队自撰(GC9)",
            "p_star_is_not_an_output": True,
        },
        "evidence_digest": {
            "P3_verdict": "CORNER_DEGENERATE",
            "P3_max_component": 0.9999999999999927,
            "P3_argmax_domain": "dm_mathematics",
            "P3_objective_is_linear_in_p": True,
            "kappa_identifiable_from_B": False,
        },
    },
    {
        "decision_id": "q3_structural_transition_definition",
        "decision_type": "method_choice",
        "scope": "题目 success_criteria 第 2 条:结构性转移的数学定义与识别方法(P4 给出四个候选)",
        "choice": "A_main_plus_D_reported_as_contrast",
        "choice_label": "A 为主定义:活跃约束集变化(Q≤1 由非活跃转活跃);D 一并报告作对比辅证",
        "chosen_spec": {
            "main_definition_A": "结构性转移 := KKT 活跃约束集发生变化。本问中为 Q ≤ 1 由非活跃转为活跃",
            "identification_method_A": "沿 log10 C 扫描,检测 Q* 触及上界 1 的位置与互补松弛乘子由 0 转正的位置;为离散事件,不依赖阈值与步长",
            "measured_location_A": "log10 C = 21.5",
            "contrast_D": "同时报『分配份额突变(一阶差分超阈)』定义下的结果:本数据下判不出转移(step=0.25 时 max|dQ*| = 0.0420 < 0.05)",
            "why_report_both": "A 测『约束集是否改变』、D 测『是否有突跳』,两者答案相反,合起来说清转移的形态为连续饱和而非突跳。只报 A 会使读者误以为 21.5 处有跳变",
            "D_is_not_a_main_definition_because": "D 的结论是扫描步长的函数。实测同一目标函数下仅改步长:step=0.5 判 TRANSITION_EXISTS(max|dQ*|=0.0814,7 处超阈)、step=0.25 判 NO_TRANSITION(0.0420)、step=0.125 判 NO_TRANSITION(0.0215)。因饱和前 Q* 光滑上升(斜率稳定 +0.149),一阶差分 ≈ 斜率 × 步长,与固定阈值比较不是网格不变量",
            "why_not_B": "B(最优解路径不可微点)与 A 是同一事件的两种写法,但需数值微分 ⇒ 重新引入步长依赖。A 可无步长判定同一事件",
            "C_position_differs_from_A": "C(成本分项占比排序变化)实测发生在 log10 C = 22.75(C_train|C_Q|C_attn → C_train|C_attn|C_Q),与 A 的 21.5 不同。三定义三答案(A 21.5 / C 22.75 / D 不存在)可作『定义决定结论』的实证",
            "card_sign_error_to_fix": "选择卡与方法卡称饱和点处导数『由负转零』,实测为由正转零(饱和前 dQ*/dlogC = +0.1483 → +0.1500,饱和后 = 0)。该符号错误不得写入论文",
        },
        "evidence_digest": {
            "P4_verdict": "TRANSITION_EXISTS",
            "P4_share_order_changes": [[22.75, "C_train|C_Q|C_attn", "C_train|C_attn|C_Q"]],
            "P4_Q_saturation_log10_C": 21.5,
            "P4_max_abs_dQ_at_step_0.25": 0.04204174271919203,
            "P4_sweep_step": 0.25,
            "ai_support_grid_sensitivity": {
                "step_0.5": {"max_abs_dQ": 0.081404, "n_jumps": 7, "verdict": "TRANSITION_EXISTS"},
                "step_0.25": {"max_abs_dQ": 0.042042, "n_jumps": 0, "verdict": "NO_TRANSITION"},
                "step_0.125": {"max_abs_dQ": 0.021474, "n_jumps": 0, "verdict": "NO_TRANSITION"},
                "range_log10_C": [18.0, 22.0],
            },
            "ai_support_derivative_sign_at_saturation": {
                "before": 0.149961, "at": 0.036286, "after": 0.0,
            },
        },
    },
    {
        "decision_id": "q3_optimum_acceptability_criterion",
        "decision_type": "method_choice",
        "scope": "最优解的可接受性判据:是否要求满足 KKT、是否要求与 Chinchilla 经验比例对照",
        "choice": "C",
        "choice_label": "两者都要:KKT 为硬判据(通过条件),Chinchilla 对照仅作参考而非通过条件",
        "chosen_spec": {
            "hard_criterion": "KKT:互补松弛成立、梯度条件残差 < 预声明阈、分段枚举覆盖 Q=1 边界情形",
            "reference_only": "Chinchilla 对照表照出,但不作 pass/fail 判据",
            "why_chinchilla_must_not_be_a_hard_criterion": "本律隐含的 D/N 不是常数 20,而随预算漂移:1e19 时 32.06、1e22 时 62.64、1e24 时 97.89,漂移指数 (alpha-beta)/(alpha+beta) = 0.0970。20 tokens/param 是 Chinchilla Approach 1/2 的结论(a≈b≈0.5),本律用的是 Approach 3 的 alpha≠beta,两者本不给同一比例。把 20 当硬判据会拒绝本律自身的真最优解",
            "external_anchor_claim_is_void": "选择卡原列 B 的收益『有外部锚点』不成立:实测本律 B1 侧参数与 Chinchilla Approach-3 常数(E=1.69, A=406.4, B=410.7, alpha=0.34, beta=0.28)按 N,D 以十亿为单位折算后数值同一,相对差 A 5.9e-5、B 9.4e-6、alpha 6.9e-5、beta 4.4e-4、E 1.2e-4。以 Chinchilla 对照本律等于自证",
            "chinchilla_constants_source_caveat": "上述 Chinchilla 常数由 AI 凭记忆复现,使用者与队友引用前须翻原文(Hoffmann et al. 2022)核对。五参数同时吻合到 1e-4~1e-5 量级,记错可能性低但未经原文核验",
            "supersedes_card_text": "选择卡与探针摘要中 chinchilla_ratio_transferable_to_this_law 的 NOT_CHECKED 状态应改判为『已检验:本律与 Chinchilla 同律,但其隐含比值随预算漂移』",
        },
        "evidence_digest": {
            "law_alpha": 0.33997658,
            "law_beta": 0.27987806,
            "implied_D_over_N": {"1e19": 32.06, "1e22": 62.64, "1e24": 97.89},
            "drift_exponent": 0.096956,
            "chinchilla_folklore_ratio": 20,
            "chinchilla_param_match_relerr": {
                "A": 5.85e-05, "B": 9.35e-06, "alpha": 6.89e-05, "beta": 4.36e-04, "E": 1.20e-04,
            },
            "chinchilla_constants_verified_against_paper": False,
        },
        "raises_open_item_not_decided_by_user": {
            "item": "M0o baseline 的『Chinchilla 比例』若按字面取 D/N=20,baseline 被不必要削弱",
            "measured_at_C_1e22_L_ctx_2048": {
                "M1o_all_free": {"loss": 2.151061, "N_B": 5.647, "D_B": 249.1, "Q": 1.0, "D_over_N": 44.10},
                "M0o_as_carded_ratio_20": {"loss": 2.245726, "N_B": 8.832, "D_B": 176.6, "Q": 0.35},
                "M0o_fair_ratio_free": {"loss": 2.219543, "N_B": 3.168, "D_B": 492.6, "Q": 0.35, "D_over_N": 155.50},
                "gap_as_carded": 0.094665,
                "gap_attributable_to_quality_channel": 0.068482,
                "ratio_handicap": 0.026183,
                "handicap_share_of_reported_gap_pct": 27.7,
            },
            "consequence": "HD-2 成功判据为相对 baseline 制,该 27.7% 会虚增 M1o 的优势",
            "status": "NOT_IN_SCOPE_OF_THESE_THREE_RULINGS",
            "ai_will_not": "擅自改动 M0o 的定义(属方法卡内容,且 baseline 由 HD-2 声明)",
            "ai_will_do": "在 G3 代码计划中按卡上定义实现 M0o 作为已声明 baseline,同时把 M0o'(同 Q=Q0 但 N:D 自由)作为诊断项一并算出并写入 run_summary,使差距分解可见而不改动已声明 baseline;是否改 M0o 定义留待使用者裁定",
        },
    },
]


def main() -> None:
    lines = []
    for d in DECISIONS:
        rec = {
            "schema_version": 1,
            "decision_id": d["decision_id"],
            "decision_type": d["decision_type"],
            "status": "DECIDED",
            "decided_by": "human",
            "captured_in_mode": "learning",
            "rigor_profile": "lean",
            "scope": d["scope"],
            "choice": d["choice"],
            "choice_label": d["choice_label"],
            "chosen_spec": d["chosen_spec"],
            "rationale": VERBATIM,
            "rationale_is_verbatim_user_text": True,
            "option_content_authored_by": "ai",
            "user_action": "reviewed_and_adopted_ai_recommendation",
            "choice_card": "planning/choice_cards/q3_method_card.md",
            "evidence_refs": EVIDENCE,
            "evidence_digest": d["evidence_digest"],
            "ai_opinion_support": AI_SUPPORT,
            "ai_note": AI_NOTE,
            "decided_at": AT,
            "supersedes": None,
        }
        if "raises_open_item_not_decided_by_user" in d:
            rec["raises_open_item_not_decided_by_user"] = d["raises_open_item_not_decided_by_user"]
        lines.append(json.dumps(rec, ensure_ascii=False))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"WROTE {OUT.relative_to(ROOT)}  ({len(lines)} decisions)")
    for d in DECISIONS:
        print(f"   {d['decision_id']:<42} choice={d['choice']}")


if __name__ == "__main__":
    main()

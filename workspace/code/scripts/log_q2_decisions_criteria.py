"""把使用者对裁定 4/5/6（判据修正与 kappa 处置）的裁定追加写入 q2_decisions.jsonl。

append-only、幂等。rationale 一律为使用者原话照录。

使用者原话：
    「经过我们的讨论，和演算，我们决定采取你本轮的建议，记住我们的决策！
      另外比赛还有8小时，请继续推进，争取这个下午完成Q234！」

provenance（必须如实）：本轮三条的**选项内容由 AI 提出并推荐**，使用者审阅后决定采纳。
与 Q1「1D2A3C，我认同你说的。」同类。ai_note 须明确记录该来源，不得表述为使用者独立提出。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEDGER = ROOT / "methods/Q2/q2_decisions.jsonl"
TS = "2026-09-25T12:10:00+08:00"
VERBATIM = ("经过我们的讨论，和演算，我们决定采取你本轮的建议，记住我们的决策！"
            "另外比赛还有8小时，请继续推进，争取这个下午完成Q234！")

AI_NOTE = ("本条的选项内容、量化依据与推荐均由 AI 提出（见 evidence_refs 的 G3 可辨识性探针）；"
           "使用者审阅后决定采纳，rationale 为使用者原话照录，AI 未补写或强化理由。"
           "AI 在同一轮内主动更正过两处自述过强的表述：① 联合拟合对指标 1 的不利影响量级被说重了"
           "（实为 1e-6 权重级，可忽略）；② 假设(b) 并不能把 kappa 钉成单一值，只能给出参照点上的量级。"
           "GC9：论文中的建模论证须由本队自行撰写，不得直接复制 AI 生成的方案表述。")

EV = [
    "methods/Q2/q2_method_card.md",
    "methods/Q2/probes/risk_probe_summary.json",
    "workspace/data/q2_probe_g3_identifiability.json",
    "workspace/data/q2_probe_scaling.json",
]

RECORDS = [
    {
        "decision_id": "q2_baseline_comparison_venue",
        "decision_type": "method_choice",
        "scope": "预声明指标 1 失效后的修正：M1s 与 M0s 的可比较场地",
        "choice": "split_B1_degeneracy_plus_B7_superiority",
        "choice_label": "B1 改判退化检验；超越性比较移到 B7；按 GC5 披露该证据为半合成",
        "chosen_spec": {
            "B1_role": ("退化检验（预声明、按容差判 pass/fail）：M1s 在 B1 上须复现 M0s。"
                        "实测同构，RMSE 相对差 3.98e-13。该结果同时充当题目要求的"
                        "『Q=1 退化为经典形式』的依据"),
            "B7_role": ("超越性比较（预声明指标）：M1s vs M0s 的 RMSE，显著性用自助区间判定（HD-2）；"
                        "须注明 M1s 多一个参数 gamma"),
            "B4_B5_role": "保留为真实数据上的迁移检验（秩相关；禁止报跨源未去偏 R²）",
            "gc5_disclosure_required": ("Q 通道的超越性证据完全建立在半合成数据上。"
                                        "B 侧仅 B6/B7/B8 含 Q 变化且全部为半合成；"
                                        "严格按题目表述，该超越性结论本身带『补充分析』属性，须如实披露"),
            "why_metric1_was_dead": ("B1 无配比列(P2: 0/11) ⇒ z_p=0 ⇒ exp(b^T z_p)=1；B1 无 Q 变化 ⇒ Q=Q0 常数。"
                                     "M1s 塌为 L=E+A·N^-alpha+(B·Q0^(-beta*gamma))·D^-beta，与 M0s 同形同自由度"),
        },
        "evidence_refs": EV,
        "evidence_digest": {
            "M0s_rmse_on_B1": 0.00014649608992588973,
            "M1s_rmse_on_B1": 0.000146496089925948,
            "rmse_relative_difference": 3.977981036939401e-13,
            "isomorphic_on_B1": True,
            "predeclared_criterion": "RMSE 相对差 < 1e-6 即判同构",
            "B_files_with_Q_variation": ["B6", "B7", "B8"],
            "all_Q_varying_files_are_semisynthetic": True,
            "B7_weight_share_in_joint_fit_residual_sigma": 1.564e-06,
        },
    },
    {
        "decision_id": "q2_fallback_trigger_logic",
        "decision_type": "method_choice",
        "scope": "M2s 触发条件的连接词矛盾（原文『须全部成立』却用『或』连接）",
        "choice": "repair_condition2_then_OR",
        "choice_label": "先由裁定4把条件2移到 B7，条件2恢复可失败性后读『或』",
        "chosen_spec": {
            "resolved_reading": "或（两个独立失效模式，任一发生即激活 M2s）",
            "condition_1": "M1s 的 gamma 在 B1 钉住 beta 后，自助 95% 区间包含 0",
            "condition_2_repaired": "M1s 在 **B7** 上的 RMSE 不优于 M0s（自助区间判显著）",
            "why_OR_was_unsafe_before": "条件2挂在 B1 上时平凡为真，读『或』会使 M2s 立即激活并顶掉裁定2=A",
            "discipline_note_must_enter_paper": (
                "本次判据修正发生在**实验运行之前**，与 Q1 的 R6/R7『不事后放宽』不构成冲突："
                "R6/R7 是看到结果之后的问题，本次代码尚未生成。"
                "且修正方向是**收紧**而非放宽 —— B1 上的判据不可能通过（同构），"
                "B7 上的判据可能通不过（gamma 区间可能含 0）。该区分须原样写入论文，"
                "不得只写『我们把判据挪到了 B7』"),
        },
        "evidence_refs": EV,
        "evidence_digest": {
            "card_original_text_contradiction": "『须全部成立』与『或』并存（q2_method_card.md:86-88）",
            "condition2_on_B1_trivially_true": True,
            "repair_timing": "before_code_generation",
            "repair_direction": "tightening_not_loosening",
        },
    },
    {
        "decision_id": "q2_kappa_treatment",
        "decision_type": "assumption_necessity",
        "scope": "b = kappa*(w - mean(w)) 中尺度因子 kappa 的处置（B 侧严格不可辨识）",
        "choice": "a_main_plus_b_sensitivity",
        "choice_label": "(a) 声明不可辨识、只报比值与方向为主线；(b) 水平迁移假设作已声明的敏感性臂",
        "chosen_spec": {
            "main_line_a": ("声明 kappa 在 B 侧严格不可辨识（实测 RMSE 随 kappa 变化恰为 0.0）；"
                            "只报 b_i/b_j（域间替代比）与方向，二者与 kappa 无关"),
            "sensitivity_arm_b": ("假设『A 侧与 B 侧在指定参照点上 dL/dp_i 相等』"
                                  "⇒ kappa = -1/(beta*G)，G = B*D^-beta。"
                                  "**任何据此报出的绝对量级必须带参照点一起报**"),
            "b_cannot_pin_single_kappa": ("G 随 D 变 ⇒ 1B 参照 run 内 kappa 从 -14.2151 到 -1.6413（差 8.7 倍）。"
                                          "假设(b) 只能给『指定参照点上的量级』，给不出普适 kappa"),
            "reportable_limitation": ("p 与 p 相比是 kappa 无关的；p 与 N/D/Q 相比一定含 kappa。"
                                      "这是『配比的绝对效应不可跨源辨识』的精确表述，须写入局限"),
            "requirement_coverage": ("题目两个显式 p 问项（域间替代/互补、Q↔N 等价）均 kappa 无关、不受影响；"
                                     "『各因素边际效用与弹性（含符号与量级）』的 p 分量需要量级，"
                                     "由敏感性臂(b) 在声明假设下填补"),
        },
        "evidence_refs": EV,
        "evidence_digest": {
            "kappa_sweep_rmse_spread_on_B1": 0.0,
            "kappa_identifiable_from_B": False,
            "predeclared_criterion": "kappa 从 0 扫到 10，B1 预测最大变化 < 1e-12 即判严格不可辨识",
            "kappa_under_assumption_b_range": [-14.2151, -1.6413],
            "kappa_at_convergence_end": -14.2151,
            "implied_b_range": [-21.6265, 35.0093],
            "implied_dL_for_1pp_shift_lowest_to_highest_w": 0.039842,
            "dL_share_of_B1_val_loss_span_pct": 1.506,
            "sign_coherence_check": "高 Loss 域 w_i>wbar ⇒ b_i<0 ⇒ D_eff 变小 ⇒ L 上升，方向正确",
        },
    },
]


def build_line(rec: dict) -> dict:
    return {
        "schema_version": 1,
        "decision_id": rec["decision_id"],
        "decision_type": rec["decision_type"],
        "status": "DECIDED",
        "decided_by": "human",
        "captured_in_mode": "learning",
        "rigor_profile": "lean",
        "scope": rec["scope"],
        "choice": rec["choice"],
        "choice_label": rec["choice_label"],
        "chosen_spec": rec["chosen_spec"],
        "rationale": VERBATIM,
        "rationale_is_verbatim_user_text": True,
        "option_content_authored_by": "ai",
        "user_action": "reviewed_and_adopted_ai_recommendation",
        "evidence_refs": rec["evidence_refs"],
        "evidence_digest": rec["evidence_digest"],
        "ai_note": AI_NOTE,
        "decided_at": TS,
        "supersedes": None,
    }


def main() -> None:
    existing = set()
    if LEDGER.exists():
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing.add(json.loads(line)["decision_id"])

    missing = [r for rec in RECORDS for r in rec["evidence_refs"] if not (ROOT / r).exists()]
    if missing:
        raise SystemExit(f"evidence_refs 缺失，拒绝写入：{sorted(set(missing))}")

    appended = []
    with LEDGER.open("a", encoding="utf-8") as fh:
        for rec in RECORDS:
            if rec["decision_id"] in existing:
                continue
            fh.write(json.dumps(build_line(rec), ensure_ascii=False) + "\n")
            appended.append(rec["decision_id"])

    recs = [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    print("appended:", appended)
    print("ledger_lines:", len(recs))
    for r in recs:
        print(f"  {r['decision_id']:42s} {r['decision_type']:20s} choice={r['choice']}")
    assert len({r["decision_id"] for r in recs}) == len(recs)
    assert all(r["status"] == "DECIDED" and r["decided_by"] == "human" for r in recs)
    for r in recs:
        if r["decision_id"] in {x["decision_id"] for x in RECORDS}:
            assert r["option_content_authored_by"] == "ai"
            assert r["user_action"] == "reviewed_and_adopted_ai_recommendation"
    print("SELF_CHECK_OK")


if __name__ == "__main__":
    main()

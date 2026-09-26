"""把使用者对 Q2 三项方法选择的裁定追加写入 methods/Q2/q2_decisions.jsonl。

append-only、幂等（同 decision_id 已存在则跳过，不覆盖历史）。
rationale 一律为使用者原话照录，AI 不补写、不强化、不把 AI 意见并入。

使用者原始回复（一次性给出三项裁定 + 一条附加约束）：
    「1A,2A,3B，但B1的处理要谨慎。请继续推进吧」

对应决策卡 planning/choice_cards/q2_method_card.md 的三条：
    1 -> A  p 以低维投影 exp(b^T z_p) 进入
    2 -> A  Q 以乘性 D_eff = D·Q^gamma 进入
    3 -> B  半合成以「增大噪声方差」方式参与拟合
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEDGER = ROOT / "methods/Q2/q2_decisions.jsonl"
TS = "2026-09-25T11:05:00+08:00"
VERBATIM = "1A,2A,3B，但B1的处理要谨慎。请继续推进吧"

AI_NOTE = ("选项内容与其量化后果由 AI 在决策卡中构造并展示；使用者另主动索取过 AI 技术意见，"
           "AI 给出的推荐（1A/2A/3B）已明确标注为 AI 意见且不写入本账本。"
           "本条 rationale 为使用者原话照录，AI 未补写、未强化、未把 AI 论证并入 rationale。"
           "注意 GC9：论文中的建模论证须由本队自行撰写，不得直接复制 AI 生成的方案表述。")

# 使用者在三条裁定之外附加的一句约束。AI 不得代为解释其操作口径。
B1_CONSTRAINT = {
    "verbatim": "但B1的处理要谨慎",
    "status": "RECORDED_NOT_INTERPRETED",
    "operational_scope_specified_by_user": False,
    "ai_must_not": "把该句解释为某个具体的 B1 处置方案，或据此自行放宽/收紧任何判据",
    "ai_will_do": ("只执行机械可判的核查：B1 的 provenance 与列结构、"
                   "R²=0.9999998 / RMSE=1.465e-4 是否意味着 B1 非原始观测、"
                   "以及 sigma_real 是否被该残差低估；核查结果回报使用者，不自行裁定处置方式"),
    "ai_origin_disclosure": ("B1 拟合过于干净这一观察由 AI 在给出技术意见时提出，"
                             "使用者据此附加了本句约束；观察本身是 AI 意见，约束本身是使用者原话"),
}

COMMON_EVIDENCE = [
    "methods/Q2/q2_method_card.md",
    "methods/Q2/probes/risk_probe_summary.json",
    "planning/choice_cards/q2_method_card.md",
]

RECORDS = [
    {
        "decision_id": "q2_p_entry_form",
        "decision_type": "method_choice",
        "scope": "AMB-Q2-1：17 维配比 p 如何进入广义标度律",
        "choice": "A",
        "choice_label": "低维投影 exp(b^T z_p)，z_p 为配比相对基准的中心化偏移",
        "chosen_spec": {
            "form": "L = E_s + A·N^-alpha + B·(D·Q^gamma·exp(b^T z_p))^-beta",
            "p_enters_via": "exp(b^T z_p) 乘入有效数据量 D_eff",
            "degeneracy": "z_p = 0 且 Q = 1 时退化为经典式 L = E + A·N^-alpha + B·D^-beta",
            "b_dimension": 17,
            "load_bearing_assumption": ("跨源统一假设（AMB-Q2-2）：p 的效应形状可跨尺度/跨来源迁移。"
                                        "b 在 B 侧无法验证（11 个 B 文件零配比列），须显式声明并检验"),
        },
        "evidence_refs": COMMON_EVIDENCE + [
            "workspace/data/q2_probe_scaling.json",
            "results/Q1/experiments/round1/tables/q1c_q_increment_test.csv",
            "results/Q1/experiments/round1/tables/q1c_coefficients.csv",
        ],
        "evidence_digest": {
            "P2_verdict": "FAIL",
            "B_files_with_mixture_columns": 0,
            "B_files_checked": 11,
            "A_scale_inside_B1_range": {"1m": False, "60m": False, "1B": True},
            "q1_Q_corpus_increment_all_ci_contain_zero": True,
            "q1_Q_corpus_increments": [0.00028, -0.00022, -0.00082],
            "q1_Q_corpus_built_from_mapped_domains": "6/17",
            "q1c_M0c_main_effect_coefs_available": 17,
            "q1c_M0c_sign_stability_all": 1.0,
        },
    },
    {
        "decision_id": "q2_Q_entry_form",
        "decision_type": "method_choice",
        "scope": "P3 不可区分：Q 以乘性有效数据量还是加性独立项进入",
        "choice": "A",
        "choice_label": "乘性 D_eff = D·Q^gamma",
        "chosen_spec": {
            "form": "Q 经 D_eff = D·Q^gamma 进入，与 p 的 exp(b^T z_p) 同乘于 D",
            "estimation_order": ("beta 必须先由 B1 真实数据钉住（B1 无 Q 变化，Q 视为常数），"
                                 "再由 Q 指数 -beta*gamma 反解 gamma；不得在含 Q 数据上同时自由估 beta 与 gamma"),
            "prohibited_claim": ("不得在采用该形式的同时声称「Q 与 D 的替代率随位置变化」——"
                                 "P4 实测该弹性比恒为 gamma（ptp < 1e-12，值 2.0000）。仅 Q↔N 随位置变化"),
            "role_assignment": "M1s 维持 main；M2s（加性独立项）维持 conditional_fallback，触发条件不变",
        },
        "evidence_refs": COMMON_EVIDENCE + ["workspace/data/q2_probe_scaling.json"],
        "evidence_digest": {
            "P3_verdict": "CONDITIONAL",
            "P3_distinguishable_on_B6": False,
            "P3_rmse_additive": 0.06990692443086688,
            "P3_rmse_multiplicative": 0.0724711308038097,
            "P3_rmse_relative_difference": 0.03538245290920752,
            "P3_better_fit_raw": "additive",
            "P4_elasticity_ratio_Q_over_D": 2.0,
            "P4_ratio_constant": True,
            "P4_beta_gamma_separately_identifiable": True,
            "B1_beta_support": {"n": 1176, "rmse": 0.000146496089925887, "r2": 0.9999998165821044},
        },
    },
    {
        "decision_id": "q2_semisynthetic_fit_participation",
        "decision_type": "method_choice",
        "scope": "题目 success_criteria 第 3 条 + GC5：半合成数据参与拟合的程度上限",
        "choice": "B",
        "choice_label": "增大噪声方差参与（加权最小二乘中给更大 sigma）",
        "chosen_spec": {
            "mechanism": "异方差加权最小二乘，半合成来源取更大 sigma_s，不确定性自动变宽",
            "pairs_with": "P1 已确立的来源专属截距 E_s（同一来源分层结构）",
            "gamma_ci_use": "gamma 的自助 95% 区间用于判定 M2s 的触发条件之一",
            "gc5_disclosure_required": ("无论参与程度如何，B6-B8 均须按 GC5 披露为半合成；"
                                        "calibrated 半数 val_loss 下界为 0.5，低于自然语言熵常见量级"),
        },
        "evidence_refs": COMMON_EVIDENCE + ["workspace/data/q2_probe_scaling.json"],
        "evidence_digest": {
            "P5_verdict": "PASS",
            "P5_criterion_self_audit": "判据（bias 占 RMSE < 50%）太松：实测 3.2% 记 PASS，但预测 RMSE 0.6293",
            "P5_extrapolated_pred_rmse": 0.6293200406951934,
            "P5_bias_share_of_rmse": 0.03202227107797604,
            "P5_val_loss_range_calibrated": [0.5, 3.3659],
            "P5_val_loss_range_extrapolated": [0.5, 2.6033],
            "P6_B6_subset_of_B7": True,
            "P6_n_shared": 360,
            "B1_has_no_Q_variation_so_gamma_needs_B6_B8": True,
        },
    },
]


def build_line(rec: dict) -> dict:
    """补齐契约必填字段。rationale 一律为使用者原话，不做任何加工。"""
    out = {
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
        "choice_card": "planning/choice_cards/q2_method_card.md",
        "evidence_refs": rec["evidence_refs"],
        "evidence_digest": rec["evidence_digest"],
        "user_additional_constraint": B1_CONSTRAINT,
        "ai_note": AI_NOTE,
        "decided_at": TS,
        "supersedes": None,
    }
    return out


def main() -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)

    existing: dict[str, int] = {}
    if LEDGER.exists():
        for i, line in enumerate(LEDGER.read_text(encoding="utf-8").splitlines()):
            line = line.strip()
            if not line:
                continue
            existing[json.loads(line)["decision_id"]] = i

    # 证据路径必须真实存在（契约要求）
    missing = []
    for rec in RECORDS:
        for ref in rec["evidence_refs"]:
            if not (ROOT / ref).exists():
                missing.append(ref)
    if missing:
        raise SystemExit(f"evidence_refs 缺失，拒绝写入：{sorted(set(missing))}")

    appended, skipped = [], []
    with LEDGER.open("a", encoding="utf-8") as fh:
        for rec in RECORDS:
            if rec["decision_id"] in existing:
                skipped.append(rec["decision_id"])
                continue
            fh.write(json.dumps(build_line(rec), ensure_ascii=False) + "\n")
            appended.append(rec["decision_id"])

    # 自核验：逐行 json.loads，不信写入回执
    lines = [l for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    parsed = [json.loads(l) for l in lines]
    print(f"appended={appended}")
    print(f"skipped(existing)={skipped}")
    print(f"ledger_lines={len(parsed)}")
    for p in parsed:
        print(f"  {p['decision_id']}: choice={p['choice']} status={p['status']} "
              f"by={p['decided_by']} verbatim={p['rationale_is_verbatim_user_text']}")
    assert all(p["rationale"] == VERBATIM for p in parsed), "rationale 必须为原话"
    assert all(p["status"] == "DECIDED" for p in parsed)
    assert len({p["decision_id"] for p in parsed}) == len(parsed), "decision_id 必须唯一"
    print("SELF_CHECK_OK")


if __name__ == "__main__":
    main()

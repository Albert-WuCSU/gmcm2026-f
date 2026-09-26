"""Q2 过 G2.5：登记三条人工裁定、解除阻塞、开启 code_generation。

幂等：重复运行不产生重复的 gate_history / todos 条目。不改 G1/G2 历史。

provenance 纪律（本脚本的硬性约束）：
  - carried_forward_todos 只放**有约束力**的条目：使用者裁定的直接后果、探针实测事实、题目硬性要求。
  - AI 的实现提案一律放 ai_proposals_unconfirmed，带 decided_by=null，**不得**进 carried_forward_todos，
    因为下游 model-code-analyzer / python-model-code-generator 把该数组当待实现约束读。
  - 不代使用者解释「B1 的处理要谨慎」；按其指示挂起。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "planning/manifests/Q2.json"
TS = "2026-09-25T11:20:00+08:00"

# ---- 有约束力的条目（使用者裁定后果 / 探针事实 / 题目硬性要求）----
NEW_TODOS = [
    ("[G2.5 裁定1=A] p 经 exp(b^T z_p) 进入，b 为 17 维。P2 已证 b 在 B 侧不可验证"
     "（11 个 B 文件零配比列），故须显式声明跨源统一假设（AMB-Q2-2）并在可及范围内检验；"
     "论文须写明 b 的信息来源为附件 A 侧、经 Q1 输出引入（题目明文允许该路径）"),
    ("[G2.5 裁定2=A] 采用 D_eff = D·Q^gamma。禁止同时声称「Q 与 D 的替代率随位置变化」"
     "（P4 实测该弹性比恒为 2.0000，ptp<1e-12）；仅 Q↔N 随位置变化。"
     "估计顺序：beta 先由 B1 钉住，再由 Q 指数 -beta*gamma 反解 gamma，gamma 精度继承 beta 精度"),
    ("[G2.5 裁定2=A] M1s 维持 main、M2s（Q 作加性独立项）维持 conditional_fallback，触发条件不变："
     "gamma 的自助 95% 区间含 0，或 M1s 在 B1 留出集 RMSE 不优于 M0s"),
    ("[G2.5 裁定3=B] 半合成以「增大噪声方差」方式参与拟合：异方差加权最小二乘，半合成来源取更大"
     " sigma_s，与 P1 确立的来源专属截距 E_s 同属来源分层结构；不确定性须随之变宽。"
     "gamma 的自助区间用于判定 M2s 触发条件之一"),
    ("[G2.5 裁定3=B] sigma_s 的**取值方式**未由裁定指定，属实现选择：须在 run_summary 显式记录所用方式"
     "及其后果，且可被使用者否决。已知候选见 ai_proposals_unconfirmed。"
     "无论取何值，B6-B8 均须按 GC5 披露为半合成（calibrated 半数 val_loss 下界为 0.5，"
     "低于自然语言熵常见量级）"),
    ("[G2.5 数据取用] 用 B7(450) 即覆盖 B6（P6：B6 的 360 点全部包含于 B7）；B8 若参与须按 data_type 分层，"
     "其 extrapolated 720 点不进主拟合，留给 B9/B10 的百亿参数以上外推讨论。"
     "如此同时满足「B6 或 B7/B8」与「结合 B9/B10 讨论外推」两条硬性要求"),
    ("[使用者附加约束·已挂起] 使用者原话「但B1的处理要谨慎」，并于 2026-09-25 指示该项核查暂缓。"
     "已知事实：B1 拟合 R²=0.9999998、RMSE=1.465e-4（n=1176），对真实训练日志异常干净。"
     "未决后果：① 以 B1 残差作 sigma_real 会使权重比极端（半合成对共享参数几乎无扰动）；"
     "② 若 B1 非原始观测，GC5 披露范围须扩大。AI 不得自行裁定 B1 的处置方式"),
]

# ---- AI 提案：无约束力，等使用者审阅。下游不得当作待实现约束 ----
AI_PROPOSALS = [
    {
        "id": "b_calibration_from_q1c",
        "status": "AI_PROPOSAL_UNCONFIRMED",
        "decided_by": None,
        "relates_to_decision": "q2_p_entry_form (裁定1=A)",
        "proposal": ("不在 B 侧重新拟合 17 维 b，而是由 Q1c 的 M0c 系数 w 在 1B 参照点上局部匹配标定："
                     "b_i ≈ -w_i / [beta·(L - E_s - A·N^-alpha)]"),
        "why_ai_raised_it": "降低一天预算下的实现成本；Q1c 已有 17 个主效应系数，sign_stability 全 1.0",
        "embedded_assumption_user_has_not_ruled_on": (
            "该式把 M0c 的「域级 Loss 对 p 的导数」等同于标度律中「语料级 Loss 对 p 的导数」，"
            "是一条跨口径迁移假设，使用者只裁定了 p 的进入形式(1A)，未裁定 b 的标定途径"),
        "alternatives_not_excluded": ["在 A 侧数据上直接拟合含 b 的形式", "对 b 施加稀疏或分组约束"],
        "action": "由 model-code-analyzer 列为待确认项；若采用须在 run_summary 记录并可被使用者否决",
    },
    {
        "id": "sigma_semi_value_choice",
        "status": "AI_PROPOSAL_UNCONFIRMED",
        "decided_by": None,
        "relates_to_decision": "q2_semisynthetic_fit_participation (裁定3=B)",
        "proposal": "sigma_s 取值有两个候选，均未经使用者裁定",
        "candidates": [
            {"id": "residual_based",
             "how": "由各来源的拟合残差分层估计 sigma_s",
             "note": "B6 上残差约 0.0699、B1 约 1.465e-4（相差约 477 倍），"
                     "故残差法本身即给半合成更大 sigma、更小权重，方向与裁定3=B 一致"},
            {"id": "p5_out_of_sample_anchor",
             "how": "用 P5 的样本外转移 RMSE 0.6293 锚定半合成 sigma",
             "note": "更保守；但 0.6293 是 calibrated→extrapolated 的转移误差，"
                     "用它代表 calibrated 自身的噪声会高估"},
        ],
        "ai_correction_recorded": ("AI 曾声称『半合成残差小于 B1，自由估计 sigma 会反向加权半合成点』——"
                                  "该断言与已有数字相反（0.0699 vs 1.465e-4），已更正；"
                                  "故 p5_out_of_sample_anchor 并非必需修正，降为可选之一"),
        "action": "实现时参数化、可切换，默认值须在 run_summary 标注并可被使用者否决",
    },
]


def main() -> None:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))

    m["current_gate"] = "G2.5"
    m["status"] = "g25_passed_code_generation_allowed"
    m["allowed"]["code_generation"] = True
    m["artifacts"]["decision_ledger"] = "methods/Q2/q2_decisions.jsonl"
    m["blockers"] = []
    m["updated_at"] = TS

    m["human_decisions"] = {
        "count": 3,
        "ledger": "methods/Q2/q2_decisions.jsonl",
        "verbatim_reply": "1A,2A,3B，但B1的处理要谨慎。请继续推进吧",
        "decided": {
            "q2_p_entry_form": "A — 低维投影 exp(b^T z_p)",
            "q2_Q_entry_form": "A — 乘性 D_eff = D·Q^gamma",
            "q2_semisynthetic_fit_participation": "B — 增大噪声方差参与（WLS 更大 sigma）",
        },
        "additional_constraint_recorded_not_interpreted": "但B1的处理要谨慎（核查经使用者指示暂缓）",
        "ai_must_not": "把 AI 推荐或 AI 实现提案表述为使用者裁定；rationale 只录原话",
    }

    # AI 提案单独存放，不进 carried_forward_todos
    m["ai_proposals_unconfirmed"] = {
        "warning_to_downstream_skills": (
            "本键内容是 AI 意见，decided_by 为 null，**不是**待实现约束，也**不是**使用者裁定。"
            "读取待实现约束请只用 carried_forward_todos。采用任一提案前须回到使用者确认。"),
        "items": AI_PROPOSALS,
    }

    todos = m.setdefault("carried_forward_todos", [])
    for t in NEW_TODOS:
        if t not in todos:
            todos.append(t)

    gh = m.setdefault("gate_history", [])
    if not any(g.get("gate") == "G2.5" for g in gh):
        gh.append({
            "gate": "G2.5",
            "result": "PASSED",
            "at": TS,
            "basis": [
                "methods/Q2/q2_decisions.jsonl",
                "planning/choice_cards/q2_method_card.md",
                "methods/Q2/probes/risk_probe_summary.json",
            ],
            "note": ("三条人工 method_choice 均为 DECIDED、decided_by=human、rationale 为原话照录"
                     "（「1A,2A,3B，但B1的处理要谨慎。请继续推进吧」）、evidence_refs 全部存在。"
                     "裁定1=A（p 经 exp(b^T z_p)）、裁定2=A（乘性 D_eff）、裁定3=B（增大噪声方差参与）。"
                     "使用者附加「B1 的处理要谨慎」，已原样记录且未由 AI 解释；该项核查经使用者指示暂缓。"
                     "AI 曾就三条给出技术意见并被采纳为相同选项，该意见已标注为 AI 意见且未写入账本 rationale。"
                     "AI 的两条实现提案（b 的标定途径、sigma_s 取值方式）存于 ai_proposals_unconfirmed，"
                     "decided_by=null，不计为使用者裁定、不作待实现约束。"),
        })

    m["next_action"] = {
        "owner": "ai",
        "skill": "model-code-analyzer",
        "reason": ("G2.5 已过，allowed.code_generation=true。下一步 model-code-analyzer 读方法卡 + 账本 + "
                   "carried_forward_todos，产出代码计划，再进 python-model-code-generator（G3）。"
                   "实现范围仅 M1s(main) 与 M0s(usable_baseline)；M2s 保持休眠直至其触发条件成立。"
                   "注意：ai_proposals_unconfirmed 内的两项不是约束，采用前须回到使用者确认。"),
    }

    MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 自核验：重新 json.load，不信写入回执
    v = json.loads(MANIFEST.read_text(encoding="utf-8"))
    print("current_gate      :", v["current_gate"])
    print("status            :", v["status"])
    print("code_generation   :", v["allowed"]["code_generation"])
    print("decision_ledger   :", v["artifacts"]["decision_ledger"])
    print("blockers          :", v["blockers"])
    print("gates             :", [g["gate"] for g in v["gate_history"]])
    print("todos_total       :", len(v["carried_forward_todos"]))
    print("ai_proposals      :", [p["id"] for p in v["ai_proposals_unconfirmed"]["items"]])
    print("next_skill        :", v["next_action"]["skill"])
    assert v["allowed"]["code_generation"] is True
    assert v["blockers"] == []
    assert [g["gate"] for g in v["gate_history"]].count("G2.5") == 1
    for p in v["ai_proposals_unconfirmed"]["items"]:
        assert p["decided_by"] is None and p["status"] == "AI_PROPOSAL_UNCONFIRMED"
    # AI 提案不得混入待实现约束
    for t in v["carried_forward_todos"]:
        assert "AI_PROPOSAL" not in t
        assert "b_i ≈" not in t, "b 的标定式不得出现在 carried_forward_todos"
        assert "0.6293 锚定" not in t, "sigma 锚定提案不得出现在 carried_forward_todos"
    print("SELF_CHECK_OK")


if __name__ == "__main__":
    main()

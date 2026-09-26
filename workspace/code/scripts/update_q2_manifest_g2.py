"""Q2 过 G2：登记方法卡与风险探针，推进 gate 到 G2，挂 G2.5 的人工裁定 blocker。

G2 契约（AGENTS.md）：方法卡定义 main/baseline/可选 fallback；risk_probe_summary.json 存在；
main 与 baseline 通过适用的风险检查；fallback 有显式触发条件。

code_generation 保持 false —— 须等 G2.5 的人工 method_choice。
幂等：G2 不重复追加，blocker 按 id 去重。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "planning/manifests/Q2.json"
TS = "2026-09-25T10:20:00+08:00"

ARTIFACTS = {
    "method_card": "methods/Q2/q2_method_card.md",
    "risk_probe": "methods/Q2/probes/risk_probe_summary.json",
    "probe_evidence": ["workspace/data/q2_probe_scaling.json"],
    "probe_script": "workspace/code/scripts/probe_q2_scaling.py",
    "choice_card": "planning/choice_cards/q2_method_card.md",
    "q1_upstream_domain_quality": "results/Q1/experiments/round1/tables/q1a_domain_quality.csv",
}

BLOCKER = {
    "id": "q2_method_choice",
    "type": "human_decision_required",
    "gate": "G2.5",
    "summary": "三条方法选择待裁定：① p 如何进入（低维投影/标量化/仅经 Q）；② Q 进入方式（D_eff 乘性 vs 加性独立项）；③ 半合成参与拟合的程度上限",
    "why_ai_cannot_decide": "AGENTS.md：AI 不得发起使用者的选择、理由、置信度；G2.5 要求账本含 DECIDED 的人工 method_choice",
    "already_mechanical_do_not_ask": "E 不跨源共享（P1 实测极差 1.6898 ≫ 阈 0.15）；弹性符号由机械判定；baseline 由 HD-2 声明；B1 主拟合为题目硬性要求",
    "card": "planning/choice_cards/q2_method_card.md",
    "blocks": "code_generation（allowed.code_generation 保持 false 直至 G2.5 通过）",
}

TODOS = [
    "[G2 承重·P1] 跨源不可共享 E：三源各自拟合 E = B1 1.6898 / B4 0.0331 / B5 0.0000，极差 1.6898 ≫ 阈 0.15。模型须用来源专属截距 E_s；B4/B5 仅作验证；禁止报跨源未去偏的 R²，须用秩相关或去源偏后指标",
    "[G2 承重·P2] p 与 (N,D) 几乎不联合观测：11 个 B 文件逐列核验无任何配比列；A 侧三尺度仅 1B 落入 B1 的 [0.0705,11.9658]B，60m(=0.060B) 恰在下界外。故 L(N,D,Q,p) 在任何单一来源上不可辨识，跨源统一假设是承重假设（AMB-Q2-2），须显式声明并检验",
    "[G2 承重·P4] 采用 D_eff = D·Q^gamma 即锁定 Q↔D 弹性比恒为 gamma（实测 ptp<1e-12，值 2.0000）。禁止在采用该形式的同时声称『Q 与 D 的替代率随位置变化』；估计顺序须 beta 先由 B1 钉住再反解 gamma（gamma 精度继承 beta 精度）",
    "[G2·P3] Q 的加性与乘性进入方式在 B6 上不可区分（RMSE 0.06991 vs 0.07247，相对差 3.5% < 阈 10%）→ 形式选择不能靠拟合优度，须靠机理与 Q3 可用性，属人工裁定",
    "[G2·P5 须披露] B8 的 calibrated 半数 val_loss 下界也是 0.5（不止 extrapolated），低于自然语言熵常见量级，属半合成生成产物，按 GC5 须披露。预声明判据（bias 占 RMSE<50%）实测 3.2% 记 PASS，但预测 RMSE 0.6293 而 val_loss 全域仅 0.5-2.603 —— 低 bias 不等于误差小，表述须带此限制",
    "[G2·P6] B6 的 360 个 (N,D,Q) 点全部包含于 B7 → 用 B7(450) 即覆盖 B6，不必两者都用。Q 为离散设计网格（8/10/12 级），与 Q1 的连续经验 Q 非同类对象（AMB-Q2-3），须建立对齐规则并声明假设",
    "[G2·P7] B9 无 val_loss 列且 4 行 D 缺失/为零；B10 的 val_loss 为估算值。二者仅用于百亿参数以上外推的可信度讨论，不进主拟合",
    "[数据画像缺口] profile_b_scaling.json 漏了 B3；磁盘上实为 8 个 pythia_*_trajectory.csv（8×500）。B2 已画像可用，故『B2 或 B3』硬性要求不受阻，但若要用 B3 须先补画像",
    "[判据自审] P4 的预声明判据测错对象、P5 的判据太松 —— 均照实记录于 risk_probe_summary.criterion_self_audit，不事后放宽（与 Q1 的 R6/R7 同一纪律）",
]


def main() -> None:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))

    m["current_gate"] = "G2"
    m["status"] = "g2_passed_awaiting_human_method_choice"
    m.setdefault("artifacts", {}).update(ARTIFACTS)

    blockers = m.setdefault("blockers", [])
    if not any(isinstance(b, dict) and b.get("id") == BLOCKER["id"] for b in blockers):
        blockers.append(BLOCKER)

    todos = m.setdefault("carried_forward_todos", [])
    for t in TODOS:
        if t not in todos:
            todos.append(t)

    if not any(g["gate"] == "G2" for g in m.get("gate_history", [])):
        m.setdefault("gate_history", []).append({
            "gate": "G2", "result": "PASSED", "at": TS,
            "basis": ["methods/Q2/q2_method_card.md",
                      "methods/Q2/probes/risk_probe_summary.json"],
            "note": (
                "角色化清单成立：main=M1s（D_eff 乘性含 Q 与配比偏移，来源专属截距）、"
                "usable_baseline=M0s（HD-2 声明的经典式，仅用 B1）、"
                "conditional_fallback=M2s（Q 作加性独立项，有显式触发条件）。"
                "7 项风险探针实跑，main 与 baseline 七字段齐备、均为 CONDITIONAL 并附解除条件。"
                "P1/P2 两项 FAIL 改变了模型结构（须来源专属截距；跨源统一假设为承重）；"
                "P3 显示 Q 的两种进入方式在 B6 上不可区分（相对差 3.5%）；"
                "P4 确认 D_eff 形式下 Q↔D 弹性比恒定并修正了评审 3.2 的表述边界；"
                "P5/P6/P7 确认半合成与设计因子的使用限制。"
                "高自由度神经网络据证据排除（无法解析求导，与 Q3 的 KKT 需求冲突）。"
                "两条预声明判据自身的问题已照实记录，不事后放宽。"),
        })

    m["allowed"]["code_generation"] = False
    m["next_action"] = {
        "owner": "human",
        "skill": "modeler-decision-logger",
        "reason": (
            "G2 已过。G2.5 需三条人工 method_choice，选择卡已出："
            "planning/choice_cards/q2_method_card.md。"
            "① p 如何进入（AMB-Q2-1 + P2：p 与 (N,D) 仅在 1B 一点重叠）；"
            "② Q 进入方式（P3：拟合优度不可区分，须靠机理与 Q3 可用性）；"
            "③ 半合成参与拟合的程度上限（题目 success_criteria 第 3 条 + GC5 + P5）。"
            "裁定后写入 methods/Q2/q2_decisions.jsonl（rationale 只录原话），"
            "置 allowed.code_generation=true，再进 model-code-analyzer -> "
            "python-model-code-generator（G3）。"),
    }
    m["updated_at"] = TS

    missing = []
    for k, v in ARTIFACTS.items():
        for pth in (v if isinstance(v, list) else [v]):
            if not (ROOT / pth).exists():
                missing.append(pth)
    if missing:
        raise SystemExit(f"拒绝写入：登记路径不存在 {missing}")

    MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("gate:", m["current_gate"], "| status:", m["status"])
    print("gate_history:", [g["gate"] for g in m["gate_history"]])
    print("blockers:", [b["id"] for b in m["blockers"]])
    print("code_generation:", m["allowed"]["code_generation"], "(须等 G2.5)")
    print("todos:", len(m["carried_forward_todos"]))
    print("next:", m["next_action"]["skill"], "| owner", m["next_action"]["owner"])


if __name__ == "__main__":
    main()

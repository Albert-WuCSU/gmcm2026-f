"""Q3 过 G2：登记方法卡、探针摘要、选择卡；blockers 记三条人工裁定。幂等。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "planning/manifests/Q3.json"
TS = "2026-09-25T15:50:00+08:00"

TODOS = [
    ("[G2 承重·P1 FAIL] Q* 在 9 个预算×成本函数组合中有 7 个顶到上界 1.0（仅 C=1e19 的指数型 0.6460、"
     "幂型 0.5390 为内点）⇒ 内点 KKT 不足，必须分段：Q<1 内点段 + Q=1 边界降维段"),
    ("[G2 承重·P3 FAIL] p 联立优化数学退化：b^T z_p 对 p 线性 ⇒ 单纯形最优在顶点，"
     "实测最大分量 1.0000（全给 dm_mathematics）。若选联立优化须加信赖域/正则，"
     "且正则强度会与 Q2 已声明不可辨识的 kappa 纠缠"),
    ("[G2·P2] 成本函数选择的影响集中在低预算档：Q* 极差 0.4610 全部来自 C=1e19；"
     "C=1e22/1e24 下三类 g 的 Q* 完全一致（均 1.0）。题目要求的『讨论成本函数影响』有此明确答案"),
    ("[G2·P4] 结构性转移存在但形态是连续饱和：占比排序变化 1 次、Q* 一阶差分无 >0.05 跳变、"
     "Q* 在 log10 C=21.5 饱和。选『分配份额突变』定义会得出『无转移』的诚实负结果"),
    ("[G2·P5] 跨 L_ctx_crit=30000 压缩规模而非重排配比：L_ctx 2048→131072 时 "
     "N* -54.8%(5.647→2.551B)、D* -53.4%(249.1→116.1B)，N:D 仅变 3.22%。"
     "红线『30000 不是最优上下文长度』保留；可补此实测表述"),
    ("[G2·P5 判据自审] P5 判据挂在 N:D 比值上故判 WEAK_EFFECT，该判据没错（问的是配比是否重排），"
     "但单看 verdict 会误读为『L_ctx 不重要』。规模压缩效应已同时记录，不事后改判据"),
    ("[G2·P5 AI 更正] AI 曾断言『L_ctx 只等价于预算缩放』，实测仅近似且随 L_ctx 失效"
     "（N:D 相对差 1.97e-2 → 3.34e-1）。成因：C_Q=D*[g(Q)-g(Q0)] 只随 D 标度。强版本不得入论文"),
    ("[G2·P6] 高预算档为外推：C=1e24 最优 N*=40.755B / D*=3771.0B，相对 B1 上界外推 3.41x / 12.57x。"
     "须结合 B9/B10 可信度边界说明（AMB-Q3-3），不得表述为可靠预测"),
    ("[G2 待办] M0o 的 Chinchilla 比例对本标度律的可迁移性未检验（本律 alpha=0.3400、beta=0.2799）。"
     "作为 baseline 的已声明简化假设，须在论文注明；若裁定3 选 B 则同一未检验假设承担两重角色"),
    ("[G2 待办] Q0 取值本轮探针用 0.35（Q1 实测域级 Q 落在 0.2233-0.3815 的上端附近）。"
     "该取值未经使用者裁定，实现时须参数化并在 run_summary 记录"),
]


def main() -> None:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    m["current_gate"] = "G2"
    m["status"] = "g2_passed_awaiting_human_method_choice"
    m["updated_at"] = TS
    a = m.setdefault("artifacts", {})
    a["method_card"] = "methods/Q3/q3_method_card.md"
    a["risk_probe"] = "methods/Q3/probes/risk_probe_summary.json"
    a["choice_card"] = "planning/choice_cards/q3_method_card.md"
    a["probe_evidence"] = ["workspace/data/q3_probe_optimization.json"]
    a["probe_script"] = "workspace/code/scripts/probe_q3_optimization.py"
    a["upstream_q2_run"] = "results/Q2/experiments/round1/run_summary.json"
    m.setdefault("allowed", {})["code_generation"] = False

    m["blockers"] = [{
        "id": "q3_method_choice", "type": "human_decision_required", "gate": "G2.5",
        "summary": ("三条方法选择待裁定：① p 是否联立优化（P3 实测角点退化，联立须加正则）；"
                    "② 结构性转移的数学定义（P4 四候选，选『份额突变』会得出无转移的负结果）；"
                    "③ 最优解可接受性判据（KKT / Chinchilla 对照 / 两者）"),
        "why_ai_cannot_decide": "AGENTS.md：AI 不得发起使用者的选择、理由、置信度",
        "already_mechanical_do_not_ask": ("L_ctx 外生且取值须来自 C7；L_ctx_crit=6/eta=30000 为题目给定闭式；"
                                         "baseline 由 HD-2 声明；至少三档预算为题目硬性"),
        "card": "planning/choice_cards/q3_method_card.md",
        "blocks": "code_generation（allowed.code_generation 保持 false 直至 G2.5 通过）",
    }]

    todos = m.setdefault("carried_forward_todos", [])
    for t in TODOS:
        if t not in todos:
            todos.append(t)

    gh = m.setdefault("gate_history", [])
    if not any(g.get("gate") == "G2" for g in gh):
        gh.append({
            "gate": "G2", "result": "PASSED", "at": TS,
            "basis": ["methods/Q3/q3_method_card.md", "methods/Q3/probes/risk_probe_summary.json",
                      "workspace/data/q3_probe_optimization.json"],
            "note": ("角色化清单成立：main=M1o（分段 KKT + log C 密集扫描）、"
                     "usable_baseline=M0o（HD-2 声明的 Chinchilla 经验配置）、"
                     "conditional_fallback=M2o（纯数值全局优化，有显式触发）。"
                     "6 项风险探针实跑，main 与 baseline 七字段齐备、均 CONDITIONAL 并附解除条件。"
                     "P1/P3/P6 三项 FAIL 改变了求解结构（必须分段 KKT；p 联立须加正则；高预算为外推）；"
                     "P2 定位了成本函数影响的区间；P4 确认转移存在且形态为连续饱和；"
                     "P5 记录了跨临界压缩规模而非重排配比，并更正了一条 AI 过强断言。"
                     "已据证据排除：把 L_ctx 作为寻优变量（题目禁止）、拉格朗日松弛后不检验互补松弛。"),
        })

    m["next_action"] = {
        "owner": "human", "skill": "modeler-decision-logger",
        "reason": ("G2 已过。G2.5 需三条人工 method_choice，选择卡已出："
                   "planning/choice_cards/q3_method_card.md。裁定后写入 methods/Q3/q3_decisions.jsonl"
                   "（rationale 只录原话），置 allowed.code_generation=true，"
                   "再进 model-code-analyzer -> python-model-code-generator（G3）。"),
    }
    m["success_criteria_mode"] = "relative_to_baseline"
    m["declared_baseline"] = "Chinchilla 经验配置（固定 N:D 比例、Q=Q0 不投质量）"

    MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    v = json.loads(MANIFEST.read_text(encoding="utf-8"))
    print("gate:", v["current_gate"], "| status:", v["status"])
    print("gates:", [g["gate"] for g in v["gate_history"]])
    print("code_generation:", v["allowed"]["code_generation"], "| blockers:", len(v["blockers"]))
    print("todos:", len(v["carried_forward_todos"]))
    assert v["allowed"]["code_generation"] is False
    assert len(v["blockers"]) == 1
    print("SELF_CHECK_OK")


if __name__ == "__main__":
    main()

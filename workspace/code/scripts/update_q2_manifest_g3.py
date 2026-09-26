"""Q2 过 G3：登记 P8、run_summary、G3 gate。幂等。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "planning/manifests/Q2.json"
PROBE = ROOT / "methods/Q2/probes/risk_probe_summary.json"
TS = "2026-09-25T14:30:00+08:00"

P8 = {
    "probe_id": "P8_shape_param_cross_source_sharing",
    "added_at_gate": "G3",
    "load_bearing_risk": ("P1 只检验了 E 的跨源可共享性。若 A/alpha/B 也不可共享，联合 WLS 中被 B1 "
                          "钉死的形状参数会迫使 gamma 吸收 B7 的形状失配"),
    "criterion_timing_disclosure": ("参数数值在 G3 调试中先被观察到，本判据非盲设；"
                                    "故判据改挂在 gamma 的自助区间尺度上以保持决策相关性"),
    "predeclared_criterion": "强制共享造成的 gamma 位移 < gamma 自助 95% 区间宽度的 50% 才可共享",
    "observed": {
        "gamma_source_specific_shape": 0.9659128363851796,
        "gamma_shared_shape": 0.7968091215858158,
        "gamma_shift": 0.1691037147993637,
        "threshold": 0.08584312637409258,
        "shift_as_fraction_of_ci_width": 0.9849578058377841,
        "rmse_B7_penalty_of_sharing": 0.015493377039945314,
        "A_ratio_B7_over_B1": 1.4947,
        "alpha_B7_vs_B1": [0.283218, 0.339977],
        "B_ratio_B7_over_B1": 0.8497,
    },
    "verdict": "FAIL",
    "consequence": ("形状参数须来源专属。连带后果：除 beta 外几乎所有参数都来源专属 ⇒ 裁定3=B 的联合 WLS "
                    "在数值上退化为『B1 定 beta、B7 定 gamma』的两段式（实测 gamma 差 1.03e-7、beta 差 6.86e-8）。"
                    "WLS 机制被忠实实现但在该参数结构下无实质作用 —— 不得表述为『联合拟合提升了估计』"),
    "evidence": "workspace/data/q2_probe_shape_sharing.json",
    "script": "workspace/code/scripts/probe_q2_shape_sharing.py",
}

G3_TODOS = [
    ("[G3·P8 FAIL] A/alpha/B 不可跨源共享（gamma 位移 0.1691 = 其自助区间宽的 98.5%，阈 50%）。"
     "形状参数须来源专属；论文不得声称『联合拟合提升了估计』—— 实测联合 WLS 等价于两段式"),
    ("[G3 承重] Q2c 各输出须按参数来源拆开报：dL/dN、dL/dD 及其弹性由 B1 真实数据支撑；"
     "含 gamma 的量（dL/dQ、dN/dQ、Q+0.1 等价 N 增量、弹性比）不可避免半合成。"
     "两侧量级差实测 15.0%~31.8%，该差即『跨源统一假设的代价』的量化证据"),
    ("[G3 结果] gamma = 0.9659，自助 95% 区间 [0.8839, 1.0555] **含 1.0** ⇒ D_eff ≈ D·Q，"
     "即『质量按比例放大有效 token 数』。这是实测支撑的结构性结论，可作论文论点"),
    ("[G3 结果] Q+0.1 等价 N 增量：B1 侧 -0.13410、B7 侧 -0.09447（N=1B, D=150B, Q=0.5 参照点）。"
     "符号为负 = 提质可减少参数量。**须带参照点报，且须报两侧**"),
    ("[G3 待办] beta 是否可跨源共享**未检验**（P8 只查了 A/alpha/B）。当前作承重假设使用，须在论文声明"),
    ("[G3 待办] AMB-Q2-3 尺度对齐未解决：Q1 经验域级 Q 落在 0.2233-0.3815，B7 设计网格 Q 为 0.1-1.0。"
     "本轮未做静默映射，对齐规则仍须显式建立"),
    ("[G3 待办] B1 自助按 N 分组（仅 8 组）vs 逐行，两者 beta 区间几乎相同"
     "（[0.27982,0.27994] vs [0.27983,0.27993]）—— 与 B1 异常干净一致。"
     "使用者的『B1 处理要谨慎』约束仍挂起"),
]


def main() -> None:
    # 1) P8 写入 risk_probe_summary
    pr = json.loads(PROBE.read_text(encoding="utf-8"))
    probes = pr.setdefault("probes_added_after_G2", [])
    if not any(p.get("probe_id") == P8["probe_id"] for p in probes):
        probes.append(P8)
    pr["last_updated"] = TS
    PROBE.write_text(json.dumps(pr, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    # 2) manifest 过 G3
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    m["current_gate"] = "G3"
    m["status"] = "g3_code_and_experiment_done_awaiting_review"
    m["updated_at"] = TS
    m["artifacts"]["code_plan"] = "code/Q2/q2_code_plan.md"
    m["artifacts"]["latest_run"] = "results/Q2/experiments/round1/run_summary.json"
    m["artifacts"]["probe_evidence"] = sorted(set(m["artifacts"].get("probe_evidence", []) + [
        "workspace/data/q2_probe_scaling.json",
        "workspace/data/q2_probe_g3_identifiability.json",
        "workspace/data/q2_probe_shape_sharing.json",
    ]))

    todos = m.setdefault("carried_forward_todos", [])
    for t in G3_TODOS:
        if t not in todos:
            todos.append(t)

    # b 的标定途径已由裁定6 解决，从未确认提案中移除；sigma 取值方式仍未裁定
    ap = m.get("ai_proposals_unconfirmed", {})
    items = [i for i in ap.get("items", []) if i["id"] != "b_calibration_from_q1c"]
    for i in items:
        if i["id"] == "sigma_semi_value_choice":
            i["g3_status"] = ("实现为 --sigma-mode {residual,p5_anchor}，本轮用 residual 并已写入 "
                              "run_summary.warnings；仍未经使用者裁定，可否决。"
                              "注：P8 后该选择对结果影响极小（联合 WLS 已退化为两段式）")
    ap["items"] = items
    m["ai_proposals_unconfirmed"] = ap

    gh = m.setdefault("gate_history", [])
    if not any(g.get("gate") == "G3" for g in gh):
        gh.append({
            "gate": "G3", "result": "PASSED", "at": TS,
            "basis": ["code/Q2/q2_code_plan.md",
                      "results/Q2/experiments/round1/run_summary.json",
                      "workspace/data/q2_probe_shape_sharing.json"],
            "note": ("M1s(main) 与 M0s(usable_baseline) 均实跑成功，M2s 未实现（fallback 未触发）。"
                     "三项预声明判据：B1 退化 PASS（相对差 1.01e-8 < 1e-6）、"
                     "B7 超越性 PASS（RMSE 0.11825→0.07638，降幅区间 [0.0362,0.0478] 不含 0）、"
                     "弹性符号 PASS。gamma=0.9659 区间 [0.8839,1.0555] 含 1.0。"
                     "G3 期间新增 P8 探针并判 FAIL，改变了参数结构（形状参数来源专属），"
                     "该修正发生在结果解读之前、方向为收紧。"
                     "两处 AI 自述错误已更正：① 曾声称半合成残差小于 B1（实为大 477 倍）；"
                     "② 曾凭空报告两个不存在的表格 bug（B2 与 B4 同值、domain_ratio 错乱），"
                     "实际核验表格正确（B2 n=1029 spearman=0.788102、域比值表 17 域齐全）。"),
        })

    m["next_action"] = {
        "owner": "ai", "skill": "python-code-reviewer",
        "reason": ("G3 实验已完成，需语言评审产出 code/Q2/reviews/q2_python_review.json，"
                   "含五项命名检查。method_alignment 须逐条核对 6 条裁定 + P8 后的参数结构修正。"
                   "之后 Q2 的 G4 需使用者三类裁定（result/stability/claim_scope）。"),
    }

    MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    v = json.loads(MANIFEST.read_text(encoding="utf-8"))
    p = json.loads(PROBE.read_text(encoding="utf-8"))
    print("gate:", v["current_gate"], "| status:", v["status"])
    print("gates:", [g["gate"] for g in v["gate_history"]])
    print("todos:", len(v["carried_forward_todos"]))
    print("probe_evidence:", len(v["artifacts"]["probe_evidence"]))
    print("P8 registered:", any(x["probe_id"] == P8["probe_id"] for x in p["probes_added_after_G2"]))
    print("unconfirmed proposals:", [i["id"] for i in v["ai_proposals_unconfirmed"]["items"]])
    assert v["current_gate"] == "G3"
    assert [g["gate"] for g in v["gate_history"]].count("G3") == 1
    print("SELF_CHECK_OK")


if __name__ == "__main__":
    main()

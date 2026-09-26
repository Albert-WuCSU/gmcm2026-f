"""G4 通过：三条人工裁定已入账本，B-1/B-2 补算已执行，结果分析已回填裁定口径。

- 清空 blockers（三条 human_decision_required 已解除；顺带修正 id 不一致：
  blocker 原写 q1a_arxiv_rank1_claim_scope，账本实际为 q1a_domain_order_claim_scope[_v2]）
- decisions 补三条裁定
- gate_history 追加 G4 PASSED
- artifacts 登记补算输出
- next_action 转 Q2 的 method-selector（G2）

幂等：G4 不重复追加。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "planning/manifests/Q1.json"
TS = "2026-09-24T23:40:00+08:00"


def main() -> None:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))

    m["current_gate"] = "G4"
    m["status"] = "g4_passed_round1_final_ready_for_Q2"
    m["blockers"] = []
    m["artifacts"]["supplementary_b1_b2"] = "robustness/Q1/q1_supplementary_b1_b2.json"

    m["decisions"].update({
        "q1_result_verdict": "B",
        "q1_stability_verdict": "B",
        "q1a_domain_order_claim_scope": "A",
        "q1a_domain_order_claim_scope_superseded_by": "q1a_domain_order_claim_scope_v2",
        "card3_decided_at": "2026-09-24T22:55:00+08:00",
        "card3_correction_at": "2026-09-24T23:10:00+08:00",
    })

    if not any(g["gate"] == "G4" for g in m["gate_history"]):
        m["gate_history"].append({
            "gate": "G4", "result": "PASSED", "at": TS,
            "basis": [
                "methods/Q1/q1_decisions.jsonl",
                "results/Q1/reports/q1_final_result_analysis.md",
                "robustness/Q1/q1_robustness_summary.json",
                "robustness/Q1/q1_supplementary_b1_b2.json",
            ],
            "note": (
                "账本含 result / stability / claim-scope 三类人工裁定（共 10 条，"
                "第 10 条为 claim_scope 的 supersedes 更正）。最终结果分析与稳健性报告齐备。"
                "裁定 1=B 授权的两项补算已执行：B-1 查明 R6 的 1B 格在 B=400 下不可判定"
                "（上界蒙特卡洛极差 1.40e-4 > 离零距离约 5e-5），B>=4000 时 8 种子一致含 0，"
                "故『三尺度区间均含 0』成立、无需软化，R6 的 FAIL 按预声明口径不变；"
                "B-2 查明 3 个破 claim 的分组变体中 2 个为决定性反超（c4 高出 9.38x/3.92x 半宽和）、"
                "1 个并列，排除『反超只是噪声』的读法，支持收窄 claim；"
                "top-3 集合在 9 个配置下不变（{arxiv,c4,commoncrawl}）。"
                "域序 claim 已收窄为报最高一档、不对 arxiv 在档内位次作断言，口径已回填结果分析。"
                "rigor_profile=lean 且 allowed.freeze=false，故 frozen_numbers.json 不适用。"),
        })

    m["next_action"] = {
        "owner": "ai",
        "skill": "method-selector",
        "target": "Q2",
        "reason": (
            "Q1 已过 G4，round1 为最终轮，无阻塞。转 Q2：Q2 的 G1 已通过"
            "（gate_history 有 G1 PASSED @ 09-24T00:35，与 Q1 同批，因 parse/classification/framing "
            "是全局工件），故 Q2 的下一关是 G2 —— 走 method-selector 出方法卡与风险探针。"
            "Q2 首要探针 F8：Q1 的经验 Q（连续、受域混淆）与 B6-B8 的设计网格 Q（离散刻度 0.05-1.0）"
            "不是同类对象，Q1->Q2 是尺度校准问题而非直接代入；"
            "另须查 D_eff = D·Q^γ·exp(bᵀz_p) 的恒定弹性比问题（弹性比恒等于 γ，8 个测点均为 2.0000，"
            "沿 Q 方向只能辨识乘积 βγ => β 须先由 B1 真实数据钉住，再用 B6-B8 估 γ）。"),
    }
    m["updated_at"] = TS

    for p in [m["artifacts"]["supplementary_b1_b2"]]:
        if not (ROOT / p).exists():
            raise SystemExit(f"拒绝写入：{p} 不存在")

    MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("gate:", m["current_gate"], "| status:", m["status"])
    print("blockers:", m["blockers"])
    print("gate_history:", [g["gate"] for g in m["gate_history"]])
    print("next:", m["next_action"]["skill"], "->", m["next_action"]["target"])


if __name__ == "__main__":
    main()

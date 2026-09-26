"""Q3 过 G2.5:三条人工裁定已落账 ⇒ 解除 code_generation 封锁。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
M = ROOT / "planning/manifests/Q3.json"
AT = "2026-09-25T16:45:00+08:00"

d = json.loads(M.read_text(encoding="utf-8"))

d["current_gate"] = "G2.5"
d["status"] = "g25_passed_ready_for_code_generation"
d["artifacts"]["decision_ledger"] = "methods/Q3/q3_decisions.jsonl"
d["allowed"]["code_generation"] = True
d["blockers"] = []
d["updated_at"] = AT

d["gate_history"].append({
    "gate": "G2.5",
    "result": "PASSED",
    "at": AT,
    "basis": ["methods/Q3/q3_decisions.jsonl", "planning/choice_cards/q3_method_card.md"],
    "note": (
        "三条人工 method_choice 已裁定并落账,rationale 逐字照录使用者原话。"
        "① q3_p_joint_optimization = B_main_plus_C_supplement:p 由 Q1/Q2 固定(z_p=0),"
        "另报 dL/dp_i 符号与排序作补充;KKT 维度 3。② q3_structural_transition_definition = "
        "A_main_plus_D_reported_as_contrast:主定义为活跃约束集变化(实测 log10 C = 21.5),"
        "并一并报 D 定义下判不出转移,以说明转移形态为连续饱和而非突跳。"
        "③ q3_optimum_acceptability_criterion = C:KKT 为硬判据,Chinchilla 对照仅作参考。"
        "裁定 3 的理由经核验后与选择卡原文不同:本律 B1 侧参数与 Chinchilla Approach-3 常数数值同一,"
        "故 Chinchilla 不构成外部锚点;且本律隐含 D/N 随预算漂移 32.06→97.89,"
        "把常数 20 当硬判据会拒绝本律自身的真最优解。"
    ),
})

# 裁定带来的实现约束与新增待办
d["carried_forward_todos"] += [
    "[G2.5 裁定1] p 固定为 Q1 基准配比(z_p=0),决策变量 (N,D,Q),KKT 维度 3。"
    "另需输出 dL/dp_i 的符号与域间排序作补充分析(与 kappa 无关);不报最优 p*。"
    "题目要求的『说明理由』由 P3 角点退化实测支撑,论证须本队自撰(GC9)",

    "[G2.5 裁定2] 结构性转移主定义 = 活跃约束集变化(Q≤1 由非活跃转活跃),识别用 log C 扫描 + "
    "互补松弛乘子由 0 转正;实测位置 log10 C = 21.5。同时报 D 定义(一阶差分超阈)下的负结果作对比。"
    "扫描步长须在 run_summary 记录,并须报『D 的结论随步长翻转』(0.5 判有、0.25 与 0.125 判无)",

    "[G2.5 裁定2 修正] 方法卡与选择卡称饱和点处 dQ*/dlogC『由负转零』是符号错误,"
    "实测为由正转零(+0.1500 → 0)。写作时不得沿用错误表述",

    "[G2.5 裁定2 可报] C 定义(占比排序变化)实测位置 log10 C = 22.75,与主定义 A 的 21.5 不同。"
    "三定义三答案(A 21.5 / C 22.75 / D 不存在)可作『定义决定结论』的实证",

    "[G2.5 裁定3] KKT 为硬判据(互补松弛 + 梯度残差 < 预声明阈 + 分段枚举覆盖 Q=1 边界);"
    "Chinchilla 对照表照出但不作 pass/fail",

    "[G2.5 裁定3 更正上游] 探针摘要 chinchilla_ratio_transferable_to_this_law 的 NOT_CHECKED 应改判:"
    "已检验,本律 B1 侧参数与 Chinchilla Approach-3 常数按十亿单位折算后数值同一"
    "(相对差 9.4e-6 ~ 4.4e-4),但本律隐含 D/N 随预算漂移(1e19:32.06、1e22:62.64、1e24:97.89,"
    "漂移指数 0.0970),与 20 tokens/param 不同。该 Chinchilla 常数由 AI 凭记忆复现,引用前须核原文",

    "[G2.5 未裁定·待使用者定] M0o 若按字面取 D/N=20 会被不必要削弱:C=1e22 下报告差距 0.094665 中,"
    "0.026183(27.7%)来自比值被强制而非质量通道。HD-2 为相对 baseline 制 ⇒ 会虚增 M1o 优势。"
    "G3 实现:按卡上定义实现 M0o 作已声明 baseline,同时把 M0o'(Q=Q0、N:D 自由)作诊断项写入 run_summary,"
    "不改动已声明 baseline;是否改 M0o 定义留待使用者裁定",
]

d["next_action"] = {
    "owner": "ai",
    "skill": "model-code-analyzer",
    "reason": (
        "G2.5 已过,allowed.code_generation=true。下一步 model-code-analyzer 出 Q3 代码计划,"
        "再 python-model-code-generator 生成 M1o(分段 KKT + log C 扫描)与 M0o(Chinchilla 配置)进 G3。"
        "M2o 保持休眠直至触发条件成立。"
    ),
}

M.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("WROTE", M.relative_to(ROOT))
print("  current_gate =", d["current_gate"])
print("  code_generation =", d["allowed"]["code_generation"])
print("  blockers =", len(d["blockers"]))
print("  decision_ledger =", d["artifacts"]["decision_ledger"])
print("  todos =", len(d["carried_forward_todos"]))

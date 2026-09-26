"""把 planning/manifests/Q1.json 推进到 G2（方法已筛选，等待人工选择）。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MF = ROOT / "planning/manifests/Q1.json"
TS = "2026-09-24T18:20:00+08:00"


def main() -> None:
    m = json.loads(MF.read_text(encoding="utf-8"))

    m["current_gate"] = "G2"
    m["status"] = "method_screened_awaiting_human_choice"
    m["artifacts"]["method_card"] = "methods/Q1/q1_method_card.md"
    m["artifacts"]["risk_probe"] = "methods/Q1/probes/risk_probe_summary.json"
    m["artifacts"]["probe_evidence"] = [
        "workspace/data/q1_polarity_evidence.json",
        "workspace/data/q1_probe_quality.json",
        "workspace/data/q1_probe_corr.json",
        "workspace/data/q1_probe_quality2.json",
        "workspace/data/q1_probe_mixture.json",
    ]
    m["shortlist"] = {
        "quality_side": {"main_candidate": "M1", "usable_baseline": "M0",
                         "conditional_fallback": "M2"},
        "mixture_side": {"main_candidate": "M1c", "usable_baseline": "M0c",
                         "conditional_fallback": None},
        "verdicts": {"M0": "CONDITIONAL", "M1": "CONDITIONAL", "M2": "PASS",
                     "M0c": "PASS", "M1c": "CONDITIONAL"},
    }
    m["blockers"] = [
        {"id": "q1_tierC_direction", "owner": "human", "gate": "G2.5",
         "summary": "6 个 Tier C 指标（dsir×3 / word_count / num_sentences / mean_word_length）"
                    "的方向语义待裁定；其中 5 项承重",
         "impact": "book 域级 Q 在五种方向假设下位列第 5/2/7/2/5 位，跨 5 个名次（7 域中），"
                   "Spearman 最低 0.625",
         "evidence": "methods/Q1/probes/risk_probe_summary.json#tierC_direction_sensitivity"},
        {"id": "q1_normalization_population", "owner": "human", "gate": "G2.5",
         "summary": "归一化总体口径待裁定：按域去混淆 vs 保留跨域信号",
         "impact": "按域 ecdf 使域间极差降至 0.0028（域级 Q 近乎恒等，与 Q1a 必交产出冲突）；"
                   "合并/参照 A1 使 Q 还原域标签 AUC 达 0.98-0.99",
         "evidence": "methods/Q1/probes/risk_probe_summary.json"
                     "#methods[?id=='M0'].assumption_checks"},
        {"id": "q1c_interaction_tradeoff", "owner": "human", "gate": "G2.5",
         "summary": "M1c 的交互项增益为尺度局部（1m 0.913→0.983，1B 0.705→0.658），"
                    "且系数符号稳定率降至 0.549；属 HD-2 预告的升级条款",
         "impact": "决定 Q1c 是否声明域组合效应",
         "evidence": "methods/Q1/probes/risk_probe_summary.json"
                     "#methods[?id=='M1c'].assumption_checks"},
    ]
    m["next_action"] = {
        "owner": "human",
        "skill": "decision-prompt-builder -> modeler-decision-logger",
        "reason": "G2 探针完成，三项建模判断须由使用者裁定后方可进入 G2.5",
    }
    m["gate_history"].append({
        "gate": "G2", "result": "PASSED", "at": TS,
        "basis": ["methods/Q1/q1_method_card.md",
                  "methods/Q1/probes/risk_probe_summary.json"],
        "note": "角色化清单成立，主方法与 baseline 均有证据判定，fallback 有具体触发条件；"
                "5 个候选据证据排除。CONDITIONAL 项的解除条件已登记为 blockers。",
    })
    m["eliminated_with_evidence"] = [
        "熵权法/熵权-TOPSIS 族：权重离散度完全由归一化方案决定（分位数下 max/equal=1.002 退化为等权）",
        "Q=V−P 差值式：跨零使 CV=1.44e6，负 Q 与 Q3 成本函数不相容",
        "绝对阈冲突判据 V>0.75∧P>0.75：冲突率恰为 0.0",
        "平方根变换主效应回归：训练 R²=−2.78",
        "ILR 对数比变换：511/512 行含精确零（数据阶段结论，方法卡已记录）",
    ]
    m["carried_forward_todos"] = [
        "[已解决] 域级聚合改用 Huber/截尾均值 + bootstrap 区间 —— 探针已实现，"
        "book 区间宽度为 github 的 29.6 倍",
        "[已解决] ILR 不采纳的理由已写入方法卡『考察过但排除』",
        "[已解决] 不可行候选记录违反的约束及违反程度 —— 见 eliminated_with_evidence，"
        "均附可核验指标值",
        "[已升级为人工决策] 分位数标准化的总体口径 —— 已量化两难，见 blocker "
        "q1_normalization_population",
        "[已推进] 冲突定义候选已实测：绝对阈版退化为 0.0 已排除，分位数锚定版 0.0363 / "
        "MAD 版 0.3748 / CD3 版 0.3911-0.6736 均落在开区间；最终判据留到首轮实验后的第二张决策卡",
        "[待 G3] 实验设计四件套：baseline + 主方法 + 消融 + 参数扰动（消融含合并口径归一化对照）",
        "[待论证] 4 个无 Loss 列域（nih_exporter/philpapers/enron_emails/europarl）在配比侧仅作"
        "自变量、不在目标中出现，该处理方式须在论文中论证",
        "[新增·待论证] A6–A11 的验证口径须含按尺度截距或改用秩相关 —— 原始 R² 在 60m/1B 为 "
        "−8.4/−173，但 bias 占 RMSE 98.8%/99.9%",
        "[新增·待论证] A12/A14 配比行与训练集完全重复，A12–A15 只能检验 Loss 外推，"
        "不能检验配比泛化",
        "[新增·须披露] 《数据说明》并未给出 22 指标方向标注（赛题附录 B.2 指向该处），"
        "方向表由本队按三层可信度推得",
    ]
    m["updated_at"] = TS
    MF.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    print("updated", MF)


if __name__ == "__main__":
    main()

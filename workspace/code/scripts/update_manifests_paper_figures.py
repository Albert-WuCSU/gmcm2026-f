"""把论文图（Type 3）的路径回填进四问 manifest。幂等：重跑不产生重复键。

图路径属 AGENTS.md 的 CANONICAL 变更（`figure paths`），
故本脚本同时把 `next_action` 从「做可视化」推进到「写作/G5 前置」。

用法：python workspace/code/scripts/update_manifests_paper_figures.py
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MAN = ROOT / "planning" / "manifests"
CST = timezone(timedelta(hours=8))

FIGURES = {
    "Q1": ["fig_q1_gating_stability", "fig_q1_conflict_matrix", "fig_q1_q_increment"],
    "Q2": ["fig_q2_gamma_routes", "fig_q2_domain_ratio",
           "fig_q2_cross_source_validation"],
    "Q3": ["fig_q3_optimal_path", "fig_q3_transition_definitions",
           "fig_q3_lctx_compression"],
    "Q4": ["fig_q4_channel_decomposition", "fig_q4_scale_vs_frontier",
           "fig_q4_forecast_scenarios"],
}

# 每问另有一张方法流程图
FLOW = {q: f"fig_framework_{q.lower()}" for q in ("Q1", "Q2", "Q3", "Q4")}
# 全篇共用：全文框架图与数据预处理图（登记进每一问，便于任一章写作时取用）
SHARED = ["fig_framework_overall", "fig_data_pipeline"]
FRAMEWORK_SCRIPT = "code/paper_framework_figures.py"

# 每问的下一动作：图已完成，剩写作与 G5 前置
NEXT = {
    "Q1": "论文图已出（3 张，Type 3，均通过渲染核验）。下一步：paper-section-writer 按 "
          "methods/Q1/q1_figure_table_plan.md 的章节映射写作；引用须遵守本 manifest 的 "
          "must_write_limits 与三条非正面结果。",
    "Q2": "论文图已出（3 张，Type 3，均通过渲染核验）。下一步：写作时头条结论必须同报两条路线、"
          "FAIL 进正文、beta 跨源共享表述为承重假设（见 methods/Q2/q2_figure_table_plan.md）。",
    "Q3": "论文图已出（3 张，Type 3，均通过渲染核验，33 项对拍通过）。下一步：写作时须遵守"
          "六条限制（30000 非最优上下文长度、由正转零、F4 三数同报等）。",
    "Q4": "论文图已出（3 张，Type 3，均通过渲染核验）。**待使用者决定**：Q4-F2（matplotlib）与"
          "既有 TikZ 图 fig_q4_frontier_vs_scale.tex 讲同一 claim，建议择一；另 TikZ 图需在导言区"
          "补 pgfplots，其趋势线截距已由 27.0855 修正为落盘 OLS 值 28.0897。",
}


def main() -> None:
    stamp = datetime.now(CST).replace(microsecond=0).isoformat()
    for q, names in FIGURES.items():
        p = MAN / f"{q}.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        art = d.setdefault("artifacts", {})
        changed = []
        pairs = {
            "figure_plan": [f"methods/{q}/{q.lower()}_figure_table_plan.md"],
            "paper_figures": [f"paper/figures/{n}.pdf" for n in names],
            "paper_figures_png": [f"paper/figures/{n}.png" for n in names],
            "figure_scripts": [f"code/{q}/{q.lower()}_paper_figures.py",
                               "code/figstyle.py"],
            "method_flow_figure": [f"paper/figures/{FLOW[q]}.pdf",
                                   f"paper/figures/{FLOW[q]}.png"],
            "shared_paper_figures": [x for n in SHARED for x in
                                     (f"paper/figures/{n}.pdf",
                                      f"paper/figures/{n}.png")],
            "framework_script": [FRAMEWORK_SCRIPT],
        }
        for k, v in pairs.items():
            if art.get(k) != v:
                art[k] = v
                changed.append(k)
        # Q3 另登记图的数据出处表
        if q == "Q3":
            sw = "results/Q3/experiments/round1/tables/q3_optimal_path_sweep.csv"
            if art.get("figure_source_table") != sw:
                art["figure_source_table"] = sw
                changed.append("figure_source_table")
        if d.get("next_action", {}).get("reason") != NEXT[q]:
            d["next_action"] = {"owner": "human", "skill": "paper-section-writer",
                               "target": "paper", "reason": NEXT[q]}
            changed.append("next_action")
        if changed:
            d["updated_at"] = stamp
            p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
        print(f"{q}: {'更新 ' + ', '.join(changed) if changed else '无变化（幂等）'}")


if __name__ == "__main__":
    main()

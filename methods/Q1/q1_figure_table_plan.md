# Q1 图表规划（Type 3 论文图）

**生成**：2026-09-25　**依据**：`results/Q1/reports/q1_final_result_analysis.md`、
`robustness/Q1/q1_robustness_summary.json`、`methods/Q1/q1_decisions.jsonl`（10 条裁定）

所有图的 claim 均落在已裁定范围内；数字由 `code/Q1/q1_paper_figures.py` 从落盘工件读取，
脚本内无手打结果数字。渲染核验：逐张目视复核（见各图 render 记录），矢量 PDF 供正文，
PNG 400 dpi 供预览。

| ID | 类型 | 目标章节 | 核心 claim（已裁定） | 图形式 | 源工件 | 输出 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q1-F1 | 3 | `sections/problem1.tex` | 门控合成 M1 与等权平均 M0 给出同一域序；M1 的可分辨域对数为 19–21 中的上限，权重扰动下域序更稳 | 2×2：slopegraph + 分组柱 + log-log 散点 + 抖动条带 | `tables/q1a_domain_quality.csv`、`metrics/q1_quality_{M0,M1}.json`、`robustness/Q1/q1_robustness_quality.json`（R1/R2） | `fig_q1_gating_stability.{pdf,png}` | 已出图，渲染核验通过 |
| Q1-F2 | 3 | `sections/problem1.tex` | 冲突率对判据与锚点敏感；主判据 CD2@p75 = 0.040824 落在非退化带 (0.01, 0.50) 内 | 2 联热力图（主口径 / 消融臂）+ 主判据框注 | `tables/q1b_conflict_rates.csv`、`metrics/q1_quality_M1.json#conflict_criterion_decision` | `fig_q1_conflict_matrix.{pdf,png}` | 已出图，渲染核验通过 |
| Q1-F3 | 3 | `sections/problem1.tex` | 引入域级 Q 的去偏 R² 增量在三尺度上 95% 区间均跨 0（有证据的零结果）；M1c 的增益只在 1m 尺度为正 | 分组柱 + 森林式区间图 | `tables/q1c_validation_by_scale.csv`、`tables/q1c_q_increment_test.csv` | `fig_q1_q_increment.{pdf,png}` | 已出图，渲染核验通过 |

## 未列为论文图的 Q1 资产

- `results/Q1/experiments/round1/figures/F1–F4`：Type 1/2 诊断图（`code/Q1/q1_figures.py`），
  **不进正文**，保留作内部追溯。
- 域级逐项数值（Huber / 截尾 / 中位 / 均值、两口径）宜以**表**呈现，不另作图。

## 写作提示（不改变结论口径）

- Q1-F1 的 (a) 面板只画域序，不画两法的绝对 Q 值 —— 两法量纲不同，同轴比较会误导。
- Q1-F3 的零结果是题目「是否以及如何引入 Q」的有证据回答，按 §0 的三条非正面结果如实写。
- `book ~ wikipedia` 的方向不作断言（裁定 `q1a_book_wikipedia_claim_scope`）；
  Q1-F1(a) 中该对被标为唯一互换对，正文须说明其为**不可区分**而非位次改变。

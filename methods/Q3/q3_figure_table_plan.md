# Q3 图表规划（Type 3 论文图）

**生成**：2026-09-25　**依据**：`results/Q3/reports/q3_final_result_analysis.md`、
`robustness/Q3/q3_robustness_report.md`、`methods/Q3/q3_decisions.jsonl`（9 条裁定）

`code/Q3/q3_paper_figures.py` 从 `q3_common.Model` 重算相图曲线，
`assert_canonical()` 逐项对拍落盘工件（33 项，容差 1e-9 相对 / 1e-6 口径），
**对拍不过即拒绝出图**。重算的 57 个扫描点落盘为
`results/Q3/experiments/round1/tables/q3_optimal_path_sweep.csv`，作为本组图的数据出处。

| ID | 类型 | 目标章节 | 核心 claim（已裁定） | 图形式 | 源工件 | 输出 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q3-F1 | 3 | `sections/problem3.tex` | 最优路径分两段：`Q*` 在内点分支光滑上升至 1 后保持；活跃约束集在 `log10 C` = 21.405181884765625 改变；`dQ*/dlog C` 由正转零 | 4 联共享 x 轴：`Q*`（分区着色）/ 规模路径 / 成本占比 / 饱和点导数 | `q3_optimal_path_sweep.csv`、`tables/q3_optimal_by_budget.csv`、`tables/q3_transition_definitions.csv` | `fig_q3_optimal_path.{pdf,png}` | 已出图，33 项对拍通过，渲染核验通过 |
| Q3-F2 | 3 | `sections/problem3.tex` | **定义决定结论**：定义 A 给出 21.4052（不依赖阈值/步长），定义 C 给出 22.625（依赖步长），定义 D 在阈值 0.05 下无越阈点 | 上宽下双联：`Q*` + 三定义标注 / D 的步长敏感性 / C 的占比翻转 | `tables/q3_transition_definitions.csv`、扫描重算 | `fig_q3_transition_definitions.{pdf,png}` | 已出图，渲染核验通过 |
| Q3-F3 | 3 | `sections/problem3.tex` | 跨临界 `L_ctx`（30000）显著压缩可负担规模（`N*` −54.8%、`D*` −53.4%），但 `N:D` 相对极差仅 3.22% | 三联：规模 / 配比 / 注意力成本占比 | `tables/q3_lctx_sensitivity.csv`、`metrics/q3_M1o.json#lctx_sensitivity` | `fig_q3_lctx_compression.{pdf,png}` | 已出图，渲染核验通过 |

## 必须在正文（非图内）承担的口径

1. `L_ctx_crit` = 30000 **仅为两类成本相等的临界尺度，不是最优上下文长度**。
2. 准确表述为「跨临界显著压缩可负担规模，几乎不改变相对配比」，**而非**「最优配置显著偏移」。
3. 不得笼统写「各档预算最优质量恒为 1」——`C` = 1e19 档 `Q*` 为 0.6460。
4. 饱和点导数**由正转零**（上游方法卡的「由负转零」是符号错误，不得沿用）。
5. `1e24` 是外推；Chinchilla 不构成外部锚点。
6. F4：baseline 维持 `M0o`（`D/N` = 20），**正文须三数同报** handicap 占比
   32.10 % / 27.66 % / 34.01 %。

## 未列为论文图的 Q3 资产

- `diag_q3_optimal_path.png`、`diag_q3_definitionD_grid_sensitivity.png` 为 Type 1 诊断图
  （`run_all.py` 生成），**不进正文**；Q3-F1/F2 是其论文级重制。
- 三档锚点解、KKT 五项判据、成本函数三类的对照数值以**表**呈现。

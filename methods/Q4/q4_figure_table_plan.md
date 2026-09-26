# Q4 图表规划（Type 3 论文图）

**生成**：2026-09-25　**依据**：`results/Q4/reports/q4_final_result_analysis.md`（§5.4、§9.3）、
`robustness/Q4/q4_robustness_report.md`、`methods/Q4/q4_decisions.jsonl`（6 条裁定）

数字由 `code/Q4/q4_paper_figures.py` 从落盘工件读取；脚本内不出现手打结果数字。

| ID | 类型 | 目标章节 | 核心 claim（已裁定） | 图形式 | 源工件 | 输出 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q4-F1 | 3 | `sections/problem4.tex` | 窗口内能力提升约 **5.4865–6.6592** 点（10 个口径极差）；技术通道在全部口径下为正，规模通道符号随口径翻转 | 上：8+2 口径堆叠条 + 合成总提升菱形；下：分组份额区间 | `q4_endpoint_sensitivity.csv`、`q4_spec_sensitivity.csv`、`q4_trend_method.json`、`q4_by_type_group.csv` | `fig_q4_channel_decomposition.{pdf,png}` | 已出图，渲染核验通过 |
| Q4-F2 | 3 | `sections/problem4.tex` | 同期 `N_q90` 由 46.703 降至 14.770（端点比值 3.162×），而前沿 `S_q90` 由 25.9201 升至 41.3875（斜率 +1.5333/月） | 双联：规模四分位（对数）+ 前沿趋势 | `q4_N_and_frontier_by_month.csv`、`n_frontier_meta.json` | `fig_q4_scale_vs_frontier.{pdf,png}` | 已出图，渲染核验通过 |
| Q4-F3 | 3 | `sections/problem4.tex` | 三情景 h12/h24 预测与 **baseline M0a** 对照（主方法 h12 中位 56.330 < baseline 点 60.290）；情景极差随规模份额缩放 11.786 → 4.1408 → 0 | 双联：情景区间图（含 baseline 与当前前沿线）+ 极差缩放 | `q4_frontier_scenarios.csv`、`metrics/q4_M0a.json`、`q4_scenario_spread_scaling.csv` | `fig_q4_frontier_scenarios.{pdf,png}` | 已出图，渲染核验通过 |
| Q4-F4 | 3 | `sections/problem4.tex` | 与 Q4-F2 同 claim 的 TikZ 向量版 | pgfplots 双轴（左 `N` 分位 / 右 `S_q90`） | 同 Q4-F2 | `fig_q4_frontier_vs_scale.tex` | **与 Q4-F2 重复，待使用者择一**；本机无法编译 TeX，未做渲染核验 |

## 待使用者决定的一处（AI 不代选）

**Q4-F2 与 Q4-F4 讲同一个 claim**（规模下行 + 前沿上行）。二者择一即可：

- 保留 **Q4-F2**（matplotlib）：已通过渲染核验，与其余 11 张图同一视觉系统，直接 `\includegraphics`。
- 保留 **Q4-F4**（TikZ）：向量排版更贴合正文，但需在导言区加 `\usepackage{pgfplots}` +
  `\pgfplotsset{compat=1.18}` + `\usetikzlibrary{patterns}`（现 `gmcm2026.cls` 只 `\RequirePackage{tikz}`），
  且**截距已修正**（原 27.0855 与落盘 OLS 拟合 28.0897 不符，已改为 28.0897）。

两图并存会构成重复叙述，建议只留一张。

## 必须在正文（非图内）承担的口径

1. **26%/74% 及任何百分比分割已作废** —— 图内只显示份额区间，不得作点主张；
   `pretrained` 组能力回落且不可给占比，`chat_finetuned` 组规模份额区间含 0。
2. 预测表**必须同表列出 baseline 60.290**；预测维度主方法**未打赢** baseline
   （56.330 vs 60.290，95% 宽度 41.935 vs 11.750）。
3. 预测判据 PASS 系修 bug 所致且裕度仅 1.881 点。
4. `tau` 只能写「非规模技术/数据工程综合进步」。
5. `N` 下降倍数**两种不可混用**：端点比值 3.162（图内采用）与斜率隐含值 3.675。

## 未列为论文图的 Q4 资产

- `q4_bridge_tiers.csv`、`q4_M0a.json` 的结构性限制说明以文字/表呈现。

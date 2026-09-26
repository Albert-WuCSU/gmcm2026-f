# 全篇框架图 / 数据预处理图 / 四问方法流程图（Type 3）

**生成**：2026-09-25　**脚本**：`code/paper_framework_figures.py`
**风格**：计算机顶会 / 美赛 pipeline figure —— 圆角盒 + 浅色填充 + 阶段色 + 正交布线，
全部矢量 PDF，中文 Microsoft YaHei。

## 图清单

| ID | 目标章节 | 内容 | 输出 | 状态 |
| --- | --- | --- | --- | --- |
| FW-1 | `sections/problem.tex` 或 `analysis.tex` | **全文框架图**：数据层（A/B/C 三组附件，映射 18/13/4/8）→ Q1→Q2→Q3→Q4 链（各含方法要点）→ 论文结论 → 证据链与审计 | `fig_framework_overall.{pdf,png}` | 已出图 |
| FW-2 | `sections/problem.tex`（数据描述段） | **数据预处理**：40 个原始附件（551 MB，只读）→ 按问映射 → 规范化与清洗 → 落盘核验；下附数据审计关键发现 | `fig_data_pipeline.{pdf,png}` | 已出图 |
| FW-3 | `sections/problem1.tex` | Q1 方法流程：规范化 → 语义分组 → 门控合成 → 冲突判据 → 配比与对照 | `fig_framework_q1.{pdf,png}` | 已出图 |
| FW-4 | `sections/problem2.tex` | Q2 方法流程：多源整备 → 退化检验 → 联合拟合 → 交叉源验证 → 条件化检验 | `fig_framework_q2.{pdf,png}` | 已出图 |
| FW-5 | `sections/problem3.tex` | Q3 方法流程：目标与成本 → 三类 $g(Q)$ → 分段 KKT → 活跃集扫描 → 三定义与敏感性 | `fig_framework_q3.{pdf,png}` | 已出图 |
| FW-6 | `sections/problem4.tex` | Q4 方法流程：窗口与样本 → 规模通道 → 技术通道 → 端点多规格 → 情景与对照 | `fig_framework_q4.{pdf,png}` | 已出图 |

## 数字出处（脚本内不手打）

- 附件数 / 体积 / 分问映射 / 覆盖行数：`workspace/data/data_profile.json`
- 规范化后行数：`workspace/data/q1_canonical_verification.json`
- $\gamma$ 双路线：`workspace/data/q2_probe_beta_sharing.json`
- Q3 转移点与 $L_{\mathrm{ctx}}$ 三项百分比：`results/Q3/experiments/round1/metrics/q3_M1o.json`
- Q4 总提升极差与端点比值：`results/Q4/experiments/round2/metrics/q4_trend_method.json`、
  `n_frontier_meta.json`

## 图内不含的内容（写在正文或图注）

按使用者要求，**图内只放数据与结果**，不出现「不得表述为……」「判 FAIL」这类
报告口吻的告诫。以下材料改由正文承担：

- 各问的口径限制与写作红线（见各问 figure_table_plan 的「必须在正文承担的口径」）。
- GC5 半合成披露、AMB-Q2-3 尺度未对齐、Q4 百分比分割作废等。
- FW-5 的 Q3 三档锚点解与 $N{:}D$ 极差已在图内，但「30000 非最优上下文长度」
  与「饱和点导数由正转零」只在正文写。

## 布局参数（便于后续微调）

- 画布：宽 6.3 in（模板 `\linewidth` = 469.47 pt ≈ 6.52 in，故正文中放大约 3.5%）。
- 字号：标题 6.0–6.6 pt，正文 5.5–5.6 pt；行距由 `_upp()` 按画布高度换算，
  与字号解耦，改画布高度不会压字。
- 阶段色见脚本 `STAGE`：同一阶段在六张图里同色。

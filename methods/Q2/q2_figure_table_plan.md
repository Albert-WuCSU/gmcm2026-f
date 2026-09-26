# Q2 图表规划（Type 3 论文图）

**生成**：2026-09-25　**依据**：`results/Q2/reports/q2_final_result_analysis.md`（§4.3）、
`robustness/Q2/q2_robustness_report.md`、`methods/Q2/q2_decisions.jsonl`（11 条裁定）

数字由 `code/Q2/q2_paper_figures.py` 从落盘工件读取；脚本内 `assert_canonical()`
交叉核对 P9 探针与 G4 补算工件，不一致即拒绝出图。

| ID | 类型 | 目标章节 | 核心 claim（已裁定） | 图形式 | 源工件 | 输出 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q2-F1 | 3 | `sections/problem2.tex` | `gamma` 的取值**依赖 `beta` 的来源假设**：`beta` 取自 B1 时 γ = 0.9659（CI 含 1.0），`beta` 在 B7 自由时 γ = 1.1798（CI 不含 1.0）；位移为区间宽的 1.246 倍（阈 0.5） | 双联区间图：左 γ 双路线，右 β 辨识缺口 | `workspace/data/q2_probe_beta_sharing.json`、`robustness/Q2/q2_robustness_supplement.json` | `fig_q2_gamma_routes.{pdf,png}` | 已出图，渲染核验通过 |
| Q2-F2 | 3 | `sections/problem2.tex` | 17 个 Pile 域的 `b_i/b_ref` 有方向性结构：dm_mathematics 是唯一 `|比值| > 1` 的域 | 发散条形图（按 b 值排序，零线 + 参考域标记） | `tables/q2_domain_ratio.csv` | `fig_q2_domain_ratio.{pdf,png}` | 已出图，渲染核验通过 |
| Q2-F3 | 3 | `sections/problem2.tex` | 三个外部源（真实 / 文献 / 半合成）均复现本律（Spearman 0.788–0.983）；弹性符号在 B1 与 B7 两臂一致 | 双联：来源棒棒糖图 + 弹性对照条 | `tables/q2_validation.csv`、`tables/q2_elasticity.csv` | `fig_q2_cross_source_validation.{pdf,png}` | 已出图，渲染核验通过 |

## 必须在正文（非图内）承担的口径

图内**只放数据与数值**，以下解读/限制全部写在正文，不得省略：

1. **Q2 头条结论的条件化**：两路线必须同报（裁定 `q2_claim_scope_conditioned_v2` 四禁令）；
   不得改为只报 `beta*gamma`；`beta` 跨源共享须表述为**承重假设**。
2. **GC5**：Q2-F3 中的半合成源（Cerebras 轨迹）在图内仅标注来源性质，
   正文须披露其**不得表述为直接观测**。
3. **AMB-Q2-3** 尺度未对齐的披露。

## 未列为论文图的 Q2 资产

- `q2_params.csv`、`q2_elasticity.csv` 的逐项数值以**表**呈现更合适；
  Q2-F3(b) 只承担「符号一致」这一点，数值表另出。

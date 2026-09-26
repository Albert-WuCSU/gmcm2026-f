export const meta = {
  name: 'gmcm-f-paper-draft',
  description: 'Draft the four problem sections of the GMCM2026 F paper, each with independent number verification against landed artifacts',
  phases: [
    { title: '文献核验', detail: '检索并核验参考文献，产出可用 BibTeX' },
    { title: '起草', detail: '每问一节，读源工件撰写正文与图表' },
    { title: '数字核验', detail: '逐数字对拍落盘工件，并检查口径红线' },
    { title: '修订', detail: '按核验结论修订正文' },
    { title: '全篇一致', detail: '跨节符号、编号、引用与口径一致性' },
  ],
}

const TODAY = args && args.today ? args.today : '2026-09-26'

// ---------------------------------------------------------------- style
const STYLE = String.raw`
【写作契约 —— 逐条遵守】

一、语体（这是硬要求：读者是竞赛评审专家，必须读起来像人写的学术论文）
1. 中文书面学术语体，第三人称。主语用「本文」「该模型」「本节的判据」等；「我们」至多偶用，
   不要每段主语都是「我们」。
2. 禁止 AI 腔与套话。下列表达一律不得出现（除非有确切技术含义）：
   「值得注意的是」「综上所述」「总而言之」「不难发现」「众所周知」「深入探讨」「赋能」
   「闭环」「抓手」「维度上」「全方位」「极大地」「有效地」「具有重要意义」「提供了有力支撑」
   「在……的大背景下」「首先……其次……最后……」式的三段式排比罗列。
3. 段落靠内容推进，不要用项目符号列表代替论述。技术要点写成连贯的段落。
4. 句式长短交替，避免每句等长、每段同构。
5. 术语首次出现给中英文对照，如「标度律（scaling law）」「弹性（elasticity）」。
6. 数字与单位：首次出现给出单位；位数取源工件精度，做四舍五入时要说明。

二、学术规范
7. 每条结论后写清成立条件。不确定的结论用「在……范围内」「在该口径下」「与……不可区分」
   「不构成……的证据」等限定语，不做无条件断言。
8. 与 baseline 的比较必须同口径、同表列出，不得只报主方法。
9. 半合成 / 外推 / 估算 / 插值数据（B2、B3、B6、B7、B8、B10、A12–A15）在首次使用处
   必须标明性质，不得表述为直接实验观测。
10. 绝不使用「判 FAIL」「红线」「不得表述为」「承重假设……禁止」这类工作流报告口吻。
    要改写成学术化的局限陈述，例如：
    「该检验在预声明口径下未通过（γ 的位移达其区间宽的 1.25 倍），故下方结论以该共享假设为前提」
    「两路线的比较对象不一致，故本节不据此判定优劣」。
11. 文献依据处用 \citep{key} 或 \citet{key} 引用，分散在正文相关位置；不要在一处堆砌多篇。

三、LaTeX 约定（模板已加载全部宏包，禁止写 \usepackage / \documentclass / \begin{document}）
- 章节：\section{...}\label{sec:...}，下一级 \subsection{...}，再下一级 \subsubsection{...}
- 图：
  \begin{figure}[htbp]
    \centering
    \includegraphics[width=0.92\linewidth]{figures/fig_xxx.pdf}
    \caption{图题（写清横纵轴与关键读数，不写工作流口吻）}
    \label{fig:xxx}
  \end{figure}
  正文必须用 图~\ref{fig:xxx} 引用它。禁止使用 [H] 浮动选项。
- 表：
  \begin{table}[htbp]
    \centering
    \caption{表题}\label{tab:xxx}
    \begin{tabular}{@{}lcc@{}}
      \toprule
      ... \\ \midrule
      ... \\ \bottomrule
    \end{tabular}
  \end{table}
  用 booktabs 三线表，不要竖线，表题在表上方，正文必须用 表~\ref{tab:xxx} 引用。
- 公式：\begin{equation}...\label{eq:xxx}\end{equation}；多行用 align；编号只在正文引用处保留。
- 可用宏包：amsmath、amssymb、amsthm、bm、graphicx、booktabs、multirow、array、tabularx、
  caption、subcaption、enumitem、algorithm、algpseudocode、listings、natbib、hyperref。
- 定理类环境可用：theorem / lemma / definition。
- 图文件只从给定清单里取，不要臆造文件名。
`

// ---------------------------------------------------------------- per-question briefs
const QS = [
  {
    id: 'Q1',
    file: 'paper/sections/problem1.tex',
    heading: '问题一：数据质量评价、冲突消解与领域配比建模',
    report: 'results/Q1/reports/q1_final_result_analysis.md',
    robustness: 'robustness/Q1/q1_robustness_summary.json',
    plan: 'methods/Q1/q1_figure_table_plan.md',
    csvs: [
      'results/Q1/experiments/round1/tables/q1a_domain_quality.csv',
      'results/Q1/experiments/round1/tables/q1b_conflict_rates.csv',
      'results/Q1/experiments/round1/tables/q1c_validation_by_scale.csv',
      'results/Q1/experiments/round1/tables/q1c_q_increment_test.csv',
    ],
    metrics: [
      'results/Q1/experiments/round1/metrics/q1_quality_M0.json',
      'results/Q1/experiments/round1/metrics/q1_quality_M1.json',
      'results/Q1/experiments/round1/metrics/q1_mixture_M0c.json',
      'results/Q1/experiments/round1/metrics/q1_mixture_M1c.json',
    ],
    figures: [
      'figures/fig_framework_q1.pdf',
      'figures/fig_q1_gating_stability.pdf',
      'figures/fig_q1_conflict_matrix.pdf',
      'figures/fig_q1_q_increment.pdf',
    ],
    limits: [
      '样本量：全量 A1+A2+A3 为 272 486 / 272 505 行（99.993%），剔除 19 行整条 6 维 NaN（A1 18 条 + A3 1 条）。',
      'CANONICAL 预处理为 20 列（22 指标中 dsir 三列合一），pooled + 经验分位数为主口径，per_domain 为消融臂。',
      '《数据说明》并未给出 22 指标的方向标注（赛题附录 B.2 指向该处，但该 PDF 可见文本中无方向说明），方向表由本队按三层可信度推得。这条必须写进局限。',
      'Tier C（方向不确定）的承重项由本队裁定并报敏感性；ad_en / fluency_en 的 margin = pos1 − pos0 本身已是「越高越好」，不需补转换。',
      '必须报统计上不可区分：book 与 wikipedia 的域级 Q 差值 0.00617（M0）/ 0.01113（M1），方向随合成方式反转，裕度仅 1.12 倍区间和，因此不对二者先后作断言。',
      '不得声称 arxiv 是质量最高的域。可报的是最高一档为 {arxiv, c4, commoncrawl}（9 个配置下不变）；arxiv 在档内位次依 V/P 分组的单列归属而变（实测取到 1/2/3）。',
      'c4 优于 commoncrawl（裕度 4.37 倍）与 github 居末在全部变体下成立，可照常报方向。',
      '域序为 arxiv > c4 > commoncrawl > stackexchange > book > wikipedia > github（M1, Huber, pooled）。该域序不符直觉，判断为部分真实（22 个指标都是现代网页文本训练的分类器，book 域 n=171 的 19 世纪 Gutenberg 文本在现代可读性/整洁度打分上本就吃亏），应作为局限写出，不得靠调方向去修。',
      '单一标量 Q 高度可由域标签分离（AUC 0.9486）；这不是本规格新引入的缺陷（25 个候选标量中 15 个近乎完美分离 arxiv 与 github）。应表述为可证的限制：在这批指标上，单一标量 Q 不可能同时做到跨域可比与域去混淆。',
      'Q 增量检验是零结果，必须如实写入，并说明成因是构造性相关（Q_corpus 本身是 p 的函数；17 个配方域中仅 6 个有质量域对应，映射域配比质量中位仅 0.5995；512 训练行中 5 行映射质量为 0 已剔除，A/B 在同一 507 行子集上拟合）。这是对题目「是否以及如何引入 Q 由参赛队伍论证」的有证据回答。',
      'Q 增量零结果在 1B 尺度上须 B≥4000 才可判定（B=400 下该格上界蒙特卡洛极差 1.40e-4 大于上界离零距离约 5e-5，不可判定）；三尺度区间均含 0 这一表述成立，但须注明成立条件是 B≥4000、n=64。',
      '配比侧以 M0c 为主、M1c 作组合效应辅证；M1c 的增益只在 1m 尺度为正（+0.0703），60m 为 −0.0050、1B 为 −0.0464，不构成跨尺度优势。',
      '禁止报未去偏的原始 R²：60m/1B 的原始 R² 为 −8.412 / −173.115，但 bias 占 RMSE 的 98.8% / 99.9%，去尺度偏移后回到 0.771 / 0.705。须写「配比→Loss 的形状跨尺度可迁移，只有水平随规模平移」。',
      'M1c 只报符号稳定率 ≥0.95 的项（84/153，其中主效应 17/17、交互 ≥0.95 共 67 项、≥0.99 共 53 项）；稳定子集外的单个交互系数不得解释为域间替代或互补。',
      '目标 pweighted13 把 p 同时置于等式两侧，存在部分循环，须在正文声明，并说明域效应的量级排序依赖目标口径（两口径系数向量 Spearman −0.5809）。',
      'rps_doc_frac_unique_words 与 rps_doc_unigram_entropy「这一对」受长度反向混淆（对 log word_count 的 Spearman 分别为 −0.85 与 +0.95），须成对写出，不得只点前者。',
      'A18 文本统计量由本队自算，A1–A3 的 22 指标是数据集自带的模型打分，两者不同源，只能作趋势/秩一致性对照，绝对值不可比。',
      'A12–A15 为外推/子集，仅支持定性讨论；A12/A14 的配比行与训练集重复率 1.0，不能检验配比泛化。',
      '三条稳健性 FAIL 性质不同，不得笼统表述为「稳健性检查通过/未通过」：R4 是真发现（claim 已收窄）；R6 是自助次数不足（B=400 下该格不可判定）；R7 是判据设计失效（系数符号一致率 1.000 是平凡结果——目标是 Loss、设计矩阵去截距、Σp=1 ⇒ 每个系数即该域的 Loss 水平，必然全正；真信息是系数量级排序反转）。',
    ],
    extra: String.raw`
本节要交代清楚：① 22 个原始指标如何统一方向（含 dsir 三列的长度效应与合并、三个长度类指标的非单调处理、
五个污染类指标的 1−z、截尾而非字面 Min-Max 的理由）；② 门控合成 Q = V·(1−P) 的构造与它相对等权平均的
优势所在；③ 冲突判据 CD2 的定义（高价值 ∧ 高污染，双锚点 p75）与锚点敏感性；
④ 域级 Q 的聚合方式（Huber M 估计 k=1.345，B=400 自助 95% 区间）与域序稳健性；
⑤ 配比侧的线性基线与其二阶交互扩展、跨尺度验证、以及 Q 增量零结果。
小节划分自行安排，建议 5–6 个 \subsection。
篇幅：正文约 3200–4200 个汉字 + 4 图 + 4 表。
`,
  },
  {
    id: 'Q2',
    file: 'paper/sections/problem2.tex',
    heading: '问题二：跨维度数据融合与广义标度律',
    report: 'results/Q2/reports/q2_final_result_analysis.md',
    robustness: 'robustness/Q2/q2_robustness_report.md',
    plan: 'methods/Q2/q2_figure_table_plan.md',
    csvs: [
      'results/Q2/experiments/round1/tables/q2_params.csv',
      'results/Q2/experiments/round1/tables/q2_elasticity.csv',
      'results/Q2/experiments/round1/tables/q2_validation.csv',
      'results/Q2/experiments/round1/tables/q2_domain_ratio.csv',
    ],
    metrics: [
      'results/Q2/experiments/round1/metrics/q2_M1s.json',
      'results/Q2/experiments/round1/metrics/q2_M0s.json',
    ],
    figures: [
      'figures/fig_framework_q2.pdf',
      'figures/fig_q2_gamma_routes.pdf',
      'figures/fig_q2_domain_ratio.pdf',
      'figures/fig_q2_cross_source_validation.pdf',
    ],
    limits: [
      '主方法 L = E_s + A·N^(−α) + B·(D·Q^γ·exp(bᵀz_p))^(−β)，E_s 来源专属。',
      '三项预声明判据全过：B1 退化相对差 1.0122e−08 < 1e−6；B7 超越性降幅 0.041868，CI95 [0.036236, 0.047781] 不含 0；弹性符号两侧成立。',
      '判据 1 是「退化检验」而非「主方法超过 baseline 的性能比较」，不得写成后者。',
      '判据的替换必须写清时序与方向：方法卡原预声明指标第 1 条「B1 留出集 RMSE」结构性失效（B1 无配比列 ⇒ z_p = 0；B1 无 Q 变化 ⇒ Q 为常数 ⇒ M1s 塌为与 M0s 同形同自由度），故改为退化检验、超越性比较移到 B7。该修正发生在代码生成之前、方向为收紧。不得只写「把判据挪到了 B7」。',
      'γ 的头条结论必须条件化并同报两条路线：在 B7 设计刻度上、且 β 取自 B1（0.279878）这一前提下，γ = 0.9659128，CI95 [0.8838600, 1.0555462] 含 1.0 ⇒ D_eff ≈ D·Q；若 β 在 B7 上自由估计，γ = 1.1797810，CI95 [1.0884410, 1.2833591] 不含 1.0，且 B7 rmse 由 0.076384 降到 0.069544（放开 β 反而更好 9%）。',
      'β 跨源共享的检验未通过：γ 位移 0.213868 = 其自助区间宽的 1.245692 倍；B1 的 β 落在 B7 自估 β 的区间之外。取 B1 的 β 的理由（B1 的 CI 宽 1.163e−04、1176 行、D 跨 0.1–299.9B；B7 只有 5 个不同 D 取值且 D 与 N 在设计上纠缠）不构成该检验未发生。',
      '不得改为只报 β·γ 以回避条件性：该量同样路线依赖（0.270396 vs 0.097985，差 2.76 倍）。',
      '超越性证据完全建立在半合成 B7 上（B 侧仅 B6/B7/B8 含 Q 变化且全部半合成），首次使用处须标明。',
      'p 的跨源统一假设不可检验且承重：11 个 B 文件无一含配比列（0/11）；A 侧三尺度中仅 1B 落入 B1 的 [0.070542, 11.965825]B 区间。',
      '尺度对齐未解决：Q1 的经验域级 Q 落在 [0.223306, 0.381496]，而 B7 设计网格 Q 为 {0.1, …, 1.0}，二者不是同一对象，γ 的解释绑定在 B7 的设计刻度上，不能直接代入 Q1 的经验 Q。',
      '联合 WLS 在数值上退化为「B1 定 β、B7 定 γ」的两段式（γ 差 1.03e−7、β 差 6.86e−8），不得表述为「联合拟合提升了估计」。',
      '弹性比恒等式：采用 D_eff = D·Q^γ 时 elasticity_ratio_Q_over_D 恒等于 γ（两侧相对差 0.0000，ptp < 1e−12）。因此不得同时声称「Q 与 D 的替代率随位置变化」，只有 Q↔N 随位置变化。',
      '禁止报跨源未去偏的 R²。跨源验证只报秩相关与去源偏后 RMSE（B4 n=57 ρ=0.982982；B5 n=44 ρ=0.958808，为文献值、他人发表、非本队观测；B2 n=1029 ρ=0.788102，为半合成轨迹，不得表述为直接观测的迁移验证）。',
      'Q + 0.1 等价 N 增量须带参照点报且两侧同报：参照点 N = 1.0B、D = 150.0B、Q = 0.5；B1 侧 −0.134101、B7 侧 −0.094469。符号为负表示提质可减少参数量。',
      'kappa 在 B 侧严格不可辨识（实测 RMSE 随 kappa 变化恰为 0.0）且随参照点变（B1 的 1B run 内从 −14.2151 到 −1.6413，差 8.7 倍），不存在普适 kappa；任何绝对量级须带参照点。',
      'b 的方向只报排序与符号：dm_mathematics 是全表唯一 |比值| > 1 的域（−1.618816），其余 16 个域 |比值| 均不大于 1。该值语义是「中心化 w 之比，非有界比例」，负值表示 upweight 该域会降低 Loss。',
      '禁止把 G2 探针阶段的 2.0000 当作本轮弹性比估计（那是 B6 上的早期拟合值）。',
      'B1 拟合异常干净（R² = 0.9999998，RMSE = 1.465e−04），使用者对 B1 的处理附加了须谨慎的约束，该约束尚未裁定，须作为局限声明。',
      'σ_s 的取值方式为未确认的提案（本轮取残差口径，B7 总权重份额 1.4075e−06），不得写成「经使用者裁定」。',
    ],
    extra: String.raw`
本节要讲清：① 广义标度律的设计动机（Q=1 且 z_p=0 时退化为经典形式；Q 以乘性有效 token 数进入；
p 经 exp(bᵀz_p) 进入）与单位一致性；② 参数辨识顺序（β 由 B1 钉住、γ 由 B7 反解）及其理由；
③ 三项预声明判据；④ γ 的双路线结论与 β 共享假设的检验；⑤ 边际效用、弹性与 Q↔N 的等价条件；
⑥ 域间关系（b 的排序、kappa 的不可辨识）；⑦ 跨源验证。
小节划分自行安排，建议 5–6 个 \subsection。
篇幅：正文约 3200–4200 个汉字 + 4 图 + 3 表。
`,
  },
  {
    id: 'Q3',
    file: 'paper/sections/problem3.tex',
    heading: '问题三：算力约束下的多维资源联合优化与结构性转移',
    report: 'results/Q3/reports/q3_final_result_analysis.md',
    robustness: 'robustness/Q3/q3_robustness_report.md',
    plan: 'methods/Q3/q3_figure_table_plan.md',
    csvs: [
      'results/Q3/experiments/round1/tables/q3_optimal_by_budget.csv',
      'results/Q3/experiments/round1/tables/q3_transition_definitions.csv',
      'results/Q3/experiments/round1/tables/q3_cost_form_comparison.csv',
      'results/Q3/experiments/round1/tables/q3_lctx_sensitivity.csv',
      'results/Q3/experiments/round1/tables/q3_baseline_gap_decomposition.csv',
      'results/Q3/experiments/round1/tables/q3_dldp_direction.csv',
    ],
    metrics: [
      'results/Q3/experiments/round1/metrics/q3_M1o.json',
      'results/Q3/experiments/round1/metrics/q3_M0o.json',
    ],
    figures: [
      'figures/fig_framework_q3.pdf',
      'figures/fig_q3_optimal_path.pdf',
      'figures/fig_q3_transition_definitions.pdf',
      'figures/fig_q3_lctx_compression.pdf',
    ],
    limits: [
      '优化模型：min E + A·N^(−α) + B·(D·Q^γ)^(−β)  s.t. k·N·D + D·[g(Q) − g(Q0)]_+ ≤ C，k = 6 + η·L_ctx。决策变量 3 个（p 由前两问固定 z_p = 0），KKT 维度 3。',
      '上游标度律参数取自 Q2 的 B1 侧（相对差 < 1e−15），评审已显式核对未误取 B7 侧 E。',
      'p 未联立优化：G2 探针实测 bᵀz_p 对 p 线性 ⇒ 单纯形上最优在顶点，最大分量 0.9999999999999927（全给 dm_mathematics）。故固定 p，只报 dL/dp 的符号与排序，不报 p*、不报绝对量级。',
      '必须分段 KKT 的理由：9 个「预算 × 成本函数」组合中 Q* 落在内点的只有 2 个（C=1e19 的指数型 0.6460175、幂型 0.5390440），其余 7 个顶到上界 1.0。',
      'L_ctx^crit = 6/η = 30000 只是两类成本相等的临界尺度，不是最优上下文长度。',
      '跨临界的准确表述是「显著压缩可负担规模，几乎不改变相对配比」：N* 由 5.6475B 降到 2.5507B（−54.8351%）、D* 由 249.0624B 降到 116.1159B（−53.3788%），而 N:D 相对极差仅 3.22%。',
      '不得笼统写「各档预算最优质量恒为 1」：C = 1e19 档的 Q* 为 0.6460175（指数型）与 0.5390440（幂型）。',
      '饱和点处 dQ*/dlog C 由正转零：饱和前 0.1482887 → 0.1499612，跨饱和点的 21.375→21.5 那段 0.0362859 须单列排除，21.625 及以后为 0。',
      'C = 1e24 档是外推：N 相对 B1 观测上界 3.4060×、D 12.5743×，不得表述为可靠预测。',
      'Chinchilla 对照不构成外部锚点（本律 B1 侧参数与 Chinchilla Approach-3 常数按十亿单位折算后数值同一，相对差 9.4e−6 ~ 4.4e−4，以其对照本律等于自证），且该常数未经原文核验。',
      '本律隐含 D/N 随预算漂移而非常数 20：79.59104144631574 / 155.5004609503274 / 243.02074222002932（漂移指数 0.0969558）。把 20 当硬判据会拒绝本律自身的真最优解。',
      'baseline 为 M0o（Chinchilla 经验配置，固定 D/N = 20、Q = Q0 不投质量）。三数必须同报：gap_reported / gap_quality_only / gap_ratio_handicap，handicap 占报告差距 32.1032% / 27.6584% / 34.0083%。成因是 M0o 的 D/N 被强制为 20，而本律自身的无质量投入最优比值不同。M0o′ 是诊断参照（其 loss 与 M1o 的 lower_Q_eq_Q0 分支全位相同），不得作为官方 baseline 报出。',
      'Q0 = 0.35 未经裁定。实测在 [0.223306, 0.381496] 内扫动时 Q* 极差仅 0.011712、转移位置移动 0.005981（non-load-bearing in tested range），但该取值本身未经裁定的状态不变，须声明。',
      '第四类 g(Q) 的三个候选只作分析、不进入主结论：饱和指数型与 Hill 型（有界型）使 Q* ≡ 1、无结构性转移（会消灭核心发现）；二次型产生双侧转移，但单谓词二分定位不了左事件（返回 nan），且左支依赖未裁定的 Q0。不得表述为「给定的三类 g 是最优选择」，只能说它们不被这两个方向的改进所取代。',
      '结构性转移三定义三答案，必须写明主定义是哪一个：定义 A（活跃约束集变化，主）位置 log10 C = 21.405181884765625，不依赖阈值与步长；定义 C（成本分项占比排序变化）位置 22.625，依赖步长；定义 D（分配份额突变，delta = 0.05）判不出（步长 0.5 时翻转）。合读结论：转移存在，形态为连续饱和而非突跳。',
      'KKT 五项硬判据三档锚点 + 57 点扫描全过；三条独立核验：中心差分重建相对残差 < 3.3e−8、邻域 4000 次采样无更优者、差分进化相对差 −1.35e−14 / −2.85e−14 / −6.53e−14 ⇒ 分支枚举完备，fallback M2o 休眠。',
      'dL/dp 的域间排序只报符号与排序，因 dL/dp_i ÷ dL/dp_j = b_i/b_j 与 kappa 无关；该排序与 Q2 的域比值表同源（两者都源自 Q1 的 w），不构成独立佐证，仅作内部一致性检查。',
      '禁止声称 Chinchilla 对照构成外部锚点。',
    ],
    extra: String.raw`
本节要讲清：① 优化模型的目标、三类成本函数与预算约束的构成；② 为什么必须分段 KKT（内点段 + Q=1 边界降维段）
以及 KKT 约减得到的解析结构（R1）α·A·N^(−α)·(k·N + Δg) = β·B·S^(−β)·k·N 与 (R2) γ·(k·N + Δg) = Q·g′(Q)，
并解释 (R2) 不含 λ 与 D 这一点如何与由 ∂N 独立求 λ 互为交叉验证；③ 三档锚点解与最优性核验；
④ 结构性转移的三种数学定义与识别方法，以及「定义决定结论」这一发现的含义；
⑤ 成本函数选择的影响（集中在低预算档）与题目「或改进」部分的回答；⑥ L_ctx 跨临界的敏感性；
⑦ 与 baseline 的对照及差距构成分解；⑧ 领域配比的边际方向。
小节划分自行安排，建议 6–7 个 \subsection。
篇幅：正文约 3400–4400 个汉字 + 4 图 + 5 表。
`,
  },
  {
    id: 'Q4',
    file: 'paper/sections/problem4.tex',
    heading: '问题四：技术演进分析与前沿预测',
    report: 'results/Q4/reports/q4_final_result_analysis.md',
    robustness: 'robustness/Q4/q4_robustness_report.md',
    plan: 'methods/Q4/q4_figure_table_plan.md',
    csvs: [
      'results/Q4/experiments/round1/tables/q4_spec_sensitivity.csv',
      'results/Q4/experiments/round1/tables/q4_by_type_group.csv',
      'results/Q4/experiments/round1/tables/q4_frontier_path.csv',
      'results/Q4/experiments/round1/tables/q4_frontier_scenarios.csv',
      'results/Q4/experiments/round1/tables/q4_bridge_tiers.csv',
      'results/Q4/experiments/round2/tables/q4_endpoint_sensitivity.csv',
      'results/Q4/experiments/round2/tables/q4_N_and_frontier_by_month.csv',
      'results/Q4/experiments/round2/tables/q4_scenario_spread_scaling.csv',
    ],
    metrics: [
      'results/Q4/experiments/round1/metrics/q4_M1a.json',
      'results/Q4/experiments/round1/metrics/q4_M0a.json',
      'results/Q4/experiments/round2/metrics/q4_trend_method.json',
    ],
    figures: [
      'figures/fig_framework_q4.pdf',
      'figures/fig_q4_channel_decomposition.pdf',
      'figures/fig_q4_scale_vs_frontier.pdf',
      'figures/fig_q4_forecast_scenarios.pdf',
    ],
    limits: [
      '总体界定为 Open LLM Leaderboard 投榜模型（不是模型总体）；窗口 2024-06 → 2025-03，278 天 ≈ 9.1 个月；可用行 4561。综合能力 S 取 C1 的 Average，六维（IFEval / BBH / MATH Lvl5 / GPQA / MUSR / MMLU-PRO）等权。前沿定义为每月 Average 的 0.90 分位。',
      '主 claim（归因侧）：窗口内能力提升约 5.4865–6.6592 点，是非规模技术/数据工程综合进步主导，规模通道贡献与 0 不可区分。该区间是四种端点/规格算法的极差；趋势法的 drop-last 变体给 5.3581，略低于下界，故须写成「四种端点/规格算法下的极差」，不得写成「所有方法下的极差」。',
      '26%/74% 及任何百分比分割一律不得出现：端点敏感性下 scale_share 极差 0.2875 且符号翻转（+0.2593 / +0.1811 / −0.0282 / +0.2205），极差已大于主口径点值本身。自助区间 [0.0223, 0.4019] 未覆盖该项并不矛盾——两者测的是不同来源的不确定性（自助测换一批模型，端点测换一个末端定义）。',
      '主 claim 的实际依据是趋势法（用全部 10 个月斜率）：slope_f = +0.05750（log10 点/月）、slope_tau = +0.57377（点/月），斜率比 9.98；scale_share = +0.0911，自助 95% 区间 [−0.1942, +0.2258] 含 0（B=1000，按月分层重抽）。',
      '规格敏感性必须一并报：线性 log N 规格下 scale_share 为 −0.2827（月度）与 −0.4972（季度），与主口径符号相反，不得取绝对值、不得截断到 0、不得只报主口径。成因而非缺陷：窗口内高分段中位规模在下降，线性 f(N) 斜率为正时必然给出负的规模贡献。',
      '子组分解：chat_finetuned（n=4231）total +7.0278、scale_share 0.1554 其 CI95 [−0.0328, 0.3567] 含 0，不得称该组规模贡献显著为正；pretrained（n=330）total −3.5789（负），该组在本窗口内能力回落，只报绝对点数与方向，不得给任何占比（份额是负数分母上的比值）。两组结论不得互相推广。',
      'tau 只能表述为「非规模技术/数据工程综合进步」，不得写成架构/算法进步——它吸收未观测的数据质量变化与榜单过拟合。',
      '规模通道定义取丙（仅 #Params (B)，全样本）；甲（仅 N）与乙（N, D, compute）的对照只作偏误机制验证：省略 compute 会在规模通道与技术通道之间重分配解释力（重分配量 0.2451 点，精确抵消），但该子集 total_points = −4.5487（负），share 与 points 的比较必然反向，偏误方向不成立。该偏误只给符号与量级，不得作全样本修正系数，不得表述为「已校正」；66 子集的结论不得推广到全样本。',
      'N 的下降须区分两种倍数：端点比值 3.162（N_q90 由 46.703B 降到 14.770B，即缩至 1/3.162）；斜率隐含值 10^0.5653 = 3.675（十个月累计 −0.5653 dex，0.90 分位月斜率 −0.06281）。两者不是同一量，因 N_q90 逐月路径非单调。引用时必须写明是哪一种。',
      '前沿轨迹：S_q90 由 25.9201 升到 41.3875，线性拟合斜率 +1.5333/月。同期 log10 N 中位月斜率仅 −0.00209（基本不动），下降集中在高分段。',
      '预测部分不作主 claim：中性情景 h12 中位 56.330、80% 区间 [43.268, 69.699]、95% 宽度 41.935。必须同表列出 baseline M0a 的 60.290（80% 区间 [56.448, 64.131]，95% 宽度 11.750），并说明主方法 h12 点值比 baseline 低约 6.6%、95% 区间宽约 3.6 倍；预声明的预测判据 baseline 也满足（其 lo80 = 56.448 > 41.387），故在该判据上主方法不构成对 baseline 的优势。不得只报主方法的中位数。',
      '预声明预测判据：中性情景 12 个月的 80% 区间下界 > 当前前沿值。实测 lo80 = 43.268 > 41.387，裕度仅 1.881 点。该判据首轮曾判未通过（首轮把均值层面的 tau 月斜率 0.4675 加到 q90 前沿水平上，对象不一致），修正为「用 q90 自身斜率按归因份额拆通道」后通过；缺陷是在看到首轮结果之后才被发现的。判据文字未改。这一段发现次序必须如实写在正文。',
      '24 个月不作主报：乐观 h24 中位 94.118 逼近 0–100 上界，其 95% 宽度 29.236 反而窄于 h12 的 41.184，这是截断到 100 造成的假象，不是精度提高；得分上界的饱和形态在 9.1 个月窗口内不可检验。题目原文为 12 个月或 24 个月，只报 12 个月即合规；若列出 h24 须显式声明该假设不可验证。',
      '情景极差随规模份额严格缩放：scale_share 0.2593 → 11.786 点；0.0911 → 4.1408 点；0 → 0。用趋势法口径，三情景极差仅 4.1408 点（约占中性中位数 56.330 的 7.4%）。这条是本节最有价值的发现之一：算力增长放缓对开源前沿短期预测影响很小，因为前沿推进本就不靠规模扩张。',
      '桥接：LB_Average = 62.7406 − 22.393·Val_Loss（High 层权重 3:1），斜率 CI95 [−44.481, −7.8308]，单调递减成立，rmse 10.9842，映射误差 σ = 10.1726 已作独立随机项传播进蒙特卡洛（4000 次）。High 层 n=7 的 ρ = −0.6071、p = 0.148 方向正确但不显著，不得据此认为 High 层质量更差（是样本量所致）。Loss_Source 全为技术报告/训练日志，无标度律估算行，故桥接无循环论证。桥接 rmse 与得分尺度同量级，是 95% 区间偏宽的主因——这是数据条件的结果，不是算法缺陷。',
      '识别性与分解合法性：spearman(t, logN) = −0.0615（时间与规模不共线）；spearman(S, logN) = +0.6352；四个规模档内 tau 均显著为正（4–10B 档 spearman(t,S) = 0.3125，10–30B 档 0.4827）⇒ f(N) 与 tau_t 可分。加性结构下两因子 Shapley 值与本分解代数恒等，无交互项需估计，份额和恒为 1（四规格与四端点全部数值核验）。',
      'C8 逐任务聚合：1860 个目录可用（实测可解析 1860 / 1863），4 个不可解析文件同属一次导出事故，任务级记录 65137，BBH 子任务 24 个；聚合口径为按 BBH 子任务逐任务 z-score 后按模型取均值。缺失 benchmark 用可比样本子集口径，不得填 0。',
      'C1 为投榜样本，tau 含 benchmark 过拟合成分；跨源统一假设（C1 得分与 C4 compute 经名称连接后视为同一模型）为承重假设。',
    ],
    extra: String.raw`
本节要讲清：① 数据口径与综合能力、前沿的定义，以及开源筛选、模型类型、时间轴三项口径；
② 归因模型的设定（规模项取 log N 的十分位 dummy 以吸收分布形变、技术项为月度固定效应）与识别性；
③ 分解结果、规格敏感性、端点敏感性，以及为什么百分比分割不可主张；
④ 趋势法作为主 claim 证据；⑤ 子组分解的两条限制；⑥ 规模通道两种定义的偏误机制；
⑦ Loss → Score 的桥接及其误差传播；⑧ 前沿预测、与 baseline 的对照、以及情景极差随规模份额的缩放；
⑨ C8 逐任务聚合。
小节划分自行安排，建议 7–8 个 \subsection。
篇幅：正文约 3600–4600 个汉字 + 4 图 + 5 表。
`,
  },
]

function brief(q) {
  return String.raw`
你负责撰写 2026 年"华为杯"中国研究生数学建模竞赛 F 题论文的【${q.heading}】一节（G5 写作阶段）。

输出文件（用 Write 工具直接写入，只需一节的内容，不要写导言区、不要写 \documentclass 或 \begin{document}）：
  ${q.file}

## 权威数字来源（必须逐个打开阅读，不得凭印象写数）
- 最终结果分析：${q.report}
- 稳健性报告：${q.robustness}
- 图表规划：${q.plan}
- 落盘表格（用 Read 直接读，表格数值必须与之一致）：
${q.csvs.map(function (p) { return '    ' + p }).join('\n')}
- 落盘指标：
${q.metrics.map(function (p) { return '    ' + p }).join('\n')}

## 可用的图
写入 tex 时用下面这种相对路径（\includegraphics 相对的是 paper/main.tex 所在目录）：
${q.figures.map(function (p) { return '    ' + p }).join('\n')}
若想先目视确认每张图画了什么再写图注，可读同名 PNG（在 paper/ 下）：
${q.figures.map(function (p) { return '    paper/' + p.replace(/\.pdf$/, '.png') }).join('\n')}
四张图都要用上，其中第一张是本节的方法流程图（放在方法陈述处）。

## 不要做的事
- 不要读 planning/HANDOFF.md（很长且与本任务无关）。
- 不要执行任何 gate、不要索取人工裁定、不要新建 manifest；四问的结论已经完全冻结，
  你只做"把已冻结的结论写成论文正文"这一件事。
- 不要修改 paper/ 之外的任何文件。

## 本节必须承担的口径与限制（以学术化措辞融入正文相应位置，不是可选附注）
${q.limits.map(function (s, i) { return (i + 1) + '. ' + s }).join('\n')}

## 本节的结构要求
${q.extra}

## 文献
正文引用的 key 只能从下面这个清单里取（用 \citep{} 或 \citet{}）：
hoffmann2022, kaplan2020, bahri2024, muennighoff2023, sorscher2022, schaeffer2023,
xia2024regmix, goyal2024filtering, biderman2023pythia, gao2020pile, beeching2023leaderboard,
fourrier2024leaderboard, penedo2024fineweb, xie2023dsir, xie2023doremi, liu2024datacomp,
rae2021gopher, raffel2020c4, warner2024modernbert, albalak2024survey, chen2023skillit,
asai2026openscholar, dubey2024llama3, hoffmann2022training
只能引用与所论述内容真正相关的文献，每节引用 4–8 处，分散在正文里。不要为了凑数而引用。

${STYLE}
`
}

function verifyPrompt(q) {
  return String.raw`
你是独立核验员，任务是审计刚写好的论文一节，找出**任何**与落盘工件不一致之处。
被审文件：${q.file}

## 核验方法（必须实际执行，不得凭印象）
1. 用 Read 打开 ${q.file}，把正文、表格、公式里的**每一个数字**（含百分比、区间、指数、n、
   时间、倍数）列出来。忽略纯粹的章节号、图表编号、文献编号、公式编号。
2. 对每个数字，回到下列落盘工件里找到它的出处并比对：
   - ${q.report}
   - ${q.robustness}
${q.csvs.map(function (p) { return '   - ' + p }).join('\n')}
${q.metrics.map(function (p) { return '   - ' + p }).join('\n')}
   比对规则：四舍五入到更少位数不算错；位数相同但末位不同算错；张冠李戴（把 A 的值写成 B 的）
   算错；把区间上下界写反算错；把不同口径的数混用算错。
3. 逐条检查下面这张清单里的口径是否**确实出现在正文中**（不是只在附录）：
${q.limits.map(function (s, i) { return '   (' + (i + 1) + ') ' + s }).join('\n')}
   若某条缺失，或表述被弱化/反向了，记为错误。
4. 检查 LaTeX 可用性：花括号配平；每个 \begin 有对应 \end；每个 \includegraphics 引用的文件
   存在于清单中（清单见下）；每个 \label 唯一；每个 \ref 有对应 \label；没有 \usepackage；
   没有 [H] 浮动选项；表格用 booktabs 三线表。
   本节可用图文件：${q.figures.join('、')}
5. 检查语体：是否出现被禁的套话（「值得注意的是」「综上所述」「总而言之」「不难发现」
   「众所周知」「深入探讨」「赋能」「闭环」「抓手」「维度上」「极大地」「有效地」
   「具有重要意义」「提供了有力支撑」），是否出现「判 FAIL」「红线」「不得表述为」这种
   工作流报告口吻。发现即记为错误并给出改写建议。

## 最重要的纪律
- 你**不得**凭空报告不存在的错误。每一条错误都必须写下你在哪个文件、哪一行看到的值。
- 若某个数字在落盘工件里找不到出处，如实记为错误并说明「无法在任何落盘工件中追溯」。
- 若全部核对通过，verdict 填 PASS、errors 填空数组。不要为了显得有产出而编造问题。
`
}

const VERIFY_SCHEMA = {
  type: 'object',
  properties: {
    file: { type: 'string' },
    n_numbers_checked: { type: 'integer' },
    errors: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          severity: { type: 'string', enum: ['blocking', 'major', 'minor'] },
          location: { type: 'string' },
          problem: { type: 'string' },
          evidence: { type: 'string' },
          correct_value_or_action: { type: 'string' },
        },
        required: ['severity', 'location', 'problem', 'evidence', 'correct_value_or_action'],
      },
    },
    limits_missing: { type: 'array', items: { type: 'string' } },
    latex_issues: { type: 'array', items: { type: 'string' } },
    style_issues: { type: 'array', items: { type: 'string' } },
    verdict: { type: 'string', enum: ['PASS', 'NEEDS_FIX'] },
  },
  required: ['file', 'verdict', 'n_numbers_checked', 'errors', 'limits_missing', 'latex_issues', 'style_issues'],
}

const DRAFT_SCHEMA = {
  type: 'object',
  properties: {
    file: { type: 'string' },
    summary: { type: 'string' },
    figure_labels: { type: 'array', items: { type: 'string' } },
    table_labels: { type: 'array', items: { type: 'string' } },
    citations_used: { type: 'array', items: { type: 'string' } },
    chinese_chars_approx: { type: 'integer' },
  },
  required: ['file', 'summary', 'figure_labels', 'table_labels', 'citations_used'],
}

// ---------------------------------------------------------------- phase 1: refs
phase('文献核验')

const REF_BRIEF = String.raw`
今天是 ${TODAY}。任务：为 2026 年"华为杯"F 题论文核验参考文献，产出可直接用于 paper/reference.bib 的 BibTeX 条目。

## 硬性约束（BibTeX 样式只支持三类条目，字段是必填的，缺字段会报警告）
样式 paper/gmcm-numerical.bst 只识别三种类型：
  @article  必填 author, title, journal, volume, pages, year（number 可选）
  @book     必填 author, title, address, publisher, pages, year（尽量不要用）
  @misc     必填 author, title, url, urldate（用于网络资源/预印本/数据集/榜单）
  会议论文若无从核实的卷号与页码，一律降级为 @misc + arXiv/官方 url。
  urldate 一律填 ${TODAY}。
  不要使用 @inproceedings / @conference / @techreport / @online（样式不识别）。

## 纪律（极其重要）
- **每一个字段都必须来自你实际抓取到的页面。** 抓不到就不要写，改降级为 @misc 并给出可抓取的 url。
- 严禁凭记忆填写卷号、期号、页码。宁可少给一篇，不可编造一个字段。
- 每条都要在返回结果里注明：你用什么 url 核验的、核验到了哪些字段。
- 若某条最终无法核验，明确标记 status=UNVERIFIED 并不要放进最终 BibTeX。

## 输出
返回一个 JSON 对象：
{
  "bibtex": "<全部条目的 BibTeX 文本，条目之间空行分隔>",
  "verified": [{"key": "...", "entry_type": "...", "verified_fields": ["journal","volume","pages","year"], "evidence_url": "...", "status": "VERIFIED|PARTIAL|UNVERIFIED"}],
  "dropped": [{"key": "...", "reason": "..."}]
}
`

const REF_A = REF_BRIEF + String.raw`
## 你负责这批（经典标度律与训练计算最优方向）
1. hoffmann2022 / hoffmann2022training —— Hoffmann et al., Training Compute-Optimal Large Language Models,
   NeurIPS 35, 2022（Chinchilla）。**同时必须核验其 Approach-3 拟合常数**：
   E ≈ 1.69、A ≈ 406.4、B ≈ 410.7、α ≈ 0.34、β ≈ 0.28（单位：N、D 以十亿计）。
   请在论文原文（arXiv:2203.15556）中定位到给出这组数的表，逐个核对并回报实际值与你看到的表名/页码段落。
   这条的核验结论直接决定论文能不能引用这些常数，务必做实。
2. kaplan2020 —— Kaplan et al., Scaling Laws for Neural Language Models, arXiv:2001.08361, 2020。
3. bahri2024 —— Bahri, Dyer, Kaplan et al., Explaining neural scaling laws, PNAS 121(27), 2024。DOI 10.1073/pnas.2311878121。
4. muennighoff2023 —— Muennighoff et al., Scaling Data-Constrained Language Models, NeurIPS 36, 2023（arXiv:2305.16264）。
5. sorscher2022 —— Sorscher et al., Beyond neural scaling laws: beating power law scaling via data pruning,
   Nature Communications 2022（arXiv:2206.14486）。
6. schaeffer2023 —— Schaeffer, Miranda, Koyejo, Are Emergent Abilities of Large Language Models a Mirage? NeurIPS 36, 2023。
7. dubey2024llama3 —— Dubey et al., The Llama 3 Herd of Models, arXiv:2407.21783, 2024。
8. albalak2024survey —— Albalak et al., A Survey on Data Selection for Language Models, TACL 2024（arXiv:2402.16827）。
`

const REF_B = REF_BRIEF + String.raw`
## 你负责这批（数据配比、数据质量指标、数据集与评测榜）
1. xia2024regmix —— Xia et al., RegMix: Data Mixture as Regression for Language Model Pre-training, ICML 2024（arXiv:2407.01492）。
2. xie2023dsir —— Xie et al., Data Selection for Language Models via Importance Resampling, NeurIPS 36, 2023（arXiv:2302.03169）。
3. xie2023doremi —— Xie et al., DoReMi: Optimizing Data Mixtures Speeds Up Language Model Pretraining, NeurIPS 36, 2023（arXiv:2305.10429）。
4. goyal2024filtering —— Goyal et al., Scaling Laws for Data Filtering — Data Curation Cannot be Compute Agnostic, CVPR 2024（arXiv:2404.07177）。
5. liu2024datacomp —— Li et al., DataComp-LM: In search of the next generation of training sets for language models, NeurIPS 2024（arXiv:2406.11794）。
6. biderman2023pythia —— Biderman et al., Pythia: A Suite for Analyzing Large Language Models Across Training and Scaling, ICML 2023（arXiv:2304.01373）。
7. gao2020pile —— Gao et al., The Pile: An 800GB Dataset of Diverse Text for Language Modeling, arXiv:2101.00027, 2020。
8. beeching2023leaderboard —— Beeching et al., Open LLM Leaderboard（Hugging Face），arXiv:2306.01693, 2023。
9. fourrier2024leaderboard —— Fourrier et al., Open LLM Leaderboard 2（Hugging Face），arXiv:2406.07594, 2024。
10. penedo2024fineweb —— Penedo et al., The FineWeb Datasets: Decanting the Web for the Finest Text Data at Scale, NeurIPS 2024（arXiv:2406.17557）。
11. rae2021gopher —— Rae et al., Scaling Language Models: Methods, Analysis & Insights from Training Gopher, arXiv:2112.11446, 2021。
12. raffel2020c4 —— Raffel et al., Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer, JMLR 21(140), 2020（C4 数据集）。
13. warner2024modernbert —— Warner et al., Smarter, Better, Faster, Longer: A Modern Bidirectional Encoder for Fast, Memory Efficient, and Long Context Finetuning and Inference, arXiv:2412.13663, 2024。
14. chen2023skillit —— Chen et al., Skill-It! A Data-Driven Skills Framework for Understanding and Training Language Models, NeurIPS 36, 2023（arXiv:2307.14430）。
15. asai2026openscholar —— Asai et al., Synthesizing scientific literature with retrieval-augmented language models, Nature 650, 857–863 (2026)。DOI 10.1038/s41586-025-10072-4。
`

const refs = await parallel([
  function () { return agent(REF_A, { label: 'refs:scaling', phase: '文献核验' }) },
  function () { return agent(REF_B, { label: 'refs:data', phase: '文献核验' }) },
])

log('文献核验完成：' + refs.filter(Boolean).length + '/2 组返回')

// ---------------------------------------------------------------- phase 2-4: pipeline
const drafted = await pipeline(
  QS,
  function (q) {
    return agent(brief(q), { label: 'draft:' + q.id, phase: '起草', schema: DRAFT_SCHEMA })
  },
  function (d, q) {
    return agent(verifyPrompt(q), { label: 'verify:' + q.id, phase: '数字核验', schema: VERIFY_SCHEMA })
  },
  function (v, q) {
    return agent(
      String.raw`
你是修订者。文件：${q.file}

独立核验员提交了下面的问题清单。请逐条处置：
- 对 severity = blocking / major 的条目：**必须**打开 ${q.file} 与被引用的落盘工件核对后修正。
- 对 limits_missing：把缺失的口径以学术化措辞补写进正文相应位置（不得写成报告口吻）。
- 对 latex_issues / style_issues：逐条修正。
- 对 severity = minor：修，除非你核对后确认核验员判断有误。

修正原则：只动被指出问题的地方，不要顺手改写其他段落。改完后表格与正文的数字必须仍然自洽。

核验结论：
${JSON.stringify(v, null, 1)}

完成后返回一句话说明你改了哪些地方（未改的也要说明理由）。
`,
      { label: 'fix:' + q.id, phase: '修订' }
    )
  }
)

// ---------------------------------------------------------------- phase 5: cross-section consistency
phase('全篇一致')

const consistency = await agent(
  String.raw`
你是全篇一致性审计员。已写好四节：paper/sections/problem1.tex、problem2.tex、problem3.tex、problem4.tex。

请只做**跨节**的一致性检查（单节内部已由各自的核验员查过）：
1. **同一量在不同节出现时必须一致**。重点核这几条（打开相关落盘工件核对，不要凭印象）：
   - 标度律参数（E, A, α, B, β, γ）在 Q2 与 Q3 两节取值是否一致：Q3 用的是 B1 侧参数
     （E=1.6897974079310756, A=0.3539803206630743, α=0.3399765818978297,
      B=1.2403057700818418, β=0.2798780599420644, γ=0.9659129389937917）。
   - γ 在 Q2 节里必须同时给出两条路线（0.9659128363851796 与 1.1797809819428589）且都带区间。
   - η = 2e-4、L_ctx^crit = 30000、Q0 = 0.35、k = 6 + η·L_ctx 在 Q3 与全篇符号说明中的一致性。
   - Q1 的域级 Q 范围 [0.223306, 0.381496] 与 Q2 节里引用的同一个范围是否一致。
   - Q4 的总提升区间 5.4865–6.6592、N 的两种倍数（3.162 与 3.675）、baseline 60.290。
2. **符号冲突**：同一个符号是否在两节里表示不同的量（尤其 N、D、Q、p、C、L、S、α、β、γ、λ、η、κ）。
   列出所有冲突，给出建议的统一写法。
3. **交叉引用**：有没有 \ref 指向不存在的 label；有没有两节用了同一个 label 名。
   用 grep 把所有 \label{...} 与 \ref{...} 列出来做集合比对。
4. **口径自相矛盾**：同一件事在两节里的表述是否打架（例如 Q1 说某假设不可检验、Q2 又说已验证；
   Q3 说 30000 是临界尺度、Q4 又说它是最优上下文长度）。
5. **全篇图号**：四节各自用了哪几张图，有没有重复引用同一张图讲不同的事。

输出：先给出一个「必须修正」清单（每条写清文件、位置、问题、建议改法），再给出一个「已核对无问题」清单。
不要修改文件，只报告。若某条你无法判断，如实说需要人工确认。
`,
  { label: 'consistency:cross-section', phase: '全篇一致' }
)

return {
  refs: refs.filter(Boolean),
  sections: drafted.filter(Boolean),
  consistency: consistency,
}

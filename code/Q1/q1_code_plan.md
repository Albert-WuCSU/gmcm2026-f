# Q1 Code Plan — round1

**目标语言**：Python（本机无 MATLAB，见交接文档 §1）
**轮次目的**：首轮实跑已批准的主方法与 baseline，产出与 HD-2 预声明指标直接可比的结果，
为首轮实验后的第二张决策卡（冲突判据选择）提供证据。
**Gate**：G2.5 已过 → 本计划服务 G3。
**种子**：`20260924`（全项目统一）
**Profile**：`learning` + `lean`

---

## 1. 依据的人工决策

| decision_id | choice | 对实现的约束 |
| --- | --- | --- |
| `q1_tierC_direction` | **D** | dsir 逐 token 归一化 + 三合一 + 长度类非单调；实现一律经 `build_canonical()` |
| `q1_normalization_population` | **A** | `pooled+ecdf` 为主报口径；`per_domain+ecdf` 为**必跑消融臂** |
| `q1c_interaction_tradeoff` | **C** | M0c 与 M1c 都跑，M0c 为主、M1c 作组合效应辅证 |
| `q1_frac_unique_words_treatment` | **no_treatment** | **不得**对 `rps_doc_frac_unique_words` 做任何长度校正；规格保持 20 列 |

全局框定：`HD-1`（隐藏文本不报告）、`HD-2`（相对 baseline 制，显著性用重抽样区间机械判定）、
`HD-3`（必用集 + A18 抽样）。

---

## 2. 本轮实现范围

| ID | Role | 子任务 | 脚本 |
| --- | --- | --- | --- |
| **M1** | main（质量侧） | Q1a/Q1b | `code/Q1/q1_quality_main.py` |
| **M0** | usable_baseline（质量侧） | Q1a/Q1b | `code/Q1/q1_quality_baseline.py` |
| **M1c** | main（配比侧） | Q1c | `code/Q1/q1_mixture_main.py` |
| **M0c** | usable_baseline（配比侧） | Q1c | `code/Q1/q1_mixture_baseline.py` |

共享层：`code/Q1/q1_common.py`（加载、聚合、bootstrap、指标、落盘）。

**M2 保持休眠，本轮不实现**（见 §9）。质量侧与配比侧是两个数学上不可合并的估计问题，
各配恰一主一 baseline，非凑候选数（依据见 `risk_probe_summary.json#shortlist_structure_rationale`）。

---

## 3. 输入契约

### 3.1 质量侧（M0 / M1）

| 项 | 内容 |
| --- | --- |
| 数据源 | `workspace/data_raw/real_attachments/A_data_value/` 下 A1+A2+A3 三个 `.jsonl.xz` |
| 读取入口 | `q1_features.load_all()` → `X[n,22]`、`dom_idx[n]`、`meta` |
| 行数 | **全量 272 486 / 272 505**（仅剔除整条 NaN 向量：A1 18 行、A3 1 行）。**禁止抽样**（题目硬性） |
| 预处理入口 | `q1_features.build_canonical(X, dom_idx, meta["columns"], ref_mask=ref_mask)` |
| 预处理产出 | `U[n,20]`，全部"越高越好"，值域 `[0,1]`，无量纲 |
| 域 | 7 个：arxiv / book / c4 / commoncrawl / github / stackexchange / wikipedia |

**不得另写一套预处理。** 20 列 = 22 指标中 dsir 三列合一。列名见
`q1_features.DIRECTION` 与 `collapse_dsir()` 的返回。

### 3.2 配比侧（M0c / M1c）

| 项 | 内容 |
| --- | --- |
| 数据源 | `workspace/data_raw/real_attachments/A_data_value/regmix_tables/*.csv` |
| 训练 | `train_mixture_1m.csv`（512×17） + `train_pile_loss_1m.csv`（512×13） |
| 检验 | `test_*_{1m,60m,1B}`（256 / 256 / 64 行） |
| 外推（仅定性） | `est_*_{10b,70b}`（63 / 63 行） |
| 配比列 | `train_the_pile_<domain>`，17 列，**单位：占比，行和 ∈ [0.996, 1.003]** |
| Loss 列 | `metric/the_pile_<domain>_val_loss`，13 列，**单位：交叉熵 nats/token** |
| 列名映射 | `c.removeprefix("metric/the_pile_").removesuffix("_val_loss")` → 13/13 全匹配。**不要用 `replace`** |
| 目标变量 | `pweighted13`：以配比在 13 域上**重归一化**后的加权 Loss 均值 |

**目标变量声明（AMB-Q1-2）**：`pweighted13` 把 `p` 同时置于等式两侧，**存在部分循环**，
须在论文声明。选它的依据：R² 0.896 vs `mean13` 的 0.296，符号稳定 1.000 vs 0.882。
本轮**同时记录 `mean13` 的同口径结果**作为该声明的支撑证据，不作主报。

### 3.3 域级 Q → 配比侧的桥接（Q1c 增量检验用）

`workspace/data_raw/real_attachments/A_data_value/domain_mapping_guide.csv`：
**17 配方域中仅 6 个有质量域对应**（`direct` 3：arxiv/github/stackexchange；
`near_direct` 3：wikipedia_en→wikipedia、gutenberg_pg_19→book、pile_cc→commoncrawl；
`inferred` 11 全为 `(none)`）。质量域 `c4` 不出现在配方域中。

语料级 Q 构造：`Q_corpus = Σ_{i∈mapped} p_i · Q_i / Σ_{i∈mapped} p_i`（6 域重归一化）。
**须记录 6 域的配比质量占比分布**——若该占比中位数过低，则 Q 通道本身信息有限，属如实报告项。

---

## 4. 计算步骤

### 4.1 M0（baseline，质量侧）

1. `U, cols = build_canonical(...)`（主口径 pooled+ecdf）。
2. 样本级 `Q_i = mean(U[i, :])`，20 列等权。
3. 域级聚合：**Huber 均值（k=1.345，30 次迭代）** 与 **10% 截尾均值** 各算一份，主报 Huber。
4. 每域 bootstrap 95% 区间，**B=400**，`default_rng(20260924)`。
5. 落盘域级表 + 样本级 Q 的分布摘要（不落盘 272k 行明细，只落分位数与直方图计数）。

### 4.2 M1（main，质量侧）

1. 同一 `U`、同一口径（与 M0 的唯一差异是权重与合成方式）。
2. 语义分组：`P` = 污染组 6 列（`q1_features.POLLUTION_COLS`，含 `ad_en_margin` 取负后的广告性），
   `V` = 其余 14 列。**分组是语义划分，不得声称由相关结构导出**（组内相关 0.051/0.026 与组间 0.016 同量级）。
3. `V_i = mean(U[i, V列])`；`P_i = mean(1 − U[i, P列])` 即污染度（越高越脏）。
4. **门控合成 `Q_i = V_i · (1 − P_i)`**。**差值式 `V−P` 已据证据排除，不得实现**
   （跨零使 CV=1.44e6，且负 Q 与 Q3 的 `γQ^4`/`γe^{6Q}` 不相容）。
5. 域级聚合与 bootstrap 同 M0。
6. **冲突判据（Q1b）——一律分位数锚定**，四个候选全算，落表供第二张决策卡：
   - `CD2`：`V > p75(V)` ∧ `P > p75(P)`
   - `CD1`：指标间 MAD > 0.25
   - `CD3-5`：≥5 项高 ∧ ≥5 项低；`CD3-3`：≥3 项高 ∧ ≥3 项低
   **绝对阈版（0.75 硬阈）已排除，不得实现**（冲突率恰为 0.0）。
7. 冲突样本须可回溯原文：按域各取冲突样本的行号与 `id`，落 `tables/q1b_conflict_examples.csv`，
   供人工核验。**AI 不对冲突成因作物理解释**，只落可核验的指标取值。

### 4.3 M0c（baseline，配比侧）

1. 读 `train_mixture_1m` + `train_pile_loss_1m`，索引严格对齐（6 对表已核验全对齐）。
2. 构造目标 `pweighted13`（见 §3.2）。
3. **显式去截距**拟合 17 维 `p`（`lstsq`，无常数列）。**不得依赖 Σp=1 的千分位舍入来辨识截距**
   （cond 61 → 4773，×78，该系数无实质解释）。同时记录"指定参照域"变体作为等价性对照。
4. 在 `test_1m/60m/1B` 上预测。
5. **验证口径（硬性）**：每个检验集分别报
   - 原始 R²（仅作对照，**禁止单独引用**）
   - **按尺度去常数偏移后的 R²**
   - **Spearman**
   报告须同时给出 `bias_share_of_rmse`，以说明原始 R² 为负的成因是水平平移。
6. `est_10b/est_70b` **仅作定性讨论**（GC5）：A12/A14 配比行与训练集重复率 1.0，
   不能检验配比泛化；去偏后 R² 仍为负。

### 4.4 M1c（main，配比侧）

1. 特征：17 主效应 + 136 个二阶交互 = **153 特征**（`features/rows = 0.299`）。
2. 岭正则，**5 折 CV 选 λ**，网格 `[1e-8, 1e-6, 1e-4, 1e-3, 1e-2, 1e-1, 1, 10]`（探针选出 1e-3）。
3. 同一目标、同一检验集、同一验证口径（与 M0c 逐项可比）。
4. **系数报告过滤（硬性）**：B=400 自助，**仅报符号稳定率 ≥0.95 的交互项**。
   已测 136 项中 69 项 ≥0.95、53 项 ≥0.99；主效应 17/17 稳定。
   **禁止把稳定子集外的单个交互系数解释为域间替代/互补。**
5. 跨尺度增益如实报：同尺度 1m 去偏 R² 0.913→0.983 有增益，60m 基本持平（0.771→0.766），
   **1B 反而更差（0.705→0.658）**。即增益是尺度局部的。

### 4.5 消融臂（必跑，`q1_normalization_population=A` 的附带要求）

对 **M0 与 M1** 各跑一遍 `population="per_domain"`，与主口径同表并列。
预期：域间极差降至约 0.0033、AUC 降至约 0.500（域级 Q 近乎恒等）。
**该臂的作用是证明主口径选择的代价，不是备选主口径。**

### 4.6 参数扰动（必跑）

| 对象 | 扰动 | 记录 |
| --- | --- | --- |
| M0 | 列权重 uniform ±10%，reps=40 | 域序 Kendall τ、最大名次位移、top1% 样本重叠 |
| M1 | 同上 **+ V/P 分组权重 ±10%**（探针未测，G3 须补） | 同上 + Q 的分布位移 |
| M1 冲突判据 | 分位锚点 p70 / p75 / p80 | 四个判据的冲突率对锚点的敏感性 |
| M0c / M1c | B=400 自助 | 系数符号稳定率、相对标准误 |
| M1c | λ 在选定值的 ±1 个数量级 | 去偏 R² 与稳定子集大小的变化 |

### 4.7 Q1c 的 Q 增量检验（硬性，决策附带要求）

题目原文要求「是否以及如何引入质量评分 Q，由参赛队伍论证」。须做**嵌套比较**：

- `A`：仅 17 维 `p`（= M0c）
- `B`：17 维 `p` + `Q_corpus`（18 特征）
- 同一目标、同一检验集、同一去偏口径；增量显著性用 **B=400 自助区间**判定（HD-2：机械可判）。

**若无增量，如实写入。这本身就是对该问的有证据回答，不是失败。**
同时记录 `Q_corpus` 与 17 维 `p` 的共线性（VIF 或条件数变化），因 Q 由 6 域的 p 加权构成，
**与 p 存在构造性相关**，须在论文声明。

---

## 5. 可比输出契约

主方法与 baseline **必须逐项可比**：同一预处理、同一口径、同一检验集、同一指标定义。

### 5.1 质量侧（M0 vs M1）

| 指标 | 定义 | 比较方向 |
| --- | --- | --- |
| `domain_range` | 域级 Q 的极差（Huber 聚合） | 越大越可分辨 |
| `n_domain_pairs_distinguishable` | bootstrap 95% 区间不重叠的域对数（共 21 对） | 越多越好 |
| `rank_stability_kendall_tau` | ±10% 权重扰动下域序的 Kendall τ 均值/最小值 | 越高越稳 |
| `conflict_rate`（Q1b） | 四个分位数锚定判据各自的冲突率 | 须落在 (0,1) 开区间 |
| `auc_Q_recovering_domain` | AUC(arxiv:github) | **披露项**，越接近 0.5 越少域混淆 |
| 退化检查 | std / CV / 唯一值比 / 基尼 / top1% 质量占比 | 不得退化 |

HD-2 判定：M1 在 `domain_range` 与 `rank_stability` 上超过 M0，且超出幅度大于 bootstrap 噪声。

### 5.2 配比侧（M0c vs M1c）

| 指标 | 定义 |
| --- | --- |
| `r2_raw` | 原始 R²（对照用，禁止单独引用） |
| `r2_after_offset_removal` | **按尺度去常数偏移后的 R²（主报）** |
| `spearman` | 秩相关（主报） |
| `bias_share_of_rmse` | 偏移占 RMSE 比重（解释 `r2_raw` 为负的成因） |
| `frac_coefs_sign_stable_ge_0.95` | B=400 下符号稳定系数占比 |
| `mean_relative_se` | 平均相对标准误 |

三个尺度（1m/60m/1B）**分别报**，不得合并成单一数字。

---

## 6. 实现须在运行时监测的探针条件

| 探针条件 | 来源 | 运行时动作 |
| --- | --- | --- |
| `direction_table_internal_consistency` | 决策后已由 canonical 解除（r<−0.8 对数 = 0） | 重算并断言仍为 0；若 >0 立即报警 |
| `indicator_redundancy` | dsir 三列已合一；最大 \|r\| 仍 0.9998 前为 dsir 内部 | 记录 20 列的最大非对角 \|r\| 与条件数 |
| `naive_minmax_numerical_degeneracy` | 已由 ecdf 规避 | 断言未使用字面 Min-Max |
| `VP_block_cohesion` | CONDITIONAL，组内相关与组间同量级 | 记录组内/组间平均相关，供论文的语义论证 |
| `conflict_definition_non_degeneracy` | CONDITIONAL | 断言所选判据冲突率 ∈ (0,1)；绝对阈版不实现 |
| `simplex_induced_singularity` | CONDITIONAL | 断言已去截距；记录 cond(17) 与 cond(18) |
| `interaction_identifiability` | **FAIL** | 强制执行 ≥0.95 过滤；未过滤的系数不得进入任何表 |
| `cross_scale_transfer` | PASS，但 bias 占比 98.8%/99.9% | 强制同时输出去偏 R² 与 Spearman |
| `book` 域样本量 | n=171，区间宽度为 github 的 29.6 倍 | 域级结论须附区间；`book`/`wikipedia` 不可区分须如实标注 |

---

## 7. 输出路径

```text
results/Q1/experiments/round1/
├── figures/            # Type 1 诊断为主；论文用图留到 figure-table-planner
├── tables/
│   ├── q1a_domain_quality.csv          # 域级 Q + bootstrap 区间（M0/M1 × 主口径/消融臂）
│   ├── q1a_ablation_per_domain.csv
│   ├── q1b_conflict_rates.csv          # 四判据 × 三分位锚点
│   ├── q1b_conflict_examples.csv       # 可回溯原文的冲突样本
│   ├── q1c_coefficients.csv            # M0c 全部 17 项；M1c 仅稳定子集
│   ├── q1c_validation_by_scale.csv     # 三尺度 × 三指标
│   └── q1c_q_increment_test.csv        # 17维p vs 17维p+Q_corpus
├── metrics/
│   ├── q1_quality_metrics.json
│   ├── q1_mixture_metrics.json
│   └── q1_perturbation.json
└── run_summary.json
```

`logs/` **仅在失败或需复现异常时创建**（lean 契约）。
中间结果若需固化，写 `workspace/data_clean/`；**不得写回 `workspace/data_raw/`**（已 `attrib +R`）。

---

## 8. 环境与运行

| 项 | 值 |
| --- | --- |
| Python | 3.14.6；numpy 2.5.1、scipy 1.18.0（仅统计检验）、pandas 3.0.5（仅落表） |
| 禁用 | sklearn（岭回归与 CV 用 numpy 显式实现，避免隐藏默认值影响可复现性） |
| 种子 | `20260924`，所有 `default_rng` 显式传入，**不得用全局 `np.random`** |
| 预期运行时 | 质量侧约 90 s（加载 60 s + 计算 30 s）；扰动 40 reps 约 +5 min；配比侧约 10 s |
| 峰值内存 | 约 530 MB（全量 A1+A2+A3），满足 GC11 |
| 控制台编码 | 命令前加 `PYTHONIOENCODING=utf-8`（Git Bash 下 GBK 会抛错） |

---

## 9. Fallback 触发评估

| 项 | 内容 |
| --- | --- |
| `fallback_id` | **M2**（指标间中位数合成 + 离散度冲突判据） |
| 触发条件 | 使用者裁定 Tier C 方向后，① 方向表仍有 **≥3 对 r<−0.8** 的矛盾对，**或** ② M1 门控式在所选口径下**冲突率落到 (0.01, 0.50) 之外** |
| 条件① 现状 | **已判定未触发**：canonical 下 r<−0.8 对数 = **0**（`q1_canonical_verification.json`） |
| 条件② 现状 | **本轮须实测**。决策前 CD2 分位数锚定为 0.0363 ∈ (0.01, 0.50)，预期不触发，但须在 canonical 口径下复算 |
| 本轮动作 | **不实现 M2**。仅在 `run_summary.json#fallback_trigger` 记录两个条件的实测值与 `observed` 布尔 |

**若条件②实测落到区间外**：停止，把证据提交使用者决定是否激活 M2。**AI 不得自行激活。**

---

## 10. 下游评审须通过的命名检查

`code/Q1/reviews/q1_python_review.json` 须含五项命名检查（AGENTS.md G3）：

| 检查 | 本轮的具体判据 |
| --- | --- |
| `syntax` | 四个脚本 + 共享层可导入、无语法错误 |
| `input_contract` | 全量 272 486 行；20 列；13/13 Loss 列匹配；NaN 判定同时判 `None` 与 `x != x` |
| `method_alignment` | 门控式而非差值式；分位数锚定而非绝对阈；M0c 已去截距；M1c 仅报稳定子集；`frac_unique_words` 未被校正 |
| `reproducibility` | 种子 20260924 显式传入；无全局随机；同输入两次运行结果一致 |
| `output_contract` | §7 全部路径存在；`run_summary.json` 字段齐全；三尺度分报；消融臂与扰动均落盘 |

---

## 11. run_summary.json 契约

```json
{
  "schema_version": 1,
  "question": "Q1",
  "round": "round1",
  "implementation_target": "python",
  "random_seed": 20260924,
  "approved_decision_id": ["q1_tierC_direction", "q1_normalization_population",
                           "q1c_interaction_tradeoff", "q1_frac_unique_words_treatment"],
  "methods": [
    {"method_id": "M1", "role": "main_candidate", "script": "code/Q1/q1_quality_main.py",
     "status": "", "execution_time_seconds": 0, "input_files": [], "output_files": [],
     "figure_files": [], "metrics_summary": {}, "warnings": [], "errors": []},
    {"method_id": "M0", "role": "usable_baseline", "script": "code/Q1/q1_quality_baseline.py"},
    {"method_id": "M1c", "role": "main_candidate", "script": "code/Q1/q1_mixture_main.py"},
    {"method_id": "M0c", "role": "usable_baseline", "script": "code/Q1/q1_mixture_baseline.py"}
  ],
  "ablation": {"arm": "per_domain+ecdf", "applied_to": ["M0", "M1"], "metrics": {}},
  "perturbation": {"weights_pm10pct_reps40": {}, "group_weights_pm10pct": {},
                   "conflict_anchor_p70_p75_p80": {}, "bootstrap_B400": {}, "lambda_pm1decade": {}},
  "comparison": {
    "quality_side": {"metric": "domain_range / rank_stability_kendall_tau",
                     "M0": null, "M1": null, "verdict_vs_baseline": ""},
    "mixture_side": {"metric": "r2_after_offset_removal / spearman by scale",
                     "M0c": null, "M1c": null, "verdict_vs_baseline": ""},
    "q_increment_test": {"p_only": null, "p_plus_Q": null, "increment_ci95": null,
                         "significant": null}
  },
  "fallback_trigger": {
    "fallback_id": "M2",
    "condition": "≥3 pairs r<-0.8 OR M1 conflict_rate outside (0.01, 0.50)",
    "observed": false,
    "evidence": {"n_pairs_lt_-0.8": null, "conflict_rate_CD2": null}
  },
  "environment": {}
}
```

---

## 12. 交接

下一步：**`python-model-code-generator`**，按本计划生成 `code/Q1/` 下五个文件，
随后 `python-code-reviewer` 产出 `code/Q1/reviews/q1_python_review.json`。

**不得**在生成阶段扩大范围、增加候选、实现 M2、或改动 `q1_features.py` 的 CANONICAL 规格。

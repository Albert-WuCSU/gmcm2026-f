# Q3 代码计划 — 算力约束下的多维资源联合优化与结构性转移

**目标语言**：Python　**轮次**：round1（一轮跑通 + L_ctx/成本函数敏感性）
**批准的决策**：`methods/Q3/q3_decisions.jsonl` 全 3 条
（`q3_p_joint_optimization` = `B_main_plus_C_supplement`、
`q3_structural_transition_definition` = `A_main_plus_D_reported_as_contrast`、
`q3_optimum_acceptability_criterion` = `C`）
**种子**：20260924　**模式**：`learning` + `lean`
**时间预算**：比赛剩约 3 小时且使用者随后开新窗口写论文 ⇒ 只覆盖 main + usable_baseline，不做多轮迭代。

## 1. 实现范围

| ID | 角色 | 形式 | 实现？ |
| --- | --- | --- | --- |
| **M1o** | main | 分段 KKT（`Q<1` 内点段 / `Q=1` 边界段 / `Q=Q0` 下界段）+ `log C` 密集扫描 | **是** |
| **M0o** | usable_baseline | Chinchilla 经验配置：固定 `N:D`、`Q=Q0`（不投质量） | **是** |
| M2o | conditional_fallback | 纯数值全局优化（多起点 SLSQP / 差分进化） | **不实现**（休眠，仅评估触发） |

**M0o′（诊断项，非 baseline）**：`Q=Q0` 但 `N:D` 自由。**不得作为官方 baseline 报出**，
仅用于把 M1o−M0o 的差距分解为「质量通道」与「比值被强制」两部分（见 §5.3）。
理由：裁定 3 的落账条目 `raises_open_item_not_decided_by_user` 记录了 27.7% 的虚增，
但 M0o 的定义属 HD-2 已声明 baseline，**未经使用者裁定不得改动**。

## 2. 输入契约（字段与单位，全部已核实存在）

| 来源 | 文件 | 用到的内容 | 单位 |
| --- | --- | --- | --- |
| **Q2out** | `results/Q2/experiments/round1/metrics/q2_M1s.json` | `stage3_joint_wls.M1s_params` 的 **B1 侧** `E_B1, A_B1, alpha_B1, B_B1, beta, gamma` | `N`,`D` 以十亿计 |
| **Q1out** | `results/Q1/experiments/round1/tables/q1c_coefficients.csv` | `method=M0c` 的 17 行 `feature`,`coef` ⇒ `w`，供 §6 的 `dL/dp_i` 符号与排序 | 域级 Loss 水平 |
| **Q1out** | `results/Q1/experiments/round1/tables/q1a_domain_quality.csv` | 域级 `Q` 经验范围（0.2233–0.3815），供 `Q0` 取值与 AMB-Q2-3 披露 | `Q ∈ [0,1]` |
| **C7** | `model_architecture_metadata.csv` | `max_position_embeddings` ⇒ 可行 `L_ctx` = {2048, 4096, 8192, 32768, 131072}（计数 18/8/7/11/1） | tokens |
| **题目** | 附件 B 给定 | 三类 `g(Q)` 参数：指数型 `(1e7, 6.0)`、幂型 `(5e9, 4.0)`、对数渐进型 `(2e9, 10.0)` | FLOPs/token |
| **题目** | 给定常数 | `η = 2e-4`；`C_train = 6ND`；`C_Q = D[g(Q)−g(Q0)]_+`；`C_attn = ηND·L_ctx` | — |

**命名冲突警告（实现时必须区分）**：附件 B 的三类 `g` 用 `γ, λ` 作参数名，
与标度律的 `γ`（`Q` 的指数）**同名不同义**。代码中成本函数参数一律记 `g_coef`、`g_rate`，
**不得**复用符号 `gamma`。论文符号表须显式声明该区分。

**`Q0` 取值**：探针用 `0.35`（Q1 实测域级 `Q` 上端附近）。**该取值未经使用者裁定** ⇒
实现为 `--Q0`（默认 0.35），实际取值与其来源必须写入 `run_summary.Q0_spec`，可被使用者否决。

**硬性约束满足情况**：`L_ctx` 仅作参数扫描、取值全部来自 C7，**不列为决策变量**；
`L_ctx^crit = 6/η = 30000` 由解析式给出（§7）；预算档 ≥ 3 个量级。

## 3. 目标函数与约束（`p` 已由裁定 1 固定）

裁定 1 = B 为主 ⇒ `z_p = 0` ⇒ `exp(bᵀz_p) = 1`，该因子从目标函数消去：

```
min_{N,D,Q}  L(N,D,Q) = E + A·N^(-α) + B·(D·Q^γ)^(-β)
s.t.         6ND + D·[g(Q) − g(Q0)]_+ + η·N·D·L_ctx  ≤  C
             Q0 ≤ Q ≤ 1,    N > 0,  D > 0
```

决策变量 **3 个**（`N, D, Q`），KKT 维度 3（原 17+3 降至 3）。
`N, D` 以十亿为单位输入，代入成本式各乘 `1e9`（GC10）。

记 `k ≡ 6 + η·L_ctx`（合并两项与 `ND` 成正比的成本），`Δg ≡ [g(Q) − g(Q0)]_+`，`S ≡ D·Q^γ`：

```
成本 = k·N·D + D·Δg
```

## 4. M1o：分段 KKT（裁定 3 = C ⇒ KKT 为硬判据）

拉格朗日 `𝓛 = L + λ·(k·N·D + D·Δg − C)`，`λ ≥ 0`。预算必然紧（`L` 对 `N,D` 严格递减）。

### 4.1 三个分支（必须全部枚举，P1 FAIL 的解除条件）

**分支 I — 内点段（`Q0 < Q < 1`）**：三条驻点条件

```
∂N:  α·A·N^(-α-1)        = λ·k·D
∂D:  β·B·S^(-β)/D        = λ·(k·N + Δg)
∂Q:  β·γ·B·S^(-β)/Q      = λ·D·g'(Q)
```

消去 `λ` 得两条可解析核对的约减式（**实现须逐条计算残差**）：

```
(R1)  α·A·N^(-α)·(k·N + Δg)  =  β·B·S^(-β)·k·N
(R2)  γ·(k·N + Δg)           =  Q·g'(Q)                    ← 由 ∂Q ÷ ∂D 得，λ 与 D 全消
```

配合预算等式 `k·N·D + D·Δg = C`，三式三未知，用 `brentq`/`fsolve` 解。

**(R2) 是本问最干净的解析结构**，值得进论文：它把 `Q` 的最优性化为
「质量成本的对数弹性 `Q·g'(Q)` 须等于 `γ` 倍的单位数据总成本」，不含 `λ` 与 `D`。

**分支 II — 上界段（`Q = 1`）**：`Δg = g(1) − g(Q0)` 固定，降为 `(N,D)` 二变量

```
∂N:  α·A·N^(-α-1) = λ·k·D
∂D:  β·B·D^(-β)/D = λ·(k·N + Δg)          （S = D，因 Q=1）
预算: k·N·D + D·Δg = C
```

**有效性条件（互补松弛）**：`Q≤1` 的乘子 `μ = β·γ·B·D^(-β) − λ·D·g'(1) ≥ 0`。
`μ < 0` ⇒ 该分支不成立，须落回分支 I。**实现必须显式算 `μ` 并记录符号。**

**分支 III — 下界段（`Q = Q0`）**：`Δg = 0` ⇒ 成本退化为 `k·N·D`，
问题对 `N·D` 齐次，有闭式：`α·A·N^(-α) = β·B·(D·Q0^γ)^(-β)` 配预算。
探针未观测到该分支活跃，但**枚举完备性要求实现它**（否则 M2o 触发条件 1 无法判定）。

### 4.2 分支选择与 KKT 硬判据（裁定 3 = C）

对每个 `(C, g, L_ctx)`：三分支各求解 → 丢弃不可行与乘子符号错误者 → 取 `L` 最小者。

**硬判据（预声明，全部须通过，否则该点标 `kkt_failed` 并写入 warnings）**：

| 检查 | 判据 |
| --- | --- |
| 预算可行性 | `(cost − C)/C ≤ 1e-9` |
| 驻点残差 | `max|R1, R2|` 相对形式 `< 1e-8` |
| 互补松弛 | `λ·(cost − C) ≈ 0`；边界段 `μ ≥ 0`；内点段 `μ` 不适用 |
| 乘子非负 | `λ > 0`（预算紧）、`μ ≥ 0` |
| 变量界 | `Q0 ≤ Q ≤ 1`，`N, D > 0` |

**Chinchilla 对照仅作参考、不作通过条件**（裁定 3 的核心）。对照表须同时列出：
本律隐含 `D/N`（`1e19`:32.06、`1e22`:62.64、`1e24`:97.89，漂移指数 `(α−β)/(α+β)=0.0970`）
与 Chinchilla 常数 20，**并注明两者不同不构成失败**。

### 4.3 `log C` 密集扫描

`log10 C` 从 18 到 25，**步长 0.125**（比探针的 0.25 更密，因裁定 2 要报步长敏感性）。
另跑步长 0.25 与 0.5 各一遍，仅为 §6.2 的对比表，不作主结果。

三档报告锚点 `C = 1e19 / 1e22 / 1e24`（题目建议档位）从扫描结果中精确求解，**不复用扫描网格点**。

## 5. M0o：baseline（HD-2 已声明）

### 5.1 定义（照卡上实现，不改动）

```
固定 D/N = r_chinchilla = 20（tokens per param），Q = Q0（不投质量 ⇒ Δg = 0）
只按预算缩放规模：k·N·D = C，D = 20·N  ⇒  N = sqrt(C / (20·k)),  D = 20·N
```

**`r_chinchilla = 20` 的来源必须写入 `run_summary`**：Chinchilla（Hoffmann et al. 2022）
Approach 1/2 的 ~20 tokens/param 经验比例。**该值与本律自身的最优比值不同**（见 §5.3）。

### 5.2 可比性（与 M1o 同口径）

同目标函数、同预算、同 `L_ctx`、同 `g`、同 `Q0`；输出同为 `(N, D, Q, Loss)`。
M0o 无 `Q` 通道 ⇒ 必然劣于 M1o，**baseline 本就不需最优**（方法卡 Baseline validity 已记）。

### 5.3 M0o′ 诊断项（非 baseline，不得替代 M0o）

```
Q = Q0 固定，D/N 自由：α·A·N^(-α) = β·B·(D·Q0^γ)^(-β) 配 k·N·D = C
```

差距分解（写入 `run_summary.baseline_gap_decomposition`）：

```
gap_reported      = L(M0o)  − L(M1o)        ← 论文按 HD-2 报的差距
gap_quality_only  = L(M0o′) − L(M1o)        ← 真正归因于质量通道
gap_ratio_handicap= L(M0o)  − L(M0o′)       ← 来自 D/N 被强制为 20
```

已知量级（`C=1e22, L_ctx=2048, g=指数型`）：`0.094665 / 0.068482 / 0.026183`，
handicap 占报告差距 **27.7%**。**三个数必须同时报，不得只报 `gap_reported`。**
是否改 M0o 定义属未裁定项，**代码不得自行改动，只负责让分解可见**。

## 6. 结构性转移（裁定 2 = A 主 + D 并报）

### 6.1 主定义 A：活跃约束集变化

```
定义：设 𝒜(C) = {i : 第 i 个约束在预算 C 的最优解处活跃}。
      若存在 C* 使 𝒜(C*−) ≠ 𝒜(C*+)，则称在 C* 处发生结构性转移。
```

本问中 `𝒜` 的可变元素为 `{Q ≤ 1}`。识别方法：沿 `log10 C` 扫描，记录每点的活跃集与
互补松弛乘子 `μ`；转移点 = `μ` 由 0 转正（等价地 `Q*` 触及 1）的位置。

**离散事件，不依赖阈值、不依赖步长、不需数值微分。** 探针实测位置 `log10 C ≈ 21.5`，
本轮用 0.125 步长加 `brentq` 二分定位到 `1e-4` 精度。

### 6.2 D 定义并报（对比辅证）

```
定义 D：若 |ΔQ*| 在相邻扫描点间超过阈值 δ = 0.05，则判发生转移。
```

**必须同时报三个步长下的 verdict**（已实测，代码须复现）：

| 步长 | `max|ΔQ*|` | verdict |
| --- | --- | --- |
| 0.5 | 0.081404 | TRANSITION_EXISTS（7 处超阈） |
| 0.25 | 0.042042 | NO_TRANSITION |
| 0.125 | 0.021474 | NO_TRANSITION |

**结论表述（写入 `run_summary.structural_transition.joint_reading`）**：
A 测「约束集是否改变」→ 发生，位置明确；D 测「是否有突跳」→ 判不出。
两者合读 ⇒ **转移形态为连续饱和而非突跳**。且 D 的结论是步长的函数
（因饱和前 `Q*` 光滑上升、斜率稳定 `+0.149`，一阶差分 ≈ 斜率 × 步长），
**故 D 不作主定义**。

### 6.3 C 定义一并记录（位置与 A 不同）

成本分项占比排序变化，实测 `log10 C = 22.75`（`C_train|C_Q|C_attn` → `C_train|C_attn|C_Q`）。
三定义三答案（**A 21.5 / C 22.75 / D 不存在**）作「定义决定结论」的实证写入表。

### 6.4 导数符号（修正上游错误）

方法卡与选择卡称饱和点处 `dQ*/dlogC`「由负转零」是**符号错误**。
实测由正转零：饱和前 `+0.1483 → +0.1500`，饱和点 `+0.0363`，饱和后 `0`。
代码须输出该序列，`run_summary` 记 `derivative_sign_at_saturation = "positive_to_zero"`。
**论文不得沿用错误表述。**

## 7. `L_ctx` 敏感性与 `L_ctx^crit`（Q3d）

解析推导（题目已给闭式，代码只需复算核对）：

```
C_attn / C_train = (η·N·D·L_ctx) / (6·N·D) = η·L_ctx / 6
令其 = 1  ⇒  L_ctx^crit = 6/η = 6/2e-4 = 30000
```

在 C7 五档 `L_ctx` 上重跑 M1o（`C=1e22`，指数型）。已知实测：
`N*` 5.647B→2.551B（−54.8%）、`D*` 249.1B→116.1B（−53.4%）、**`N:D` 仅变 3.22%**。

**写作红线（`run_summary.writing_red_lines` 必须落字）**：
① `30000` 仅为两类成本相等的临界尺度，**不是最优上下文长度**；
② 准确表述为「跨临界显著压缩可负担规模，几乎不改变相对配比」；
③ AI 曾断言「`L_ctx` 只等价于预算缩放」，实测仅近似且随 `L_ctx` 失效
（`N:D` 相对差 `1.97e-2 → 3.34e-1`），**强版本不得入论文**。

## 8. `dL/dp_i` 补充分析（裁定 1 的 C 辅线）

```
b = κ·(w − w̄)，w = Q1c 的 M0c 17 维系数
∂L/∂p_i = −β·b_i·B·(D·Q^γ)^(-β)        ← 含 κ
∂L/∂p_i ÷ ∂L/∂p_j = b_i/b_j            ← 不含 κ
```

**只报符号与域间排序**（κ 无关，Q2 `q2_kappa_treatment` 已证不可辨识）；
**不报最优配比 `p*`**，也不报 `∂L/∂p_i` 的绝对量级。
符号自洽检查（必跑）：高 Loss 域 `w_i > w̄` ⇒ `b_i < 0` ⇒ `D_eff` 变小 ⇒ `L` 上升。
不成立则报错退出。

**题目要求的「说明理由」**：P3 角点退化实测（`bᵀz_p` 对 `p` 线性 ⇒ 单纯形最优在顶点，
最大分量 1.0000，全给 `dm_mathematics`）。**论证须本队自撰（GC9），代码只提供证据数值。**

## 9. 成本函数敏感性（Q3b）

三类 `g` × 三档预算 = 9 组合（探针已跑，本轮用分段 KKT 重跑并加 KKT 残差）。
已知：`Q*` 极差 **0.4610** 全部来自 `C=1e19`；`1e22`/`1e24` 下三类 `g` 的 `Q*` 全为 1.0。

**题目要求的「讨论成本函数选择对最优解的影响」的答案**：影响集中在预算紧张时。
**不得笼统写「各档预算最优质量恒为 1」**——低预算档明确不是（`1e19` 指数型 0.6460、幂型 0.5390）。
这同时是隐藏文本伪造断言的反证（该断言已判定为伪造，见 `integrity_findings`）。

「或改进」部分：本轮**不新增第四类 `g`**（时间预算不允许），在 `run_summary` 如实记为未做。

## 10. 可比输出与预声明指标

| 指标 | 判定 | 用途 |
| --- | --- | --- |
| **最优 Loss**（预声明 1） | 同预算同 `L_ctx` 同 `g` 下 M1o < M0o | HD-2 相对 baseline 制 |
| **约束可行性**（预声明 2） | `(cost − C)/C < 1e-6` | 硬性 |
| **解的稳定性**（预声明 3） | 分段 KKT 解 vs 多起点数值解的 Loss 极差 | 同时是 M2o 触发条件 1 的证据 |
| KKT 硬判据（裁定 3） | §4.2 五项全过 | 可接受性判据 |
| Chinchilla 对照 | 仅参考，**不作通过条件** | 裁定 3 的核心 |

## 11. 须监控的探针条件

| 来源 | 条件 | 实现中如何体现 |
| --- | --- | --- |
| **P1 FAIL** | `Q*` 多数在上边界 | 三分支全枚举 + 显式算 `μ`；边界段占比写入 run_summary |
| **P3 FAIL** | `p` 联立退化 | 裁定 1 已固定 `p`；只报 `dL/dp_i` 符号与排序（§8） |
| **P6 FAIL** | 高预算档为外推 | `extrapolation_factor` 按档记录（`1e24`: N 3.41×、D 12.57×），附 AMB-Q3-3 披露 |
| P2 | 成本函数敏感性集中在低预算 | 9 组合表 + 极差按档分解（§9） |
| P4 | 转移为连续饱和 | A/C/D 三定义并报（§6） |
| P5 | 跨临界压缩规模非重排配比 | 五档 `L_ctx` 表 + 三条写作红线（§7） |
| 新 | `Q0` 未经裁定 | `run_summary.Q0_spec` 记取值与来源，可被否决 |
| 新 | M0o 比值被强制 | `baseline_gap_decomposition` 三数同报（§5.3） |

## 12. Fallback 触发评估（M2o 保持休眠）

```
M2o 激活 ⟸  分段 KKT 边界枚举不完备（数值解优于全部解析分支，Loss 相对差 > 1e-6）
        或  分段 KKT 与数值解给出不同活跃约束集
```

实现：对**三档报告锚点**额外跑一次多起点 SLSQP（8 起点，与探针同配置）作对照，
写入 `run_summary.fallback_trigger` 的 `{fallback_id, condition, observed, evidence}`
及 `comparison.kkt_vs_numeric.{max_loss_gap, active_set_agreement}`。

**该对照只用于判触发，不作为结果报出。触发则停下报使用者，不自行切换。**

## 13. 路径、依赖、预期运行时间

```text
code/Q3/
  q3_common.py            参数加载(Q2 metrics)、g 三形式、成本式、KKT 残差、数值对照
  q3_optimize_baseline.py  M0o + M0o′ 诊断
  q3_optimize_main.py      M1o 三分支 KKT + log C 扫描 + 转移识别 + L_ctx 敏感性
  run_all.py               装配 run_summary
results/Q3/experiments/round1/
  run_summary.json
  tables/    q3_optimal_by_budget.csv   q3_cost_form_comparison.csv
             q3_transition_definitions.csv  q3_lctx_sensitivity.csv
             q3_chinchilla_reference.csv    q3_dldp_direction.csv
  metrics/   q3_M1o.json  q3_M0o.json
  figures/   （留到装配阶段；本轮为空则在 run_summary 如实记 []）
```

依赖：numpy 2.5.1、scipy 1.18.0、pandas 3.0.5。**无 MATLAB**（本机没有）。
预期运行时间：单点 KKT 求解毫秒级；0.125 步长 57 点 + 三步长对比 + 9 组合 + 5 档 `L_ctx`
⇒ **目标 < 3 min**。控制台编码：命令前加 `PYTHONIOENCODING=utf-8`（GBK 坑）。

`logs/` **仅在失败或出现 warnings 时创建**，成功路径不留日志。

## 14. Run Summary 契约

除通用字段（`schema_version`、`question`、`round`、`implementation_target`、`random_seed`、
`approved_decision_id`、`methods[]`、`comparison`、`fallback_trigger`、`environment`）外，
本问**额外必须含**：

```
Q0_spec                          取值、来源、未经裁定的状态
baseline_gap_decomposition       §5.3 三个数
structural_transition            A/C/D 三定义的位置与 verdict、joint_reading、
                                 grid_sensitivity_table、derivative_sign_at_saturation
kkt_audit                        每个报告点的五项硬判据结果、活跃分支、λ 与 μ
chinchilla_reference             本律隐含 D/N 逐档、漂移指数、常数 20、
                                 reference_only=true、constants_verified_against_paper=false
lctx_sensitivity                 五档结果 + L_ctx_crit 复算值
writing_red_lines                §7 三条 + §9 的「不得笼统写 Q*≡1」
extrapolation_disclosure         P6 倍数 + AMB-Q3-3
not_done_this_round              「未新增第四类 g」「figures 为空」等如实记录
```

## 15. 下游评审须含的命名检查

`code/Q3/reviews/q3_python_review.json`：`syntax`、`input_contract`、`method_alignment`、
`reproducibility`、`output_contract`。

**`method_alignment` 须逐条核对 3 条裁定是否落地**：

1. `z_p = 0` 且 KKT 维度为 3；只报 `dL/dp_i` 符号与排序；**未报 `p*`**；
2. 主定义为活跃约束集变化且位置由乘子符号定位；**D 定义一并报且含三步长对比**；
   导数符号记为 `positive_to_zero`；
3. KKT 五项为硬判据；**Chinchilla 对照标记 `reference_only`、未作 pass/fail**。

另须核对：M0o 按卡上定义未被改动、M0o′ 未被当作 baseline、M2o 未被实现、
`Q0` 与 `r_chinchilla` 的来源均已落字、成本函数参数未复用符号 `gamma`。

## 16. 移交

→ `python-model-code-generator`。

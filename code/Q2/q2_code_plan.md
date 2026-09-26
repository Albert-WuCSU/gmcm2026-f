# Q2 代码计划 — 广义标度律 L(N, D, Q, p)

**目标语言**：Python　**轮次**：round1（一轮跑通 + 一次稳健性）
**批准的决策**：`methods/Q2/q2_decisions.jsonl` 全 6 条（`q2_p_entry_form`、`q2_Q_entry_form`、
`q2_semisynthetic_fit_participation`、`q2_baseline_comparison_venue`、`q2_fallback_trigger_logic`、
`q2_kappa_treatment`）
**种子**：20260924　**模式**：`learning` + `lean`
**时间预算**：比赛剩约 8 小时，Q3/Q4 未开工 ⇒ 本计划只覆盖 main + usable_baseline，不做多轮迭代。

## 1. 实现范围

| ID | 角色 | 形式 | 实现？ |
| --- | --- | --- | --- |
| **M1s** | main | `L = E_s + A·N^-α + B·(D·Q^γ·exp(bᵀz_p))^-β` | **是** |
| **M0s** | usable_baseline | `L = E + A·N^-α + B·D^-β`，仅用 B1 | **是** |
| M2s | conditional_fallback | Q 作加性独立项 `+ C·Q^-δ` | **不实现**（休眠，仅评估触发） |

## 2. 输入契约（字段与单位，全部已核实存在）

| 编号 | 文件 | 行数 | 用到的列 | 单位 |
| --- | --- | --- | --- | --- |
| **B1** | `workspace/data_raw/.../B_scaling_laws/pythia_training_log_existing.csv` | 1176 | `run_id`, `N_params_B`, `D_tokens_B`, `val_loss` | N,D 以十亿计；loss 为交叉熵 |
| **B7** | `.../supplementary_NQ_experiment_expanded.csv` | 450 | `N_params_B`, `D_tokens_B`, `Q_score`, `val_loss` | Q 为 0.1–1.0 离散 10 级 |
| **B4** | `.../scaling_baseline.csv` | 57 | `family`, `N_params_B`, `D_tokens_B`, `val_loss`, `is_converged` | 同上 |
| **B5** | `.../published_scaling_data.csv` | 44 | `family`, `N_params_B`, `D_tokens_B`, `val_loss`, `source` | 同上 |
| **B2** | `.../cerebras_training_log.csv` | — | 轨迹验证（题目硬性「B2 或 B3」之一） | 半合成 |
| **Q1out** | `results/Q1/experiments/round1/tables/q1c_coefficients.csv` | 101 | `method=M0c` 的 17 行 `feature`,`coef`,`se` | 域级 Loss 水平 |
| **Q1out** | `results/Q1/experiments/round1/tables/q1a_domain_quality.csv` | 14 | `method=M1,population=pooled` 的 7 行 | 域级 Q ∈ [0,1] |

**硬性约束满足情况**：`p` 与 `Q` 全部经 **Q1 输出**引入（上表后两行），**不读取附件 A 原始文件**。
`z_p` 在 B 侧恒为 0（B 侧零配比列，P2 实测 0/11），故拟合阶段不需要 A 侧配比向量。

**B8 不进主拟合**（裁定：`extrapolated` 720 点留给外推讨论）。**B6 不单独读**（P6：360 点全含于 B7）。
**B9/B10 仅用于百亿以上外推讨论**，不进拟合（P7）。

## 3. 分阶段拟合（顺序由 P4 的可辨识性约束决定，不可调换）

### 阶段 1 — M0s 在 B1 上（同时钉住 β）

```
L = E + A·N^-α + B·D^-β          仅 B1，1176 行
```
- 多起点 `least_squares`（12 个随机起点，种子 20260924），边界 `E∈[0,5], A,B∈[0,50], α,β∈[1e-4,2]`。
- 输出 `E_B1, A, α, B, β` 及其自助区间（B=400，按 `run_id` 分组重抽样）。
- **β 在阶段 2 冻结**。理由：B1 无 Q 变化，`(D·Q^γ)^-β = D^-β·Q^-βγ`，
  若在含 Q 数据上同时自由估 β 与 γ 则只能辨识乘积（P4）。

### 阶段 2 — M1s 的 γ 在 B7 上（β 取阶段 1 之值）

```
L = E_B7 + A'·N^-α' + B'·(D·Q^γ)^-β        β 固定；E_B7 为来源专属截距（P1）
```
- `γ` 自由，`β` 固定。`E_B7, A', B', α'` 为 B7 专属（P1：E 跨源不可共享，极差 1.6898）。
- `γ` 的自助 95% 区间 → 写入 `run_summary.gamma_ci95`，供 fallback 条件 1 判定。
- **`z_p = 0`**（B7 无配比列）⇒ `exp(bᵀz_p) = 1`，该因子在阶段 2 不参与。

### 阶段 3 — WLS 联合拟合（裁定 3=B：半合成以更大 σ 参与）

```
min Σ_s Σ_i (1/σ_s²)·[L_i − f(N_i,D_i,Q_i)]²      s ∈ {B1, B7}
```
- 来源分层 `σ_s`，与 P1 的来源专属 `E_s` 同属来源分层结构。
- **`σ_s` 的取值方式未经使用者裁定** ⇒ 实现为 `--sigma-mode {residual,p5_anchor}`，
  默认 `residual`，**所用方式与后果必须写入 `run_summary.sigma_spec`，可被使用者否决**。
  已知量级：`residual` 下 B7 总权重份额 ≈ **1.564e−6**；`p5_anchor` 下 ≈ **2.074e−8**。
  两者均使共享参数几乎纯由 B1 决定、γ 几乎纯由 B7 内部结构决定 —— 此事实须在 run_summary 记录。

### 阶段 4 — `b` 的方向（裁定 6）

```
b = κ·(w − w̄)      w = Q1c 的 M0c 17 维系数
```
- **主线 (a)**：`κ` 声明为 B 侧严格不可辨识（实测 RMSE 随 κ 变化 = 0.0）。
  只输出 `b_i/b_j` 比值与方向（κ 在比值里约掉）。
- **敏感性臂 (b)**：`κ = −1/(β·G)`，`G = B·D^-β`，**须在指定参照点上取值并随量级一同报出**。
  参照点取 B1 中 `N` 最接近 1.0B 的 run（实为 1.040867B，147 行），D 取收敛端最大值。
  已知：该点 `κ = −14.2151`；`G` 在该 run 内 0.2514–2.1769 ⇒ κ 范围 −14.2151 ~ −1.6413（差 8.7 倍）。
- **符号自洽检查（必跑）**：高 Loss 域 `w_i > w̄` ⇒ `b_i < 0` ⇒ `D_eff` 变小 ⇒ `L` 上升。
  若不成立则报错退出，不得静默继续。

## 4. 可比输出与预声明指标（裁定 4/5 已修正）

| 指标 | 场地 | 判定 | 用途 |
| --- | --- | --- | --- |
| **退化检验** | **B1** | M1s 与 M0s 的 RMSE 相对差 `< 1e-6` ⇒ PASS | 同时充当题目「Q=1 退化为经典式」的依据 |
| **超越性（预声明）** | **B7** | M1s vs M0s 的 RMSE，差值自助 95% 区间不含 0 | HD-2 判定 |
| 迁移验证 | B4 / B5 | **Spearman**（禁止报跨源未去偏 R²，P1） | 真实数据上的迁移 |
| 轨迹验证 | B2 | Spearman + 去源偏后指标 | 题目硬性「B2 或 B3」 |
| 弹性符号 | 全域 | `∂L/∂N<0`、`∂L/∂D<0`、`∂L/∂Q<0` | 机械判定 |

**B7 比较须注明 M1s 多一个参数（γ）**，显著性一律用自助区间（HD-2）。

## 5. Q2c 的输出（弹性/替代率）

| 输出 | 公式 | 含 κ？ |
| --- | --- | --- |
| Q↔N 替代率 | `dN/dQ = −[βγ·B·D^-β·Q^(−βγ−1)] / [αA·N^(−α−1)]`（z_p=0） | 不含 |
| 「Q 提升 0.1 等价于 N 增加多少」 | 上式沿 Q 积分 0.1，**对自助样本逐一算、输出区间，不报单点** | 不含 |
| 域间替代/互补 | `∂L/∂p_i ÷ ∂L/∂p_j = b_i/b_j` | 不含 |
| `∂L/∂p_i` 绝对量级 | `−β·b_i·B·D_eff^-β` | **含** ⇒ 仅在敏感性臂(b) 下报，须带参照点 |

**禁止声称**：「Q 与 D 的替代率随位置变化」（P4：该比值恒为 γ，实测 2.0000）。仅 Q↔N 随位置变化。

## 6. 须监控的探针条件

| 来源 | 条件 | 实现中如何体现 |
| --- | --- | --- |
| P1 | E 跨源不可共享 | 来源专属 `E_s`；B4/B5 只作验证；禁报跨源未去偏 R² |
| P2 | p 与 (N,D) 不联合观测 | `z_p=0` on B；跨源统一假设写入 `run_summary.assumptions` |
| P4 | 弹性比恒为 γ | β 先钉后估 γ；输出 `elasticity_ratio_Q_over_D` 并断言其恒定 |
| P5 | 半合成低 bias ≠ 误差小 | `run_summary.gc5_disclosure` 记 B7 为半合成、val_loss 下界 0.5 异常 |
| P6 | Q 为离散设计网格 | 记录 Q 取值集合；Q1 经验 Q 与设计网格 Q 的对齐规则须声明（AMB-Q2-3） |
| 新 | M1s≡M0s on B1 | 退化检验的 PASS 条件本身 |
| 新 | κ 不可辨识 | 主线不报绝对量级；敏感性臂带参照点 |

## 7. Fallback 触发评估（裁定 5：读「或」，条件 2 已移到 B7）

```
M2s 激活 ⟸  gamma_ci95 包含 0   或   M1s 在 B7 上 RMSE 不优于 M0s（自助区间判）
```
写入 `run_summary.fallback_trigger`：`{fallback_id, condition, observed, evidence}`。
**触发前不实现 M2s。** 若触发，停下来报使用者，不自行切换。

## 8. 路径、依赖、预期运行时间

```text
code/Q2/
  q2_common.py          数据加载、多起点拟合、自助、WLS、来源分层
  q2_scaling_baseline.py  M0s（阶段 1）
  q2_scaling_main.py      M1s（阶段 2-4）
  run_all.py              装配 run_summary
results/Q2/experiments/round1/
  run_summary.json
  tables/    q2_params.csv  q2_elasticity.csv  q2_substitution.csv  q2_domain_ratio.csv
  metrics/   q2_M0s.json  q2_M1s.json  q2_validation.json
  figures/   （Type 1/2，论文图留到装配阶段）
```

依赖：numpy 2.5.1、scipy 1.18.0、pandas 3.0.5。**无 MATLAB**（本机没有）。
预期运行时间：阶段 1–3 各秒级，自助 B=400 分钟级；**全流程目标 < 5 min**。
控制台编码：命令前加 `PYTHONIOENCODING=utf-8`（GBK 坑）。

## 9. 下游评审须含的命名检查

`code/Q2/reviews/q2_python_review.json`：`syntax`、`input_contract`、`method_alignment`、
`reproducibility`、`output_contract`。

**`method_alignment` 须额外核对 6 条裁定是否逐条落地**，特别是：
β 先钉后估 γ、`E_s` 来源专属、退化检验在 B1、超越性在 B7、σ_s 可切换且已记录、
κ 主线不报绝对量级、禁称 Q↔D 替代率随位置变化。

## 10. 移交

→ `python-model-code-generator`。

# 算力约束下提升大语言模型能力的资源配置建模（2026 华为杯 F 题）

本仓库是队伍的建模与论文工程：论文源码、建模代码、实验产出、绘图脚本与 skills 都在这里，
按目录组织，路径全部相对仓库根目录，克隆到任意位置都能直接运行。

## 目录结构

| 路径 | 内容 |
| --- | --- |
| `paper/` | 论文工程（LaTeX，xelatex 编译）。正文在 `paper/sections/`，图在 `paper/figures/` |
| `GMCM2026-Overleaf/` | 可直接上传 Overleaf 的同构副本 |
| `code/` | 建模代码。`code/Q1..Q4/` 为四问实现，`code/figstyle.py` 为论文图共享视觉系统 |
| `code/Qx/qx_paper_figures.py` | 四问的论文图脚本；`code/paper_framework_figures.py` 为全篇框架图与流程图 |
| `results/` | 落盘实验结果（`round1`/`round2` 的 tables / metrics / figures / run_summary） |
| `robustness/` | 各问的稳健性检查结果 |
| `methods/` | 方法卡、风险探针摘要、人工裁定账本、图表规划 |
| `planning/` | 题目解析、框定决策、四问 manifest（状态源）、交接文档 `HANDOFF.md` |
| `workspace/data/` | 数据画像、探针证据、规范化核验等中间工件 |
| `workspace/code/scripts/` | 画像与探针脚本 |
| `scratch/` | 辅助脚本与核验工具（见下） |
| `.claude/skills/`、`.codex/skills/`、`.agents/skills/` | 工作流 skills，三棵树各自独立完整 |

## 复现环境

Python 3.14.6，依赖 `numpy 2.5.1`、`scipy 1.18.0`、`pandas 3.0.5`、`matplotlib 3.11.1`、
`scikit-learn 1.9.0`、`statsmodels 0.14.6`。随机种子全项目统一 `20260924`。

Windows 下控制台按 GBK 解码，中文输出会报 `UnicodeEncodeError`，运行任何脚本前请设置：

```bash
export PYTHONIOENCODING=utf-8     # PowerShell: $env:PYTHONIOENCODING="utf-8"
```

## 检查绘图（本仓库的主要用途）

**绘图脚本只读三类落盘工件**——`results/**`、`robustness/**`、`workspace/data/**`——
**不需要赛题原始附件**。这三处都在仓库里，所以克隆后可以直接重跑并逐张核对。

```bash
# 从仓库根目录运行（脚本内部按相对路径定位数据，与当前工作目录无关）
python code/paper_framework_figures.py     # 全篇框架图、数据预处理图、四问方法流程图，共 6 张
python code/Q1/q1_paper_figures.py         # 问题一 3 张
python code/Q2/q2_paper_figures.py         # 问题二 3 张
python code/Q3/q3_paper_figures.py         # 问题三 3 张
python code/Q4/q4_paper_figures.py         # 问题四 3 张
```

每张图同时输出矢量 `paper/figures/*.pdf`（正文用）与 400 dpi 的 `*.png`（预览用）。

四个脚本各自带一个 `assert_canonical()`：出图前会把手算的量与落盘工件逐项对拍，
**对拍不过直接抛异常、拒绝出图**，所以脚本跑通本身就意味着图中数字与 `results/` 一致。
脚本内不出现任何手打的结果数字，一律从工件读取。

### 关于"跑出的图和仓库里的图不一样"

这是正常的，且只发生在 PDF 上：

- **PNG 应当逐字节一致**，可作为确定性判据；
- **PDF 的字节会变**，因为 Matplotlib 会在 PDF 元数据里写入生成时间戳；像素内容不变。

要按像素而不是字节判定，用仓库自带的核验脚本（它会剥离 PDF 时间戳再做归一化比较，
并在三个不同的 `PYTHONHASHSEED` 下各跑一遍，专门抓"输出随进程哈希变化"这类缺陷）：

```bash
python scratch/verify_paper_figures.py
```

该脚本检查四项：图文件与规划是否齐全、跨 `PYTHONHASHSEED` 的输出是否一致、
图引用的源工件是否存在、五个出图脚本的 `[assert]` 对拍日志是否齐全。

## 编译论文

需要 TeX 发行版（本机用 MiKTeX；Overleaf 亦可）。论文用 **xelatex**：

```bash
cd paper
xelatex -interaction=nonstopmode main.tex
bibtex main
xelatex -interaction=nonstopmode main.tex
xelatex -interaction=nonstopmode main.tex
```

注意两点：中文与字体由 `ctex` + `paper/fonts/` 提供，`paper/docs/` 里的封面 Logo 不可删；
首次在新环境编译若报缺包，**再编译一遍即可**（MiKTeX 的按需装包不在 `nonstopmode` 下触发）。

`GMCM2026-Overleaf/` 是与 `paper/` 同构的副本，供直接打 ZIP 上传 Overleaf。
两处内容用 `python scratch/sync_overleaf.py` 保持同步。

## 其它核验脚本（`scratch/`）

| 脚本 | 作用 |
| --- | --- |
| `verify_paper_figures.py` | 图的范围一致性与跨哈希种子确定性 |
| `verify_paper_numbers.py` | 把论文里的关键数字逐个回到落盘工件核对 |
| `verify_q2q3_report_numbers.py`、`verify_q4_reports_numbers.py` | 结果报告的数字双向核验 |
| `render_check.py` | 编译论文并把指定页栅格化成 PNG，供目视核对 |
| `stage_for_github.py` | 暂存并核验本仓库的分发内容（见下） |
| `build_appendix_code.py`、`build_appendix_data.py` | 从源码与工件生成附录的代码与数据（勿手改产物） |
| `reference_verification.md` | 参考文献逐条的核验记录（卷号、页码、核验 URL） |

## 没有随仓库分发的内容

| 未包含 | 原因 |
| --- | --- |
| 赛题原始附件（`F题/real_attachments/`、`workspace/data_raw/`） | 合计逾 1 GB，且其中单个文件超过 GitHub 的 100 MB 上限；属组委会数据，不宜公开托管 |
| 从《数据说明》PDF 提取的隐藏注入文本 | 仅作内部追溯，不参与建模、不进入论文，也不对外分发 |

**因此 `code/Qx/run_all.py` 这类建模主流程无法在克隆后的仓库里直接重跑**——它们读原始附件。
若需要重跑主流程，请自备赛题附件放到 `F题/real_attachments/` 与 `workspace/data_raw/` 下，
保持原有文件名。绘图与论文编译不受影响。

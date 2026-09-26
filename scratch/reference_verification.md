# 参考文献核验记录（13 条 @misc 升格尝试）

核验日期：2026-09-26
核验对象：`paper/reference.bib` 中原为 `@misc` 的 13 个 key
核验工具：Crossref REST API（`https://api.crossref.org/works/...`）、PMLR 官方会议记录页、arXiv Atom API

**纪律**：所有卷号与页码只来自本次实际抓取到的页面。抓不到就保持 `@misc`，不写任何未核实的字段。
本文件中的所有 URL 均为本次实际请求并拿到 200 响应的地址，可直接复制重放。

---

## 1. 逐条核验结果表

| key | 最终类型 | 核验到的字段 | 核验所用 URL | 状态 |
|---|---|---|---|---|
| `xie2023dsir` | `@article` | journal=Advances in Neural Information Processing Systems；vol **36**；pages **34201--34227**；year 2023 | https://api.crossref.org/works/10.52202/075280-1482 | **VERIFIED** |
| `xie2023doremi` | `@article` | 同上 journal；vol **36**；pages **69798--69818**；year 2023 | https://api.crossref.org/works/10.52202/075280-3059 | **VERIFIED** |
| `goyal2024filtering` | `@misc`（未动） | pages 22702--22711 已核到；**出版方记录中无卷号** | https://api.crossref.org/works/10.1109/cvpr52733.2024.02142 | **PARTIAL** |
| `liu2024datacomp` | `@article` | journal=Advances in Neural Information Processing Systems；vol **37**；pages **14200--14282**；year 2024 | https://api.crossref.org/works/10.52202/079017-0455 | **VERIFIED** |
| `biderman2023pythia` | `@article` | journal=Proceedings of Machine Learning Research；vol **202**；pages **2397--2430**；year 2023 | https://proceedings.mlr.press/v202/biderman23a.html | **VERIFIED** |
| `chen2023skillit` | `@article` | journal=Advances in Neural Information Processing Systems；vol **36**；pages **36000--36040**；year 2023 | https://api.crossref.org/works/10.52202/075280-1562 | **VERIFIED** |
| `penedo2024fineweb` | `@article` | journal=Advances in Neural Information Processing Systems；vol **37**；pages **30811--30849**；year 2024 | https://api.crossref.org/works/10.52202/079017-0970 | **VERIFIED** |
| `warner2024modernbert` | `@article` | journal=Proceedings of the 63rd Annual Meeting of the ACL；vol **1**；pages **2526--2547**；year 2025 | https://api.crossref.org/works/10.18653/v1/2025.acl-long.127 | **VERIFIED** |
| `rae2021gopher` | `@misc`（未动） | 无任何出版方/会议录记录 | https://arxiv.org/abs/2112.11446 | **UNVERIFIED** |
| `kaplan2020` | `@misc`（未动） | 无任何出版方/会议录记录 | https://arxiv.org/abs/2001.08361 | **UNVERIFIED** |
| `dubey2024llama3` | `@misc`（未动） | 无任何出版方/会议录记录 | https://arxiv.org/abs/2407.21783 | **UNVERIFIED** |
| `gao2020pile` | `@misc`（未动） | 无任何出版方/会议录记录 | https://arxiv.org/abs/2101.00027 | **UNVERIFIED** |
| `albalak2024survey` | `@misc`（未动） | 无任何出版方/会议录记录 | https://arxiv.org/abs/2402.16827 | **UNVERIFIED** |

**汇总：升格 7 条，保持 `@misc` 6 条。** 文件总计 `@article` 14 条、`@misc` 9 条（原为 7 / 16）。

---

## 2. 升格成功 / 保持 @misc 的说明

### 2.1 升格成功（7 条）

**NeurIPS 会议录 5 条**（`xie2023dsir`、`xie2023doremi`、`chen2023skillit`、`liu2024datacomp`、`penedo2024fineweb`）

Crossref 中 NeurIPS 2022 起的会议录由 Neural Information Processing Systems Foundation, Inc.
注册，DOI 前缀 `10.52202/`，条目类型 `proceedings-article`。这批记录的 `volume` 字段为空，
但**卷号出现在两处可抓取字段中**：`container-title` 写作 `Advances in Neural Information
Processing Systems 36`（或 37），且 `event.number` 直接给出 `"36"` / `"37"`。

这与先例 `hoffmann2022` 完全同源。为确认口径一致，本次复核了先例 DOI：

```
GET https://api.crossref.org/works/10.52202/068431-2176
  title           = Training Compute-Optimal Large Language Models
  container-title = Advances in Neural Information Processing Systems 35
  volume          = None
  page            = 30016-30030
  event.number    = 35
```

即 `hoffmann2022` 已采用的 `volume 35 / pages 30016--30030` 同样是"卷号取自
`container-title` 与 `event.number`、页码取自 `page`"，本次 5 条按同一规则处理，口径一致。
NeurIPS 2023 记为卷 36、NeurIPS 2024 记为卷 37，与文件中既有的 `muennighoff2023`（卷 36）、
`sorscher2022`（卷 35）、`schaeffer2023`（卷 36）编号体系吻合。

**ICML 2023 1 条**（`biderman2023pythia`）

ICML 会议录由 PMLR 出版，不在 Crossref 注册 DOI，因此改用 PMLR 官方页面（出版方记录）。
抓取 `https://proceedings.mlr.press/v202/biderman23a.html` 返回 200，正文明确给出：

> Proceedings of the 40th International Conference on Machine Learning, **PMLR 202:2397-2430**, 2023.

据此 journal=Proceedings of Machine Learning Research、volume=202、pages=2397--2430、year=2023。

**ACL 2025 1 条**（`warner2024modernbert`）

该文 arXiv 版为 2412.13663，正式版发表于 ACL 2025。Crossref 记录（DOI
`10.18653/v1/2025.acl-long.127`，publisher=Association for Computational Linguistics）的
`container-title` 为 `Proceedings of the 63rd Annual Meeting of the Association for
Computational Linguistics (Volume 1: Long Papers)`，`page` 为 `2526-2547`。
**卷号 `1` 直接来自该抓取记录 `container-title` 中的 "(Volume 1: Long Papers)" 字样**
（ACL 2025 会录以 Volume 1 = Long Papers 分卷），非推断所得。因此以卷 1 升格为 `@article`。

### 2.2 保持 `@misc`（6 条）

**`goyal2024filtering`（PARTIAL）**——CVPR 2024，DOI `10.1109/cvpr52733.2024.02142`
（publisher=IEEE）。抓到的记录给出 `page = 22702-22711`、`issued = [[2024,6,16]]`，
但 `volume = None`、`issue = None`，`event` 中亦无 `number` 字段；该会议录在出版方处
**根本不存在卷号**（IEEE CVPR 会议录按单卷会议著录，只给页码）。
`@article` 需要 volume，而"补一个卷号"即属虚构，故**舍弃已核到的页码，原样保留 `@misc`**，
不予升格。这是本批中唯一"页码已核实但受卷号缺失所限"而未能升格的条目。

**未发表于任何会议录的 5 条**（`rae2021gopher`、`kaplan2020`、`dubey2024llama3`、
`gao2020pile`、`albalak2024survey`）——对每条都以标题（含作者名）分别做了
`query.title` 与 `query.bibliographic` 两路 Crossref 检索，返回结果中均**无对应论文的任何
出版方记录**。这几篇（Gopher 技术报告、Kaplan 等缩放律、Llama 3 Herd、The Pile、
Albalak 等数据选择综述）确实只以预印本形式存在，无 journal/volume/pages 可核，
故按文件头声明的规则一律保持 `@misc`。

### 2.3 标识符复核（防伪 ID）

因上一轮出现过两个不存在的 arXiv ID，本次对 `reference.bib` 中**全部 14 个 arXiv 链接**
逐一经 arXiv Atom API 反查（`https://export.arxiv.org/api/query?id_list=...`），
**每一个都解析到对应标题，无虚构 ID**：

| arXiv ID | 返回标题（截断） | 对应 key |
|---|---|---|
| 2001.08361 | Scaling Laws for Neural Language Models | kaplan2020 |
| 2101.00027 | The Pile: An 800GB Dataset of Diverse Text for Language Modeling | gao2020pile |
| 2112.11446 | Scaling Language Models: Methods, Analysis & Insights from Training Gopher | rae2021gopher |
| 2302.03169 | Data Selection for Language Models via Importance Resampling | xie2023dsir |
| 2304.01373 | Pythia: A Suite for Analyzing Large Language Models Across Training and Scaling | biderman2023pythia |
| 2305.10429 | DoReMi: Optimizing Data Mixtures Speeds Up Language Model Pretraining | xie2023doremi |
| 2307.14430 | Skill-it! A Data-Driven Skills Framework for Understanding and Training LMs | chen2023skillit |
| 2402.16827 | A Survey on Data Selection for Language Models | albalak2024survey |
| 2404.07177 | Scaling Laws for Data Filtering -- Data Curation cannot be Compute Agnostic | goyal2024filtering |
| 2406.11794 | DataComp-LM: In search of the next generation of training sets for LMs | liu2024datacomp |
| 2406.17557 | The FineWeb Datasets: Decanting the Web for the Finest Text Data at Scale | penedo2024fineweb |
| 2407.01492 | RegMix: Data Mixture as Regression for Language Model Pre-training | liu2024regmix |
| 2407.21783 | The Llama 3 Herd of Models | dubey2024llama3 |
| 2412.13663 | Smarter, Better, Faster, Longer: A Modern Bidirectional Encoder ... | warner2024modernbert |

---

## 3. Hoffmann et al. (2022) Approach-3 常数核验结论

**结论：该组常数位于 arXiv:2203.15556 附录 D.2 的正文，不在任何编号表格中。**

核验方式：下载 arXiv 全文 PDF（`https://arxiv.org/pdf/2203.15556`，返回 200，
36 页，application/pdf），用 PyMuPDF 抽取全部文本后定位。

逐项确认结果：

1. **章节位置**：附录小节标题为 **`D.2. Approach 3: Parametric fitting of the loss`**
   （位于 PDF 第 **24** 页）。
2. **常数出现位置**：在 D.2 内部一个**段内小标题**（run-in heading）
   **`Expected forms of the loss terms.`** 之下（位于 PDF 第 **25** 页），
   以**编号公式 (10)** 的形式给出：

   ```
   L(N, D) = E + A / N^0.34 + B / D^0.28            (10)

   with E = 1.69, A = 406.4, B = 410.7.
   ```

   抽取到的原文串为：
   `"Empirically, we find after fitting (2) that L(N,D) = E + A/N^{0.34} + B/D^{0.28}, (10) with E = 1.69, A = 406.4, B = 410.7."`
3. **指数 α、β**：公式 (10) 中两个指数写作 **`0.34`（N 的指数）** 与 **`0.28`（D 的指数）**。
   紧随其后的拟合问题 (11) 用 `(a, b, e, α, β)` 参数化
   （`min_{a,b,e,α,β} Σ Huber_δ( LSE(a − α log N_i, b − β log D_i, e) − log L_i )`，
   并令 `A,B,E = exp(a),exp(b),exp(e)`），
   即 α 为 N 的指数、β 为 D 的指数，与 `α≈0.34`、`β≈0.28` 一致。
   连同 E、A、B，该组常数**全部为正文行文所述，非表格数值**。
4. **与正文 Table 2 的区别**：正文 Table 2 的标题为
   `Table 2 | Estimated parameter and data scaling with increased training compute.`
   其表体只含"给定计算预算下参数量/数据量的分配系数 a、b"：

   | Approach | a (N_opt ∝ C^a) | b (D_opt ∝ C^b) |
   |---|---|---|
   | 1. Minimum over training curves | 0.50 (0.488, 0.502) | 0.50 (0.501, 0.512) |
   | 2. IsoFLOP profiles | 0.49 (0.462, 0.534) | 0.51 (0.483, 0.529) |
   | 3. Parametric modelling of the loss | **0.46** (0.454, 0.455) | **0.54** (0.542, 0.543) |
   | Kaplan et al. (2020) | 0.73 | 0.27 |

   即 **Table 2 只有 a=0.46、b=0.54（及置信区间），不含 E/A/B/α/β**。
   Approach 3 的 a、b 是由分布系数 α、β 经 `a = β/(α+β)`、`b = α/(α+β)` 换算而来
   （论文式 (4)），与式 (10) 的 α、β 是两套不同参数，**不可混引**。
5. **核验所用 URL**：
   - `https://arxiv.org/pdf/2203.15556`（全文 PDF，本次实际下载并抽取）
   - `https://arxiv.org/abs/2203.15556`（元数据页，用于确认标题与 arXiv 编号）
   - 会议录卷页来源：`https://api.crossref.org/works/10.52202/068431-2176`

**对论文引用的影响**：该组常数（E≈1.69、A≈406.4、B≈410.7、α≈0.34、β≈0.28）**可以引用**，
但引用出处须写成 **"Hoffmann et al. (2022), 附录 D.2, 式 (10)"**，不得写成"Table 2"或
"D.2 的表 X"——附录 D.2 中并无承载该组常数的编号表格。若他处需要 a=0.46、b=0.54，
则应改引正文 **Table 2**，二者不可互相替代。

---

## 4. 附带发现：注释头里的 `@` 会让 BibTeX 报错并以退出码 1 结束

本次为验证升格结果，用本机 MiKTeX（`D:\Users\luqianwu\AppData\Local\Programs\MiKTeX\miktex\bin\x64`）
在临时目录对 `reference.bib` 副本跑了 BibTeX（**未改动 `paper/` 下任何文件**），发现一个
与本次升格无关、但值得处理的问题。

**现象**（`main.blg` 中同样存在，即既有构建就已如此）：

```
I was expecting a `{' or a `('---line 3 of file reference.bib
 : % 会议论文若无从核实的卷号与页码，一律按网络资源（@misc）著录，不虚构卷页。
I'm skipping whatever remains of this entry
(There was 1 error message)
```

**根因**：注释头第 3 行里的 **`（@misc）`**。BibTeX 对 `%` 注释行并非整行跳过——它仍会在整份
文件中扫描 `@`，把 `@misc` 当成一条新条目的开头，随后因其后不是 `{...}` 而报错、并"跳过该条目"。
最小复现：含 `% see @misc` 的 bib 必报错；把 `@` 去掉即消失。与中文编码无关
（ASCII 注释里写 `@misc` 同样报错），也与注释长度、字节数无关。

**影响**：
- 仅 1 条 error message，**且不损失任何条目**：加/不加 `@` 两种版本渲染出的 `.bbl`
  **md5 完全相同**（`99fabe497f6d3ac8739d5210e37b5d44`），23 条 `\bibitem` 全部齐备。
- 但 BibTeX 会**以退出码 1 结束**（去掉 `@` 后为退出码 0）。`paper/build.sh` 用了
  `set -euo pipefail`，非零退出码在严格构建流程里可能被当作失败。

**建议的最小修法**（本次未执行，因任务要求"保持文件的注释头不变"）：把注释头第 3 行的
`（@misc）` 改为 `（misc）`，或写成 `（"@"misc）` 之类不含裸 `@` 的写法。改完 BibTeX 退出码回到 0，
参考文献输出一字不变。

> **后续状态**：撰写本记录期间，注释头第 3 行已由他处改为 `（misc）`。复核确认：BibTeX
> 退出码回到 **0**、无任何 error message，且渲染出的 `.bbl` 与修改前 **md5 完全相同**
> （`99fabe497f6d3ac8739d5210e37b5d44`，23 条 `\bibitem` 齐备）。此问题已消除。

**核验方式**：
```bash
# 在临时目录,不触碰 paper/
cp paper/reference.bib paper/gmcm-numerical.bst .
printf '\\citation{*}\n\\bibstyle{gmcm-numerical}\n\\bibdata{reference}\n' > t.aux
bibtex t          # 报 1 条 error, 退出码 1; .bbl 仍完整生成
```

# 本机 LaTeX 渲染环境（2026-09-25 配好）

## 装了什么

| 项 | 值 |
| --- | --- |
| 发行版 | **MiKTeX 25.12**（winget 安装，用户级） |
| 安装路径 | `D:\Users\luqianwu\AppData\Local\Programs\MiKTeX\miktex\bin\x64` |
| 按需装包 | 已开（`[MPM]AutoInstall=1`），首次编译缺包会自动从 CTAN 拉 |
| PDF 栅格化 | MiKTeX 自带的 Ghostscript（`mgs`，9.25），用于把编译结果转 PNG 目视核对 |
| 中文 | 走 `ctex` + 系统字体，无需额外配置 |

> 为什么不装 TeX Live：TeXT Live 镜像此前实测慢/403；MiKTeX 经 winget 装、体量小、
> 且缺包自动补齐，最贴合「能看到图片渲染效果就好」这个目标。

## 怎么用

```bash
export PATH="/d/Users/luqianwu/AppData/Local/Programs/MiKTeX/miktex/bin/x64:$PATH"

# 编译（论文用 xelatex；跑两遍以稳定交叉引用）
cd paper    # 或 GMCM2026-Overleaf
xelatex -interaction=nonstopmode main.tex
xelatex -interaction=nonstopmode main.tex

# 把结果转成图片目视核对
mgs -q -dNOPAUSE -dBATCH -dSAFER -sDEVICE=png16m -r110 \
    -sOutputFile=page-%d.png main.pdf
```

首次编译会自动下载 `ctex`、`setspace`、`pgfplots` 等缺失包，耗时较长；
之后再编译很快。

## 已验证到什么程度

1. **冒烟测试**：`scratch/tex/smoke/` —— article + ctex + 中文 + 公式 + 一张
   论文图 PDF，编译出 1 页，中文与矢量图均正常。
2. **论文图渲染核验册**：`scratch/tex/figcheck/` —— 用**论文真实模板**
   `gmcm2026.cls` 把 18 张论文图按 `\linewidth` 全部插入，编译**零错误、11 页**，
   并逐页栅格化目视核对（字号、图例、标注、留白均正常）。
   - `main.tex` 是核验册正文，`figures/` 是 18 张图，`docs/` 是封面 logo 资源
     （缺它会报 `Official logo asset missing`）。
   - 重新生成：把 `paper/figures/*.pdf` 拷进 `figcheck/figures/` 再编译即可。
3. **模板届数**：`paper/` 与 `GMCM2026-Overleaf/` 两处 `gmcm2026.cls` 与
   `config.tex` 均已是**第二十三届**（此项无需再做）。

## 注意事项

- 模板 `\linewidth` = 469.47 pt ≈ **6.52 in**。论文图按 6.3 in 设计，正文中会被
  放大约 3.5%，字号只会略大不会缩小。
- `paper/main.tex` 目前只 include 到 `sections/problem3`，**Q4 需新建
  `sections/problem4.tex` 并加一行 `\input`**（`GMCM2026-Overleaf/` 同样）。
- 若要用 TikZ 图 `paper/figures/fig_q4_frontier_vs_scale.tex`，需在导言区补
  `\usepackage{pgfplots}` + `\pgfplotsset{compat=1.18}` + `\usetikzlibrary{patterns}`
  （现 `gmcm2026.cls` 只 `\RequirePackage{tikz}`）。该图与 `fig_q4_scale_vs_frontier.pdf`
  讲同一 claim，建议择一。
- 编译日志里的 `security risk: running with elevated privileges` 是 MiKTeX 在
  管理员 shell 下的例行警告，不影响输出。
- Overleaf 仍是可用的备份路径（`GMCM2026-Overleaf/` 可直接上传）。

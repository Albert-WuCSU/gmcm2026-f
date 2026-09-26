"""论文图共享视觉系统（Type 3）。

设计约束（来自 `.claude/skills/math-figure-generator/references/`）：

- 语义色不随面板改变：主方法恒为 `MAIN`，baseline 恒为 `BASE`（灰）。
- `POS`/`NEG` 只用于**有符号的变化量**，不用于一般分类着色。
- 每个函数只负责一件事；图脚本只读落盘工件，不手打数字。

配色取 Nature/NPG 色系（`#3C5488` 藏青、`#E64B35` 砖红、`#00A087` 蓝绿、
`#4DBBD5` 天青、`#F39B7F` 鲑、`#8491B4` 钢蓝），保持顶刊观感同时满足
色盲可分辨与灰度可区分（明度分层：深=主证据，浅=支撑证据）。
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PAPER_FIGS = ROOT / "paper" / "figures"

# ---- 语义色板（NPG 色系）----
MAIN = "#244966"          # 主方法 M1 / hero
MAIN_MID = "#6E7FA8"
MAIN_LIGHT = "#8491B4"    # 主方法的对照臂 / 次要变体
MAIN_PALE = "#C9D0E0"
BASE = "#989EA5"          # baseline M0，恒灰
BASE_DARK = "#4D4D4D"
POS = "#00A087"           # 仅用于有符号变化：增/优
NEG = "#E64B35"           # 仅用于有符号变化：减/劣
CRIT = "#B75A42"          # 临界线 / 判据线
ACCENT = ("#4DBBD5", "#F39B7F", "#7E6148", "#91D1C2", "#B09C85")
INK = "#2B2B2B"
MID = "#A8A8A8"
PALE = "#E6E6E6"
BAND = "#F2F4F8"

CJK = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]


def apply_style() -> None:
    """Nature 风格 rc：细轴线、外向刻度、无顶/右框、7pt 基准字号。"""
    plt.rcParams.update({
        "figure.dpi": 120,
        "savefig.dpi": 400,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.10,
        "pdf.fonttype": 42,          # 嵌入 TrueType，Overleaf 可直接用
        "ps.fonttype": 42,
        "font.family": "sans-serif",
        "font.sans-serif": CJK,
        "font.size": 8.0,
        "axes.titlesize": 7.5,
        "axes.labelsize": 8.0,
        "axes.linewidth": 0.7,
        "axes.edgecolor": INK,
        "axes.labelcolor": INK,
        "axes.axisbelow": True,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.unicode_minus": False,
        "xtick.labelsize": 7.0,
        "ytick.labelsize": 7.0,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.width": 0.7,
        "ytick.major.width": 0.7,
        "xtick.major.size": 2.4,
        "ytick.major.size": 2.4,
        "legend.fontsize": 7.0,
        "legend.frameon": True,          # 不透明白底，避免曲线穿过图例文字
        "legend.framealpha": 1.0,
        "legend.facecolor": "white",
        "legend.edgecolor": "none",
        "legend.fancybox": False,
        "legend.handlelength": 1.6,
        "legend.handletextpad": 0.5,
        "legend.labelspacing": 0.28,
        "legend.borderaxespad": 0.2,
        "lines.linewidth": 1.2,
        "lines.markersize": 3.4,
        "mathtext.fontset": "dejavusans",
        "figure.facecolor": "white",
    })


def load_json(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def load_csv(rel: str) -> list[dict]:
    import csv
    with (ROOT / rel).open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def num(rows: list[dict], key: str) -> list[float]:
    return [float(r[key]) for r in rows]


def save(fig, name: str) -> list[str]:
    """同时落 PDF（正文用，矢量）与 PNG（预览/核验用，400 dpi）。"""
    PAPER_FIGS.mkdir(parents=True, exist_ok=True)
    out = []
    for ext in ("pdf", "png"):
        p = PAPER_FIGS / f"{name}.{ext}"
        fig.savefig(p, format=ext)
        out.append(str(p.relative_to(ROOT)).replace("\\", "/"))
    plt.close(fig)
    return out


def panel(ax, letter: str, dx: float = -0.115, dy: float = 1.06) -> None:
    """Nature 式面板字母：粗体小写，位于面板左上外侧。"""
    ax.text(dx, dy, letter, transform=ax.transAxes, fontsize=8.5,
            fontweight="bold", va="bottom", ha="left", color=INK)


def vline(ax, x, label=None, color=CRIT, ls="--", lw=0.9, y=0.94, side="right",
          fs=6.2):
    """临界/参考竖线 + 顶部标注。"""
    ax.axvline(x, color=color, ls=ls, lw=lw, zorder=1.5)
    if label:
        ha, off = ("left", 0.012) if side == "right" else ("right", -0.012)
        ax.text(x + off, y, label, transform=ax.get_xaxis_transform(),
                ha=ha, va="top", fontsize=fs, color=color)


def direct_label(ax, x, y, text, color, dx=0.02, dy=0.0, dy_data=0.0, fs=6.5, **kw):
    """直接标注曲线末端，替代图例。`dy` 以字号为单位，`dy_data` 以数据为单位。"""
    ax.annotate(text, xy=(x, y + dy_data), xytext=(dx, dy),
                textcoords="offset fontsize", color=color, fontsize=fs,
                va="center", ha="left", **kw)


def legend_handles(pairs, **kw):
    return [Line2D([], [], color=c, marker=m, ls=s, lw=1.2, ms=3.4, label=l)
            for l, c, m, s in pairs]

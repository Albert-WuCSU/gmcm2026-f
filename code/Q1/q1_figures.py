"""Q1 round1 诊断图（Type 1 内部诊断 / Type 2 对比）。

**不是论文图**。论文图留到 figure-table-planner 与 math-figure-generator。
本脚本只出首轮实验后第二张决策卡需要看的四张：
  F1 域级 Q ± bootstrap 区间：M0 vs M1（主口径）+ per_domain 消融臂
  F2 冲突率对分位锚点的敏感性（四判据 × 三锚点）
  F3 配比侧去偏 R² 与 Spearman 的三尺度对照：M0c vs M1c
  F4 Q 增量检验：三尺度增量与 95% 区间

读 metrics/*.json，不重算。种子无关（纯绘图）。
"""
from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import q1_common as C  # noqa: E402

SCALES = ("test_1m", "test_60m", "test_1B")
# 中文字体：本机已确认可用（DejaVu Sans 无 CJK 字形，不设会显示为方框）
plt.rcParams.update({"figure.dpi": 130, "font.size": 9, "axes.grid": True,
                     "grid.alpha": 0.3, "axes.axisbelow": True,
                     "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
                     "axes.unicode_minus": False})


def load(mid: str) -> dict:
    fn = {"M0": "q1_quality_M0.json", "M1": "q1_quality_M1.json",
          "M0c": "q1_mixture_M0c.json", "M1c": "q1_mixture_M1c.json"}[mid]
    return json.loads((C.METRICS / fn).read_text(encoding="utf-8"))


def f1_domain_quality(m: dict) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.4))
    for ax, (pop, title) in zip(axes, [("pooled", "主口径 pooled+ecdf"),
                                       ("per_domain", "消融臂 per_domain+ecdf")]):
        names = list(m["M0"]["arms"][pop]["domain"]["per_domain"])
        x = np.arange(len(names))
        for k, (mid, off, col) in enumerate([("M0", -0.16, "#4C72B0"),
                                             ("M1", 0.16, "#C44E52")]):
            pd_ = m[mid]["arms"][pop]["domain"]["per_domain"]
            v = np.array([pd_[n]["huber"] for n in names])
            lo = np.array([pd_[n]["huber"] - pd_[n]["ci95_lo"] for n in names])
            hi = np.array([pd_[n]["ci95_hi"] - pd_[n]["huber"] for n in names])
            ax.errorbar(x + off, v, yerr=[lo, hi], fmt="o", ms=4, capsize=3,
                        color=col, label=mid, lw=1.2)
        ax.set_xticks(x)
        ax.set_xticklabels(names, rotation=40, ha="right")
        ax.set_title(title)
        ax.set_ylabel("域级 Q（Huber）")
        ax.legend(fontsize=8)

    ax = axes[2]
    names = list(m["M0"]["arms"]["pooled"]["domain"]["per_domain"])
    for mid, col in (("M0", "#4C72B0"), ("M1", "#C44E52")):
        pd_ = m[mid]["arms"]["pooled"]["domain"]["per_domain"]
        hw = [pd_[n]["half_width"] for n in names]
        ax.plot([pd_[n]["n"] for n in names], hw, "o", color=col, label=mid, ms=5)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("域样本量 n（对数）")
    ax.set_ylabel("bootstrap 半宽（对数）")
    ax.set_title("区间宽度 vs 样本量\n(book n=171 为最宽)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(C.FIGURES / "F1_domain_quality_M0_vs_M1.png", bbox_inches="tight")
    plt.close(fig)


def f2_conflict(m: dict) -> None:
    cr = m["M1"]["conflict_anchor_sensitivity"]
    anchors = list(cr)
    crits = list(cr[anchors[0]])
    fig, ax = plt.subplots(figsize=(6, 3.4))
    x = np.arange(len(anchors))
    for i, c in enumerate(crits):
        ax.plot(x, [cr[a][c] for a in anchors], "o-", ms=5,
                label=c.replace("_", " ")[:34])
    ax.axhline(0.01, ls=":", c="gray", lw=1)
    ax.axhline(0.50, ls=":", c="gray", lw=1)
    ax.set_xticks(x)
    ax.set_xticklabels(anchors)
    ax.set_xlabel("分位锚点")
    ax.set_ylabel("冲突率")
    ax.set_title("Q1b 冲突率对锚点的敏感性\n虚线为 fallback 触发边界 (0.01, 0.50)")
    ax.legend(fontsize=7, loc="center left", bbox_to_anchor=(1.01, 0.5))
    fig.tight_layout()
    fig.savefig(C.FIGURES / "F2_conflict_rate_vs_anchor.png", bbox_inches="tight")
    plt.close(fig)


def f3_mixture(m: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4))
    x = np.arange(len(SCALES))
    for ax, key, lab in ((axes[0], "r2_after_offset_removal", "去偏 R²"),
                         (axes[1], "spearman", "Spearman")):
        for mid, off, col in (("M0c", -0.17, "#4C72B0"), ("M1c", 0.17, "#C44E52")):
            v = [m[mid]["validation_by_scale"][s][key] for s in SCALES]
            ax.bar(x + off, v, 0.34, color=col, label=mid)
            for xi, vi in zip(x + off, v):
                ax.text(xi, vi + 0.012, f"{vi:.3f}", ha="center", fontsize=7)
        ax.set_xticks(x)
        ax.set_xticklabels(SCALES)
        ax.set_ylabel(lab)
        ax.set_ylim(0, 1.08)
        ax.legend(fontsize=8)
    axes[0].set_title("配比→Loss 去偏 R²（主报口径）")
    axes[1].set_title("Spearman（主报口径）")
    fig.suptitle("M1c 增益为尺度局部：1m 有增益、60m 持平、1B 更差", fontsize=9, y=1.02)
    fig.tight_layout()
    fig.savefig(C.FIGURES / "F3_mixture_M0c_vs_M1c_by_scale.png", bbox_inches="tight")
    plt.close(fig)


def f4_q_increment(m: dict) -> None:
    inc = m["M0c"].get("q_increment_test", {})
    if "by_scale" not in inc:
        return
    bs = inc["by_scale"]
    ks = [k for k in SCALES if k in bs]
    fig, ax = plt.subplots(figsize=(5.4, 3.4))
    y = np.arange(len(ks))
    val = [bs[k]["increment"] for k in ks]
    lo = [bs[k]["increment"] - bs[k]["increment_ci95"][0] for k in ks]
    hi = [bs[k]["increment_ci95"][1] - bs[k]["increment"] for k in ks]
    ax.errorbar(val, y, xerr=[lo, hi], fmt="o", ms=6, capsize=4, color="#55A868")
    ax.axvline(0, c="k", lw=1)
    ax.set_yticks(y)
    ax.set_yticklabels(ks)
    ax.set_xlabel("去偏 R² 增量（p+Q 减 仅 p）")
    ax.set_title("引入域级 Q 的增量与 95% 区间\n三尺度区间均含 0 → 无显著增量")
    fig.tight_layout()
    fig.savefig(C.FIGURES / "F4_q_increment_test.png", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    C.ensure_dirs()
    m = {k: load(k) for k in ("M0", "M1", "M0c", "M1c")}
    f1_domain_quality(m)
    f2_conflict(m)
    f3_mixture(m)
    f4_q_increment(m)
    out = sorted(p.name for p in C.FIGURES.glob("*.png"))
    print("诊断图（Type 1/2，非论文图）:", out)


if __name__ == "__main__":
    main()

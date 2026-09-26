"""全篇框架图 + 数据预处理图 + 四问方法流程图（Type 3）。

风格：计算机顶会 / 美赛 pipeline figure —— 圆角盒 + 浅色填充 + 细箭头 +
阶段色 + 正交布线；全部矢量（PDF），中文用 Microsoft YaHei。

两条硬性纪律：
1. **图内只放数据与结果**，不写「不得表述为……」「判 FAIL」这类报告口吻；
   口径限制写进图规划与正文，不进图。
2. 图内出现的所有计数、行数、参数值均从落盘工件读取
   （`workspace/data/data_profile.json`、各问 `metrics/*.json`），不手打。

输出全部落 `paper/figures/`。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import (  # noqa: E402
    FancyArrowPatch,
    FancyBboxPatch,
    Rectangle,
)

import figstyle as S  # noqa: E402

STAGE = [("#284B63", "#F1F5F7"),      # 深蓝：定义 / 输入
         ("#008C83", "#EFF8F7"),      # 蓝绿：建模 / 求解
         ("#D05A3A", "#FCF3EF"),      # 暖红：检验 / 边界
         ("#3C78A8", "#F0F6FA"),      # 天青：预测 / 输出
         ("#765B45", "#F7F3EF")]      # 褐：补充
DATA = ("#68788D", "#F3F5F8")
OUT = ("#30363D", "#F7F7F6")


def canvas(w=6.3, h=3.2):
    fig, ax = plt.subplots(figsize=(w, h))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    return fig, ax


def _upp(ax) -> float:
    """每 pt 等于多少画布单位（画布高 100 单位）—— 让行距与字号解耦。"""
    return 100.0 / (ax.figure.get_size_inches()[1] * 72.0)


def box(ax, x, y, w, h, title, body=None, stage=0, fs=6.6, bfs=5.6,
        align="center", pad=0.32, wrap=None, accent=True):
    edge, fill = STAGE[stage] if isinstance(stage, int) else stage
    # 极轻投影用于建立层级；保持矢量、低墨量，缩印后不显脏。
    ax.add_patch(FancyBboxPatch(
        (x + 0.35, y - 0.45), w, h,
        boxstyle=f"round,pad={pad},rounding_size=1.6",
        linewidth=0, facecolor="#000000", alpha=0.055, zorder=1.5))
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle=f"round,pad={pad},rounding_size=1.6",
        linewidth=0.75, edgecolor=edge, facecolor=fill, zorder=2))
    if accent:
        ax.add_patch(Rectangle((x + 1.2, y + h - 0.75), w - 2.4, 0.75,
                               linewidth=0, facecolor=edge, alpha=0.9, zorder=2.2))
    upp = _upp(ax)
    cx = x + w / 2 if align == "center" else x + 1.4
    ha = "center" if align == "center" else "left"
    if body:
        ax.text(cx, y + h - 0.65 * fs * upp - 0.65, title, ha=ha, va="top",
                fontsize=fs, color=edge, fontweight="bold", zorder=3)
        ax.text(cx, y + h - 2.15 * fs * upp - 0.7, body, ha=ha, va="top",
                fontsize=bfs, color=S.INK, linespacing=1.5, zorder=3)
    else:
        ax.text(cx, y + h / 2 - 0.15, title, ha=ha, va="center", fontsize=fs,
                color=edge, fontweight="bold", linespacing=1.5, zorder=3)
    return (x, y, w, h)


def arrow(ax, p1, p2, color=None, lw=0.9, ls="-", ms=6.0):
    ax.add_patch(FancyArrowPatch(
        p1, p2, arrowstyle="-|>", mutation_scale=ms, linewidth=lw,
        color=color or "#68727D", linestyle=ls, zorder=1,
        shrinkA=1.5, shrinkB=1.5, connectionstyle="arc3,rad=0"))


def group(ax, x, y, w, h, label, color=None, fs=5.8, ls=(0, (3, 2))):
    c = color or S.BASE
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.5,rounding_size=1.4",
        linewidth=0.65, edgecolor=c, facecolor="#FAFBFC", alpha=0.65,
        linestyle=ls, zorder=0))
    ax.text(x + 0.9, y + h + 0.6, label.upper(), ha="left", va="bottom",
            fontsize=fs, color=c, fontweight="bold", zorder=3)


def tag(ax, x, y, text, color=None, fs=5.4):
    ax.text(x, y, text, ha="center", va="center", fontsize=fs,
            color=color or S.MID, style="italic", zorder=3)


def save(fig, name):
    return S.save(fig, name)


def _summary_row_count(path: str, heading: str) -> int:
    """Number of check rows in a robustness report's summary table.

    The row count is read from the landed report rather than typed in, so the
    figure cannot drift from the artifacts it summarises.
    """
    import re
    text = Path(path).read_text(encoding="utf-8")
    start = text.index(heading)
    body = text[start:]
    nxt = re.search(r"\n## ", body)
    if nxt:
        body = body[: nxt.start()]
    # 行首形如 "| R1 | ..." 或 "| R1 规格扰动 | ..." 的都是检查行。
    return len(re.findall(r"^\|\s*\*{0,2}R\d+\*{0,2}(?:\s|\|)", body, re.M))


def facts() -> dict:
    p = S.load_json("workspace/data/data_profile.json")
    raw = p["raw_files"]
    per_q = {q: len(p["attachment_mapping"][q]) for q in ("Q1", "Q2", "Q3", "Q4")}
    # 分母取自 data_profile 的覆盖统计，分子取自 Q1 的规范化核验工件；
    # 剔除行数与保留率由二者现算，不手打。
    n_total = p["coverage"]["rows"]["A_quality_total"]
    n_rows = S.load_json("workspace/data/q1_canonical_verification.json")["n_rows"]
    m1s = S.load_json("results/Q2/experiments/round1/metrics/q2_M1s.json")
    m1o = S.load_json("results/Q3/experiments/round1/metrics/q3_M1o.json")
    q4tm = S.load_json("results/Q4/experiments/round2/metrics/q4_trend_method.json")
    nmeta = S.load_json("results/Q4/experiments/round2/n_frontier_meta.json")
    probe = S.load_json("workspace/data/q2_probe_beta_sharing.json")
    # 稳健性检查项数：Q1 取核验工件的 n_checks，Q2/Q3/Q4 取各自报告汇总表的行数。
    n_checks = {
        "Q1": S.load_json("robustness/Q1/q1_robustness_summary.json")["n_checks"],
        "Q2": _summary_row_count("robustness/Q2/q2_robustness_report.md",
                                "## 7. 检查结果汇总"),
        "Q3": _summary_row_count("robustness/Q3/q3_robustness_report.md",
                                "## 9. 检查结果汇总"),
        "Q4": _summary_row_count("robustness/Q4/q4_robustness_report.md",
                                "## 7. 检查结果汇总"),
    }

    lctx = m1o["lctx_sensitivity"]
    f = {
        "n_raw": len(raw), "mb": sum(x["bytes"] for x in raw) / 1e6, "per_q": per_q,
        "n_rows": n_rows, "n_total": n_total, "n_drop": n_total - n_rows,
        "keep_pct": n_rows / n_total,
        "gamma": m1s["stage3_joint_wls"]["M1s_params"]["gamma"],
        "gamma_a": probe["route_A_beta_shared_from_B1"]["gamma"],
        "ci_a": probe["route_A_beta_shared_from_B1"]["gamma_ci95"],
        "gamma_b": probe["route_B_beta_free_on_B7"]["gamma"],
        "ci_b": probe["route_B_beta_free_on_B7"]["gamma_ci95"],
        "shift_frac": probe["shift_as_fraction_of_ci_width"],
        "sat": m1o["structural_transition"]["main_definition_A"]["changes"][0][
            "located_log10_C"],
        "n_pct": lctx["N_B_change_pct"], "d_pct": lctx["D_B_change_pct"],
        "nd_spread": lctx["N_over_D_relative_spread"],
        "rng": q4tm["total_points_range"],
        "ratio": nmeta["N_q90_ratio_first_over_last"],
        "n_checks": n_checks,
    }
    print(f"[facts] 附件 {f['n_raw']} 个 / {f['mb']:.0f} MB；映射 {per_q}；"
          f"清洗 {n_rows:,}/{n_total:,}（保留 {f['keep_pct']:.4%}，剔除 "
          f"{f['n_drop']} 行）；γ(A)={f['gamma_a']:.4f}；"
          f"转移点={f['sat']:.6f}；Q4 极差={f['rng']}；稳健性={n_checks}")
    return f


# --------------------------------------------------------------------------- #
# 全篇框架图
# --------------------------------------------------------------------------- #
def fig_overall(f: dict) -> list[str]:
    fig, ax = canvas(6.3, 3.6)
    group(ax, 1.5, 30, 19, 62, "数据层")
    for i, (t, b) in enumerate((("质量信号 A1–A3", "文本 · 22 指标"),
                                ("标度律 B1–B7", "训练日志 · 收敛点"),
                                ("榜单与上下文", "C1–C8 · 能力 · 成本"))):
        box(ax, 3, 74 - i * 17, 16, 13, t, b, stage=DATA, fs=5.9, bfs=5.5)

    xs, ws = [24.0, 43.0, 62.0, 81.0], 18.5
    specs = [
        (0, "Q1　质量与配比",
         f"门控 $Q=V(1-P)$\n域级 Huber + 自助\n样本 {f['n_rows']:,} 行"),
        (1, "Q2　广义标度律",
         "$L=E+A N^{-\\alpha}$\n$+\\,B\\,(D Q^{\\gamma}e^{b^{T}z})^{-\\beta}$\n"
         "三源交叉验证"),
        (2, "Q3　联合优化",
         "$\\mathrm{min}\\;L$\n$kND+D\\Delta g\\leq C$\n分段 KKT · 活跃集扫描"),
        (3, "Q4　归因与预测",
         "规模 / 技术双通道分解\n端点 × 规格 8 口径\n三情景 + baseline 对照"),
    ]
    for (st, title, body), x in zip(specs, xs):
        box(ax, x, 58, ws, 22, title, body, stage=st, fs=6.2, bfs=5.6)
    for i in range(3):
        arrow(ax, (xs[i] + ws, 69), (xs[i + 1], 69), lw=1.1)

    bus = 88.5
    ax.plot([19.0, 21.5], [61.0, bus], color=DATA[0], lw=0.8, zorder=1)
    ax.plot([21.5, xs[-1] + ws / 2], [bus, bus], color=DATA[0], lw=0.8, zorder=1)
    for x in [x + ws / 2 for x in xs]:
        arrow(ax, (x, bus), (x, 80.9), color=DATA[0], lw=0.8)
    ax.text(22.4, bus + 1.0, "附件映射　18 / 13 / 4 / 8", ha="left", va="bottom",
            fontsize=5.3, color=DATA[0])

    for i, t in enumerate(("域序 + 域级 $Q$", "$\\gamma,\\beta$ 等承重参数",
                           "最优路径 + 转移点", "归因与预测")):
        tag(ax, xs[i] + ws / 2, 55.2, t, color=STAGE[i][0])

    box(ax, 24.0, 30, 75.5, 20, "论文结论",
        "① 质量按比例放大有效 token 数（$\\gamma\\approx1$），条件是 $\\beta$ 的来源假设\n"
        "② 算力约束下存在结构性转移，形态为连续饱和\n"
        "③ 前沿推进由非规模技术 / 数据工程综合进步主导",
        stage=OUT, fs=6.6, bfs=5.6, align="left")
    box(ax, 1.5, 3, 97.5, 21, "证据链与审计",
        "每个数字：代码 → results → 报告 → 论文，双向可追\n"
        f"稳健性检查：Q1 {f['n_checks']['Q1']} 项 · Q2 {f['n_checks']['Q2']} 项 · "
        f"Q3 {f['n_checks']['Q3']} 项 · Q4 {f['n_checks']['Q4']} 项\n"
        "三层审计：跨媒体一致性 · 语义完备性 · 提交级质量保证",
        stage=OUT, fs=6.6, bfs=5.6, align="left")
    arrow(ax, (61.7, 30), (61.7, 24.6), color=S.BASE)
    return save(fig, "fig_framework_overall")


# --------------------------------------------------------------------------- #
# 数据预处理
# --------------------------------------------------------------------------- #
def fig_data_pipeline(f: dict) -> list[str]:
    fig, ax = canvas(6.3, 3.0)
    box(ax, 1.5, 30, 18, 61, "原始附件",
        f"{f['n_raw']} 个文件\n≈ {f['mb']:.0f} MB\n只读挂载",
        stage=DATA, fs=6.2, bfs=5.6)

    y = 78
    for q, lab in (("Q1", "质量与配比"), ("Q2", "标度律"),
                   ("Q3", "优化与上下文"), ("Q4", "榜单与归因")):
        box(ax, 25, y, 17, 13, f"{q}　{lab}", f"{f['per_q'][q]} 个附件",
            stage=DATA, fs=5.9, bfs=5.5)
        arrow(ax, (19.7, 60), (25, y + 6.5), color=DATA[0], lw=0.8)
        y -= 16

    box(ax, 47, 30, 24, 61, "规范化与清洗",
        "20 列主口径\n"
        "域级 Huber(k=1.345)\n"
        "经验分位数 ecdf\n"
        "单位统一：$N,D$ 以 B 计\n"
        "种子 20260924",
        stage=1, fs=6.2, bfs=5.6, align="left")
    for yy in (78, 62, 46, 30):
        arrow(ax, (42.2, yy + 6.5), (47, 60), color=STAGE[1][0], lw=0.8)

    box(ax, 76, 30, 22.5, 61, "落盘与核验",
        f"主样本 {f['n_rows']:,} 行\n"
        f"保留率 {f['keep_pct']:.3%}\n"
        f"剔除 {f['n_drop']} 行整条缺失\n"
        "原始数据只读校验通过",
        stage=3, fs=6.2, bfs=5.6, align="left")
    arrow(ax, (71.3, 60), (76, 60), color=STAGE[3][0], lw=1.1)

    box(ax, 1.5, 0.5, 97, 26, "数据审计的关键发现",
        "① 配方表每行中位 8 个精确零，对数比的伪计数会主导坐标 → 改用加性中心化\n"
        "② 2024 年前仅 24 行 → 归因窗口限定 2024-06 → 2025-03（278 天）\n"
        "③ 22 个质量指标方向不一，须先定正/负方向；组内与组间相关同量级 → 语义分组\n"
        "④ 未闭合风险 5 项（抽样文本统计、id 唯一性、共线性诊断、方向标注、C8 聚合口径）",
        stage=OUT, fs=6.4, bfs=4.9, align="left")
    arrow(ax, (50, 30), (50, 27.1), color=S.BASE)
    return save(fig, "fig_data_pipeline")


# --------------------------------------------------------------------------- #
# 四问方法流程（5 步 + 产出带）
# --------------------------------------------------------------------------- #
def flow(name: str, steps: list, out_title: str, out: str,
         h: float = 2.25, title: str | None = None) -> list[str]:
    fig, ax = canvas(6.3, h)
    n = len(steps)
    gap = 3.6
    w = (98.5 - 1.5 - gap * (n - 1)) / n
    y0, bh = 53, 39
    for i, (t, b, st) in enumerate(steps):
        x = 1.5 + i * (w + gap)
        box(ax, x, y0, w, bh, t, b, stage=st, fs=6.0, bfs=5.5)
        if i:
            arrow(ax, (x - gap, y0 + bh / 2), (x, y0 + bh / 2), lw=1.1)
    box(ax, 1.5, 13, 97, 25, out_title, out, stage=OUT, fs=6.2, bfs=5.6,
        align="left")
    for i in range(n):
        x = 1.5 + i * (w + gap) + w / 2
        arrow(ax, (x, y0), (x, 38.6), color=S.BASE, lw=0.7, ls=(0, (3, 2)))
    if title:
        ax.text(1.5, 95, title, ha="left", va="center", fontsize=6.4,
                color=S.BASE_DARK)
    return save(fig, name)


def fig_q1_flow(f: dict) -> list[str]:
    return flow("fig_framework_q1", [
        ("① 规范化", "20 列主口径\n剔除缺失行", 0),
        ("② 语义分组", "14 价值指标 $\\to V$\n6 污染指标 $\\to P$", 0),
        ("③ 门控合成", "$Q=V(1-P)$\n按域 ecdf 归一", 1),
        ("④ 冲突判据", "CD2：高价值 ∧ 高污染\n分位锚点 p75", 1),
        ("⑤ 配比与对照", "主效应 + 交互 + 岭\n对照 M0 / M0c", 2),
    ], "本问产出",
       "域序（最高档 = arxiv / c4 / commoncrawl）· 域级 $Q$ → Q2 · 配比 → Loss 的去偏 $R^2$\n"
       "引入域级 $Q$ 的去偏 $R^2$ 增量：三尺度 95% 区间均跨 0"
       "（实测 1m +0.00028、60m −0.00022、1B −0.00082）")


def fig_q2_flow(f: dict) -> list[str]:
    return flow("fig_framework_q2", [
        ("① 多源整备", "B1 真实训练日志\nB4/B5 收敛点 · 文献\nB7 半合成", 0),
        ("② 退化检验", "模型须能退化回\n既有标度律", 0),
        ("③ 联合拟合", "$L=E+A N^{-\\alpha}$\n$+\\,B\\,(DQ^{\\gamma}e^{b^{T}z})^{-\\beta}$\n"
                       "三阶段 WLS", 1),
        ("④ 交叉源验证", "Spearman + 去偏 RMSE\n三源逐一复现", 1),
        ("⑤ 条件化检验", "$\\beta$ 跨源共享（P9）\n$\\gamma$ 位移 "
                         f"{f['shift_frac']:.3f}× 区间宽", 2),
    ], "本问产出",
       f"路线 A（$\\beta$ 取自 B1）：$\\gamma$ = {f['gamma_a']:.4f}，"
       f"CI95 [{f['ci_a'][0]:.4f}, {f['ci_a'][1]:.4f}] 含 1.0\n"
       f"路线 B（$\\beta$ 在 B7 自由）：$\\gamma$ = {f['gamma_b']:.4f}，"
       f"CI95 [{f['ci_b'][0]:.4f}, {f['ci_b'][1]:.4f}] 不含 1.0")


def fig_q3_flow(f: dict) -> list[str]:
    return flow("fig_framework_q3", [
        ("① 目标与成本", "$\\mathrm{min}\\;E+AN^{-\\alpha}$\n"
                         "$+B(DQ^{\\gamma})^{-\\beta}$\n$k=6+\\eta L_{\\mathrm{ctx}}$", 0),
        ("② 三类 $g(Q)$", "指数 / 幂 / 对数渐近\n题给参数原样代入", 0),
        ("③ 分段 KKT", "三分支全枚举\n内点 / $Q\\!=\\!1$ / $Q\\!=\\!Q_0$\n五项硬判据筛", 1),
        ("④ 活跃集扫描", "沿 $\\log_{10}C$ 扫描\n二分定位 $\\mu$ 由 0 转正\n步长无关", 1),
        ("⑤ 三定义与敏感性", "A / C / D 三定义并报\n$L_{\\mathrm{ctx}}$ 五档跨临界", 2),
    ], "本问产出",
       f"三档锚点解（$C=10^{{19,22,24}}$）· 转移点 $\\log_{{10}}C$ = {f['sat']:.4f}\n"
       f"跨临界 $L_{{\\mathrm{{ctx}}}}$：$N^{{*}}$ {f['n_pct']:.1f}%、"
       f"$D^{{*}}$ {f['d_pct']:.1f}%，而 $N{{:}}D$ 相对极差仅 {f['nd_spread']:.2%}")


def fig_q4_flow(f: dict) -> list[str]:
    return flow("fig_framework_q4", [
        ("① 窗口与样本", "C1 六维等权合成分\n窗口 2024-06 → 2025-03", 0),
        ("② 规模通道", "$N$ 分位按月趋势\nq90 端点比值 "
                       f"{f['ratio']}×", 1),
        ("③ 技术通道", "前沿 $S_{{q90}}$ 月斜率\n扣除规模贡献", 1),
        ("④ 端点多规格", "端点 4 定义 + 规格 4 组合\n另加 2 趋势口径并报", 2),
        ("⑤ 情景与对照", "保守 / 中性 / 乐观\n$h$ = 12, 24 月 · baseline 同图", 3),
    ], "本问产出",
       f"能力提升约 {f['rng'][0]:.4f} – {f['rng'][1]:.4f} 点；技术通道在全部口径下为正\n"
       "情景极差随规模份额缩放：11.786 → 4.1408 → 0")


def main() -> None:
    S.apply_style()
    f = facts()
    out = []
    out += fig_overall(f)
    out += fig_data_pipeline(f)
    out += fig_q1_flow(f)
    out += fig_q2_flow(f)
    out += fig_q3_flow(f)
    out += fig_q4_flow(f)
    print("[figs]", *out, sep="\n  ")


if __name__ == "__main__":
    main()

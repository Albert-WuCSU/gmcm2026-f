"""Q4 论文图（Type 3）—— 通道分解、规模趋势、前沿预测与情景。

数字纪律：全部读自落盘工件，脚本内不出现手打结果数字。

- `results/Q4/experiments/round2/metrics/q4_trend_method.json`（9 口径与趋势法）
- `results/Q4/experiments/round1/tables/q4_spec_sensitivity.csv`
- `results/Q4/experiments/round2/tables/q4_endpoint_sensitivity.csv`
- `results/Q4/experiments/round1/tables/q4_by_type_group.csv`
- `results/Q4/experiments/round2/tables/q4_N_and_frontier_by_month.csv`
- `results/Q4/experiments/round2/n_frontier_meta.json`
- `results/Q4/experiments/round1/tables/q4_frontier_scenarios.csv`（主方法预测）
- `results/Q4/experiments/round1/metrics/q4_M0a.json`（**baseline 预测，须同图列出**）
- `results/Q4/experiments/round2/tables/q4_scenario_spread_scaling.csv`

写作红线：**不出现任何百分比分割作为结论**；份额只作「随口径变动且符号可翻转」的披露项。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))

import numpy as np  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

import figstyle as S  # noqa: E402

R1T = "results/Q4/experiments/round1/tables/"
R2T = "results/Q4/experiments/round2/tables/"


def assert_canonical() -> dict:
    tm = S.load_json("results/Q4/experiments/round2/metrics/q4_trend_method.json")
    meta = S.load_json("results/Q4/experiments/round2/n_frontier_meta.json")
    ep = S.load_csv(R2T + "q4_endpoint_sensitivity.csv")
    sp = S.load_csv(R1T + "q4_spec_sensitivity.csv")
    m0 = S.load_json("results/Q4/experiments/round1/metrics/q4_M0a.json")

    rng = tm["total_points_range"]
    disk_tot = [float(r["total_points"]) for r in ep] + \
               [float(r["total_points"]) for r in sp]
    # `q4_spec_sensitivity.csv` 只保留 4 位小数，故按该表精度（1e-3）对拍
    if (abs(min(disk_tot) - rng[0]) > 1e-3) or (abs(max(disk_tot) - rng[1]) > 1e-3):
        raise AssertionError(f"总点数极差与逐口径表不符：{rng} vs "
                             f"[{min(disk_tot)}, {max(disk_tot)}]")
    if not tm["endpoint_sign_flips"]:
        raise AssertionError("落盘工件称无符号翻转，与「规模通道与 0 不可区分」的表述不符")
    if abs(meta["N_q90_ratio_first_over_last"] - 3.162) > 5e-4:
        raise AssertionError(f"N_q90 端点比值与报告不符：{meta['N_q90_ratio_first_over_last']}")
    base = m0["predictions"]["h12"]["point"]
    print(f"[assert] 口径数={len(disk_tot)}，总点数极差=[{rng[0]:.4f}, {rng[1]:.4f}]；"
          f"符号翻转={tm['endpoint_sign_flips']}；"
          f"N_q90 端点比值={meta['N_q90_ratio_first_over_last']}；"
          f"baseline h12 点={base}")
    return {"tm": tm, "meta": meta, "ep": ep, "sp": sp, "m0": m0, "range": rng}


# --------------------------------------------------------------------------- #
# 图 1：通道分解（8 口径）
# --------------------------------------------------------------------------- #
def fig_decomposition(c: dict) -> list[str]:
    ep, sp, tm = c["ep"], c["sp"], c["tm"]
    rows = [("端点 " + r["endpoint_def"], float(r["scale_points"]),
             float(r["tech_points"]), float(r["total_points"])) for r in ep]
    rows += [("规格 " + r["spec"], float(r["scale_points"]),
              float(r["tech_points"]), float(r["total_points"])) for r in sp]
    rows += [("趋势 " + k, float(v["scale_points"]), float(v["tech_points"]),
              float(v["total_points"])) for k, v in tm["trend_method"].items()]
    rows.sort(key=lambda r: r[3])

    fig = plt.figure(figsize=(6.3, 4.3))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.55, 1.0], hspace=0.46)
    a = fig.add_subplot(gs[0])
    b = fig.add_subplot(gs[1])

    y = np.arange(len(rows))
    tech = np.array([r[2] for r in rows])
    scale = np.array([r[1] for r in rows])
    a.barh(y, tech, 0.58, color=S.MAIN, label="技术/数据工程通道", zorder=3)
    a.barh(y, scale, 0.58, left=tech, color=S.ACCENT[0], label="规模通道", zorder=3)
    a.axvline(0, color=S.INK, lw=0.8, zorder=4)
    for yi, r in zip(y, rows):
        a.plot([r[3]], [yi], "D", color=S.INK, ms=4.0, zorder=5)
        a.text(r[3] + 0.16, yi, f"{r[3]:.4f}", va="center", fontsize=5.9,
               color=S.INK)
    a.set_yticks(y)
    a.set_yticklabels([r[0] for r in rows], fontsize=6.1)
    a.set_xlabel("能力提升（C1 分值）")
    a.set_xlim(-5.6, 12.6)
    a.tick_params(axis="y", length=0)
    # 图例放在左上空白区（所有口径的合成柱都不落在负侧）
    a.legend(loc="upper left", bbox_to_anchor=(0.005, 0.99), ncol=1)
    a.annotate(f"◇ 合成总提升　极差 [{c['range'][0]:.4f}, {c['range'][1]:.4f}]",
               xy=(0.5, 1.015), xycoords="axes fraction", ha="center",
               fontsize=6.1, color=S.CRIT)
    S.panel(a, "a", dx=-0.30, dy=1.09)

    # --- b: 分组份额区间（份额可读的子组才画；分母为负者只标注口径） ---
    grp = S.load_csv(R1T + "q4_by_type_group.csv")
    for i, r in enumerate(grp):
        b.text(-2.35, i - 0.34, f"{r['group']}（n = {int(float(r['n']))}）",
               va="center", fontsize=6.1, color=S.BASE_DARK)
        if str(r["share_interpretable"]).strip().lower() not in ("true", "1"):
            b.text(-0.04, i, "规模份额不可读（分母为负）", va="center",
                   fontsize=6.1, color=S.BASE_DARK)
            continue
        lo, hi = [float(v) for v in r["scale_share_ci95"].strip("[]").split(",")]
        pt = float(r["scale_share"])
        col = S.MAIN if lo > 0 else (S.NEG if hi < 0 else S.BASE)
        b.plot([lo, hi], [i, i], color=col, lw=2.4, solid_capstyle="round", zorder=3)
        b.plot([pt], [i], "o", color="white", ms=5.0, zorder=4,
               markeredgecolor=col, markeredgewidth=1.4)
        b.text(hi + 0.09, i, f"[{lo:.4f}, {hi:.4f}]", va="center", fontsize=6.0,
               color=col)
    b.axvline(0, color=S.INK, lw=0.8, zorder=2)
    b.axvline(1, color=S.MID, ls=":", lw=0.8, zorder=2)
    b.text(1.0, len(grp) - 0.62, "份额 = 1", fontsize=6.0, color=S.BASE_DARK,
           ha="center")
    b.set_yticks([])
    b.set_ylim(-0.86, len(grp) - 0.14)
    b.set_xlim(-2.4, 4.9)
    b.set_xlabel("规模通道份额（95% 自助区间）", labelpad=1.5)
    b.spines["left"].set_visible(False)
    S.panel(b, "b", dx=-0.06, dy=1.10)

    return S.save(fig, "fig_q4_channel_decomposition")


# --------------------------------------------------------------------------- #
# 图 2：规模下降 vs 前沿上升
# --------------------------------------------------------------------------- #
def fig_N_trend(c: dict) -> list[str]:
    rows = S.load_csv(R2T + "q4_N_and_frontier_by_month.csv")
    meta = c["meta"]
    months = [r["month"] for r in rows]
    x = np.arange(len(rows))
    q10 = np.array([float(r["N_q10"]) for r in rows])
    q50 = np.array([float(r["N_q50"]) for r in rows])
    q90 = np.array([float(r["N_q90"]) for r in rows])
    qmax = np.array([float(r["N_max"]) for r in rows])
    sq = np.array([float(r["S_q90"]) for r in rows])

    fig, (a, b) = plt.subplots(1, 2, figsize=(6.3, 2.9),
                               gridspec_kw={"wspace": 0.34})

    # --- a: 规模分位 ---
    a.fill_between(x, q10, qmax, color=S.MAIN_PALE, alpha=0.55, zorder=1,
                   lw=0)
    for v, col, lab, dy in ((qmax, S.MAIN_LIGHT, r"$N_{\max}$", -14),
                            (q90, S.MAIN, r"$N_{q90}$", 6),
                            (q50, S.BASE_DARK, r"$N_{q50}$", 0),
                            (q10, S.BASE, r"$N_{q10}$", 0)):
        a.semilogy(x, v, "-", color=col, lw=1.3, zorder=3)
        a.annotate(lab, xy=(x[-1], v[-1]), xytext=(4, dy),
                   textcoords="offset points", color=col, fontsize=6.5,
                   va="center", ha="left")
    a.set_yscale("log")
    a.set_ylim(0.075, 4000)
    a.set_xticks(x[::2])
    a.set_xticklabels([m[2:] for m in months[::2]], fontsize=6.0, rotation=30,
                      ha="right")
    a.set_ylabel("模型规模 $N$（B 参数，对数）")
    a.set_xlim(-0.4, len(rows) + 1.9)
    a.set_xlabel("月份（2024–2025）")
    i_first, i_last = 0, len(rows) - 1
    # 比值标注放在 q10 之下（该带内无任何曲线）
    a.annotate("", xy=(i_last, 0.105), xytext=(i_first, 0.105),
               arrowprops=dict(arrowstyle="-|>", lw=0.9, color=S.NEG))
    a.text((i_first + i_last) / 2 + 0.2, 0.128,
           rf"$N_{{q90}}$ 端点比值 {meta['N_q90_ratio_first_over_last']}×",
           ha="center", va="bottom", fontsize=6.3, color=S.NEG)
    S.panel(a, "a", dx=-0.30, dy=1.08)

    # --- b: 前沿分值 ---
    b.plot(x, sq, "o-", color=S.MAIN, lw=1.4, ms=3.2, zorder=3)
    fit = np.polyfit(x, sq, 1)
    b.plot(x, np.polyval(fit, x), "--", color=S.CRIT, lw=1.0, zorder=2)
    b.set_ylim(23.5, 47.5)
    b.annotate(f"线性拟合斜率 +{meta['S_q90_slope_per_month']:.4f}/月",
               xy=(0.02, 0.97), xycoords="axes fraction", fontsize=6.3,
               color=S.CRIT, ha="left", va="top")
    b.annotate(f"前沿当前值\n{meta['S_q90_last']:.4f}", xy=(x[-1], sq[-1]),
               xytext=(-6, 12), textcoords="offset points", fontsize=6.3,
               color=S.MAIN, ha="right")
    b.set_xticks(x[::2])
    b.set_xticklabels([m[2:] for m in months[::2]], fontsize=6.0, rotation=30,
                      ha="right")
    b.set_ylabel(r"前沿能力 $S_{q90}$")
    b.set_xlabel("月份（2024–2025）")
    S.panel(b, "b", dx=-0.30, dy=1.08)

    return S.save(fig, "fig_q4_scale_vs_frontier")


# --------------------------------------------------------------------------- #
# 图 3：前沿预测与情景极差
# --------------------------------------------------------------------------- #
def fig_forecast(c: dict) -> list[str]:
    sc = S.load_csv(R1T + "q4_frontier_scenarios.csv")
    m0 = c["m0"]["predictions"]
    spr = S.load_csv(R2T + "q4_scenario_spread_scaling.csv")
    cur = c["meta"]["S_q90_last"]

    fig = plt.figure(figsize=(6.3, 3.2))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.5, 1.0], wspace=0.30)
    a = fig.add_subplot(gs[0])
    b = fig.add_subplot(gs[1])

    # --- a: 三情景 + baseline ---
    order = ["conservative", "neutral", "optimistic"]
    zh = {"conservative": "保守", "neutral": "中性", "optimistic": "乐观"}
    xpos, labels = [], []
    for i, s in enumerate(order):
        for j, h in enumerate(("h12", "h24")):
            r = next(r for r in sc if r["scenario"] == s and r["horizon"] == h)
            xp = i * 2.6 + j * 1.05
            xpos.append(xp)
            labels.append(f"{h[1:]}")
            a.plot([xp, xp], [float(r["lo95"]), float(r["hi95"])], color=S.MID,
                   lw=1.0, zorder=2)
            a.plot([xp, xp], [float(r["lo80"]), float(r["hi80"])], color=S.MAIN,
                   lw=3.0, solid_capstyle="butt", zorder=3)
            a.plot([xp], [float(r["median"])], "o", color="white", ms=4.6,
                   markeredgecolor=S.MAIN, markeredgewidth=1.4, zorder=4)
        a.text(i * 2.6 + 0.52, 0.30, zh[s], transform=a.get_xaxis_transform(),
               ha="center", va="top", fontsize=6.4, color=S.BASE_DARK)
    # baseline（M0a，h12）—— 硬性要求同图列出
    xb = -1.75
    a.plot([xb, xb], [m0["h12"]["lo95"], m0["h12"]["hi95"]], color=S.MID, lw=1.0,
           zorder=2)
    a.plot([xb, xb], [m0["h12"]["lo80"], m0["h12"]["hi80"]], color=S.ACCENT[0],
           lw=3.0, solid_capstyle="butt", zorder=3)
    a.plot([xb], [m0["h12"]["point"]], "o", color="white", ms=4.6,
           markeredgecolor=S.ACCENT[0], markeredgewidth=1.4, zorder=4)
    a.text(xb, 0.30, "baseline\nM0a  h12", transform=a.get_xaxis_transform(),
           ha="center", va="top", fontsize=6.2, color=S.ACCENT[0])
    a.axhline(cur, color=S.CRIT, ls="--", lw=1.0, zorder=1)
    a.set_xlim(-2.9, len(order) * 2.6 - 1.4)
    a.set_ylim(24, 106)
    a.annotate(f"当前前沿 {cur:.4f}", xy=(a.get_xlim()[1], cur),
               xytext=(-2, 3), textcoords="offset points", fontsize=6.2,
               color=S.CRIT, ha="right", va="bottom")
    a.set_xticks([])
    a.set_ylabel("C1 分值")
    a.legend(handles=[
        Line2D([], [], color=S.MAIN, lw=3, label="主方法：80% 区间"),
        Line2D([], [], color=S.MID, lw=1, label="95% 区间"),
        Line2D([], [], color=S.ACCENT[0], lw=3, label="baseline M0a 80% 区间"),
    ], loc="upper left", bbox_to_anchor=(0.0, 1.0), ncol=1)
    S.panel(a, "a", dx=-0.14, dy=1.07)

    # --- b: 情景极差随规模份额缩放 ---
    ss = np.array([float(r["scale_share"]) for r in spr])
    sd = np.array([float(r["implied_scenario_spread_h12"]) for r in spr])
    o = np.argsort(ss)
    b.plot(ss[o], sd[o], "o-", color=S.MAIN, lw=1.4, ms=4.2, zorder=3)
    for xi, yi in zip(ss[o], sd[o]):
        b.annotate(f"{yi:.4g}", xy=(xi, yi), xytext=(9, -3),
                   textcoords="offset points", ha="left", va="center",
                   fontsize=6.0, color=S.MAIN)
    b.set_xlabel("规模通道份额")
    b.set_ylabel("h12 情景极差（分值）")
    b.set_ylim(-1.4, 15.2)
    b.set_xlim(-0.035, 0.31)
    S.panel(b, "b", dx=-0.34, dy=1.07)

    return S.save(fig, "fig_q4_forecast_scenarios")


def main() -> None:
    S.apply_style()
    c = assert_canonical()
    out = []
    out += fig_decomposition(c)
    out += fig_N_trend(c)
    out += fig_forecast(c)
    print("[figs]", *out, sep="\n  ")


if __name__ == "__main__":
    main()

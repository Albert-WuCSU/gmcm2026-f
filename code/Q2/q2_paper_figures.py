"""Q2 论文图（Type 3）—— `gamma` 双路线条件化、域权重比、跨源验证。

数字纪律：全部读自落盘工件，脚本内不出现手打结果数字。

- `workspace/data/q2_probe_beta_sharing.json`（P9 探针，`gamma`/`beta` 双路线）
- `robustness/Q2/q2_robustness_supplement.json`（P9b 自助稳定性）
- `results/Q2/experiments/round1/tables/q2_domain_ratio.csv`
- `results/Q2/experiments/round1/tables/q2_validation.csv`
- `results/Q2/experiments/round1/tables/q2_elasticity.csv`

`assert_canonical()` 交叉核对两份 G4 工件中的同名量；不一致即拒绝出图。
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

PROBE = "workspace/data/q2_probe_beta_sharing.json"
SUPP = "robustness/Q2/q2_robustness_supplement.json"
TBL = "results/Q2/experiments/round1/tables/"


def assert_canonical() -> dict:
    p = S.load_json(PROBE)
    sup = S.load_json(SUPP)["P9_beta_sharing"]
    pairs = {
        "gamma_shift": (p["gamma_shift"], sup["gamma_shift"]),
        "threshold": (p["threshold"], sup["threshold"]),
        "shift_over_width": (p["shift_as_fraction_of_ci_width"],
                             sup["shift_as_fraction_of_ci_width"]),
        "beta_b1_point": (p["beta_b1_point"], sup["beta_b1_point"]),
        "verdict_is_fail": (p["verdict"] == "FAIL", sup["verdict"] == "FAIL"),
    }
    bad = {k: v for k, v in pairs.items() if v[0] != v[1]}
    if bad:
        raise AssertionError(f"P9 探针与 G4 补算工件不一致：{bad}")
    print(f"[assert] P9 双工件 {len(pairs)} 项一致；verdict="
          f"{p['verdict']}，位移={p['shift_as_fraction_of_ci_width']:.4f}× 区间宽"
          f"（阈 0.5）")
    return p


# --------------------------------------------------------------------------- #
# 图 1：gamma 双路线（本问头条结论的条件化）
# --------------------------------------------------------------------------- #
def fig_gamma_routes(p: dict) -> list[str]:
    A, B = p["route_A_beta_shared_from_B1"], p["route_B_beta_free_on_B7"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 2.7),
                               gridspec_kw={"width_ratios": [1.32, 1.0]})

    # --- a: 两条路线的 gamma 区间 ---
    rows = [(r"路线 A" + "\n" + r"$\beta$ 取自 B1", A["gamma"], A["gamma_ci95"],
             S.MAIN, True),
            (r"路线 B" + "\n" + r"$\beta$ 在 B7 上自由", B["gamma"],
             B["gamma_ci95"], S.NEG, False)]
    for i, (lab, g, ci, col, contains) in enumerate(rows):
        y = 1 - i
        a.plot(ci, [y, y], color=col, lw=2.6, solid_capstyle="round", zorder=3)
        a.plot([g], [y], "o", color="white", ms=5.6, zorder=4,
               markeredgecolor=col, markeredgewidth=1.5)
        a.text(g, y + 0.26, rf"$\gamma$ = {g:.4f}", ha="center", fontsize=7.0,
               color=col, fontweight="bold",
               bbox=dict(fc="white", ec="none", pad=0.6))
        a.text(ci[1] + 0.010, y, "CI 含 1.0" if contains else "CI 不含 1.0",
               va="center", fontsize=7.0, color=col)
    a.axvline(1.0, color=S.BASE_DARK, ls="--", lw=1.0, zorder=2)
    a.text(1.0, 1.48, "1.0", ha="center", fontsize=7.0, color=S.BASE_DARK,
           bbox=dict(fc="white", ec="none", pad=0.6))
    a.set_yticks([1, 0])
    a.set_yticklabels([r[0] for r in rows], fontsize=7.0)
    a.set_ylim(-0.42, 1.72)
    a.set_xlim(0.80, 1.38)
    a.set_xlabel(r"指数 $\gamma$（自助 95% 区间）")
    a.spines["left"].set_visible(False)
    a.tick_params(axis="y", length=0)
    a.annotate(f"$\\gamma$ 位移 {p['gamma_shift']:.4f}，为区间宽的 "
               f"{p['shift_as_fraction_of_ci_width']:.3f} 倍（判据阈 0.5）",
               xy=(0.5, -0.46), xycoords="axes fraction", ha="center",
               fontsize=7.0, color=S.CRIT)
    S.panel(a, "a", dx=-0.30, dy=1.06)

    # --- b: beta 的辨识缺口 ---
    b1lo, b1hi = p["beta_b1_ci95_grouped"]
    ci7 = B["beta_ci95"]
    b.plot(ci7, [0, 0], color=S.NEG, lw=2.6, solid_capstyle="round", zorder=3)
    b.plot([B["beta"]], [0], "o", color="white", ms=5.6, zorder=4,
           markeredgecolor=S.NEG, markeredgewidth=1.5)
    b.plot([b1lo, b1hi], [1, 1], color=S.MAIN, lw=2.6, solid_capstyle="round",
           zorder=3)
    b.plot([p["beta_b1_point"]], [1], "o", color="white", ms=5.6, zorder=4,
           markeredgecolor=S.MAIN, markeredgewidth=1.5)
    b.axvline(p["beta_b1_point"], color=S.MID, ls=":", lw=0.8, zorder=1)
    b.annotate("", xy=(ci7[1], 0.52), xytext=(p["beta_b1_point"], 0.52),
               arrowprops=dict(arrowstyle="<->", lw=0.8, color=S.CRIT))
    b.text((ci7[1] + p["beta_b1_point"]) / 2, 0.60,
           f"辨识缺口 {p['beta_shift']:.4f}", ha="center", fontsize=7.0,
           color=S.CRIT)
    b.text(0.004, 1.22, r"B1（真实训练日志）" + f"　$\\beta$ = {p['beta_b1_point']:.4f}",
           fontsize=7.0, color=S.MAIN)
    b.text(0.004, 0.22, r"B7 上自由估计" + f"　$\\beta$ = {B['beta']:.4f}",
           fontsize=7.0, color=S.NEG)
    b.set_yticks([])
    b.set_ylim(-0.32, 1.62)
    b.set_xlim(0.0, 0.325)
    b.set_xlabel(r"指数 $\beta$（自助 95% 区间）")
    b.spines["left"].set_visible(False)
    b1_width = b1hi - b1lo
    b.annotate(f"B1 区间宽 {b1_width:.3e}",
               xy=(0.5, -0.46), xycoords="axes fraction", ha="center",
               fontsize=7.0, color=S.BASE_DARK)
    S.panel(b, "b", dx=-0.06, dy=1.06)

    fig.subplots_adjust(wspace=0.16)
    return S.save(fig, "fig_q2_gamma_routes")


# --------------------------------------------------------------------------- #
# 图 2：域权重比 b_i / b_ref
# --------------------------------------------------------------------------- #
def fig_domain_ratio() -> list[str]:
    rows = S.load_csv(TBL + "q2_domain_ratio.csv")
    rows = sorted(rows, key=lambda r: float(r["b_ratio_vs_reference_domain"]))
    names = [r["domain"].replace("train_the_pile_", "") for r in rows]
    vals = np.array([float(r["b_ratio_vs_reference_domain"]) for r in rows])
    ref = next(r for r in rows
               if abs(float(r["b_ratio_vs_reference_domain"]) - 1.0) < 1e-9)

    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    y = np.arange(len(rows))
    cols = [S.NEG if v > 0 else S.POS for v in vals]
    ax.barh(y, vals, color=cols, height=0.66, zorder=3)
    ax.axvline(0.0, color=S.INK, lw=0.8, zorder=4)
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=7.0)
    ax.set_xlabel(r"域权重比 $b_i/b_{\mathrm{ref}}$（中心化 $w$ 之比，非有界比例）")
    ax.set_ylim(-0.8, len(rows) - 0.2)
    ax.set_xlim(-2.05, 1.55)
    ax.tick_params(axis="y", length=0)

    ref_i = next(i for i, r in enumerate(rows) if r is ref)
    ax.plot([1.0], [ref_i], "D", color=S.MAIN, ms=4.6, zorder=5)
    # 注解放进左侧空白区（除 dm_mathematics 外，负侧长条都很短）
    ax.annotate("参考域 philpapers\n比值 ≡ 1", xy=(1.0, ref_i),
                xytext=(-1.35, ref_i - 1.1), fontsize=7.0,
                color=S.MAIN, ha="center", va="center",
                arrowprops=dict(arrowstyle="-", lw=0.7, color=S.MAIN,
                                connectionstyle="arc3,rad=-0.15"))
    for i, v in enumerate(vals):
        if i == ref_i:
            continue
        off = 0.05 if v >= 0 else -0.05
        ax.text(v + off, i, f"{v:.3f}", va="center", fontsize=7.0,
                ha="left" if v >= 0 else "right", color=S.BASE_DARK)

    ax.legend(handles=[
        Line2D([], [], color=S.NEG, lw=5, label="上调该域会抬高损失（应降权）"),
        Line2D([], [], color=S.POS, lw=5, label="上调该域会降低损失（应升权）"),
    ], loc="lower right", bbox_to_anchor=(0.995, 0.02), labelcolor=S.INK)
    over = [r["domain"].replace("train_the_pile_", "")
            for r in rows if r["abs_gt_1"] == "yes"]
    ax.annotate(r"$|b_i/b_{\mathrm{ref}}|>1$：" + "、".join(over)
                + f"（{len(over)}/{len(rows)}）",
                xy=(0.5, 1.015), xycoords="axes fraction", ha="center",
                fontsize=7.0, color=S.BASE_DARK)
    return S.save(fig, "fig_q2_domain_ratio")


# --------------------------------------------------------------------------- #
# 图 3：跨源验证与弹性对照
# --------------------------------------------------------------------------- #
def fig_cross_source_validation() -> list[str]:
    rows = sorted(S.load_csv(TBL + "q2_validation.csv"), key=lambda r: float(r["spearman"]))
    effects = S.load_csv(TBL + "q2_elasticity.csv")
    fig = plt.figure(figsize=(7.2, 4.8))
    gs = fig.add_gridspec(3, 3, width_ratios=[1.55, 1, 1], wspace=.85, hspace=1.10)
    a = fig.add_subplot(gs[:, 0])
    provenance = {"B4": "真实收敛点", "B5": "文献报告值", "B2": "半合成轨迹"}
    for i, r in enumerate(rows):
        rho=float(r["spearman"])
        a.plot([.7, rho], [i,i], color=S.PALE, lw=2)
        a.plot(rho,i,'o',color=S.MAIN,ms=6)
        a.text(rho+.012,i,f"{rho:.3f}",va='center',fontsize=8.0,color=S.MAIN)
        a.text(.705,i+.23,f"{r['source']}  {provenance[r['source']]}",fontsize=8.0,color=S.INK)
        a.text(.705,i-.25,f"n = {int(float(r['n']))} · RMSE {float(r['rmse_after_deoffset']):.3f}",fontsize=7.0,color=S.BASE_DARK)
    a.set(xlim=(.69,1.08),ylim=(-.65,2.65),yticks=[],xlabel='Spearman 秩相关')
    a.spines['left'].set_visible(False)
    a.set_title('外部来源验证',loc='left',pad=18,fontsize=9.0)
    S.panel(a,'a',dx=-.12)
    labels = [
        (r'$\partial L/\partial N$', 'nats/token / B 参数'),
        (r'$\partial L/\partial D$', 'nats/token / B token'),
        (r'$\partial L/\partial Q$ *', 'nats/token / 单位 Q'),
        (r'$dN/dQ$ *', 'B 参数 / 单位 Q'),
        (r'$\Delta N$（$\Delta Q=0.1$）*', 'B 参数'),
        (r'质量 / 数据量弹性比 *', '无量纲'),
    ]
    for i,(r,(title,unit)) in enumerate(zip(effects,labels)):
        ax=fig.add_subplot(gs[i//2,1+i%2])
        vals=[float(r['B1_side_primary']),float(r['B7_side_sensitivity'])]
        ax.plot(vals,[1,0],color=S.PALE,lw=1.4)
        for y,v,col,mark in zip([1,0],vals,[S.MAIN,S.MAIN_LIGHT],['o','s']):
            ax.plot(v,y,marker=mark,color=col,ms=5)
            ax.annotate(f'{v:.4g}',(v,y),xytext=(0,7),textcoords='offset points',
                        ha='center',fontsize=7.0,color=col)
        low,high=min(vals),max(vals)
        span=max(high-low,max(abs(v) for v in vals)*.20,1e-8)
        ax.set(xlim=(low-span*.7,high+span*.7),ylim=(-.5,1.7),yticks=[1,0],
               yticklabels=['B1','B7'],xlabel=unit)
        ax.set_title(title,fontsize=8.0,pad=9)
        ax.spines['left'].set_visible(False)
        ax.tick_params(axis='y',length=0,labelsize=7)
        ax.tick_params(axis='x',labelsize=6.5)
        ax.xaxis.set_major_locator(plt.MaxNLocator(3))
        if max(abs(v) for v in vals) < .001:
            ax.ticklabel_format(axis='x', style='sci', scilimits=(0,0))
            ax.xaxis.get_offset_text().set_visible(False)
            ax.set_title(title + r' ($\times 10^{-4}$)', fontsize=8.0, pad=9)
        ax.xaxis.get_offset_text().set_fontsize(6)
    fig.text(.54,.015,'* 依赖半合成质量网格；各分量使用独立数轴',ha='center',fontsize=7.0,color=S.BASE_DARK)
    fig.subplots_adjust(bottom=.16,top=.89)
    return S.save(fig,"fig_q2_cross_source_validation")


def main() -> None:
    S.apply_style()
    p = assert_canonical()
    out = []
    out += fig_gamma_routes(p)
    out += fig_domain_ratio()
    out += fig_cross_source_validation()
    print("[figs]", *out, sep="\n  ")


if __name__ == "__main__":
    main()

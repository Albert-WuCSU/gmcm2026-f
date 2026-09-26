"""Q1 论文图（Type 3）—— 门控合成的域序与稳定性、冲突判据矩阵、Q 增量零结果。

数字纪律：全部读自落盘工件，脚本内不出现手打结果数字。

- `results/Q1/experiments/round1/tables/q1a_domain_quality.csv`（pooled 口径）
- `results/Q1/experiments/round1/tables/q1b_conflict_rates.csv`
- `results/Q1/experiments/round1/tables/q1c_validation_by_scale.csv`
- `results/Q1/experiments/round1/tables/q1c_q_increment_test.csv`
- `results/Q1/experiments/round1/metrics/q1_quality_{M0,M1}.json`（权重扰动 τ）
- `robustness/Q1/q1_robustness_quality.json`（R1 可分辨域对数、R2 种子稳定性）
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

TBL = "results/Q1/experiments/round1/tables/"
MET = "results/Q1/experiments/round1/metrics/"


def assert_canonical() -> dict:
    rob = S.load_json("robustness/Q1/q1_robustness_quality.json")
    obs = rob["checks"]["R1_domain_aggregator_swap"]["observed"]
    seeds = rob["checks"]["R2_seed_stability"]["observed"]
    m0 = S.load_json(MET + "q1_quality_M0.json")["perturbation_weights"]
    m1 = S.load_json(MET + "q1_quality_M1.json")["perturbation_weights"]
    rows = S.load_csv(TBL + "q1a_domain_quality.csv")

    # 主报口径（pooled + Huber）下的可分辨域对数须与主报告一致
    tbl_pairs = {m: obs[m]["huber"]["n_pairs_distinguishable"] for m in ("M0", "M1")}
    seed_pairs = {m: seeds["seed_20260924"][m]["n_pairs_distinguishable"]
                  for m in ("M0", "M1")}
    if tbl_pairs != seed_pairs:
        raise AssertionError(f"R1 与 R2 的可分辨域对数不一致：{tbl_pairs} vs {seed_pairs}")
    # 主报告引用的 τ 须等于 M0/M1 metrics 里的落盘值
    tau = {"M0": m0["domain_rank_kendall_tau_mean"],
           "M1": m1["domain_rank_kendall_tau_mean"]}
    frac = {"M0": m0["frac_reps_domain_order_unchanged"],
            "M1": m1["frac_reps_domain_order_unchanged"]}
    if len(m0["tau_per_rep"]) != len(m1["tau_per_rep"]):
        raise AssertionError("两臂的扰动重复数不等，τ 不可直接对照")
    print(f"[assert] 可分辨域对数 {tbl_pairs}（R1=R2）；"
          f"τ 均值 {tau['M0']:.4f}→{tau['M1']:.4f}；"
          f"域序不变比例 {frac['M0']:.3f}→{frac['M1']:.3f}；"
          f"reps={len(m0['tau_per_rep'])}；pooled 行数={len(rows)}")
    return {"obs": obs, "tau": tau, "frac": frac, "m0": m0, "m1": m1, "rows": rows}


# --------------------------------------------------------------------------- #
# 图 1：门控合成给出的域序 + 可分辨性 + 稳定性（2×2）
# --------------------------------------------------------------------------- #
def fig_gating_stability(c: dict) -> list[str]:
    rows = c["rows"]
    m0 = {r["domain"]: float(r["huber"]) for r in rows if r["method"] == "M0"}
    m1 = {r["domain"]: float(r["huber"]) for r in rows if r["method"] == "M1"}
    n_by = {r["domain"]: int(float(r["n"])) for r in rows if r["method"] == "M0"}
    hw0 = {r["domain"]: float(r["half_width"]) for r in rows if r["method"] == "M0"}
    hw1 = {r["domain"]: float(r["half_width"]) for r in rows if r["method"] == "M1"}
    o0 = sorted(m0, key=m0.get, reverse=True)
    o1 = sorted(m1, key=m1.get, reverse=True)

    fig = plt.figure(figsize=(7.2, 4.4))
    gs = fig.add_gridspec(2, 2, hspace=0.62, wspace=0.36)
    a = fig.add_subplot(gs[0, 0])
    b = fig.add_subplot(gs[0, 1])
    cc = fig.add_subplot(gs[1, 0])
    d = fig.add_subplot(gs[1, 1])

    # --- a: 域序 slopegraph ---
    r0 = {dm: i for i, dm in enumerate(o0)}
    r1 = {dm: i for i, dm in enumerate(o1)}
    for dm in o0:
        moved = r0[dm] != r1[dm]
        col = S.NEG if moved else S.MID
        a.plot([0, 1], [r0[dm], r1[dm]], color=col, lw=1.6 if moved else 1.0,
               ls="-" if moved else ":", zorder=3 if moved else 2)
        a.plot([0], [r0[dm]], "o", color=S.BASE, ms=3.4, zorder=4)
        a.plot([1], [r1[dm]], "o", color=S.MAIN, ms=3.4, zorder=4)
        a.text(-0.045, r0[dm], dm, ha="right", va="center", fontsize=7.0,
               color=S.BASE_DARK)
        a.text(1.045, r1[dm], dm, ha="left", va="center", fontsize=7.0,
               color=S.NEG if moved else S.BASE_DARK,
               fontweight="bold" if moved else "normal")
    a.set_xlim(-0.62, 1.62)
    a.set_ylim(len(o0) - 0.4, -0.6)
    a.set_xticks([0, 1])
    a.set_xticklabels(["M0\n等权平均", "M1\n门控 $Q=V(1-P)$"], fontsize=7.0)
    a.set_yticks([])
    a.spines["left"].set_visible(False)
    a.spines["bottom"].set_visible(False)
    a.tick_params(axis="x", length=0)
    a.set_title("域序：M0 vs M1", fontsize=7.0, pad=3)
    S.panel(a, "a", dx=-0.10, dy=1.10)

    # --- b: 可分辨域对数（4 个估计量） ---
    ests = ["huber", "trimmed10", "median", "mean"]
    total = len(o0) * (len(o0) - 1) // 2
    x = np.arange(len(ests))
    v0 = [c["obs"]["M0"][e]["n_pairs_distinguishable"] for e in ests]
    v1 = [c["obs"]["M1"][e]["n_pairs_distinguishable"] for e in ests]
    b.bar(x - 0.19, v0, 0.36, color=S.BASE, label="M0", zorder=3)
    b.bar(x + 0.19, v1, 0.36, color=S.MAIN, label="M1", zorder=3)
    for xi, va, vb in zip(x, v0, v1):
        b.text(xi - 0.19, va + 0.25, str(va), ha="center", fontsize=7.0,
               color=S.BASE_DARK)
        b.text(xi + 0.19, vb + 0.25, str(vb), ha="center", fontsize=7.0,
               color=S.MAIN)
    b.axhline(total, color=S.CRIT, ls="--", lw=0.9)
    b.text(0.02, total + 1.5, f"上限 {total}", fontsize=7.0,
           color=S.CRIT, ha="left", va="bottom")
    b.set_xticks(x)
    b.set_xticklabels([e.replace("trimmed10", "截尾10%") for e in ests], fontsize=7.0)
    b.set_ylabel("可分辨域对数", labelpad=1.5)
    b.set_ylim(0, total + 4.6)
    b.legend(loc="upper center", bbox_to_anchor=(0.5, -0.20), ncol=2)
    b.set_title("可分辨域对数（4 个估计量）", fontsize=7.0, pad=3)
    S.panel(b, "b", dx=-0.26, dy=1.08)

    # --- c: 区间半宽 vs 样本量 ---
    for dm in o0:
        cc.plot([n_by[dm], n_by[dm]], [hw0[dm], hw1[dm]], color=S.PALE, lw=0.8,
                zorder=1)
    cc.loglog([n_by[dm] for dm in o0], [hw0[dm] for dm in o0], "o", color=S.BASE,
              ms=4.4, label="M0", zorder=3)
    cc.loglog([n_by[dm] for dm in o1], [hw1[dm] for dm in o1], "o", color=S.MAIN,
              ms=4.4, label="M1", zorder=3)
    bk = "book"
    cc.set_ylim(1.6e-4, 4.6e-2)
    cc.set_xlim(120, 2.4e6)
    cc.annotate(f"book：n={n_by[bk]}\n半宽 {hw0[bk]:.4f}",
                xy=(n_by[bk], hw0[bk]), xytext=(14, -18),
                textcoords="offset points", fontsize=7.0, color=S.NEG, ha="left")
    cc.set_xlabel("域样本量 $n$（对数）")
    cc.set_ylabel("自助半宽（对数）", labelpad=1.5)
    cc.legend(loc="lower left", bbox_to_anchor=(0.0, 0.0), ncol=2)
    cc.set_title("区间半宽 vs 样本量", fontsize=7.0, pad=3)
    S.panel(cc, "c", dx=-0.28, dy=1.08)

    # --- d: 权重扰动下的域序稳定性 ---
    t0 = np.array(c["m0"]["tau_per_rep"])
    t1 = np.array(c["m1"]["tau_per_rep"])
    rng = np.random.default_rng(20260924)
    for i, (t, col, lab) in enumerate(((t0, S.BASE, "M0"), (t1, S.MAIN, "M1"))):
        jit = rng.uniform(-0.13, 0.13, size=t.size)
        d.plot(t, np.full(t.size, i) + jit, "o", color=col, ms=2.2, alpha=0.75,
               markeredgecolor="none", zorder=3)
        d.plot([t.mean()], [i], "D", color=col, ms=5.0, zorder=4,
               markeredgecolor="white", markeredgewidth=0.8)
        d.plot([t.min()], [i], "|", color=col, ms=7, mew=1.2, zorder=4)
        d.text(t.mean(), i + 0.34, f"均值 {t.mean():.4f}", ha="center",
               fontsize=7.0, color=col)
    d.set_yticks([0, 1])
    d.set_yticklabels(["M0", "M1"], fontsize=7.0)
    d.set_ylim(-0.72, 1.62)
    d.set_xlim(0.775, 1.045)
    d.set_xlabel(r"域序 Kendall $\tau$（$n_{\rm rep}$ = " + f"{t0.size})")
    d.spines["left"].set_visible(False)
    d.tick_params(axis="y", length=0)
    d.annotate(f"域序不变的重复比  {c['frac']['M0']:.3f} → {c['frac']['M1']:.3f}",
               xy=(0.5, -0.40), xycoords="axes fraction", ha="center",
               fontsize=7.0, color=S.BASE_DARK)
    d.set_title("权重扰动下的域序稳定性", fontsize=7.0, pad=3)
    S.panel(d, "d", dx=-0.18, dy=1.08)

    return S.save(fig, "fig_q1_gating_stability")


# --------------------------------------------------------------------------- #
# 图 2：冲突判据 × 锚点矩阵
# --------------------------------------------------------------------------- #
def fig_conflict_matrix() -> list[str]:
    rows = S.load_csv(TBL + "q1b_conflict_rates.csv")
    dec = S.load_json(MET + "q1_quality_M1.json")["conflict_criterion_decision"]
    pops = ["pooled", "per_domain"]
    anchors = ["p70", "p75", "p80"]
    # 判据顺序必须**全序**：`sorted(set, key=族名)` 在同族内会因字符串哈希随机化
    # 而逐进程改变行序（已实测），故键取 (族, 全名)。
    crits = sorted({r["criterion"] for r in rows},
                   key=lambda k: (k.split("_")[0], k))
    # 判据短名必须能区分同族变体（CD1 与 CD3 各有两种）
    short = {}
    for kk in crits:
        fam = kk.split("_")[0]
        if fam == "CD2":
            short[kk] = "CD2"
        elif "MAD" in kk and "fixed" not in kk:
            short[kk] = "CD1\nMAD 锚定"
        elif "fixed_ref" in kk:
            short[kk] = "CD1\n固定 0.25"
        elif "ge5" in kk:
            short[kk] = "CD3\n≥5 高 ∧ ≥5 低"
        else:
            short[kk] = "CD3\n≥3 高 ∧ ≥3 低"
    val = {(r["population"], r["anchor"], r["criterion"]): float(r["conflict_rate"])
           for r in rows}
    # 主判据与其锚点取自落盘裁定，不在此处臆测
    prim_key, prim_anchor = dec["primary_key"], dec["primary_anchor"]
    prim_pop = "pooled"
    prim_val = val[(prim_pop, prim_anchor, prim_key)]
    if dec["choice"] != f"CD2@{prim_anchor}" or not prim_key.startswith("CD2"):
        raise AssertionError(f"裁定与判据键不符：{dec['choice']} / {prim_key}")

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.75),
                             gridspec_kw={"wspace": 0.10})
    lo_band, hi_band = 0.01, 0.50
    for ax, pop, title in zip(axes, pops,
                              ["主口径 pooled + ecdf", "消融臂 per_domain + ecdf"]):
        M = np.array([[val[(pop, a, kk)] for a in anchors] for kk in crits])
        im = ax.imshow(M, cmap="Blues", vmin=0.0, vmax=1.0, aspect="auto")
        for i in range(len(crits)):
            for j in range(len(anchors)):
                v = M[i, j]
                inband = lo_band < v < hi_band
                ax.text(j, i, f"{v:.3f}", ha="center", va="center", fontsize=7.0,
                        color="white" if v > 0.55 else S.INK,
                        fontweight="bold" if not inband else "normal")
                if not inband:
                    ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False,
                                               edgecolor=S.CRIT, lw=1.4, zorder=5))
        if pop == prim_pop:
            i = crits.index(prim_key)
            j = anchors.index(prim_anchor)
            ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False,
                                       edgecolor=S.INK, lw=1.8, zorder=6))
            # The black cell border identifies the selected criterion; avoid text on adjacent cells.
        ax.set_xticks(range(len(anchors)))
        ax.set_xticklabels(anchors, fontsize=7.0)
        ax.set_yticks(range(len(crits)))
        ax.set_yticklabels([short[kk] for kk in crits], fontsize=7.0)
        if pop == "per_domain":
            ax.tick_params(labelleft=False)
        ax.set_title(title, fontsize=7.0, pad=3)
        ax.tick_params(length=0)
        for sp in ax.spines.values():
            sp.set_visible(False)
    fig.colorbar(im, ax=axes, fraction=0.030, pad=0.015, label="冲突率")
    axes[0].annotate("红框：非退化带 (0.01, 0.50) 之外　　黑框：主判据",
                     xy=(0.0, -0.32), xycoords="axes fraction", fontsize=7.0,
                     color=S.CRIT)
    axes[0].set_ylabel("冲突判据", fontsize=7.0, labelpad=1.5)
    for ax, lab in zip(axes, "ab"):
        S.panel(ax, lab, dx=-0.20, dy=1.12)
    print(f"[conflict] 主判据 {dec['choice']} = {prim_val:.6f}"
          f"（裁定 choice={dec['choice']}）；非退化带 ({lo_band}, {hi_band})")
    return S.save(fig, "fig_q1_conflict_matrix")


# --------------------------------------------------------------------------- #
# 图 3：配比侧的 Q 增量零结果
# --------------------------------------------------------------------------- #
def fig_q_increment() -> list[str]:
    val = S.load_csv(TBL + "q1c_validation_by_scale.csv")
    inc = S.load_csv(TBL + "q1c_q_increment_test.csv")
    scales = [r["scale"] for r in inc]
    scale_labels = [s.replace("test_", "") for s in scales]
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 2.6),
                               gridspec_kw={"width_ratios": [1.15, 1.0]})

    x = np.arange(len(scales))
    for mid, off, col in (("M0c", -0.19, S.BASE), ("M1c", 0.19, S.MAIN)):
        v = [float(next(r["r2_after_offset_removal"] for r in val
                        if r["method"] == mid and r["scale"] == s))
             for s in scales]
        a.bar(x + off, v, 0.36, color=col, label=mid, zorder=3)
        for xi, vi in zip(x + off, v):
            a.text(xi, vi + 0.02, f"{vi:.3f}", ha="center", fontsize=7.0,
                   color=S.BASE_DARK)
    a.set_xticks(x)
    a.set_xticklabels(scale_labels, fontsize=7.0)
    a.set_ylabel("去偏 $R^2$（配比 → 损失）")
    a.set_ylim(0, 1.22)
    a.legend(loc="upper right", ncol=2)
    S.panel(a, "a", dx=-0.22, dy=1.08)

    y = np.arange(len(scales))
    v = np.array([float(r["increment"]) for r in inc])
    lo = v - np.array([float(r["ci95_lo"]) for r in inc])
    hi = np.array([float(r["ci95_hi"]) for r in inc]) - v
    b.errorbar(v, y, xerr=[lo, hi], fmt="o", ms=5.0, capsize=3, color=S.MAIN,
               elinewidth=1.2, zorder=3)
    b.axvline(0.0, color=S.CRIT, ls="--", lw=1.0)
    span = max(hi.max(), lo.max(), v.max()) * 1.30
    b.set_xlim(-span, span)
    for yi, vi in zip(y, v):
        # 数值列固定在轴内右侧空白带，既不压零线也不压误差棒
        b.text(0.78, yi, f"{vi:+.5f}", transform=b.get_yaxis_transform(),
               ha="left", va="center", fontsize=7.0, color=S.BASE_DARK)
    # 显著性并入刻度标签，避免与数值列争位
    b.set_yticks(y)
    b.set_yticklabels([f"{s}\n（{'显著' if sig == 'True' else '不显著'}）"
                       for s, sig in zip(scale_labels, [r["significant"] for r in inc])],
                      fontsize=7.0)
    b.set_ylim(-0.68, len(scales) - 0.32)
    b.ticklabel_format(axis="x", style="sci", scilimits=(-3, -3))
    b.xaxis.set_major_locator(plt.MaxNLocator(4))
    b.xaxis.get_offset_text().set_visible(False)
    b.set_xlabel("引入域级 $Q$ 的去偏 $R^2$ 增量（95% 区间，$\\times 10^{-3}$）")
    b.spines["left"].set_visible(False)
    b.tick_params(axis="y", length=0)
    S.panel(b, "b", dx=-0.10, dy=1.08)

    fig.subplots_adjust(wspace=0.46)
    return S.save(fig, "fig_q1_q_increment")


def main() -> None:
    S.apply_style()
    c = assert_canonical()
    out = []
    out += fig_gating_stability(c)
    out += fig_conflict_matrix()
    out += fig_q_increment()
    print("[figs]", *out, sep="\n  ")


if __name__ == "__main__":
    main()

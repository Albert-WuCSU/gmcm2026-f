"""Q3 论文图（Type 3）—— 结构性转移、三定义对比、`L_ctx` 跨临界压缩。

数字纪律：本脚本**不手打任何结果数字**。相图曲线由 `q3_common.Model` 从
`results/Q2/.../q2_M1s.json` 的承重参数重算，并在 `assert_canonical()` 中
逐项对拍落盘工件：

- `results/Q3/experiments/round1/tables/q3_optimal_by_budget.csv`（三档锚点解）
- `results/Q3/experiments/round1/tables/q3_transition_definitions.csv`（A/C 位置）
- `results/Q3/experiments/round1/tables/q3_lctx_sensitivity.csv`（五档 `L_ctx`）

对拍不过即抛错，不产图。重算的扫描点落盘为
`results/Q3/experiments/round1/tables/q3_optimal_path_sweep.csv`，作为本图的
数据出处（该表由 `q3_optimize_main.sweep` 生成，与 round1 同参数同种子）。
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

import figstyle as S  # noqa: E402
from q3_common import L_CTX_CRIT, L_CTX_DEFAULT, Q0_DEFAULT, Model, load_law_params  # noqa: E402
from q3_optimize_main import (D_THRESHOLD, SWEEP_MAIN_STEP, SWEEP_RANGE,  # noqa: E402
                              definition_A, definition_C, sweep)

TBL = ROOT / "results/Q3/experiments/round1/tables"
TOL = 1e-9


def _close(a, b, tol=TOL):
    return a is not None and b is not None and abs(float(a) - float(b)) <= tol * max(
        1.0, abs(float(a)), abs(float(b)))


def assert_canonical(model: Model, pts: list) -> dict:
    """把重算结果钉在落盘工件上；任一不符即中止。

    `L_ctx` 三项百分比取自 `metrics/q3_M1o.json` 的 `lctx_sensitivity`，
    **不由本脚本自行定义**（自算 `(max-min)/mean` 得 3.17%，与落盘口径 3.22% 不同）。
    """
    anchors_disk = S.load_csv(str((TBL / "q3_optimal_by_budget.csv").relative_to(ROOT)))
    trans_disk = S.load_csv(str((TBL / "q3_transition_definitions.csv").relative_to(ROOT)))
    lctx_disk = S.load_csv(str((TBL / "q3_lctx_sensitivity.csv").relative_to(ROOT)))
    m1o_disk = S.load_json("results/Q3/experiments/round1/metrics/q3_M1o.json")
    lctx_canon = m1o_disk["lctx_sensitivity"]
    n_spread = lctx_canon["N_over_D_relative_spread"]
    n_pct = lctx_canon["N_B_change_pct"]
    d_pct = lctx_canon["D_B_change_pct"]
    crit = lctx_canon["L_ctx_crit_recomputed"]

    def _pct(vals):
        return 100.0 * (vals[-1] - vals[0]) / vals[0]

    n_disk = [float(r["N_B"]) for r in lctx_disk]
    d_disk = [float(r["D_B"]) for r in lctx_disk]
    rnd_disk = [float(r["N_over_D"]) for r in lctx_disk]
    checks_pct = {
        "lctx_N_B_change_pct": (_pct(n_disk), n_pct),
        "lctx_D_B_change_pct": (_pct(d_disk), d_pct),
        "lctx_N_over_D_relative_spread": (
            (max(rnd_disk) - min(rnd_disk)) / min(rnd_disk), n_spread),
        "lctx_crit": (L_CTX_CRIT, crit),
    }
    bad_pct = {k: v for k, v in checks_pct.items()
               if abs(v[0] - v[1]) > 1e-6 * max(1.0, abs(v[1]))}
    if bad_pct:
        raise AssertionError(f"Q3 落盘口径与实现口径不一致：{bad_pct}")

    defA = definition_A(model, pts)
    defC = definition_C(pts)
    sat = defA["changes"][0]["located_log10_C"]

    checks = {"transition_A": (sat, float(trans_disk[0]["location_log10_C"]))}
    checks["transition_C"] = (defC["changes"][0]["at_log10_C"],
                              float(trans_disk[1]["location_log10_C"]))
    for row in anchors_disk:
        C = float(row["C"])
        best, _ = model.solve_kkt(C)
        for k in ("N_B", "D_B", "Q", "loss"):
            checks[f"anchor_{row['C']}_{k}"] = (best[k], float(row[k]))
    for row in lctx_disk:
        m = Model(load_law_params(), Q0=Q0_DEFAULT, L_ctx=int(row["L_ctx"]),
                  form="exponential")
        best, _ = m.solve_kkt(1e22)
        checks[f"lctx_{row['L_ctx']}_N_B"] = (best["N_B"], float(row["N_B"]))
        checks[f"lctx_{row['L_ctx']}_D_B"] = (best["D_B"], float(row["D_B"]))
        checks[f"lctx_{row['L_ctx']}_N_over_D"] = (best["N_over_D"],
                                                   float(row["N_over_D"]))

    bad = {k: v for k, v in checks.items() if not _close(*v)}
    if bad:
        raise AssertionError(f"重算与落盘工件不一致，拒绝出图：{bad}")
    print(f"[assert] {len(checks) + len(checks_pct)} 项对拍全部通过（1e-9 相对 / 1e-6 口径）")
    return {"sat": sat, "defC": defC["changes"][0]["at_log10_C"],
            "n_checks": len(checks) + len(checks_pct),
            "n_pct": n_pct, "d_pct": d_pct, "nd_spread": n_spread, "crit": crit}


def dump_sweep(pts: list) -> str:
    rel = "results/Q3/experiments/round1/tables/q3_optimal_path_sweep.csv"
    cols = ["log10_C", "N_B", "D_B", "Q", "N_over_D", "loss", "branch",
            "share_C_train", "share_C_Q", "share_C_attn"]
    with (ROOT / rel).open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for p in pts:
            sh = p["cost_shares"]
            w.writerow([p["log10_C"], p["N_B"], p["D_B"], p["Q"], p["N_over_D"],
                        p["loss"], p["branch"], sh["C_train"], sh["C_Q"], sh["C_attn"]])
    print(f"[dump] {rel}（{len(pts)} 点）")
    return rel


# --------------------------------------------------------------------------- #
# 图 1：最优路径相图
# --------------------------------------------------------------------------- #
def fig_optimal_path(pts: list, sat: float, c_trans: float) -> list[str]:
    lc = np.array([p["log10_C"] for p in pts])
    Q = np.array([p["Q"] for p in pts])
    N = np.array([p["N_B"] for p in pts])
    D = np.array([p["D_B"] for p in pts])
    sh = {k: np.array([p["cost_shares"][k] for p in pts])
          for k in ("C_train", "C_Q", "C_attn")}
    dQ = np.gradient(Q, lc)
    xmax = lc[-1] + 1.35          # 右侧留白供直接标注

    fig, axes = plt.subplots(4, 1, figsize=(7.2, 7.4), sharex=True,
                             gridspec_kw={"height_ratios": [1.15, 1.0, 1.0, 0.8],
                                          "hspace": 0.16})
    (a, b, c, d) = axes

    # --- a: Q*，活跃约束集分区着色 ---
    a.axvspan(lc[0], sat, color=S.BAND, zorder=0)
    a.axvspan(sat, xmax, color="#FBF0ED", zorder=0)
    a.axhline(1.0, color=S.MID, lw=0.7, ls=":", zorder=1)
    a.axhline(Q0_DEFAULT, color=S.MID, lw=0.7, ls=":", zorder=1)
    a.plot(lc, Q, color=S.MAIN, lw=1.5, zorder=3)
    a.set_ylim(0.30, 1.14)
    a.set_ylabel(r"最优质量 $Q^{*}$", labelpad=1.5)
    a.text(0.015, 0.74, "内点分支  $Q_0<Q^{*}<1$", transform=a.transAxes,
           fontsize=7.0, color=S.BASE_DARK, va="top")
    a.text(0.985, 0.74, r"边界分支  $Q^{*}\equiv1$", transform=a.transAxes,
           fontsize=7.0, color=S.NEG, va="top", ha="right")
    a.text(lc[0] + 0.08, Q0_DEFAULT + 0.025, r"$Q_0=0.35$", fontsize=7.0,
           color=S.BASE_DARK)
    S.vline(a, sat, None, y=0.99)
    a.annotate(rf"$\log_{{10}}C = {sat:.4f}$",
               xy=(sat, 0.86), xytext=(10, 0), textcoords="offset points",
               fontsize=7.0, color=S.CRIT, ha="left", va="top")
    S.panel(a, "a")

    # --- b: 规模路径 ---
    b.semilogy(lc, D, color=S.ACCENT[2], lw=1.4, zorder=3)
    b.semilogy(lc, N, color=S.MAIN, lw=1.4, zorder=3)
    b.set_ylabel("最优规模 (B)", labelpad=1.5)
    b.set_ylim(0.03, 2e5)
    S.direct_label(b, lc[-1], D[-1], r" $D^{*}$", S.ACCENT[2], fs=7)
    S.direct_label(b, lc[-1], N[-1], r" $N^{*}$", S.MAIN, fs=7)
    S.vline(b, sat, None)
    S.panel(b, "b")

    # --- c: 成本分项占比 ---
    for k, col, lab in (("C_train", S.MAIN, r"$C_{\mathrm{train}}$"),
                        ("C_attn", S.ACCENT[0], r"$C_{\mathrm{attn}}$"),
                        ("C_Q", S.ACCENT[1], r"$C_{Q}$")):
        c.plot(lc, sh[k], color=col, lw=1.4, zorder=3)
    S.direct_label(c, lc[-1], sh["C_train"][-1], r" $C_{\mathrm{train}}$", S.MAIN)
    S.direct_label(c, lc[-1], sh["C_attn"][-1], r" $C_{\mathrm{attn}}$",
                   S.ACCENT[0], dy_data=0.09)
    S.direct_label(c, lc[-1], sh["C_Q"][-1], r" $C_{Q}$", S.ACCENT[1], dy_data=0.30)
    c.set_ylabel("成本分项占比", labelpad=1.5)
    c.set_ylim(-0.20, 1.06)
    S.vline(c, sat, None)
    S.vline(c, c_trans, None, ls="-.", lw=0.9)
    c.annotate(rf"$\log_{{10}}C = {c_trans:.3f}$", xy=(c_trans, 0.60),
               xytext=(-16, 0), textcoords="offset points", fontsize=7.0,
               color=S.CRIT, ha="right", va="center")
    S.panel(c, "c")

    # --- d: 饱和点导数 ---
    pos = lc <= sat
    d.plot(lc[pos], dQ[pos], color=S.MAIN, lw=1.5, zorder=3)
    d.plot(lc[~pos], dQ[~pos], color=S.MID, lw=1.5, zorder=3)
    d.axhline(0.0, color=S.MID, lw=0.7, ls=":")
    d.set_ylabel(r"$dQ^{*}/d\log_{10}C$", labelpad=1.5)
    d.set_xlabel(r"算力预算 $\log_{10}C$  (FLOPs)")
    S.vline(d, sat, None)
    d.set_ylim(-0.02, 0.19)
    S.panel(d, "d")

    for ax in axes[:-1]:
        ax.tick_params(labelbottom=False)
        ax.set_xlim(lc[0], xmax)
    fig.subplots_adjust(left=0.135, right=0.995)
    return S.save(fig, "fig_q3_optimal_path")


# --------------------------------------------------------------------------- #
# 图 2：三定义转移点对比
# --------------------------------------------------------------------------- #
def fig_transition_definitions(model: Model, pts: list, sat: float,
                               c_trans: float) -> list[str]:
    lc = np.array([p["log10_C"] for p in pts])
    Q = np.array([p["Q"] for p in pts])
    sh = {k: np.array([p["cost_shares"][k] for p in pts])
          for k in ("C_train", "C_Q", "C_attn")}

    fig = plt.figure(figsize=(7.2, 4.8))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.15, 1.0], hspace=0.62, wspace=0.30)
    a = fig.add_subplot(gs[0, :])
    b = fig.add_subplot(gs[1, 0])
    c = fig.add_subplot(gs[1, 1])

    # --- a: Q* + 三定义的判定位置 ---
    a.plot(lc, Q, color=S.MAIN, lw=1.6, zorder=3)
    a.axhline(1.0, color=S.MID, lw=0.7, ls=":")
    a.set_ylim(0.28, 1.12)
    a.set_ylabel(r"$Q^{*}$", labelpad=1.5)
    a.set_xlim(lc[0], lc[-1])
    a.tick_params(labelbottom=False)
    S.vline(a, sat, None, y=0.99)
    S.vline(a, c_trans, None, ls="-.", lw=0.9, y=0.99)
    a.legend(handles=[
        Line2D([], [], color=S.CRIT, ls="--", lw=0.9,
               label=f"A 活跃约束集变化：{sat:.4f}"),
        Line2D([], [], color=S.CRIT, ls="-.", lw=0.9,
               label=f"C 成本占比排序翻转：{c_trans:.3f}"),
        Line2D([], [], color=S.MID, ls=":", lw=1.4,
               label=r"D 分配份额突变（阈值 0.05）：无越阈点"),
        Line2D([], [], color=S.MAIN, ls="-", lw=1.6, label=r"最优路径 $Q^{*}(\log_{10}C)$"),
    ], loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2, frameon=False)
    S.panel(a, "a")

    # --- b: 定义 D 的步长敏感性 ---
    for st, col in zip((0.5, 0.25, 0.125), (S.NEG, S.ACCENT[1], S.MAIN_LIGHT)):
        p = sweep(model, st)
        x = np.array([q["log10_C"] for q in p])[1:]
        dq = np.abs(np.diff(np.array([q["Q"] for q in p])))
        b.plot(x, dq, "o-", ms=2.2, lw=1.1, color=col, label=f"扫描步长 {st:g}")
    b.axhline(D_THRESHOLD, color=S.CRIT, ls="--", lw=0.9)
    b.text(lc[-1], D_THRESHOLD * 1.45, f" 判定阈值 {D_THRESHOLD}", fontsize=7.0,
           color=S.CRIT, ha="right")
    b.set_yscale("log")
    b.set_ylim(2.2e-4, 1.4)
    b.set_xlim(lc[0], lc[-1])
    b.set_xlabel(r"$\log_{10}C$")
    b.set_ylabel(r"相邻点 $|\Delta Q^{*}|$", labelpad=1.5)
    b.legend(loc="lower left", bbox_to_anchor=(0.005, 0.02))
    b.annotate("仅步长 0.5 出现越阈点", xy=(18.07, 0.082), xytext=(19.4, 0.42),
               fontsize=7.0, color=S.NEG, ha="left",
               arrowprops=dict(arrowstyle="-", lw=0.6, color=S.NEG))
    b.annotate("饱和后 $\\Delta Q^{*}=0$", xy=(21.7, 2.6e-4), fontsize=7.0,
               color=S.BASE_DARK, ha="left", va="bottom")
    S.panel(b, "b")

    # --- c: 定义 C 的排序翻转 ---
    for k, col, lab in (("C_train", S.MAIN, r"$C_{\mathrm{train}}$"),
                        ("C_attn", S.ACCENT[0], r"$C_{\mathrm{attn}}$"),
                        ("C_Q", S.ACCENT[1], r"$C_{Q}$")):
        c.plot(lc, sh[k], color=col, lw=1.4, label=lab)
    c.set_xlim(lc[0], lc[-1])
    c.set_ylim(-0.05, 1.06)
    c.set_xlabel(r"$\log_{10}C$")
    c.set_ylabel("成本分项占比", labelpad=1.5)
    S.vline(c, c_trans, None, ls="-.")
    c.legend(loc="center left", bbox_to_anchor=(0.02, 0.50))
    S.panel(c, "c")

    return S.save(fig, "fig_q3_transition_definitions")


# --------------------------------------------------------------------------- #
# 图 3：`L_ctx` 跨临界 —— 压缩规模而非重排配比
# --------------------------------------------------------------------------- #
def fig_lctx_compression(law: dict, meta: dict) -> list[str]:
    rows = S.load_csv("results/Q3/experiments/round1/tables/q3_lctx_sensitivity.csv")
    L = np.array([float(r["L_ctx"]) for r in rows])
    N = np.array([float(r["N_B"]) for r in rows])
    D = np.array([float(r["D_B"]) for r in rows])
    rND = np.array([float(r["N_over_D"]) for r in rows])
    ratio = np.array([float(r["attn_over_train"]) for r in rows])
    crit, n_pct, d_pct = meta["crit"], meta["n_pct"], meta["d_pct"]

    fig, (a, b, c) = plt.subplots(1, 3, figsize=(7.2, 2.45))
    for ax in (a, b, c):
        ax.axvspan(crit, L[-1], color="#FBF0ED", zorder=0)

    # --- a: N*, D* 各自腰斩 ---
    a.loglog(L, D, "o-", color=S.ACCENT[2], lw=1.3, ms=3.2)
    a.loglog(L, N, "o-", color=S.MAIN, lw=1.3, ms=3.2)
    a.set_xlabel(r"上下文长度 $L_{\mathrm{ctx}}$")
    a.set_ylabel("最优规模 (B)", labelpad=1.5)
    a.set_ylim(1.5, 1500)
    a.set_xlim(L[0] * 0.72, L[-1] * 1.9)
    S.direct_label(a, L[-1], N[-1], r" $N^{*}$", S.MAIN, fs=7)
    S.direct_label(a, L[-1], D[-1], r" $D^{*}$", S.ACCENT[2], fs=7)
    a.axvline(crit, color=S.CRIT, ls="--", lw=0.9)
    a.annotate(f"临界 {crit:.0f}", xy=(crit, 2200), fontsize=7.0, color=S.CRIT,
               ha="center", va="bottom")
    a.text(0.03, 0.05, f"$N^{{*}}$ {n_pct:+.1f}%\n$D^{{*}}$ {d_pct:+.1f}%",
           transform=a.transAxes, fontsize=7.0, color=S.NEG, va="bottom")
    S.panel(a, "a", dx=-0.34, dy=1.09)

    # --- b: N:D 几乎不动 ---
    b.semilogx(L, rND, "o-", color=S.MAIN, lw=1.4, ms=3.2)
    b.set_xlabel(r"上下文长度 $L_{\mathrm{ctx}}$")
    b.set_ylabel(r"配比 $N^{*}\!:\!D^{*}$", labelpad=1.5)
    b.set_ylim(rND.min() * 0.955, rND.max() * 1.035)
    b.set_xlim(L[0] * 0.72, L[-1] * 1.35)
    b.axvline(crit, color=S.CRIT, ls="--", lw=0.9)
    b.annotate(f"相对极差 {meta['nd_spread']:.2%}", xy=(0.5, 0.05),
               xycoords="axes fraction", fontsize=7.0, color=S.POS,
               ha="center", va="bottom")
    S.panel(b, "b", dx=-0.34, dy=1.09)

    # --- c: 注意力/训练成本比跨过 1 ---
    c.loglog(L, ratio, "o-", color=S.ACCENT[0], lw=1.4, ms=3.2)
    c.axhline(1.0, color=S.CRIT, ls="--", lw=0.9)
    c.annotate(r"$C_{\mathrm{attn}}=C_{\mathrm{train}}$", xy=(L[0] * 1.05, 1.16),
               fontsize=7.0, color=S.CRIT, ha="left", va="bottom")
    c.set_xlabel(r"上下文长度 $L_{\mathrm{ctx}}$")
    c.set_ylabel(r"$C_{\mathrm{attn}}/C_{\mathrm{train}}$", labelpad=1.5)
    c.set_ylim(0.03, 12)
    c.set_xlim(L[0] * 0.72, L[-1] * 1.35)
    c.axvline(crit, color=S.CRIT, ls="--", lw=0.9)
    S.panel(c, "c", dx=-0.34, dy=1.09)

    fig.subplots_adjust(wspace=0.52)
    return S.save(fig, "fig_q3_lctx_compression")


def main() -> None:
    S.apply_style()
    law = load_law_params()
    model = Model(law, Q0=Q0_DEFAULT, L_ctx=L_CTX_DEFAULT, form="exponential")
    pts = sweep(model, SWEEP_MAIN_STEP)
    meta = assert_canonical(model, pts)
    sweep_rel = dump_sweep(pts)

    out = []
    out += fig_optimal_path(pts, meta["sat"], meta["defC"])
    out += fig_transition_definitions(model, pts, meta["sat"], meta["defC"])
    out += fig_lctx_compression(law, meta)
    print("[figs]", *out, sep="\n  ")
    print(f"[meta] sweep={sweep_rel} n_checks={meta['n_checks']} "
          f"range={SWEEP_RANGE} step={SWEEP_MAIN_STEP}")


if __name__ == "__main__":
    main()

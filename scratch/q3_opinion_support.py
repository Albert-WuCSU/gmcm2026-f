"""支撑 AI 对 Q3 三条裁定的意见的算例。非交付物，不进论文、不进账本。

目标函数与成本式逐行照抄 workspace/code/scripts/probe_q3_optimization.py，
只改扫描步长，以检验「裁定 2 选 D」的结论是否依赖网格步长。

检验项：
  T1  D 定义（一阶差分 > 0.05）在 step = 0.5 / 0.25 / 0.125 下的 verdict 是否翻转
  T2  饱和点附近 dQ*/dlogC 的符号（核对选择卡「导数由负转零」的表述）
  T3  本标度律隐含的 D/N 是否等于 Chinchilla 的 20 tokens/param
"""
from __future__ import annotations

import time

import numpy as np
from scipy.optimize import brentq, minimize

E, A, AL, B, BE, GA = 1.68979741, 0.35398032, 0.33997658, 1.24030577, 0.27987806, 0.96591294
ETA = 2e-4
Q0 = 0.35
SEED = 20260924
G = {
    "exponential": lambda q: 1e7 * np.exp(6.0 * q),
    "power": lambda q: 5e9 * q ** 4.0,
    "log_asymptotic": lambda q: 2e9 * np.log(1.0 + 10.0 * q),
}


def loss(N_B, D_B, Q):
    return E + A * N_B ** (-AL) + B * (D_B * Q ** GA) ** (-BE)


def cost(N_B, D_B, Q, gname, L_ctx):
    N, D = N_B * 1e9, D_B * 1e9
    g = G[gname]
    return 6.0 * N * D + D * max(g(Q) - g(Q0), 0.0) + ETA * N * D * L_ctx


def solve(C, gname="exponential", L_ctx=2048, n_start=8):
    def obj(x):
        return loss(10 ** x[0], 10 ** x[1], x[2])

    def con(x):
        return (C - cost(10 ** x[0], 10 ** x[1], x[2], gname, L_ctx)) / C

    rng = np.random.default_rng(SEED)
    base = 0.5 * np.log10(max(C / 6.0 / 1e18, 1e-12))
    best = None
    for _ in range(n_start):
        x0 = np.array([base + rng.uniform(-1, 1), base + rng.uniform(-1, 1),
                       rng.uniform(Q0 + 0.01, 0.99)])
        try:
            r = minimize(obj, x0, method="SLSQP", bounds=[(-4, 5), (-4, 6), (Q0, 1.0)],
                         constraints=[{"type": "ineq", "fun": con}],
                         options={"maxiter": 500, "ftol": 1e-12})
        except Exception:
            continue
        if not r.success or con(r.x) < -1e-6:
            continue
        if best is None or r.fun < best.fun:
            best = r
    if best is None:
        return None
    return {"Q": float(best.x[2]), "N_B": float(10 ** best.x[0]), "D_B": float(10 ** best.x[1])}


def sweep(lo, hi, step):
    pts = []
    for lc in np.arange(lo, hi + 1e-9, step):
        s = solve(10 ** lc)
        if s:
            pts.append((float(lc), s["Q"]))
    return pts


def main():
    t0 = time.time()

    print("=" * 74)
    print("T1  D-definition grid sensitivity  (threshold 0.05 on |dQ*|)")
    print("=" * 74)
    cache = {}
    for step in (0.5, 0.25, 0.125):
        pts = sweep(18.0, 22.0, step)
        cache[step] = pts
        q = np.array([p[1] for p in pts])
        dq = np.abs(np.diff(q))
        imax = int(dq.argmax())
        print(f"  step={step:<6} n={len(pts):<4} max|dQ|={dq.max():.6f}  "
              f"at log10C={pts[imax + 1][0]:.3f}  "
              f"verdict={'TRANSITION_EXISTS' if dq.max() > 0.05 else 'NO_TRANSITION':<18} "
              f"(n_jumps={int((dq > 0.05).sum())})")
    print(f"  [{time.time() - t0:.0f}s]")

    print()
    print("=" * 74)
    print("T2  sign of dQ*/dlogC around saturation")
    print("=" * 74)
    pts = cache[0.125]
    for i in range(1, len(pts)):
        lc, q = pts[i]
        d = (q - pts[i - 1][1]) / (lc - pts[i - 1][0])
        if 20.8 <= lc <= 21.9:
            print(f"  log10C={lc:6.3f}  Q*={q:.6f}  dQ*/dlogC={d:+.6f}")

    print()
    print("=" * 74)
    print("T3  does THIS law imply Chinchilla's 20 tokens/param?")
    print("=" * 74)
    # min A N^-al + B D^-be  s.t. 6 N D = C   (pure training cost, N,D in 1e9)
    def opt_nd(C):
        c18 = C / 1e18
        f = lambda lnN: AL * A * np.exp(-AL * lnN) - BE * B * np.exp(-BE * (np.log(c18 / 6.0) - lnN))
        lnN = brentq(f, np.log(1e-6), np.log(1e6))
        return np.exp(lnN), c18 / 6.0 / np.exp(lnN)

    print("     C(FLOPs)      N*(B)         D*(B)      D/N (tokens per param)")
    for e in (19, 20, 21, 22, 23, 24):
        n, d = opt_nd(10.0 ** e)
        print(f"     1e{e}      {n:10.4f}   {d:11.2f}   {d / n:9.2f}")
    print(f"  Chinchilla folklore ratio: ~20.  drift exponent d(log D/N)/d(log C) = "
          f"{(AL - BE) / (AL + BE):.6f}")

    print()
    print("=" * 74)
    print("T4  how much of M1o-vs-M0o gap is the quality channel, and how much is")
    print("    a baseline handicapped by forcing D/N = 20?   (C=1e22, L_ctx=2048)")
    print("=" * 74)
    C, L = 1e22, 2048

    def best_at_ratio(ratio, Q):
        """固定 D/N = ratio 与 Q,只缩放规模至用尽预算。"""
        f = lambda lnN: cost(np.exp(lnN), ratio * np.exp(lnN), Q, "exponential", L) - C
        lnN = brentq(f, np.log(1e-6), np.log(1e6))
        n = np.exp(lnN)
        return loss(n, ratio * n, Q), n, ratio * n

    l_free, n_free, d_free = None, None, None
    s = solve(C)
    l_free, n_free, d_free = loss(s["N_B"], s["D_B"], s["Q"]), s["N_B"], s["D_B"]
    print(f"  M1o  (N,D,Q all free)          loss={l_free:.6f}  "
          f"N={n_free:.3f}B D={d_free:.1f}B Q={s['Q']:.4f}  D/N={d_free / n_free:.2f}")

    l20, n20, d20 = best_at_ratio(20.0, Q0)
    print(f"  M0o  as carded: D/N=20, Q=Q0    loss={l20:.6f}  "
          f"N={n20:.3f}B D={d20:.1f}B Q={Q0:.4f}  D/N=20.00")

    # 本律自身的无质量投入最优（Q=Q0 下自由 N:D）
    def free_noQ():
        bnds = [(-4, 5), (-4, 6)]
        g = lambda x: loss(10 ** x[0], 10 ** x[1], Q0)
        c = lambda x: (C - cost(10 ** x[0], 10 ** x[1], Q0, "exponential", L)) / C
        rng = np.random.default_rng(SEED)
        base = 0.5 * np.log10(C / 6.0 / 1e18)
        best = None
        for _ in range(8):
            x0 = [base + rng.uniform(-1, 1), base + rng.uniform(-1, 1)]
            r = minimize(g, x0, method="SLSQP", bounds=bnds,
                         constraints=[{"type": "ineq", "fun": c}],
                         options={"maxiter": 500, "ftol": 1e-12})
            if r.success and c(r.x) >= -1e-6 and (best is None or r.fun < best.fun):
                best = r
        return best.fun, 10 ** best.x[0], 10 ** best.x[1]

    lnq, nnq, dnq = free_noQ()
    print(f"  M0o' fair: D/N free, Q=Q0       loss={lnq:.6f}  "
          f"N={nnq:.3f}B D={dnq:.1f}B Q={Q0:.4f}  D/N={dnq / nnq:.2f}")
    print()
    print(f"  gap M1o vs M0o(as carded)  = {l20 - l_free:.6f}   <- what the paper would report")
    print(f"  gap M1o vs M0o'(fair)      = {lnq - l_free:.6f}   <-真正归因于质量通道")
    print(f"  of which ratio handicap    = {l20 - lnq:.6f}   "
          f"({(l20 - lnq) / (l20 - l_free) * 100:.1f}% of the reported gap)")
    print(f"\n  total {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()

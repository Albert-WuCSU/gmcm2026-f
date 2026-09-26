"""Q3 评审用独立核验。非交付物。

关键:**不复用** q3_common 的 R1/R2/multipliers 来验证它们自己(那是自证)。
改用对拉格朗日函数直接做有限差分,独立重建 KKT 条件。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code/Q3"))
from q3_common import G_SPECS, Model, load_law_params, g_value   # noqa: E402

law = load_law_params()
FAILS = []


def check(name, ok, detail=""):
    print(f"  [{'OK ' if ok else 'FAIL'}] {name}  {detail}")
    if not ok:
        FAILS.append(name)


print("=" * 78)
print("C1  KKT 驻点条件:对拉格朗日函数做中心差分,独立核验(不用 R1/R2)")
print("=" * 78)
for C in (1e19, 1e22, 1e24):
    for form in G_SPECS:
        m = Model(law, form=form)
        best, _ = m.solve_kkt(C)
        if best is None:
            check(f"C={C:.0e} {form} 有解", False)
            continue
        N, D, Q = best["N_B"], best["D_B"], best["Q"]
        lam = best["multipliers"]["lambda"]

        def lagrangian(n, d, q):
            return m.loss(n, d, q) + lam * (m.cost(n, d, q) - C)

        h = 1e-7
        dN = (lagrangian(N * (1 + h), D, Q) - lagrangian(N * (1 - h), D, Q)) / (2 * h * N)
        dD = (lagrangian(N, D * (1 + h), Q) - lagrangian(N, D * (1 - h), Q)) / (2 * h * D)
        # 相对化:用各自项的量级做分母
        sN = abs(m.al * m.A * N ** (-m.al - 1))
        sD = abs(m.be * m.B * (D * Q ** m.ga) ** (-m.be) / D)
        r_dN, r_dD = abs(dN) / sN, abs(dD) / sD
        ok = r_dN < 1e-5 and r_dD < 1e-5
        check(f"C={C:.0e} {form:<15} dL/dN={r_dN:.2e} dL/dD={r_dD:.2e} (branch={best['branch']})", ok)

        # Q 方向:内点段须 dL/dQ=0;边界段须 dL/dQ <= 0(继续增 Q 会降 Loss 但越界)
        if m.Q0 + 1e-6 < Q < 1.0 - 1e-6:
            dQ = (lagrangian(N, D, Q + h) - lagrangian(N, D, Q - h)) / (2 * h)
            sQ = abs(m.be * m.ga * m.B * (D * Q ** m.ga) ** (-m.be) / Q)
            check(f"   内点 dL/dQ={abs(dQ)/sQ:.2e}", abs(dQ) / sQ < 1e-4)
        elif Q >= 1.0 - 1e-6:
            dQ = (lagrangian(N, D, 1.0) - lagrangian(N, D, 1.0 - h)) / h
            check(f"   边界 dL/dQ={dQ:+.4e} 须 <= 0(乘子 mu >= 0 的等价陈述)", dQ <= 1e-9)

print()
print("=" * 78)
print("C2  最优性:在最优点邻域随机采样可行点,不得有更优者")
print("=" * 78)
rng = np.random.default_rng(12345)
for C in (1e19, 1e22, 1e24):
    m = Model(law)
    best, _ = m.solve_kkt(C)
    N, D, Q, L = best["N_B"], best["D_B"], best["Q"], best["loss"]
    better = 0
    for _ in range(4000):
        n = N * 10 ** rng.uniform(-0.6, 0.6)
        q = min(max(Q + rng.uniform(-0.3, 0.3), m.Q0), 1.0)
        d = m.D_from_budget(n, q, C)       # 用尽预算(最优必在边界)
        if d is None or d <= 0:
            continue
        if m.loss(n, d, q) < L - 1e-12:
            better += 1
    check(f"C={C:.0e} 邻域 4000 采样中更优者={better}", better == 0,
          f"L*={L:.8f}")

print()
print("=" * 78)
print("C3  分支枚举完备性:三分支之外是否存在更优可行解(差分进化独立求解)")
print("=" * 78)
from scipy.optimize import differential_evolution   # noqa: E402

for C in (1e19, 1e22, 1e24):
    m = Model(law)
    best, _ = m.solve_kkt(C)

    def obj(x):
        n, q = 10 ** x[0], x[1]
        d = m.D_from_budget(n, q, C)
        if d is None or d <= 0:
            return 1e6
        return m.loss(n, d, q)

    r = differential_evolution(obj, [(-4, 5), (m.Q0, 1.0)], seed=7, tol=1e-12,
                              maxiter=600, polish=True)
    gap = (best["loss"] - r.fun) / abs(r.fun)
    check(f"C={C:.0e} DE_loss={r.fun:.8f} KKT_loss={best['loss']:.8f} rel_gap={gap:+.2e}",
          gap < 1e-6, "(> 1e-6 即 M2o 触发条件 1)")

print()
print("=" * 78)
print("C4  单位与成本式:C_train/C_attn 比值须恰为 eta*L_ctx/6,C_Q 只随 D 标度")
print("=" * 78)
for L in (2048, 131072):
    m = Model(law, L_ctx=L)
    p = m.cost_parts(3.0, 100.0, 0.8)
    ratio = p["C_attn"] / p["C_train"]
    check(f"L_ctx={L:<7} C_attn/C_train={ratio:.8f} 理论={2e-4*L/6:.8f}",
          abs(ratio - 2e-4 * L / 6) < 1e-12)
# C_Q 对 N 不敏感
m = Model(law)
a = m.cost_parts(1.0, 50.0, 0.8)["C_Q"]
b = m.cost_parts(7.0, 50.0, 0.8)["C_Q"]
check(f"C_Q 不随 N 变:{a:.6e} vs {b:.6e}", abs(a - b) < 1e-6 * max(a, 1))
# Q=Q0 时 C_Q=0
check("Q=Q0 时 C_Q=0", m.cost_parts(1.0, 50.0, m.Q0)["C_Q"] == 0.0)
# g 在 Q0 处连续且 dg 非负
for form in G_SPECS:
    mm = Model(law, form=form)
    vals = [mm.dg(q) for q in np.linspace(mm.Q0, 1.0, 50)]
    check(f"dg({form}) 单调非降且 >= 0", all(v >= -1e-9 for v in vals)
          and all(vals[i] <= vals[i + 1] + 1e-9 for i in range(len(vals) - 1)))

print()
print("=" * 78)
print("C5  law 参数取的是 B1 侧(真实数据),不是 B7 半合成")
print("=" * 78)
import json                                          # noqa: E402
raw = json.load(open(Path(__file__).resolve().parents[1]
                     / "results/Q2/experiments/round1/metrics/q2_M1s.json",
                     encoding="utf-8"))["stage3_joint_wls"]["M1s_params"]
check(f"E={law['E']:.8f} == E_B1", abs(law["E"] - raw["E_B1"]) < 1e-15)
check(f"A={law['A']:.8f} == A_B1", abs(law["A"] - raw["A_B1"]) < 1e-15)
check(f"alpha={law['alpha']:.8f} == alpha_B1", abs(law["alpha"] - raw["alpha_B1"]) < 1e-15)
check(f"B={law['B']:.8f} == B_B1", abs(law["B"] - raw["B_B1"]) < 1e-15)
check("未误取 B7 侧 E", abs(law["E"] - raw["E_B7"]) > 1e-3)

print()
print("=" * 78)
print("C6  D 定义的扫描范围(18-22)截断是否影响 verdict:延到 25 再判")
print("=" * 78)
from q3_optimize_main import D_THRESHOLD, sweep      # noqa: E402

m = Model(law)
for st in (0.5, 0.25, 0.125):
    pts = sweep(m, st, 18.0, 25.0)
    q = np.array([p["Q"] for p in pts])
    dq = np.abs(np.diff(q))
    v_full = "TRANSITION_EXISTS" if dq.max() > D_THRESHOLD else "NO_TRANSITION"
    pts2 = sweep(m, st, 18.0, 22.0)
    q2 = np.array([p["Q"] for p in pts2])
    dq2 = np.abs(np.diff(q2))
    v_trunc = "TRANSITION_EXISTS" if dq2.max() > D_THRESHOLD else "NO_TRANSITION"
    check(f"step={st:<6} 18-25:{dq.max():.6f}/{v_full}  18-22:{dq2.max():.6f}/{v_trunc}",
          v_full == v_trunc, "(verdict 一致则截断无影响)")

print()
print("=" * 78)
print(f"结论:{'全部通过' if not FAILS else f'{len(FAILS)} 项 FAIL: ' + '; '.join(FAILS)}")
print("=" * 78)
sys.exit(1 if FAILS else 0)

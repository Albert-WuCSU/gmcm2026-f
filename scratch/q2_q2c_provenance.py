"""Q2c 各输出的数据来源归属，以及 B1 侧 vs B7 侧参数给出的量级差。

问题：形状参数来源专属（P8 FAIL）后，Q2c 该在哪一侧参数上算？
"""
from __future__ import annotations

import numpy as np

# P8 与 G3 实测值
B1 = {"E": 1.689798, "A": 0.353980, "alpha": 0.339977, "B": 1.240306}
B7 = {"E": 1.654232, "A": 0.529124, "alpha": 0.283218, "B": 1.053871}
BETA = 0.279878          # 共享，实质由 B1 钉住（B7 权重份额 1.56e-6）
GAMMA = 0.965913         # 仅由 B7 约束（B1 上 Q=1，无信息）

N_ref, D_ref, Q_ref = 1.0, 150.0, 0.5


def marginals(p, beta, gamma, N, D, Q):
    Deff = D * Q ** gamma
    dL_dN = -p["A"] * p["alpha"] * N ** (-p["alpha"] - 1)
    dL_dD = -p["B"] * beta * Deff ** (-beta - 1) * Q ** gamma
    dL_dQ = -p["B"] * beta * gamma * Deff ** (-beta - 1) * D * Q ** (gamma - 1)
    dN_dQ = -dL_dQ / dL_dN
    # Q+0.1 等价 N 增量（沿等 Loss 面数值积分）
    qs = np.linspace(Q, Q + 0.1, 256)
    Ns = [N]
    for i in range(1, len(qs)):
        Nc, Qc = Ns[-1], qs[i - 1]
        d1 = -p["A"] * p["alpha"] * Nc ** (-p["alpha"] - 1)
        d2 = (-p["B"] * beta * gamma * (D * Qc ** gamma) ** (-beta - 1) * D * Qc ** (gamma - 1))
        Ns.append(Nc + (-d2 / d1) * (qs[i] - qs[i - 1]))
    return {"dL_dN": dL_dN, "dL_dD": dL_dD, "dL_dQ": dL_dQ,
            "elast_N": dL_dN * N, "elast_D": dL_dD * D, "elast_Q": dL_dQ * Q,
            "ratio_Q_over_D": (dL_dQ * Q) / (dL_dD * D),
            "dN_dQ": dN_dQ, "dN_for_Q_plus_0.1": Ns[-1] - N}


m_b1 = marginals(B1, BETA, GAMMA, N_ref, D_ref, Q_ref)
m_b7 = marginals(B7, BETA, GAMMA, N_ref, D_ref, Q_ref)

print(f"参照点 N={N_ref}B D={D_ref}B Q={Q_ref}\n")
print(f"{'量':<22} {'B1侧参数(真实)':>18} {'B7侧参数(半合成)':>20} {'相对差':>10}")
for k in ("dL_dN", "dL_dD", "dL_dQ", "elast_N", "elast_D", "elast_Q",
          "ratio_Q_over_D", "dN_dQ", "dN_for_Q_plus_0.1"):
    a, b = m_b1[k], m_b7[k]
    rel = abs(a - b) / max(abs(a), 1e-30)
    print(f"{k:<22} {a:>18.6f} {b:>20.6f} {rel*100:>9.1f}%")

print("\n--- 各参数的数据来源 ---")
print("beta   : B1 真实（B7 权重份额 1.56e-6，实质纯 B1）")
print("gamma  : B7 半合成（B1 上 Q=1，对 gamma 零信息）")
print("A/alpha/B (B1 侧): B1 真实，1176 行、8 个 N、D 跨 0.1~299.9B")
print("A/alpha/B (B7 侧): B7 半合成，450 行、9 个 N、D 仅 5 个取值")

print("\n--- 结论 ---")
print("dL/dN、dL/dD、elast_N、elast_D 在 B1 侧可由真实数据支撑；用 B7 侧参数算是自伤")
print("dL/dQ、elast_Q、ratio_Q_over_D、dN_dQ 含 gamma ⇒ 不可避免半合成")
print(f"ratio_Q_over_D 两侧都等于 gamma={GAMMA:.6f}（P4：该比值恒为 gamma，与形状参数无关）")

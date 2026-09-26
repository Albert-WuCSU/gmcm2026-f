"""支撑 AI 对裁定 4/5/6 意见的两个数。非探针、非交付物，输出只写 scratch。

数 1：假设(b)「A 侧与 B 侧在 1B 参照点上 dL/dp_i 相等」下，kappa 的取值与隐含边际效用量级。
数 2：裁定3=B 的 WLS 下，B7 相对 B1 的权重份额（按残差法 sigma）。
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
B1 = ROOT / "workspace/data_raw/real_attachments/B_scaling_laws/pythia_training_log_existing.csv"
B7 = ROOT / "workspace/data_raw/real_attachments/B_scaling_laws/supplementary_NQ_experiment_expanded.csv"
Q1COEF = ROOT / "results/Q1/experiments/round1/tables/q1c_coefficients.csv"
PROBE = ROOT / "workspace/data/q2_probe_g3_identifiability.json"

# B1 拟合参数取自已落盘探针（P1 的 B1 各自拟合）
pr = json.loads((ROOT / "workspace/data/q2_probe_scaling.json").read_text(encoding="utf-8"))
b1p = pr["probes"]["P1_cross_source_shared_E"]["per_source"]["B1"]
E, A, alpha, B, beta = b1p["E"], b1p["A"], b1p["alpha"], b1p["B"], b1p["beta"]

rows = list(csv.DictReader(B1.open(encoding="utf-8-sig")))
N = np.array([float(r["N_params_B"]) for r in rows])
D = np.array([float(r["D_tokens_B"]) for r in rows])
L = np.array([float(r["val_loss"]) for r in rows])

# 1B 参照点：B1 中 N 最接近 1.0B 的那个 run
target = N[np.argmin(np.abs(N - 1.0))]
m = N == target
print(f"1B 参照 run: N={target}B, 行数={m.sum()}, D 范围={D[m].min():.1f}~{D[m].max():.1f}B")

# gap 项 G = B*D^-beta  （= L - E - A*N^-alpha 的模型值）
G = B * D[m] ** (-beta)
print(f"gap 项 G = B*D^-beta 范围: {G.min():.4f} ~ {G.max():.4f}")

# 假设(b): dL_A/dp_i = w_i-wbar  等于  dL_B/dp_i = -beta*kappa*(w_i-wbar)*G
#   => kappa = -1/(beta*G)
kappa = -1.0 / (beta * G)
print(f"\n【数 1】假设(b) 下 kappa = -1/(beta*G): {kappa.min():.4f} ~ {kappa.max():.4f}")
print(f"        取 D 最大（收敛端）处: kappa = {-1.0/(beta*G[np.argmax(D[m])]):.4f}")

coef = {r["feature"]: float(r["coef"]) for r in
        csv.DictReader(Q1COEF.open(encoding="utf-8-sig")) if r["method"] == "M0c"}
pcols = [c for c in coef]
w = np.array([coef[c] for c in pcols])
w_c = w - w.mean()
k_conv = -1.0 / (beta * G[np.argmax(D[m])])
b_vec = k_conv * w_c
print(f"        => b 范围: {b_vec.min():.4f} ~ {b_vec.max():.4f}")

# 1pp 配比从最低 w 域移到最高 w 域，隐含 dL
i_hi, i_lo = int(np.argmax(w_c)), int(np.argmin(w_c))
dL_1pp = -beta * (b_vec[i_hi] - b_vec[i_lo]) * 0.01 * G[np.argmax(D[m])]
print(f"        1pp 从 {pcols[i_lo].split('pile_')[1]} 移到 {pcols[i_hi].split('pile_')[1]}: dL = {dL_1pp:+.6f}")
print(f"        对比 B1 的 val_loss 跨度 {L.min():.3f}~{L.max():.3f}，占比 {abs(dL_1pp)/(L.max()-L.min())*100:.4f}%")

# 【数 2】残差法 sigma 下 B7 的权重份额
b7 = list(csv.DictReader(B7.open(encoding="utf-8-sig")))
n_b7 = len(b7)
sigma_b1 = b1p["rmse"]
sigma_b7 = pr["probes"]["P3_Q_entry_additive_vs_multiplicative"]["multiplicative_D_eff"]["rmse"]
wt_ratio = (sigma_b1 / sigma_b7) ** 2
share = n_b7 * wt_ratio / (len(rows) + n_b7 * wt_ratio)
print(f"\n【数 2】残差法 sigma: sigma_B1={sigma_b1:.6e}, sigma_B7~{sigma_b7:.6f}")
print(f"        单点权重比 B7/B1 = (sigma_B1/sigma_B7)^2 = {wt_ratio:.3e}")
print(f"        B7({n_b7} 点) 在 B1({len(rows)} 点)+B7 联合拟合中的总权重份额 = {share:.3e}")
print(f"        => 共享参数几乎纯由 B1 决定；gamma 几乎纯由 B7 内部结构决定")

# P5 锚定法对比
sigma_p5 = 0.6293200406951934
wt_ratio2 = (sigma_b1 / sigma_p5) ** 2
share2 = n_b7 * wt_ratio2 / (len(rows) + n_b7 * wt_ratio2)
print(f"        若改用 P5 锚定 sigma={sigma_p5:.4f}: 份额 = {share2:.3e}（更小，同量级结论不变）")

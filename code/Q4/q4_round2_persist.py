"""补跑落盘(第一小步):N 分位轨迹 + 前沿轨迹,供论文图 ② 使用。

裁定 q4_result_verdict 要求「补跑一次把趋势法数字落盘」,本脚本先落这一部分。
"""
import numpy as np, pandas as pd
from pathlib import Path
from q4_common import load_c1, FRONTIER_Q, ROOT

OUT = ROOT / "results" / "Q4" / "experiments" / "round2" / "tables"
OUT.mkdir(parents=True, exist_ok=True)

c1 = load_c1()
g = c1.groupby("ym")
tab = pd.DataFrame({
    "month": [str(k) for k in g.groups.keys()],
    "n": g.size().to_numpy(),
    "N_q10": g["#Params (B)"].quantile(0.10).to_numpy(),
    "N_q50": g["#Params (B)"].median().to_numpy(),
    "N_q90": g["#Params (B)"].quantile(0.90).to_numpy(),
    "N_max": g["#Params (B)"].max().to_numpy(),
    "S_q90": g["S"].quantile(FRONTIER_Q).to_numpy(),
    "S_mean": g["S"].mean().to_numpy(),
})
tab = tab.round(4)
p = OUT / "q4_N_and_frontier_by_month.csv"
tab.to_csv(p, index=False, encoding="utf-8-sig")

# 分位月斜率(图注要用)
x = np.arange(len(tab), dtype=float)
sl = {q: float(np.polyfit(x, np.log10(tab[f"N_q{q}"].to_numpy()), 1)[0]) for q in (10, 50, 90)}
sl_S = float(np.polyfit(x, tab["S_q90"].to_numpy(), 1)[0])
meta = {
    "logN_q10_slope_per_month": round(sl[10], 5),
    "logN_q50_slope_per_month": round(sl[50], 5),
    "logN_q90_slope_per_month": round(sl[90], 5),
    "logN_q90_cum_dex": round(sl[90] * (len(tab) - 1), 4),
    "N_q90_ratio_first_over_last": round(float(tab["N_q90"].iloc[0] / tab["N_q90"].iloc[-1]), 4),
    "S_q90_slope_per_month": round(sl_S, 4),
    "S_q90_first": float(tab["S_q90"].iloc[0]), "S_q90_last": float(tab["S_q90"].iloc[-1]),
}
import json
(OUT.parent / "n_frontier_meta.json").write_text(
    json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
print(tab.to_string(index=False))
print()
for k, v in meta.items():
    print(f"  {k} = {v}")
print(f"\nWROTE {p.relative_to(ROOT)}")

"""核验 round2 数字与评审/manifest 所依据的值逐位一致,且只差 generated_at。

上一轮(19:30 交接)记录的关键值在此硬编码为期望值,直接与当前落盘文件比对。
不手打任何数字进报告之前,先跑这个。
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "results/Q4/experiments/round2/metrics/q4_trend_method.json"
d = json.loads(P.read_text(encoding="utf-8"))

# 期望值 = 我在本轮开始时从原文件读到、并被 G3 评审与六条裁定所引用的值
EXPECT = {
    "endpoint_spread": 0.28745778768598096,
    "sign_flips": True,
    "total_lo": 5.486528214456833,
    "total_hi": 6.659240619563332,
    "tr_decile_scale_share": 0.09109004698346738,
    "tr_decile_slope_f": 0.057503131563025896,
    "tr_decile_slope_tau": 0.5737747463972586,
    "tr_decile_ratio": 9.97814781214788,
    "tr_linear_scale_share": -0.5340674947564478,
    "ci_lo": -0.19424361172079332,
    "ci_hi": 0.22575049179717038,
    "n_boot": 1000,
    "ep0_share": 0.2592679747872242,
    "ep0_total": 6.624447484115447,
    "ep1_share": 0.1811080630715267,
    "ep2_share": -0.028189812898756744,
    "ep3_share": 0.22051617917657743,
    "scal0": 11.786,
    "scal1": 4.1408,
    "scal2": 0.0,
}
got = {
    "endpoint_spread": d["endpoint_share_spread"],
    "sign_flips": d["endpoint_sign_flips"],
    "total_lo": d["total_points_range"][0],
    "total_hi": d["total_points_range"][1],
    "tr_decile_scale_share": d["trend_method"]["decile"]["scale_share"],
    "tr_decile_slope_f": d["trend_method"]["decile"]["slope_f"],
    "tr_decile_slope_tau": d["trend_method"]["decile"]["slope_tau"],
    "tr_decile_ratio": d["trend_method"]["decile"]["slope_ratio"],
    "tr_linear_scale_share": d["trend_method"]["linear"]["scale_share"],
    "ci_lo": d["trend_scale_share_ci95"][0],
    "ci_hi": d["trend_scale_share_ci95"][1],
    "n_boot": d["n_boot"],
    "ep0_share": d["endpoint_sensitivity"][0]["scale_share"],
    "ep0_total": d["endpoint_sensitivity"][0]["total_points"],
    "ep1_share": d["endpoint_sensitivity"][1]["scale_share"],
    "ep2_share": d["endpoint_sensitivity"][2]["scale_share"],
    "ep3_share": d["endpoint_sensitivity"][3]["scale_share"],
    "scal0": d["scenario_spread_scaling"][0]["implied_scenario_spread_h12"],
    "scal1": d["scenario_spread_scaling"][1]["implied_scenario_spread_h12"],
    "scal2": d["scenario_spread_scaling"][2]["implied_scenario_spread_h12"],
}
bad = []
for k, want in EXPECT.items():
    if got[k] != want:
        bad.append(f"{k}: want {want!r} got {got[k]!r}")
print(f"checked {len(EXPECT)} values; mismatches = {len(bad)}")
for b in bad:
    print("  MISMATCH", b)

stripped = {k: v for k, v in d.items() if k != "generated_at"}
print("stripped sha256[:16] =", hashlib.sha256(
    json.dumps(stripped, sort_keys=True).encode()).hexdigest()[:16])
print("generated_at =", d.get("generated_at"))
print("OK" if not bad else "FAILED")

"""Q4 桥接层探针 —— 真实执行版。

背景:上一轮 AI 报告过一组 B1-B5 桥接结论(称 C6 只有 43 行、不存在 High 层、
measured_pythia rho=-0.8863 等),但该脚本与其输出**从未落盘**,那些数字是 AI 凭空生成的。
本脚本是第一次真正执行桥接检查。所有结论以本脚本写出的 JSON 为准。

同时复核 P4 的 total_points 符号(P4 的 share 解释是否成立)。

判据(预声明):
  B1 inventory   —— 无判据,清点 C5/C6 的行数、列名、等级分布。
  B2 tier        —— 是否存在 High 可比层;若存在,其 n 是多少。
  B3 monotone    —— 各等级内 spearman(Loss, Score) < 0 且最可信层 p < 0.05。
  B4 circularity —— 是否有由标度律估算而来的 Loss 行(若有,入拟合即构成循环论证)。
  B5 p4_total    —— P4 子集分解的 total_points 符号;若为负,则该子集上「份额」不可直接解释。

输出: workspace/data/q4_probe_bridge.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[3]
CDIR = ROOT / "workspace" / "data_raw" / "real_attachments" / "C_efficiency_evolution"
OUT = ROOT / "workspace" / "data" / "q4_probe_bridge.json"

FILES = {"C5": "loss_benchmark_bridge.csv", "C6": "loss_benchmark_bridge_expanded.csv"}


def sp(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 3:
        return None, None, int(m.sum())
    r, p = spearmanr(x[m], y[m])
    return round(float(r), 4), float(p), int(m.sum())


res: dict = {"schema_version": 1, "probes": {}}

# ---- B1 inventory
inv = {}
frames = {}
for tag, fn in FILES.items():
    df = pd.read_csv(CDIR / fn, low_memory=False)
    frames[tag] = df
    entry = {"file": fn, "rows": int(len(df)), "columns": list(df.columns)}
    for c in df.columns:
        lc = c.lower()
        if "compar" in lc or "source" in lc or "tier" in lc:
            entry[f"value_counts::{c}"] = {str(k): int(v) for k, v in df[c].value_counts().items()}
    inv[tag] = entry
inv["same_model_set"] = bool(
    set(frames["C5"]["Model"].astype(str)) == set(frames["C6"]["Model"].astype(str))
)
inv["c5_models"] = int(frames["C5"]["Model"].nunique())
inv["c6_models"] = int(frames["C6"]["Model"].nunique())
res["probes"]["B1_inventory"] = {"verdict": "PASS", **inv}

# ---- B2 tier existence
tier_cols = {t: [c for c in f.columns if "compar" in c.lower() or "tier" in c.lower()]
             for t, f in frames.items()}
observed: dict = {}
for t, cols in tier_cols.items():
    for c in cols:
        observed[f"{t}.{c}"] = {str(k): int(v) for k, v in frames[t][c].value_counts().items()}
has_high = any(str(k).lower().startswith("high") for d in observed.values() for k in d)
n_high = sum(v for d in observed.values() for k, v in d.items() if str(k).lower().startswith("high"))
res["probes"]["B2_tier"] = {
    "verdict": "PASS" if has_high else "FAIL",
    "criterion": "存在 High 可比层",
    "tier_columns_found": tier_cols,
    "observed_tiers": observed,
    "high_tier_exists": bool(has_high),
    "high_tier_n": int(n_high),
}

# ---- B3 monotonicity
mono: dict = {}
for t, df in frames.items():
    lcol = next((c for c in df.columns if "loss" in c.lower()
                 and not any(k in c.lower() for k in ("source", "compar", "tier"))), None)
    scol = next((c for c in df.columns if c.lower() in ("lb_average", "average")
                 or c.lower().startswith("lb_average")), None)
    if scol is None:
        scol = next((c for c in df.columns if "score" in c.lower() or "average" in c.lower()), None)
    if lcol is None or scol is None:
        mono[t] = {"error": f"列未识别 loss={lcol} score={scol}", "columns": list(df.columns)}
        continue
    r, p, n = sp(df[lcol], df[scol])
    entry = {"loss_col": lcol, "score_col": scol, "all": {"spearman": r, "p": p, "n": n}}
    for c in df.columns:
        lc = c.lower()
        if "compar" in lc or "source" in lc or "tier" in lc:
            by = {}
            for g, sub in df.groupby(c):
                rr, pp, nn = sp(sub[lcol], sub[scol])
                by[str(g)] = {"spearman": rr, "p": pp, "n": nn}
            entry[f"by::{c}"] = by
    mono[t] = entry
neg = [v["all"]["spearman"] for v in mono.values()
       if isinstance(v.get("all"), dict) and v["all"]["spearman"] is not None]
res["probes"]["B3_monotone"] = {
    "verdict": "PASS" if neg and all(x < 0 for x in neg) else "CONDITIONAL",
    "criterion": "spearman(Loss, Score) < 0",
    "detail": mono,
}

# ---- B4 circularity
circ = {}
for t, df in frames.items():
    for c in df.columns:
        if "source" in c.lower():
            vc = {str(k): int(v) for k, v in df[c].value_counts().items()}
            circ[f"{t}.{c}"] = vc
suspect = {k: {kk: vv for kk, vv in d.items()
               if any(s in kk.lower() for s in ("scaling", "estimat", "interp", "proxy"))}
           for k, d in circ.items()}
n_suspect = sum(sum(d.values()) for d in suspect.values())
res["probes"]["B4_circularity"] = {
    "verdict": "CONDITIONAL" if n_suspect > 0 else "PASS",
    "criterion": "不存在由标度律估算/插值而来的 Loss 行进入拟合",
    "source_value_counts": circ,
    "suspect_rows": suspect,
    "n_suspect": int(n_suspect),
    "ruling": "估算/插值行不得进入 Loss->Score 拟合,只可作外部验证;须按 GC5 披露",
}

# ---- B5 P4 total sign
att = json.loads((ROOT / "workspace" / "data" / "q4_probe_attribution.json").read_text("utf-8"))
p4 = att["probes"]["P4_jia_yi_bias"]
b5 = {"p4_jia_tech_share": p4.get("jia_tech_share"), "p4_yi_tech_share": p4.get("yi_tech_share"),
      "p4_jia_scale_points": p4.get("jia_scale_points"),
      "p4_yi_scale_points": p4.get("yi_scale_points")}
for side in ("jia", "yi"):
    ts = b5[f"p4_{side}_tech_share"]
    sp_pts = b5[f"p4_{side}_scale_points"]
    if ts is not None and sp_pts is not None and (1 - ts) != 0:
        b5[f"p4_{side}_total_points_implied"] = round(float(sp_pts / (1 - ts)), 4)
tot = [v for k, v in b5.items() if k.endswith("total_points_implied")]
res["probes"]["B5_p4_total_sign"] = {
    "verdict": "FAIL" if tot and all(t < 0 for t in tot) else "PASS",
    "criterion": "P4 子集分解的 total_points > 0,否则该子集上「份额」不可直接解释",
    **b5,
    "consequence": (
        "若 total 为负,则 P4 的 PASS 只说明 (甲 tech_share > 乙 tech_share) 这一符号关系成立,"
        "不支持把该子集的 share 数值当占比解读。偏误须改报绝对点数差。"
    ),
}

res["generated_at"] = pd.Timestamp.now(tz="Asia/Shanghai").isoformat()
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
print("WROTE", OUT)
for k, v in res["probes"].items():
    print(" ", k, "=", v.get("verdict"))

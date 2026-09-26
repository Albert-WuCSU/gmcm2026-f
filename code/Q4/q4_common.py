"""Q4 公共层:数据加载、分解核心、桥接。

已批准方法(methods/Q4/q4_decisions.jsonl = q4_fn_spec_and_method_choice = C_main_spec_A):
  M1a main             半参数归因 S = f(N) + tau_t + eps,f(N) 主口径十分位 dummy
  M0a usable_baseline  纯时间趋势外推(HD-2 声明)
  M2a conditional_fallback  改报绝对点数(休眠;触发条件见方法卡)

口径约束(来自已裁定的框定,不得在代码里自行放宽):
  - 规模通道主口径 = 仅 N(全样本);乙(N,D,compute)只在 66 子集上作偏误验证
  - 技术项只能表述为「非规模技术/数据工程综合进步」
  - 前沿 = 每月 Average 的 0.90 分位
  - 被判定视界 = 12 个月
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CDIR = ROOT / "workspace" / "data_raw" / "real_attachments" / "C_efficiency_evolution"
Q2_METRICS = ROOT / "results" / "Q2" / "experiments" / "round1" / "metrics" / "q2_M1s.json"

SEED = 20260925
B_BOOT = 2000
FRONTIER_Q = 0.90
HORIZON_MONTHS = 12

SIX_DIMS = ["IFEval", "BBH", "MATH Lvl 5", "GPQA", "MUSR", "MMLU-PRO"]


def norm_name(s: str) -> str:
    s = str(s).lower().split("/")[-1]
    if "_" in s:
        s = s.split("_", 1)[1]
    return re.sub(r"[^a-z0-9]", "", s)


def load_c1() -> pd.DataFrame:
    """C1 主表。返回含 date/ym/logN/S 的可用子集。"""
    df = pd.read_csv(CDIR / "leaderboard_cleaned.csv", low_memory=False)
    avg = [c for c in df.columns if c.startswith("Average")][0]
    df = df.rename(columns={avg: "Average"})
    df["date"] = pd.to_datetime(df["Submission Date"], errors="coerce")
    df = df.dropna(subset=["date", "Average", "#Params (B)"]).copy()
    df = df[df["#Params (B)"] > 0].copy()
    df["logN"] = np.log10(df["#Params (B)"].astype(float))
    df["ym"] = df["date"].dt.to_period("M")
    df["S"] = df["Average"].astype(float)
    df["type_group"] = np.where(
        df["Type"].astype(str).str.contains("pretrained", case=False, na=False),
        "pretrained", "chat_finetuned")
    return df


def load_c4_join(c1: pd.DataFrame) -> pd.DataFrame:
    """乙侧:C1 x C4 名称连接,取 Params+Compute+Date 齐全者,去重。"""
    c4 = pd.read_csv(CDIR / "epoch_all_ai_models.csv", low_memory=False)
    trio = c4[["Parameters", "Training compute (FLOP)", "Publication date"]].notna().all(axis=1)
    c4t = c4[trio].copy()
    c4t["k"] = c4t["Model"].map(norm_name)
    a = c1.copy()
    a["k"] = a["Model"].map(norm_name)
    a = a[a["k"].str.len() >= 4]
    j = a.merge(c4t[["k", "Parameters", "Training compute (FLOP)",
                     "Training dataset size (total)"]], on="k", how="inner")
    j = j.drop_duplicates("k").copy()
    # C4 的数值列在 CSV 里是字符串 dtype(含注记文本),必须先强制转数值再比较
    for col in ("Parameters", "Training compute (FLOP)", "Training dataset size (total)"):
        j[col] = pd.to_numeric(j[col], errors="coerce")
    j = j[j["Training compute (FLOP)"] > 0].copy()
    j["logC"] = np.log10(j["Training compute (FLOP)"])
    d_ok = j["Training dataset size (total)"] > 0
    j["logD"] = np.where(d_ok, np.log10(j["Training dataset size (total)"].where(d_ok, np.nan)),
                         np.nan)
    return j


def load_bridge() -> pd.DataFrame:
    """C6 桥接表(75 行,含 Loss_Comparability 与 Loss_Source)。"""
    df = pd.read_csv(CDIR / "loss_benchmark_bridge_expanded.csv", low_memory=False)
    df = df.dropna(subset=["Val_Loss", "LB_Average"]).copy()
    df["tier"] = np.where(
        df["Loss_Comparability"].astype(str).str.startswith("High"), "High", "Medium")
    return df


def load_q2_params() -> dict:
    """Q2 已过 G3 的标度律参数(B1 侧为主)。"""
    d = json.loads(Q2_METRICS.read_text(encoding="utf-8"))
    p = d["stage3_joint_wls"]["M1s_params"]
    return {"E": p["E_B1"], "A": p["A_B1"], "alpha": p["alpha_B1"],
            "B": p["B_B1"], "beta": p["beta"],
            "gamma": d["stage2_gamma_on_B7"]["gamma"],
            "source": str(Q2_METRICS.relative_to(ROOT)).replace("\\", "/")}


# --------------------------------------------------------------- 分解核心
def _dummies(keys: pd.Series) -> tuple[np.ndarray, list]:
    levels = sorted(keys.unique().tolist())
    rest = levels[1:]
    M = np.zeros((len(keys), len(rest)))
    arr = keys.to_numpy()
    for j, lv in enumerate(rest):
        M[:, j] = (arr == lv).astype(float)
    return M, rest


def decompose(df: pd.DataFrame, scale_cols: list[str], time_key: str,
              fn_spec: str = "decile", n_bins: int = 10) -> dict:
    """S = f(scale) + tau_t + eps 的加性分解。

    fn_spec='decile'  主口径:第一个 scale 列取十分位 dummy,其余列线性进入
    fn_spec='linear'  敏感性:全部 scale 列线性进入

    加性结构 ⇒ 两因子 Shapley 与本分解恒等,无交互项,份额和恒为 1。
    """
    d = df.copy()
    if fn_spec == "decile":
        d["_nb"] = pd.qcut(d[scale_cols[0]], n_bins, labels=False, duplicates="drop")
        Xs, _ = _dummies(d["_nb"])
        extra = [d[[c]].to_numpy(float) for c in scale_cols[1:]]
        Xs = np.hstack([Xs] + extra) if extra else Xs
    else:
        Xs = d[scale_cols].to_numpy(float)

    Xt, t_levels = _dummies(d[time_key])
    X = np.hstack([np.ones((len(d), 1)), Xs, Xt])
    y = d["S"].to_numpy(float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)

    n_s = Xs.shape[1]
    b_s, b_t = beta[1:1 + n_s], beta[1 + n_s:]
    periods = sorted(d[time_key].unique())
    first, last = periods[0], periods[-1]
    tau = dict(zip(t_levels, b_t))
    tau_first, tau_last = 0.0, float(tau.get(last, 0.0))

    d["_f"] = Xs @ b_s
    f_first = float(d.loc[d[time_key] == first, "_f"].mean())
    f_last = float(d.loc[d[time_key] == last, "_f"].mean())

    scale_pts, tech_pts = f_last - f_first, tau_last - tau_first
    total = scale_pts + tech_pts
    return {
        "fn_spec": fn_spec,
        "scale_points": scale_pts,
        "tech_points": tech_pts,
        "total_points": total,
        "scale_share": scale_pts / total if total != 0 else float("nan"),
        "tech_share": tech_pts / total if total != 0 else float("nan"),
        "share_interpretable": bool(total > 0),
        "first_period": str(first),
        "last_period": str(last),
        "n": int(len(d)),
        "tau_path": {str(k): round(float(v), 6) for k, v in tau.items()},
    }


def bootstrap_decompose(df: pd.DataFrame, scale_cols: list[str], time_key: str,
                        fn_spec: str, rng: np.random.Generator, b: int = B_BOOT) -> dict:
    """月内重抽模型的自助。返回份额与点数的 95% 区间。"""
    groups = [g.index.to_numpy() for _, g in df.groupby(time_key)]
    keep: dict[str, list] = {"scale_share": [], "tech_share": [],
                             "scale_points": [], "tech_points": []}
    for _ in range(b):
        idx = np.concatenate([rng.choice(g, size=len(g), replace=True) for g in groups])
        try:
            r = decompose(df.loc[idx], scale_cols, time_key, fn_spec)
        except Exception:
            continue
        if np.isfinite(r["scale_share"]):
            for k in keep:
                keep[k].append(r[k])
    out = {}
    for k, v in keep.items():
        a = np.asarray(v, float)
        out[f"{k}_ci95"] = [round(float(np.quantile(a, 0.025)), 4),
                           round(float(np.quantile(a, 0.975)), 4)] if a.size else None
    out["n_boot_effective"] = int(len(keep["scale_share"]))
    return out

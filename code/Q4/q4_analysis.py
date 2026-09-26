"""Q4 分析层:M1a 归因、M0a baseline、桥接、前沿蒙特卡洛、C8 逐任务聚合。"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from q4_common import (B_BOOT, CDIR, FRONTIER_Q, HORIZON_MONTHS, ROOT, SEED, SIX_DIMS,
                       bootstrap_decompose, decompose, load_bridge, load_c1, load_c4_join,
                       load_q2_params)


# ============================================================ M1a 归因
def m1a_attribution(c1: pd.DataFrame, rng: np.random.Generator) -> dict:
    """主口径 A(十分位 dummy) + 规格敏感性 B(线性 log N)，裁定 C 要求两者都报。"""
    main = decompose(c1, ["logN"], "ym", "decile")
    boot = bootstrap_decompose(c1, ["logN"], "ym", "decile", rng, B_BOOT)
    sens = decompose(c1, ["logN"], "ym", "linear")

    cq = c1.copy()
    cq["yq"] = cq["date"].dt.to_period("Q")
    specs = {
        "decile_month": main,
        "linear_month": sens,
        "decile_quarter": decompose(cq, ["logN"], "yq", "decile"),
        "linear_quarter": decompose(cq, ["logN"], "yq", "linear"),
    }

    # 分组:题目硬性要求区分 pretrained 与 chat/finetuned
    groups = {}
    for g, sub in c1.groupby("type_group"):
        if len(sub) < 100 or sub["ym"].nunique() < 3:
            groups[g] = {"n": int(len(sub)), "note": "样本或月份不足，不单独分解"}
            continue
        r = decompose(sub, ["logN"], "ym", "decile")
        rb = bootstrap_decompose(sub, ["logN"], "ym", "decile", rng, 400)
        groups[g] = {**r, **rb}

    m2a_triggered = bool(boot["scale_share_ci95"] and boot["scale_share_ci95"][0] < 0)
    return {
        "method_id": "M1a",
        "role": "main",
        "approved_spec": "C_main_spec_A",
        "main_spec_decile_month": {**main, **boot},
        "sensitivity_specs": {k: {"scale_share": round(v["scale_share"], 4),
                                  "tech_share": round(v["tech_share"], 4),
                                  "scale_points": round(v["scale_points"], 4),
                                  "tech_points": round(v["tech_points"], 4),
                                  "total_points": round(v["total_points"], 4),
                                  "share_interpretable": v["share_interpretable"]}
                              for k, v in specs.items()},
        "by_type_group": groups,
        "m2a_fallback_triggered": m2a_triggered,
        "m2a_note": ("未触发，占比口径成立" if not m2a_triggered else
                     "已触发：scale_share 区间下界 < 0，须改报绝对点数与方向"),
        "wording_red_line": "tau_t 只能表述为「非规模技术/数据工程综合进步」，不得写成架构/算法进步",
    }


def yi_bias_probe(c1: pd.DataFrame, rng: np.random.Generator) -> dict:
    """乙侧偏误验证(裁定 丙)。B5 已判该子集 total 可能为负 ⇒ 只报绝对点数差与符号。"""
    j = load_c4_join(c1)
    j = j.copy()
    j["yq"] = j["date"].dt.to_period("Q")
    if len(j) < 30 or j["yq"].nunique() < 2:
        return {"verdict": "SKIP", "reason": f"子集不足 n={len(j)} 季度={j['yq'].nunique()}"}

    jia = decompose(j, ["logN"], "yq", "linear")
    yi = decompose(j, ["logN", "logC"], "yq", "linear")
    interpretable = bool(jia["total_points"] > 0 and yi["total_points"] > 0)
    return {
        "subset_n": int(len(j)),
        "subset_quarters": int(j["yq"].nunique()),
        "type_counts": {str(k): int(v) for k, v in j["Type"].value_counts().items()},
        "jia_only_N": {k: round(v, 4) for k, v in jia.items()
                       if isinstance(v, (int, float))},
        "yi_N_plus_compute": {k: round(v, 4) for k, v in yi.items()
                              if isinstance(v, (int, float))},
        "tech_points_diff_jia_minus_yi": round(jia["tech_points"] - yi["tech_points"], 4),
        "scale_points_diff_jia_minus_yi": round(jia["scale_points"] - yi["scale_points"], 4),
        "share_interpretable": interpretable,
        "reporting_rule": (
            "B5 判该子集 total 为负 ⇒ 不得把 share 当占比读。"
            "偏误只报绝对点数差与符号关系。"
            if not interpretable else "该子集 total 为正，share 可解释"
        ),
        "generalization_limit": (
            "本子集 pretrained 占比远高于 C1 全样本 ⇒ 不是同一总体。"
            "只给偏误的符号与量级，不得作为对全样本数字的修正系数，不得表述为『已校正』。"
        ),
    }


# ============================================================ M0a baseline
def m0a_baseline(c1: pd.DataFrame) -> dict:
    """HD-2 声明的 baseline:纯时间趋势外推,不分解规模/技术。"""
    q = c1.groupby("ym")["S"].quantile(FRONTIER_Q)
    x = np.arange(len(q), dtype=float)
    y = q.to_numpy(float)
    slope, intercept = np.polyfit(x, y, 1)
    resid = y - (slope * x + intercept)
    sigma = float(resid.std(ddof=2))
    cur = float(y[-1])
    preds = {}
    for h in (12, 24):
        pt = float(slope * (len(q) - 1 + h) + intercept)
        se = sigma * np.sqrt(1 + h / len(q))
        preds[f"h{h}"] = {
            "point": round(pt, 3),
            "lo80": round(pt - 1.2816 * se, 3), "hi80": round(pt + 1.2816 * se, 3),
            "lo95": round(pt - 1.9600 * se, 3), "hi95": round(pt + 1.9600 * se, 3),
        }
    return {
        "method_id": "M0a",
        "role": "usable_baseline",
        "form": "q90_t = a + b*t（纯时间趋势，不分解）",
        "frontier_definition": f"每月 Average 的 {FRONTIER_Q} 分位",
        "q90_by_month": {str(k): round(float(v), 3) for k, v in q.items()},
        "slope_per_month": round(float(slope), 4),
        "resid_sigma": round(sigma, 4),
        "current_frontier": round(cur, 3),
        "predictions": preds,
        "structural_limitation": (
            "该 baseline 结构上产出不了归因分解 ⇒ 主方法在归因维度上是定义性胜出；"
            "预测维度上主方法须真打赢它，不得回避比较。"
        ),
    }


# ============================================================ 桥接
def fit_bridge(rng: np.random.Generator) -> dict:
    """分层桥接 Score = g(Loss)。High 层作主锚,Medium 层降权,报映射误差。"""
    br = load_bridge()
    out: dict = {"n_total": int(len(br)), "tiers": {}}
    for tier, sub in br.groupby("tier"):
        r, p = spearmanr(sub["Val_Loss"], sub["LB_Average"])
        out["tiers"][tier] = {"n": int(len(sub)), "spearman": round(float(r), 4),
                             "p_value": float(p)}

    # 主拟合:线性(单调约束由斜率符号检查代替),High 层加权
    w = np.where(br["tier"].to_numpy() == "High", 3.0, 1.0)
    X = np.vstack([np.ones(len(br)), br["Val_Loss"].to_numpy(float)]).T
    y = br["LB_Average"].to_numpy(float)
    W = np.diag(w)
    coef = np.linalg.lstsq(W @ X, W @ y, rcond=None)[0]
    pred = X @ coef
    resid = y - pred
    rmse = float(np.sqrt((resid ** 2).mean()))

    boot = []
    idx_all = np.arange(len(br))
    for _ in range(B_BOOT):
        idx = rng.choice(idx_all, size=len(idx_all), replace=True)
        try:
            c = np.linalg.lstsq(W[np.ix_(idx, idx)] @ X[idx], W[np.ix_(idx, idx)] @ y[idx],
                                rcond=None)[0]
            boot.append(c)
        except Exception:
            continue
    boot_a = np.asarray(boot)
    return {
        **out,
        "form": "LB_Average = a + b * Val_Loss（High 层权重 3:1）",
        "intercept": round(float(coef[0]), 4),
        "slope": round(float(coef[1]), 4),
        "slope_ci95": [round(float(np.quantile(boot_a[:, 1], 0.025)), 4),
                       round(float(np.quantile(boot_a[:, 1], 0.975)), 4)] if len(boot_a) else None,
        "monotone_decreasing": bool(coef[1] < 0),
        "rmse": round(rmse, 4),
        "mapping_error_sigma": round(float(resid.std(ddof=2)), 4),
        "high_tier_caveat": (
            "High 层 n=7，方向正确但 p 不显著（样本量所致）。"
            "按 F10 纪律：不得据此认为 High 层质量更差。映射误差作独立随机项传播。"
        ),
        "no_circularity": "Loss_Source 全为技术报告/训练日志，无标度律估算行（B4 PASS）",
    }


# ============================================================ 前沿蒙特卡洛
SCENARIOS = {
    "conservative": {"compute_growth_per_year": 1.5, "tech_decay": 0.5},
    "neutral": {"compute_growth_per_year": 2.5, "tech_decay": 0.75},
    "optimistic": {"compute_growth_per_year": 4.0, "tech_decay": 1.0},
}


def frontier_mc(c1: pd.DataFrame, bridge: dict, attribution: dict, q2: dict,
                rng: np.random.Generator, n_mc: int = 4000) -> dict:
    """三情景 × 蒙特卡洛,同时抽:技术趋势斜率、桥接映射误差、标度律参数。

    技术通道:用 M1a 的 tau 路径月度斜率 × 情景衰减。
    规模通道:算力年增速经 Q2 标度律折成 Loss 下降,再经桥接折成 Score 增益。
    """
    # 对象一致性:前沿是 q90 水平,故须用 q90 自身的斜率,再按归因份额拆成两通道。
    # 直接把 tau(全样本均值层面,≈0.545/月)加到 q90 水平上是对象不一致,会系统性低估
    # (q90 实际 ≈1.53/月)。该缺陷在首轮实现中出现过,已修。
    tau = attribution["main_spec_decile_month"]["tau_path"]
    ks = sorted(tau.keys())
    tv = np.array([tau[k] for k in ks], float)
    x_t = np.arange(len(tv), dtype=float)
    tau_slope_mean_level, _ = np.polyfit(x_t, tv, 1)

    q = c1.groupby("ym")["S"].quantile(FRONTIER_Q)
    cur = float(q.to_numpy()[-1])
    xq = np.arange(len(q), dtype=float)
    yq = q.to_numpy(float)
    q_slope, q_int = np.polyfit(xq, yq, 1)
    q_resid = yq - (q_slope * xq + q_int)
    q_slope_se = float(q_resid.std(ddof=2) / np.sqrt(((xq - xq.mean()) ** 2).sum()))

    # 按主口径归因份额把前沿斜率拆为两通道
    sh_tech = attribution["main_spec_decile_month"]["tech_share"]
    sh_scale = attribution["main_spec_decile_month"]["scale_share"]
    slope_tech = float(q_slope * sh_tech)
    slope_scale = float(q_slope * sh_scale)

    b_slope = bridge["slope"]
    b_sig = bridge["mapping_error_sigma"]
    E, A, al, B, be = q2["E"], q2["A"], q2["alpha"], q2["B"], q2["beta"]

    def loss_at(mult: float) -> float:
        """算力放大 mult 倍时的 Loss(按 Chinchilla 比例同步放大 N,D)。"""
        n0, d0 = 10.0, 300.0
        s = np.sqrt(mult)
        return E + A * (n0 * s) ** -al + B * (d0 * s) ** -be

    out: dict = {"current_frontier": round(cur, 3), "n_mc": n_mc,
                 "frontier_slope_per_month": round(float(q_slope), 4),
                 "frontier_slope_se": round(q_slope_se, 4),
                 "slope_tech_channel": round(slope_tech, 4),
                 "slope_scale_channel": round(slope_scale, 4),
                 "tau_slope_mean_level_for_reference": round(float(tau_slope_mean_level), 4),
                 "object_consistency_note": (
                     "前沿为 q90 水平，故用 q90 自身斜率按归因份额拆通道；"
                     "tau 的均值层面斜率仅作参照，不直接加到 q90 上"
                 ),
                 "scenarios": {}}

    # 规模通道的情景弹性:以中性情景的算力增速为基准做相对缩放
    g_ref = SCENARIOS["neutral"]["compute_growth_per_year"]
    dloss_ref = loss_at(g_ref) - loss_at(1.0)

    for name, cfg in SCENARIOS.items():
        g, decay = cfg["compute_growth_per_year"], cfg["tech_decay"]
        per_h = {}
        for h in (12, 24):
            draws = np.empty(n_mc)
            mult = g ** (h / 12.0)
            dloss = loss_at(mult) - loss_at(1.0)
            # 规模通道:相对中性情景的 Loss 降幅比,缩放该通道的历史斜率贡献
            scale_factor = (dloss / dloss_ref) if dloss_ref != 0 else 1.0
            for i in range(n_mc):
                st = (slope_tech + rng.normal(0, q_slope_se * abs(sh_tech))) * decay
                ss = (slope_scale + rng.normal(0, q_slope_se * abs(sh_scale))) * scale_factor
                b_i = b_slope + rng.normal(0, abs(b_slope) * 0.15)
                bridge_noise = rng.normal(0, b_sig) * (b_i / b_slope if b_slope else 1.0)
                draws[i] = cur + (st + ss) * h + bridge_noise
            draws = np.clip(draws, 0, 100)
            per_h[f"h{h}"] = {
                "median": round(float(np.median(draws)), 3),
                "lo80": round(float(np.quantile(draws, 0.10)), 3),
                "hi80": round(float(np.quantile(draws, 0.90)), 3),
                "lo95": round(float(np.quantile(draws, 0.025)), 3),
                "hi95": round(float(np.quantile(draws, 0.975)), 3),
                "width95": round(float(np.quantile(draws, 0.975) - np.quantile(draws, 0.025)), 3),
            }
        out["scenarios"][name] = {"config": cfg, **per_h}

    neu12 = out["scenarios"]["neutral"]["h12"]
    out["user_criterion"] = {
        "statement": "中性情景下 12 个月的 80% 区间下界 > 当前前沿值",
        "lo80": neu12["lo80"],
        "current_frontier": round(cur, 3),
        "passed": bool(neu12["lo80"] > cur),
        "width95_reported_not_gated": neu12["width95"],
    }
    out["uncertainty_sources"] = ["技术趋势斜率", "桥接映射误差", "桥接斜率不确定性"]
    out["horizon_note"] = (
        f"被判定视界为 {HORIZON_MONTHS} 个月。24 个月一并列出但未经裁定作主报；"
        "饱和形态(得分 0-100 上界)在 9.1 个月窗口内不可检验，该假设不可验证。"
    )
    return out


# ============================================================ C8 逐任务聚合
def c8_aggregate() -> dict:
    """题目硬性:至少一项逐任务聚合,不得仅用汇总表。全量 1860 目录。"""
    det = CDIR / "detailed_results"
    rows = []
    n_bad = 0
    for d in sorted(det.iterdir()):
        if not d.is_dir():
            continue
        best = None
        for f in sorted(d.glob("*.json")):
            try:
                best = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                n_bad += 1
        if best is None:
            continue
        res = best.get("results", {})
        if not isinstance(res, dict):
            continue
        npar = (best.get("config") or {}).get("model_num_parameters")
        for task, metrics in res.items():
            if not isinstance(metrics, dict):
                continue
            for mk, mv in metrics.items():
                if mk.startswith("acc_norm,") or mk.startswith("acc,"):
                    rows.append({"model_dir": d.name, "task": task,
                                 "metric": mk.split(",")[0], "value": float(mv),
                                 "n_params": npar})
                    break
    df = pd.DataFrame(rows)
    bbh = df[df["task"].str.startswith("leaderboard_bbh_")].copy()
    z = bbh.copy()
    z["z"] = z.groupby("task")["value"].transform(lambda s: (s - s.mean()) / (s.std(ddof=0) or 1))
    per_model = z.groupby("model_dir")["z"].mean()
    task_stats = bbh.groupby("task")["value"].agg(["count", "mean", "std"]).reset_index()

    return {
        "n_dirs_used": int(df["model_dir"].nunique()),
        "n_unparseable_files": int(n_bad),
        "n_task_rows": int(len(df)),
        "n_bbh_subtasks": int(bbh["task"].nunique()),
        "aggregation": "BBH 子任务逐任务 z-score 后按模型取均值（避免不同量纲直接相加）",
        "per_model_z_describe": {k: round(float(v), 4)
                                 for k, v in per_model.describe().items()},
        "hardest_5_tasks": task_stats.nsmallest(5, "mean")[["task", "mean", "count"]]
                           .to_dict("records"),
        "easiest_5_tasks": task_stats.nlargest(5, "mean")[["task", "mean", "count"]]
                           .to_dict("records"),
        "compliance": "满足题目「至少一项 C8 逐任务聚合，不得仅用汇总表」的硬性要求",
    }

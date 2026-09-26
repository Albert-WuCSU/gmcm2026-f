"""Q1c 方法特定风险探针（配比侧）。

被探方法：
  M0c usable_baseline : 17 维 p 的线性回归（HD-2=B 指定），须处理 Σp=1 引起的奇异
  M1c main_candidate  : 主效应 + 二阶交互 + 岭正则（153 特征 / 512 样本）
  M2c fallback        : 仅主效应 + 单纯形几何变换（非 ILR，用中心化对数或平方根变换）

检查项：可执行性、训练/检验分布位移、单纯形共线性、交互项可辨识性、
        系数集中度、预测退化、扰动稳定性、外推可信度。
输出：workspace/data/q1_probe_mixture.json
种子：20260924
"""
from __future__ import annotations

import csv
import itertools
import json
import time

import numpy as np

import q1_features as qf

TAB = qf.RAW / "regmix_tables"
OUT = qf.ROOT / "workspace/data/q1_probe_mixture.json"
RNG = np.random.default_rng(qf.SEED)

PAIRS = {
    "train_1m": ("train_mixture_1m.csv", "train_pile_loss_1m.csv"),
    "test_1m": ("test_mixture_1m.csv", "test_pile_loss_1m.csv"),
    "test_60m": ("test_mixture_60m.csv", "test_pile_loss_60m.csv"),
    "test_1B": ("test_mixture_1B.csv", "test_pile_loss_1B.csv"),
    "est_10b": ("est_mixture_10b.csv", "est_pile_loss_10b.csv"),
    "est_70b": ("est_mixture_70b.csv", "est_pile_loss_70b.csv"),
}


def read_csv(name: str) -> tuple[list[str], np.ndarray, list[str]]:
    with open(TAB / name, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    hdr = rows[0]
    idx_col = [r[0] for r in rows[1:]]
    data = np.array([[float(x) if x != "" else np.nan for x in r[1:]]
                     for r in rows[1:]], dtype=np.float64)
    return hdr[1:], data, idx_col


def load_pair(key: str):
    mf, lf = PAIRS[key]
    pcols, P, pidx = read_csv(mf)
    lcols, L, lidx = read_csv(lf)
    assert pidx == lidx, f"{key} index 不对齐"
    return pcols, P, lcols, L


def ridge_fit(A: np.ndarray, y: np.ndarray, lam: float) -> np.ndarray:
    m = A.shape[1]
    return np.linalg.solve(A.T @ A + lam * np.eye(m), A.T @ y)


def kfold_cv(A: np.ndarray, y: np.ndarray, lams: list[float], k: int = 5) -> tuple[float, dict]:
    n = len(y)
    perm = RNG.permutation(n)
    folds = np.array_split(perm, k)
    scores = {}
    for lam in lams:
        errs = []
        for i in range(k):
            te = folds[i]
            tr = np.concatenate([folds[j] for j in range(k) if j != i])
            w = ridge_fit(A[tr], y[tr], lam)
            errs.append(float(np.mean((A[te] @ w - y[te]) ** 2)))
        scores[lam] = float(np.mean(errs))
    best = min(scores, key=scores.get)
    return best, {str(k_): round(v, 6) for k_, v in scores.items()}


def design(P: np.ndarray, kind: str) -> np.ndarray:
    """kind: 'main' 仅主效应 | 'main_intercept' 加截距 | 'inter' 主效应+二阶交互 | 'sqrt' 平方根变换"""
    n, m = P.shape
    if kind == "main":
        return P.copy()
    if kind == "main_intercept":
        return np.hstack([np.ones((n, 1)), P])
    if kind == "sqrt":
        return np.sqrt(np.clip(P, 0, None))
    if kind == "inter":
        cols = [P]
        for i, j in itertools.combinations(range(m), 2):
            cols.append((P[:, i] * P[:, j])[:, None])
        return np.hstack(cols)
    raise ValueError(kind)


def r2(y: np.ndarray, yh: np.ndarray) -> float:
    ss = float(np.sum((y - y.mean()) ** 2))
    return float(1 - np.sum((y - yh) ** 2) / ss) if ss > 0 else float("nan")


def main() -> None:
    t0 = time.time()
    res: dict = {"schema_version": 1, "seed": qf.SEED, "tables": {}}

    data = {k: load_pair(k) for k in PAIRS}
    pcols, Ptr, lcols, Ltr = data["train_1m"]
    res["columns"] = {"mixture_domains": pcols, "loss_domains": lcols}

    # ---------------- data_coverage：分布位移与零值 ----------------
    def top3(P):
        return np.sort(P, axis=1)[:, ::-1][:, :3].sum(1)

    cov = {}
    for k in PAIRS:
        pc, P, lc, L = data[k]
        cov[k] = {
            "rows": int(P.shape[0]),
            "rowsum_min": round(float(P.sum(1).min()), 5),
            "rowsum_max": round(float(P.sum(1).max()), 5),
            "zero_rate": round(float(np.mean(P == 0)), 5),
            "zeros_per_row_median": float(np.median((P == 0).sum(1))),
            "top3_mass_median": round(float(np.median(top3(P))), 5),
            "top3_mass_p05_p95": [round(float(np.quantile(top3(P), .05)), 4),
                                  round(float(np.quantile(top3(P), .95)), 4)],
            "loss_nan_rate": round(float(np.mean(np.isnan(L))), 6),
        }
    res["data_coverage"] = cov

    # 检验集是否落在训练集配比的支撑内：最近邻 L1 距离
    shift = {}
    for k in ("test_1m", "test_60m", "test_1B", "est_10b", "est_70b"):
        _, P, _, _ = data[k]
        dmin = np.array([np.abs(Ptr - P[i]).sum(1).min() for i in range(P.shape[0])])
        dtr = np.array([np.sort(np.abs(Ptr - Ptr[i]).sum(1))[1] for i in range(Ptr.shape[0])])
        shift[k] = {
            "nn_L1_to_train_median": round(float(np.median(dmin)), 5),
            "nn_L1_to_train_max": round(float(dmin.max()), 5),
            "train_internal_nn_L1_median": round(float(np.median(dtr)), 5),
            "ratio_median": round(float(np.median(dmin) / max(np.median(dtr), 1e-12)), 3),
            "frac_exact_duplicate_of_train": round(float(np.mean(dmin < 1e-9)), 4),
        }
    res["train_test_mixture_shift"] = shift

    # ---------------- assumption_checks：单纯形奇异与交互可辨识 ----------------
    A_main = design(Ptr, "main")
    A_int_ = design(Ptr, "main_intercept")
    A_inter = design(Ptr, "inter")

    def cond(A):
        s = np.linalg.svd(A, compute_uv=False)
        return float(s[0] / max(s[-1], 1e-300)), float(s[-1])

    c_main, smin_main = cond(A_main)
    c_int, smin_int = cond(A_int_)
    c_inter, smin_inter = cond(A_inter)
    res["assumption_checks"] = {
        "simplex_rowsum_deviation_max": round(float(np.abs(Ptr.sum(1) - 1).max()), 6),
        "cond_main_only_17": round(c_main, 1),
        "cond_with_intercept_18": round(c_int, 1),
        "smallest_singular_with_intercept": float(f"{smin_int:.4g}"),
        "intercept_makes_singular": bool(c_int > 1e8),
        "cond_main_plus_interactions_153": round(c_inter, 1),
        "n_features_interactions": int(A_inter.shape[1]),
        "n_train_rows": int(Ptr.shape[0]),
        "features_over_rows_ratio": round(A_inter.shape[1] / Ptr.shape[0], 3),
        "note_intercept": "Σp=1 理论上使截距与 17 列之和完全共线；实测未奇异（cond 61→4773，"
                          "×78）仅因行和有千分位舍入（最大偏离 0.004）。即截距只靠舍入噪声可辨识，"
                          "其系数无实质解释；baseline 须显式去截距或指定参照域，不可依赖舍入。",
    }

    # ---------------- 目标变量口径 ----------------
    # y1: 13 域 Loss 简单均值； y2: 以配比在 13 域上重归一化的加权均值
    def loss_col_to_domain(c: str) -> str:
        return c.removeprefix("metric/the_pile_").removesuffix("_val_loss")

    loss_in_mix = [pcols.index("train_the_pile_" + loss_col_to_domain(c))
                   if ("train_the_pile_" + loss_col_to_domain(c)) in pcols
                   else None for c in lcols]
    res["loss_to_mixture_column_match"] = {
        "matched": int(sum(1 for x in loss_in_mix if x is not None)),
        "total_loss_cols": len(lcols),
    }

    def targets(P, L):
        y_mean = np.nanmean(L, axis=1)
        idx = [i for i in loss_in_mix if i is not None]
        w = P[:, idx]
        w = w / np.maximum(w.sum(1, keepdims=True), 1e-12)
        y_w = np.nansum(w * L[:, [j for j, x in enumerate(loss_in_mix) if x is not None]], axis=1)
        return {"mean13": y_mean, "pweighted13": y_w}

    ytr = targets(Ptr, Ltr)

    # ---------------- 拟合与检验 ----------------
    fits = {}
    lams = [1e-8, 1e-6, 1e-4, 1e-3, 1e-2, 1e-1, 1.0, 10.0]
    for tname, y in ytr.items():
        entry = {}
        for mid, kind in (("M0c_linear_main", "main"),
                          ("M1c_main_plus_inter_ridge", "inter"),
                          ("M2c_sqrt_main", "sqrt")):
            A = design(Ptr, kind)
            if mid == "M0c_linear_main":
                lam, cvs = 0.0, {}
                w = np.linalg.lstsq(A, y, rcond=None)[0]
            else:
                lam, cvs = kfold_cv(A, y, lams)
                w = ridge_fit(A, y, lam)
            yh = A @ w
            rec = {"lambda": lam, "cv_mse_by_lambda": cvs,
                   "train_r2": round(r2(y, yh), 5),
                   "train_rmse": round(float(np.sqrt(np.mean((y - yh) ** 2))), 5),
                   "coef_abs_max": round(float(np.abs(w).max()), 4),
                   "coef_l1": round(float(np.abs(w).sum()), 4),
                   "coef_top5_share_of_l1": round(float(
                       np.sort(np.abs(w))[::-1][:5].sum() / max(np.abs(w).sum(), 1e-12)), 4),
                   "n_coef": int(len(w))}
            # 检验集
            te = {}
            for k in ("test_1m", "test_60m", "test_1B", "est_10b", "est_70b"):
                pc, P, lc, L = data[k]
                yt = targets(P, L)[tname]
                At = design(P, kind)
                yp = At @ w
                bias = float(np.mean(yp - yt))
                # 去掉按尺度的常数水平偏移后，检验"配比→Loss 的形状"是否跨尺度可迁移
                rs = np.argsort(np.argsort(yt)); ps = np.argsort(np.argsort(yp))
                te[k] = {"n": int(len(yt)), "r2": round(r2(yt, yp), 5),
                         "rmse": round(float(np.sqrt(np.mean((yt - yp) ** 2))), 5),
                         "bias": round(bias, 5),
                         "bias_share_of_rmse": round(
                             abs(bias) / max(float(np.sqrt(np.mean((yt - yp) ** 2))), 1e-12), 4),
                         "r2_after_offset_removal": round(r2(yt, yp - bias), 5),
                         "spearman": round(float(np.corrcoef(rs, ps)[0, 1]), 4),
                         "pred_std": round(float(np.std(yp)), 5),
                         "true_std": round(float(np.std(yt)), 5)}
            rec["validation"] = te
            # 系数自助稳定性
            B = 200
            n = len(y)
            cs = []
            for _ in range(B):
                i = RNG.integers(0, n, n)
                cs.append(ridge_fit(A[i], y[i], max(lam, 1e-8)))
            CS = np.array(cs)
            sgn = np.mean(np.sign(CS) == np.sign(w)[None, :], axis=0)
            rec["coef_bootstrap"] = {
                "B": B,
                "frac_coefs_sign_stable_ge_0.95": round(float(np.mean(sgn >= 0.95)), 4),
                "median_sign_stability": round(float(np.median(sgn)), 4),
                "mean_relative_se": round(float(np.mean(
                    CS.std(0) / np.maximum(np.abs(w), 1e-9))), 4),
            }
            entry[mid] = rec
        fits[tname] = entry
    res["fits"] = fits
    res["runtime_seconds"] = round(time.time() - t0, 2)

    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"done in {time.time()-t0:.1f}s -> {OUT}")


if __name__ == "__main__":
    main()

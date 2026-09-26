"""M1c — 配比侧 main_candidate。

方法：17 主效应 + 136 个二阶交互 = **153 特征**，岭正则，**5 折 CV 选 λ**。
目标与检验集与 M0c 完全相同（逐项可比）。

**系数报告过滤（硬性）**：B=400 自助，**仅报符号稳定率 ≥0.95 的项**。
  禁止把稳定子集外的单个交互系数解释为域间替代/互补
  （探针实测符号稳定率仅 0.549、平均相对 SE 1.514、cond 46512）。

跨尺度增益如实报：同尺度 1m 有增益，60m 基本持平，**1B 反而更差**
  —— 即增益是尺度局部的，不构成跨尺度优势（HD-2 升级条款已由决策 C 裁定：
  M0c 为主、M1c 作组合效应辅证）。

输出：tables/q1c_coefficients.csv（追加 M1c 稳定子集）、
      tables/q1c_validation_by_scale.csv（追加 M1c 行）、metrics/q1_mixture_M1c.json
种子 20260924。
"""
from __future__ import annotations

import csv as _csv
import time

import numpy as np

import q1_common as C

SCALES = ("test_1m", "test_60m", "test_1B")
EXTRAP = ("est_10b", "est_70b")


def main() -> None:
    t0 = time.time()
    C.ensure_dirs()
    rng = np.random.default_rng(C.SEED)

    pcols, Ptr, lcols, Ltr = C.load_pair("train_1m")
    l2m = C.loss_to_mixture_index(pcols, lcols)
    ytr = C.make_target(Ptr, Ltr, l2m, "pweighted13")
    A_tr = C.design(Ptr, "inter")
    fnames = C.feature_names(pcols, "inter")

    res = {
        "schema_version": 1, "method_id": "M1c", "role": "main_candidate",
        "subtasks": ["Q1c"], "seed": C.SEED,
        "definition": "17 主效应 + 136 二阶交互（153 特征）+ 岭正则，5 折 CV 选 λ",
        "n_features": int(A_tr.shape[1]), "n_train_rows": int(A_tr.shape[0]),
        "features_over_rows": round(A_tr.shape[1] / A_tr.shape[0], 3),
        "target_declaration": {
            "primary": "pweighted13",
            "circularity_warning": "该目标把 p 同时置于等式两侧，存在部分循环，须在论文声明（AMB-Q1-2）",
            "unit": "交叉熵 nats/token"},
    }

    # ---- 5 折 CV 选 λ
    lam, cv_scores = C.kfold_cv(A_tr, ytr, C.LAMBDAS, rng)
    w = C.ridge_fit(A_tr, ytr, lam)
    res["lambda_selection"] = {"selected": lam, "grid": C.LAMBDAS, "cv_mse": cv_scores,
                               "k_folds": 5}
    res["train"] = {"r2": C.r2(ytr, A_tr @ w), "n": int(len(ytr))}
    res["probe_monitors"] = {
        "cond_153_features": float(np.linalg.cond(A_tr)),
        "interaction_identifiability": "FAIL（探针）：本轮强制执行 >=0.95 符号稳定率过滤",
    }

    # ---- 三尺度验证 + 外推（仅定性）
    val, extrap = {}, {}
    for key in SCALES:
        pc, P, lc, L = C.load_pair(key)
        y = C.make_target(P, L, C.loss_to_mixture_index(pc, lc), "pweighted13")
        val[key] = C.validate_by_scale(w, C.design(P, "inter"), y)
    for key in EXTRAP:
        pc, P, lc, L = C.load_pair(key)
        y = C.make_target(P, L, C.loss_to_mixture_index(pc, lc), "pweighted13")
        extrap[key] = C.validate_by_scale(w, C.design(P, "inter"), y)
        extrap[key]["qualitative_only"] = True
        extrap[key]["reason"] = "A12/A14 配比行与训练集重复率 1.0，只能检验 Loss 外推（GC5）"
    res["validation_by_scale"] = val
    res["extrapolation_qualitative_only"] = extrap

    # ---- 系数稳定性与硬性过滤
    st = C.coef_stability(A_tr, ytr, lam, rng)
    sign_stab = np.array(st["sign_stability"])
    coef = np.array(st["coef"])
    keep = sign_stab >= 0.95
    n_main = len(pcols)
    res["coef_stability"] = {k: v for k, v in st.items()
                             if k not in ("coef", "sign_stability", "se", "relative_se")}
    res["coef_filter"] = {
        "rule": "仅报 sign_stability >= 0.95",
        "n_total": int(len(coef)), "n_reported": int(keep.sum()),
        "n_suppressed": int((~keep).sum()),
        "main_effects_stable": int(keep[:n_main].sum()), "main_effects_total": n_main,
        "interactions_stable_ge_0.95": int(keep[n_main:].sum()),
        "interactions_stable_ge_0.99": int((sign_stab[n_main:] >= 0.99).sum()),
        "interactions_total": int(len(coef) - n_main),
        "prohibited_claim": ("禁止把稳定子集外的单个交互系数解释为域间替代/互补；"
                            "稳定子集内的交互项亦只支持方向性陈述，不支持定量替代率"),
    }
    res["coefficients_reported"] = [
        {"feature": fnames[j], "coef": float(coef[j]), "sign_stability": float(sign_stab[j]),
         "se": st["se"][j], "relative_se": st["relative_se"][j],
         "kind": "main" if j < n_main else "interaction"}
        for j in np.flatnonzero(keep)]

    # ---- λ ±1 个数量级的扰动
    pert = {}
    for mult, tag in ((0.1, "lambda_div10"), (10.0, "lambda_x10")):
        lam2 = lam * mult
        w2 = C.ridge_fit(A_tr, ytr, lam2)
        st2 = C.coef_stability(A_tr, ytr, lam2, rng, b=100)
        pert[tag] = {
            "lambda": lam2,
            "r2_after_offset_removal": {
                k: C.validate_by_scale(w2, C.design(C.load_pair(k)[1], "inter"),
                                       C.make_target(*[C.load_pair(k)[i] for i in (1, 3)],
                                                     C.loss_to_mixture_index(
                                                         C.load_pair(k)[0], C.load_pair(k)[2]),
                                                     "pweighted13"))["r2_after_offset_removal"]
                for k in SCALES},
            "frac_coefs_sign_stable_ge_0.95": st2["frac_coefs_sign_stable_ge_0.95"],
            "n_stable_subset": int(np.sum(np.array(st2["sign_stability"]) >= 0.95)),
        }
    res["perturbation_lambda"] = pert

    # ---- 与 baseline 的跨尺度对照（如实报增益的尺度局部性）
    m0c = C.METRICS / "q1_mixture_M0c.json"
    if m0c.exists():
        import json as _json
        b = _json.loads(m0c.read_text(encoding="utf-8"))["validation_by_scale"]
        res["gain_over_baseline"] = {
            k: {"M0c": b[k]["r2_after_offset_removal"],
                "M1c": val[k]["r2_after_offset_removal"],
                "gain": val[k]["r2_after_offset_removal"] - b[k]["r2_after_offset_removal"]}
            for k in SCALES}
        res["gain_over_baseline"]["interpretation"] = (
            "增益为尺度局部：同尺度 1m 有增益，60m 基本持平，1B 更差 -> 不构成跨尺度优势")

    res["warnings"] = ["交互项可辨识性为 FAIL：已强制 >=0.95 过滤，未过滤系数不得进入任何表"]
    res["execution_time_seconds"] = round(time.time() - t0, 1)
    C.write_json(C.METRICS / "q1_mixture_M1c.json", res)

    # ---- 追加落表
    cpath = C.TABLES / "q1c_coefficients.csv"
    prev = []
    if cpath.exists():
        with open(cpath, newline="", encoding="utf-8-sig") as f:
            prev = [r for r in list(_csv.reader(f))[1:] if r and r[0] != "M1c"]
    C.write_csv(cpath,
                ["method", "feature", "coef", "sign_stability", "se", "relative_se", "reported"],
                prev + [["M1c", c["feature"], round(c["coef"], 6), round(c["sign_stability"], 4),
                         round(c["se"], 6), round(c["relative_se"], 4), "yes"]
                        for c in res["coefficients_reported"]])

    vpath = C.TABLES / "q1c_validation_by_scale.csv"
    prev = []
    if vpath.exists():
        with open(vpath, newline="", encoding="utf-8-sig") as f:
            prev = [r for r in list(_csv.reader(f))[1:] if r and r[0] != "M1c"]
    C.write_csv(vpath,
                ["method", "scale", "n", "r2_raw", "r2_after_offset_removal", "spearman",
                 "bias", "rmse", "bias_share_of_rmse", "qualitative_only"],
                prev + [["M1c", k, v["n"], round(v["r2_raw"], 5),
                         round(v["r2_after_offset_removal"], 5), round(v["spearman"], 5),
                         round(v["bias"], 5), round(v["rmse"], 5),
                         round(v["bias_share_of_rmse"], 5), v.get("qualitative_only", False)]
                        for k, v in list(val.items()) + list(extrap.items())])

    f = res["coef_filter"]
    print(f"M1c 完成 {res['execution_time_seconds']}s | λ={lam:g} | train R² {res['train']['r2']:.5f}")
    for k, v in val.items():
        print(f"  {k}: 去偏 R² {v['r2_after_offset_removal']:.4f} | Spearman {v['spearman']:.4f}")
    print(f"  稳定子集 {f['n_reported']}/{f['n_total']}（主效应 {f['main_effects_stable']}/"
          f"{f['main_effects_total']}，交互 ≥0.95 {f['interactions_stable_ge_0.95']}、"
          f"≥0.99 {f['interactions_stable_ge_0.99']}，压制 {f['n_suppressed']}）")
    if "gain_over_baseline" in res:
        for k in SCALES:
            g = res["gain_over_baseline"][k]
            print(f"  vs M0c @{k}: {g['M0c']:.4f} -> {g['M1c']:.4f} ({g['gain']:+.4f})")


if __name__ == "__main__":
    main()

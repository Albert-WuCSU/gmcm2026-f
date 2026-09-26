"""检验假设：rps_doc_frac_unique_words 的长度依赖是否与 dsir 同属一类。

背景（交接文档 §9.1）：canonical 配置下唯一残余的弱矛盾源是 frac_unique_words
（3 对 r<-0.5 全部牵涉它），与 unigram_entropy 的 Spearman = -0.684。
问题：这是否与 dsir 同属"长度效应"，因而应比照 dsir 做同类处置？

关键区分（本探针要判定的）：
  dsir 原始字段是"按 token 求和"的**外延量（extensive）**，长度依赖是量纲错误，
    除以词数是精确的量纲还原 —— 机械可判，且会翻转符号。
  frac_unique_words = V/N 本身已是**内涵量（intensive）**的比率。它的长度依赖来自
    Heaps 定律 V≈K·N^β（β<1）→ TTR=V/N≈K·N^(β-1) 随 N 机械下降，
    属**有限样本估计量偏倚**，不是量纲错误。故"再除以 N"是过度校正。

检验：
  1) 确认 frac_unique×word_count 是否为整数 → 验证 TTR=V/N 的字段语义
  2) 拟合 Heaps 定律 log V = log K + β log N，报 β 与 R²
  3) 施加 dsir 式处置（frac_unique/N）→ 检验与长度的相关是否恶化（预期恶化）
  4) Heaps 残差化（log V - β̂·log N，等价 Herdan's C 族）→ 与 N 是否解耦
  5) unigram_entropy 自身的长度依赖 → 判定"矛盾"归属是否该只记在 frac_unique 头上
  6) 偏相关 corr(frac_unique, unigram_entropy | log N) → 矛盾是否为长度共因的产物
  7) 与 fineweb_edu 的方向：残差化是否翻转符号（dsir 曾翻转；预期此处不翻转）
  8) 对 canonical Q 的实际影响：域序、极差、AUC、矛盾对数、与原 Q 的秩相关

输出：workspace/data/q1_probe_unique_words_length.json
本探针不改动 CANONICAL 规格；残差化仅在探针内构造，供使用者决策。

种子：20260924
"""
from __future__ import annotations

import json

import numpy as np

import q1_features as qf
from probe_q1_quality import huber_mean, auc_from_scores

OUT = qf.ROOT / "workspace/data/q1_probe_unique_words_length.json"
FU = "rps_doc_frac_unique_words"
UE = "rps_doc_unigram_entropy"
WC = "rps_doc_word_count"


def sp(a: np.ndarray, b: np.ndarray) -> float:
    """Spearman = 秩上的 Pearson，与 q1_probe_corr.json 的 ecdf 口径一致。"""
    ra = np.argsort(np.argsort(a))
    rb = np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


def ols_resid(y: np.ndarray, x: np.ndarray) -> tuple[np.ndarray, float, float]:
    """一元 OLS，返回 (残差, 斜率, R²)。"""
    A = np.column_stack([np.ones_like(x), x])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    pred = A @ beta
    r = y - pred
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - float((r ** 2).sum()) / ss_tot if ss_tot > 0 else float("nan")
    return r, float(beta[1]), r2


def measure_Q(U: np.ndarray, cols: list[str], dom, names) -> dict:
    """与 verify_q1_canonical.measure 同口径：等权均值 Q 的域级量。"""
    C = np.corrcoef(U, rowvar=False)
    n8 = sum(1 for i in range(len(cols)) for j in range(i + 1, len(cols))
             if C[i, j] < -0.8)
    n5 = sum(1 for i in range(len(cols)) for j in range(i + 1, len(cols))
             if C[i, j] < -0.5)
    q = U.mean(1)
    dv = np.array([huber_mean(q[dom == d]) for d in range(len(names))])
    ia, ig = names.index("arxiv"), names.index("github")
    return {"n_cols": len(cols), "n_contra_lt_08": n8, "n_contra_lt_05": n5,
            "domain_range": round(float(dv.max() - dv.min()), 4),
            "auc_arxiv_vs_github": round(auc_from_scores(q[dom == ia], q[dom == ig]), 4),
            "domain_order": [names[i] for i in np.argsort(-dv)],
            "domain_huber": {names[i]: round(float(dv[i]), 5) for i in range(len(names))},
            "_q": q}


def main() -> None:
    X, dom, meta = qf.load_all()
    cols, names = meta["columns"], meta["domains"]
    gi = {c: cols.index(c) for c in cols}
    ref_mask = np.zeros(X.shape[0], dtype=bool)
    ref_mask[:meta["rows_per_file"]["A1"]] = True

    fu = X[:, gi[FU]]
    ue = X[:, gi[UE]]
    wc = X[:, gi[WC]]
    edu = X[:, gi["fineweb_edu"]]
    logN = np.log(np.maximum(wc, 1.0))

    res = {"schema_version": 1, "n_rows": int(X.shape[0]), "domains": names,
           "seed": qf.SEED}

    # --- 1) 字段语义：确认量纲与 TTR 定义
    # 实测 min=1.22 / p50=56.90 / max=100.0 => 该字段是**百分数（0-100）**，不是 0-1 比率。
    # 故类型数 V = fu/100 * wc。该常数只平移 Heaps 拟合的截距，不影响 β 与残差。
    scale = 100.0 if fu.max() > 1.0 + 1e-9 else 1.0
    V_raw = (fu / scale) * wc
    dev = np.abs(V_raw - np.round(V_raw))
    res["field_semantics"] = {
        "hypothesis": "frac_unique_words = 100·V/N（类型数/例符数，TTR，百分数刻度）",
        "detected_scale": scale,
        "frac_unique_range": {"min": round(float(fu.min()), 5),
                              "p50": round(float(np.median(fu)), 5),
                              "max": round(float(fu.max()), 5)},
        "V_integer_deviation_after_descaling": {
            "p50": round(float(np.median(dev)), 6),
            "p95": round(float(np.quantile(dev, 0.95)), 6),
            "max": round(float(dev.max()), 6),
            "frac_within_1e-3": round(float((dev < 1e-3).mean()), 4),
        },
        "is_already_intensive_ratio": True,
        "intensive_note": ("TTR 已是比率（值域上界 100 即 N 个词全不重复），"
                           "与 dsir 的按 token 求和（外延量、无上界）本质不同"),
    }

    # --- 2) Heaps 定律：log V = log K + β log N
    V = np.maximum(np.round(V_raw), 1.0)
    _, beta_heaps, r2_heaps = ols_resid(np.log(V), logN)
    res["heaps_law"] = {
        "beta": round(beta_heaps, 4),
        "r2": round(r2_heaps, 4),
        "implied_ttr_exponent_beta_minus_1": round(beta_heaps - 1.0, 4),
        "in_canonical_range_0.4_0.8": bool(0.4 <= beta_heaps <= 0.8),
        "note": "β<1 => TTR=V/N ~ N^(β-1) 随 N 机械下降，属估计量偏倚而非量纲错误",
    }

    # --- 3) 原始长度依赖 + dsir 式处置（再除以 N）是否恶化
    fu_pertoken = fu / np.maximum(wc, 1.0)
    res["length_dependence"] = {
        "frac_unique": {
            "pearson_vs_word_count": round(float(np.corrcoef(fu, wc)[0, 1]), 4),
            "spearman_vs_word_count": round(sp(fu, wc), 4),
            "spearman_vs_log_word_count": round(sp(fu, logN), 4),
        },
        "unigram_entropy": {
            "pearson_vs_word_count": round(float(np.corrcoef(ue, wc)[0, 1]), 4),
            "spearman_vs_word_count": round(sp(ue, wc), 4),
            "spearman_vs_log_word_count": round(sp(ue, logN), 4),
        },
        "dsir_style_per_token_applied_to_frac_unique": {
            "spearman_vs_word_count": round(sp(fu_pertoken, wc), 4),
            "worsened": bool(abs(sp(fu_pertoken, wc)) > abs(sp(fu, wc))),
            "note": "dsir 式处置施加于已是比率的 TTR 属过度校正，此项用于证伪同类处置",
        },
    }

    # --- 4/5) Heaps 残差化（正确的同族校正）与 entropy 的同类校正
    fu_res, _, _ = ols_resid(np.log(V) , logN)          # = log V - β̂ log N - logK
    ue_res, ue_slope, ue_r2 = ols_resid(ue, logN)       # entropy 对 log N 近似线性
    res["residualization"] = {
        "frac_unique_heaps_residual": {
            "spearman_vs_word_count": round(sp(fu_res, wc), 4),
            "spearman_vs_original_frac_unique": round(sp(fu_res, fu), 4),
            "decoupled_from_length": bool(abs(sp(fu_res, wc)) < 0.2),
        },
        "unigram_entropy_residual": {
            "slope_vs_log_n": round(ue_slope, 4), "r2": round(ue_r2, 4),
            "spearman_vs_word_count": round(sp(ue_res, wc), 4),
        },
    }

    # --- 6) 偏相关：矛盾是否为长度共因的产物
    # 判据修正：长度共因的特征不是"偏相关缩向 0"，而是"去长度后符号翻正"。
    # 若 fu 与 ue 无真实关系，仅由长度生成的相关应约为 sp(fu,N)·sp(ue,N)。
    r_raw = sp(fu, ue)
    r_partial = sp(fu_res, ue_res)
    r_len_implied = sp(fu, logN) * sp(ue, logN)
    res["contradiction_attribution"] = {
        "spearman_frac_unique_vs_entropy_raw": round(r_raw, 4),
        "spearman_after_both_residualized": round(r_partial, 4),
        "length_only_implied_corr": round(r_len_implied, 4),
        "sign_flipped_to_agreement": bool(r_raw < 0 and r_partial > 0),
        "spurious_contradiction": bool(r_raw < -0.5 and r_partial > 0.5),
        "note": ("entropy 与 frac_unique 对长度的依赖方向相反（+0.95 / -0.85），"
                 "长度单独即可生成约 -0.81 的负相关；观测 -0.68 弱于该值，"
                 "去长度后为 +0.92 强一致 => 原负相关是长度诱导的伪矛盾，"
                 "二者在同一长度下测的是同一构念（词汇多样性）"),
    }

    # --- 6b) 伪矛盾的反面：去长度后 fu 与 ue 高度冗余，等权均值将重复计数同一构念
    res["redundancy_tradeoff"] = {
        "corr_fu_res_vs_ue_res": round(r_partial, 4),
        "raw_pair_partially_cancels_in_equal_weight_mean": bool(r_raw < 0),
        "note": ("修掉矛盾会同时制造冗余：残差化后 fu 与 ue 相关 +0.92，"
                 "在 20 列等权均值中近似双计一个构念；现状下 -0.68 反而部分互抵。"
                 "这是处置与否的实质权衡，非纯技术优劣"),
    }

    # --- 7) 与 fineweb_edu 的方向是否翻转（dsir 曾翻转）
    s_before, s_after = sp(fu, edu), sp(fu_res, edu)
    res["direction_vs_fineweb_edu"] = {
        "spearman_before": round(s_before, 4),
        "spearman_after_residualization": round(s_after, 4),
        "sign_flipped": bool(s_before * s_after < 0),
        "dsir_comparison": {"before": -0.4991, "after": 0.3741, "sign_flipped": True},
    }

    # --- 8) 对 canonical Q 的实际影响
    base = measure_Q(*qf.build_canonical(X, dom, cols, ref_mask=ref_mask), dom, names)

    # 变体：把 frac_unique 原始列替换为 Heaps 残差后，再走同一 canonical 流程
    X_adj = X.copy()
    X_adj[:, gi[FU]] = fu_res
    adj = measure_Q(*qf.build_canonical(X_adj, dom, cols, ref_mask=ref_mask), dom, names)

    q_b, q_a = base.pop("_q"), adj.pop("_q")
    dv_b = np.array([base["domain_huber"][n] for n in names])
    dv_a = np.array([adj["domain_huber"][n] for n in names])
    res["impact_on_canonical_Q"] = {
        "canonical": base,
        "with_heaps_residual_for_frac_unique": adj,
        "spearman_row_level_Q": round(sp(q_b, q_a), 5),
        "spearman_domain_level_Q": round(sp(dv_b, dv_a), 5),
        "max_abs_domain_shift": round(float(np.abs(dv_a - dv_b).max()), 5),
        "domain_order_unchanged": bool(base["domain_order"] == adj["domain_order"]),
    }

    # --- 8b) 唯一可见后果是 c4/commoncrawl 换位。该换位是实质重排还是并列上的噪声？
    # 用 bootstrap 区间判定（HD-2 规定显著性由重抽样判定，机械可判）。
    rng = np.random.default_rng(qf.SEED)
    B = 400
    tie = {}
    for tag, q in (("canonical", q_b), ("with_heaps_residual", q_a)):
        pair = {}
        for d_name in ("c4", "commoncrawl"):
            v = q[dom == names.index(d_name)]
            bs = np.array([huber_mean(v[rng.integers(0, len(v), len(v))])
                           for _ in range(B)])
            lo, hi = np.quantile(bs, [0.025, 0.975])
            pair[d_name] = {"huber": round(float(huber_mean(v)), 5),
                            "ci95": [round(float(lo), 5), round(float(hi), 5)],
                            "half_width": round(float((hi - lo) / 2), 5), "n": int(len(v))}
        gap = abs(pair["c4"]["huber"] - pair["commoncrawl"]["huber"])
        # 差值的 bootstrap 区间是否含 0 => 是否统计上并列
        vc, vm = q[dom == names.index("c4")], q[dom == names.index("commoncrawl")]
        dbs = np.array([huber_mean(vc[rng.integers(0, len(vc), len(vc))])
                        - huber_mean(vm[rng.integers(0, len(vm), len(vm))])
                        for _ in range(B)])
        dlo, dhi = np.quantile(dbs, [0.025, 0.975])
        pair["gap_abs"] = round(float(gap), 5)
        pair["diff_ci95"] = [round(float(dlo), 5), round(float(dhi), 5)]
        pair["statistically_tied"] = bool(dlo <= 0.0 <= dhi)
        tie[tag] = pair
    res["c4_vs_commoncrawl_tie_test"] = {
        "B_bootstrap": B, "results": tie,
        "note": ("若两配置下差值区间均含 0，则 c4/commoncrawl 的换位是并列上的噪声，"
                 "不构成实质域序改变"),
    }

    # --- 9) 关键：只修 fu 会拆掉 fu 与 ue 的长度互抵，复合 Q 的长度暴露可能反而上升。
    # 故须比较三配置下 corr(Q, logN)，并补测"fu 与 ue 一并残差化"的第三配置。
    X_both = X.copy()
    X_both[:, gi[FU]] = fu_res
    X_both[:, gi[UE]] = ue_res
    both = measure_Q(*qf.build_canonical(X_both, dom, cols, ref_mask=ref_mask), dom, names)
    q_both = both.pop("_q")

    res["composite_length_exposure"] = {
        cfg: {"spearman_Q_vs_log_word_count": round(sp(q, logN), 4),
              "pearson_Q_vs_log_word_count": round(float(np.corrcoef(q, logN)[0, 1]), 4)}
        for cfg, q in (("canonical", q_b),
                       ("fu_residualized_only", q_a),
                       ("fu_and_ue_residualized", q_both))
    }
    res["composite_length_exposure"]["note"] = (
        "canonical 下 fu(-0.85) 与 ue(+0.95) 的长度分量在等权均值中部分互抵；"
        "只残差化 fu 会移除互抵的一方，故须检验复合 Q 的长度暴露是否反而恶化")

    res["variant_fu_and_ue_residualized"] = both
    res["variant_comparison"] = {
        "n_contra_lt_05": {"canonical": base["n_contra_lt_05"],
                           "fu_only": adj["n_contra_lt_05"],
                           "fu_and_ue": both["n_contra_lt_05"]},
        "domain_range": {"canonical": base["domain_range"],
                         "fu_only": adj["domain_range"],
                         "fu_and_ue": both["domain_range"]},
        "auc_arxiv_vs_github": {"canonical": base["auc_arxiv_vs_github"],
                                "fu_only": adj["auc_arxiv_vs_github"],
                                "fu_and_ue": both["auc_arxiv_vs_github"]},
        "spearman_row_Q_vs_canonical": {
            "fu_only": round(sp(q_b, q_a), 5), "fu_and_ue": round(sp(q_b, q_both), 5)},
        "domain_order": {"canonical": base["domain_order"],
                         "fu_only": adj["domain_order"],
                         "fu_and_ue": both["domain_order"]},
    }

    res["verdict"] = {
        "same_family_as_dsir_length_confounded": True,
        "same_mechanism_as_dsir": False,
        "dsir_mechanism": "extensive quantity / 量纲错误（按 token 求和），除以 N 为精确还原",
        "frac_unique_mechanism": "intensive ratio / Heaps 定律下的有限样本估计量偏倚",
        "dsir_style_fix_applicable": False,
        "correct_same_family_fix": "Heaps 残差化（log V - β̂ log N），非除以 N",
        "entropy_is_at_least_as_length_dependent": bool(
            abs(sp(ue, logN)) >= abs(sp(fu, logN))),
    }

    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()

"""检验假设：dsir_books/wiki/math 是"按 token 求和"的对数似然比，因而被文档长度主导。

若成立，则三者互相关 0.999、与 word_count 相关 -0.93、量级达 1e6 都是长度效应的产物，
正确预处理是先做逐 token 归一化（除以词数），而非先裁定方向。这是机械可判的问题。

检验：
  1) 原始 dsir 与 word_count 的相关（Pearson / Spearman，对数尺度）
  2) 逐 token 化后 dsir_pt = dsir / word_count 的三者互相关是否解耦
  3) 逐 token 化后与 word_count 的残余相关
  4) 逐 token 化后与 fineweb_edu 的相关方向（是否变为可解释的质量信号）
  5) 逐 token 化后的域序是否变化

输出：workspace/data/q1_probe_dsir_length.json
"""
from __future__ import annotations

import json

import numpy as np

import q1_features as qf
from probe_q1_quality import huber_mean, auc_from_scores

OUT = qf.ROOT / "workspace/data/q1_probe_dsir_length.json"
DSIR = ["dsir_books", "dsir_wiki", "dsir_math"]


def sp(a: np.ndarray, b: np.ndarray) -> float:
    ra = np.argsort(np.argsort(a)); rb = np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


def main() -> None:
    X, dom, meta = qf.load_all()
    cols, names = meta["columns"], meta["domains"]
    gi = {c: cols.index(c) for c in cols}
    wc = X[:, gi["rps_doc_word_count"]]
    ns = X[:, gi["rps_doc_num_sentences"]]
    edu = X[:, gi["fineweb_edu"]]
    D = {c: X[:, gi[c]] for c in DSIR}
    Dpt = {c: D[c] / np.maximum(wc, 1.0) for c in DSIR}

    res = {"schema_version": 1, "n_rows": int(X.shape[0]), "domains": names}

    res["raw"] = {
        "pearson_dsir_vs_word_count": {c: round(float(np.corrcoef(D[c], wc)[0, 1]), 4) for c in DSIR},
        "spearman_dsir_vs_word_count": {c: round(sp(D[c], wc), 4) for c in DSIR},
        "pearson_log_neg_dsir_vs_log_wc": {
            c: round(float(np.corrcoef(np.log(-D[c] + 1e-9), np.log(wc))[0, 1]), 4) for c in DSIR},
        "mutual_corr": {f"{a}~{b}": round(float(np.corrcoef(D[a], D[b])[0, 1]), 5)
                        for i, a in enumerate(DSIR) for b in DSIR[i + 1:]},
        "spearman_vs_fineweb_edu": {c: round(sp(D[c], edu), 4) for c in DSIR},
        "magnitude": {c: {"min": round(float(D[c].min()), 1),
                          "p50": round(float(np.median(D[c])), 1),
                          "max": round(float(D[c].max()), 2)} for c in DSIR},
        "ratio_dsir_over_wordcount_stability": {
            c: {"p05": round(float(np.quantile(Dpt[c], .05)), 4),
                "p50": round(float(np.median(Dpt[c])), 4),
                "p95": round(float(np.quantile(Dpt[c], .95)), 4)} for c in DSIR},
    }

    res["per_token"] = {
        "pearson_dsir_pt_vs_word_count": {c: round(float(np.corrcoef(Dpt[c], wc)[0, 1]), 4) for c in DSIR},
        "spearman_dsir_pt_vs_word_count": {c: round(sp(Dpt[c], wc), 4) for c in DSIR},
        "mutual_corr": {f"{a}~{b}": round(float(np.corrcoef(Dpt[a], Dpt[b])[0, 1]), 5)
                        for i, a in enumerate(DSIR) for b in DSIR[i + 1:]},
        "spearman_vs_fineweb_edu": {c: round(sp(Dpt[c], edu), 4) for c in DSIR},
    }

    # 域序：原始 vs 逐 token（各自按 pooled ecdf 归一化后取 Huber 均值）
    def dom_order(v: np.ndarray) -> dict:
        r = (np.argsort(np.argsort(v)) + 0.5) / len(v)
        dv = np.array([huber_mean(r[dom == d]) for d in range(len(names))])
        o = [names[i] for i in np.argsort(-dv)]
        ia, ig = names.index("arxiv"), names.index("github")
        return {"order": o, "range": round(float(dv.max() - dv.min()), 5),
                "auc_arxiv_vs_github": round(auc_from_scores(r[dom == ia], r[dom == ig]), 4)}

    res["domain_order"] = {
        "raw": {c: dom_order(D[c]) for c in DSIR},
        "per_token": {c: dom_order(Dpt[c]) for c in DSIR},
    }

    # 三者解耦程度：逐 token 后能否区分 books / wiki / math 参照
    res["verdict"] = {
        "raw_mutual_corr_min": round(min(res["raw"]["mutual_corr"].values()), 5),
        "per_token_mutual_corr_min": round(min(res["per_token"]["mutual_corr"].values()), 5),
        "length_domination_confirmed": bool(
            min(abs(v) for v in res["raw"]["spearman_dsir_vs_word_count"].values()) > 0.8),
        "per_token_decouples_the_three": bool(
            min(res["per_token"]["mutual_corr"].values()) < 0.95),
    }

    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()

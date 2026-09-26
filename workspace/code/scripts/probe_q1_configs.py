"""Q1 探针补充：把决策卡的候选配置放在同一组指标上对比。

对比四个配置（均 pooled ecdf 归一化）：
  A  五项 Tier C 全按正向（= 决策卡问题 1 选项 A）
  B  dsir 三列取负，长度类保持正向（选项 B）
  C  dsir 与长度类都取负（选项 C）
  R  dsir 三列合为 1 个代表量（因 r=0.999）并取正；word_count / num_sentences /
     mean_word_length 按非单调处理（sign=0，到中位数距离取反）

判定指标：
  n_contra_*        方向统一后仍强负相关的指标对数 —— 方向表内部一致性
  domain_range/AUC  域级 Q 的可分辨性与域标签还原度
  eff_n_indicators  去冗余后的有效指标数

输出：workspace/data/q1_probe_configs.json
种子：20260924
"""
from __future__ import annotations

import json

import numpy as np

import q1_features as qf
from probe_q1_quality import huber_mean, auc_from_scores

OUT = qf.ROOT / "workspace/data/q1_probe_configs.json"

DSIR = ["dsir_books", "dsir_wiki", "dsir_math"]
LEN3 = ["rps_doc_word_count", "rps_doc_num_sentences", "rps_doc_mean_word_length"]


def collapse_dsir(U: np.ndarray, cols: list[str]) -> tuple[np.ndarray, list[str]]:
    """把互相关 0.999 的 dsir 三列换成 1 个均值列。"""
    ids = [cols.index(c) for c in DSIR]
    keep = [j for j in range(len(cols)) if j not in ids]
    rep = U[:, ids].mean(1, keepdims=True)
    return np.hstack([U[:, keep], rep]), [cols[j] for j in keep] + ["dsir_prose_likeness"]


def contra(U: np.ndarray, cols: list[str]) -> dict:
    C = np.corrcoef(U, rowvar=False)
    n5 = n8 = 0
    worst = []
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            if C[i, j] < -0.5:
                n5 += 1
                if C[i, j] < -0.8:
                    n8 += 1
                worst.append((round(float(C[i, j]), 4), cols[i], cols[j]))
    worst.sort()
    return {"n_pairs_lt_-0.5": n5, "n_pairs_lt_-0.8": n8,
            "worst3": [{"r": r, "a": a, "b": b} for r, a, b in worst[:3]]}


def main() -> None:
    X, dom, meta = qf.load_all()
    cols, names = meta["columns"], meta["domains"]
    ref_mask = np.zeros(X.shape[0], dtype=bool)
    ref_mask[:meta["rows_per_file"]["A1"]] = True
    Z = qf.normalize(X, dom, "pooled", scheme="ecdf", ref_mask=ref_mask)
    trans = json.loads((qf.ROOT / "workspace/data/q1_probe_transferability.json")
                       .read_text(encoding="utf-8"))["per_indicator"]

    ia, ig = names.index("arxiv"), names.index("github")
    configs = {
        "A_all_plus": {"ov": {}, "collapse": False},
        "B_dsir_negative": {"ov": {c: -1 for c in DSIR}, "collapse": False},
        "C_dsir_and_length_negative": {
            "ov": {**{c: -1 for c in DSIR},
                   "rps_doc_word_count": -1, "rps_doc_num_sentences": -1},
            "collapse": False},
        "R_dsir_collapsed_length_nonmonotone": {
            "ov": {c: 0 for c in LEN3}, "collapse": True},
    }

    res = {"schema_version": 1, "seed": qf.SEED, "n_rows": int(X.shape[0]),
           "domains": names, "configs": {}}

    for nm, cfg in configs.items():
        U = qf.apply_direction(Z, cols, tier_c_override=cfg["ov"])
        cc = cols
        if cfg["collapse"]:
            U, cc = collapse_dsir(U, cols)
        q = U.mean(1)
        dv = np.array([huber_mean(q[dom == d]) for d in range(len(names))])
        order = [names[i] for i in np.argsort(-dv)]
        rec = {
            "n_indicator_columns": len(cc),
            "direction_consistency": contra(U, cc),
            "domain_order_best_to_worst": order,
            "domain_huber": {n: round(float(v), 5) for n, v in zip(names, dv)},
            "domain_range": round(float(dv.max() - dv.min()), 6),
            "auc_arxiv_vs_github_of_Q": round(auc_from_scores(q[dom == ia], q[dom == ig]), 4),
            "sample_std": round(float(np.std(q)), 5),
            "book_rank": order.index("book") + 1,
            "wikipedia_rank": order.index("wikipedia") + 1,
            "c4_rank": order.index("c4") + 1,
        }
        res["configs"][nm] = rec

    # 跨域分量：只用可迁移性最好的指标（eta2 阈值扫描）
    cross = {}
    for thr in (0.05, 0.10, 0.15, 0.20):
        sel = [c for c in cols if trans[c]["eta2_domain_explained"] < thr]
        if not sel:
            continue
        U = qf.apply_direction(Z, cols)
        idx = [cols.index(c) for c in sel]
        q = U[:, idx].mean(1)
        dv = np.array([huber_mean(q[dom == d]) for d in range(len(names))])
        order = [names[i] for i in np.argsort(-dv)]
        cross[f"eta2_lt_{thr}"] = {
            "n_indicators": len(sel), "indicators": sel,
            "domain_order_best_to_worst": order,
            "domain_range": round(float(dv.max() - dv.min()), 6),
            "auc_arxiv_vs_github_of_Q": round(
                auc_from_scores(q[dom == ia], q[dom == ig]), 4),
            "max_pair_separation_of_selected": round(
                float(max(trans[c]["max_pair_separation"] for c in sel)), 4),
        }
    res["cross_domain_component_by_transferability"] = cross

    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()

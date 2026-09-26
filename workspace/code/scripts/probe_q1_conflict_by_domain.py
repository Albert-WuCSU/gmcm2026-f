"""四个冲突判据的**域级**冲突率与锚点敏感性，支撑第二张决策卡的判据选择。

首轮实验只出了全局冲突率（CD2 0.0408 / CD1 0.3031 / CD3-5 0.2181 / CD3-3 0.6561），
但判据选择的实质是「该判据能否撑起有内容的成因分析」。故本探针回答：
  1) 各判据的冲突率在 7 个域间是否有差异（有差异才谈得上成因分析）
  2) 各判据对分位锚点 p70/p75/p80 的敏感性（CD1 的 0.25 是固定阈，预期不敏感）
  3) CD2 的冲突样本在哪些指标上「高价值」、哪些上「高污染」（成因的可核验抓手）
  4) 四判据两两之间的重叠度（是否实质是同一子集的不同切法）

不改 CANONICAL，不产生决策。输出 workspace/data/q1_probe_conflict_by_domain.json
种子 20260924。
"""
from __future__ import annotations

import json

import numpy as np

import q1_features as qf

OUT = qf.ROOT / "workspace/data/q1_probe_conflict_by_domain.json"
ANCHORS = (70, 75, 80)


def criteria(U: np.ndarray, V: np.ndarray, P: np.ndarray, a: int) -> dict[str, np.ndarray]:
    qv, qp = np.quantile(V, a / 100), np.quantile(P, a / 100)
    n_hi = (U >= np.quantile(U, a / 100, axis=0)).sum(1)
    n_lo = (U <= np.quantile(U, 1 - a / 100, axis=0)).sum(1)
    mad = np.abs(U - np.median(U, axis=1, keepdims=True)).mean(1)
    return {"CD2": (V > qv) & (P > qp),
            "CD1": mad > 0.25,
            "CD3_ge5": (n_hi >= 5) & (n_lo >= 5),
            "CD3_ge3": (n_hi >= 3) & (n_lo >= 3)}


def main() -> None:
    X, dom, meta = qf.load_all()
    cols_all, names = meta["columns"], meta["domains"]
    ref = np.zeros(X.shape[0], bool)
    ref[:meta["rows_per_file"]["A1"]] = True
    U, cols = qf.build_canonical(X, dom, cols_all, ref_mask=ref)
    poll = set(qf.POLLUTION_COLS)
    v_idx = [j for j, c in enumerate(cols) if c not in poll]
    p_idx = [j for j, c in enumerate(cols) if c in poll]
    V = U[:, v_idx].mean(1)
    P = (1.0 - U[:, p_idx]).mean(1)

    res = {"schema_version": 1, "n_rows": int(X.shape[0]), "domains": names,
           "seed": qf.SEED, "columns": cols,
           "value_columns": [cols[j] for j in v_idx],
           "pollution_columns": [cols[j] for j in p_idx]}

    # 1) + 2) 域级冲突率 × 锚点
    by_anchor = {}
    for a in ANCHORS:
        cr = criteria(U, V, P, a)
        by_anchor[f"p{a}"] = {
            k: {"overall": float(m.mean()),
                "by_domain": {names[d]: float(m[dom == d].mean()) for d in range(len(names))},
                "domain_spread": float(max(m[dom == d].mean() for d in range(len(names)))
                                       - min(m[dom == d].mean() for d in range(len(names)))),
                "n_conflict": int(m.sum())}
            for k, m in cr.items()}
    res["by_anchor"] = by_anchor

    res["anchor_sensitivity"] = {
        k: {"rates": [by_anchor[f"p{a}"][k]["overall"] for a in ANCHORS],
            "range": float(max(by_anchor[f"p{a}"][k]["overall"] for a in ANCHORS)
                           - min(by_anchor[f"p{a}"][k]["overall"] for a in ANCHORS)),
            "responds_to_anchor": bool(
                max(by_anchor[f"p{a}"][k]["overall"] for a in ANCHORS)
                - min(by_anchor[f"p{a}"][k]["overall"] for a in ANCHORS) > 1e-9)}
        for k in ("CD2", "CD1", "CD3_ge5", "CD3_ge3")}

    # 3) CD2 冲突样本的指标画像：哪些列最「高」、哪些最「低」
    cr75 = criteria(U, V, P, 75)
    m2 = cr75["CD2"]
    base = U.mean(0)
    prof = U[m2].mean(0) - base
    order = np.argsort(-prof)
    res["CD2_indicator_profile"] = {
        "n_conflict": int(m2.sum()),
        "top5_above_corpus_mean": [{"col": cols[j], "delta": float(prof[j])} for j in order[:5]],
        "top5_below_corpus_mean": [{"col": cols[j], "delta": float(prof[j])} for j in order[-5:]],
        "interpretation": ("delta = 冲突子集均值 − 全体均值。正值大者是这批样本的『高价值』来源，"
                           "负值大者是其『高污染』来源。供论文的成因分析作可核验抓手。")}

    # 4) 四判据两两 Jaccard 重叠
    keys = ["CD2", "CD1", "CD3_ge5", "CD3_ge3"]
    res["pairwise_jaccard_p75"] = {
        f"{a}~{b}": float((cr75[a] & cr75[b]).sum() / max((cr75[a] | cr75[b]).sum(), 1))
        for i, a in enumerate(keys) for b in keys[i + 1:]}

    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT)
    print("\n域级冲突率 @p75（域间极差越大 => 越支撑成因分析）:")
    for k in keys:
        d = by_anchor["p75"][k]
        rng = " ".join(f"{names[i][:6]}={d['by_domain'][names[i]]:.3f}"
                       for i in range(len(names)))
        print(f"  {k:9s} 全局{d['overall']:.4f} 极差{d['domain_spread']:.4f} | {rng}")
    print("\n锚点敏感性:")
    for k in keys:
        s = res["anchor_sensitivity"][k]
        print(f"  {k:9s} p70/75/80 = {[round(x, 4) for x in s['rates']]} "
              f"响应锚点={s['responds_to_anchor']}")
    print("\nCD2 冲突样本画像 top3 高 / top3 低:")
    for e in res["CD2_indicator_profile"]["top5_above_corpus_mean"][:3]:
        print(f"  + {e['col']:45s} {e['delta']:+.4f}")
    for e in res["CD2_indicator_profile"]["top5_below_corpus_mean"][:3]:
        print(f"  - {e['col']:45s} {e['delta']:+.4f}")
    print("\n两两 Jaccard @p75:", {k: round(v, 3) for k, v
                                  in res["pairwise_jaccard_p75"].items()})


if __name__ == "__main__":
    main()

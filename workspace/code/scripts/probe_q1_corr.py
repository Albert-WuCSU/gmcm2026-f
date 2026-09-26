"""Q1 探针补充：相关结构诊断 + 熵权对归一化方案的依赖。

回答两个具体问题：
  1) 哪些指标对近乎共线（|r|>0.9），22 指标的自然分组是什么
  2) 熵权法的权重离散度是否只是归一化方案的产物
输出：workspace/data/q1_probe_corr.json
"""
from __future__ import annotations

import json

import numpy as np

import q1_features as qf
from probe_q1_quality import entropy_weights

OUT = qf.ROOT / "workspace/data/q1_probe_corr.json"


def main() -> None:
    X, dom, meta = qf.load_all()
    cols = meta["columns"]
    ref_mask = np.zeros(X.shape[0], dtype=bool)
    ref_mask[:meta["rows_per_file"]["A1"]] = True

    res = {"columns": cols}

    for scheme in ("ecdf", "winsor_minmax"):
        Z = qf.normalize(X, dom, "pooled", scheme=scheme, ref_mask=ref_mask)
        U = qf.apply_direction(Z, cols)
        C = np.corrcoef(U, rowvar=False)
        pairs = []
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                if abs(C[i, j]) > 0.7:
                    pairs.append({"a": cols[i], "b": cols[j],
                                  "r": round(float(C[i, j]), 4)})
        pairs.sort(key=lambda p: -abs(p["r"]))
        w = entropy_weights(U)
        res[scheme] = {
            "high_corr_pairs": pairs,
            "entropy_weights": {c: round(float(x), 5) for c, x in zip(cols, w)},
            "entropy_weight_ratio_max_min": round(float(w.max() / w.min()), 3),
            "entropy_weight_max_over_equal": round(float(w.max() * len(cols)), 3),
            "top3_weight_mass": round(float(np.sort(w)[::-1][:3].sum()), 4),
            "top3_columns": [cols[i] for i in np.argsort(w)[::-1][:3]],
        }

        # 层次式分组：以 1-|r| 为距离做单连接聚类，看自然块
        D = 1.0 - np.abs(C)
        assign = list(range(len(cols)))
        merges = []
        # 简单单连接：反复合并最近的两个簇
        clusters = {i: [i] for i in range(len(cols))}
        while len(clusters) > 1:
            best, bi, bj = 1e9, None, None
            keys = list(clusters)
            for a in range(len(keys)):
                for b in range(a + 1, len(keys)):
                    ka, kb = keys[a], keys[b]
                    dd = min(D[p, q] for p in clusters[ka] for q in clusters[kb])
                    if dd < best:
                        best, bi, bj = dd, ka, kb
            if best > 0.5:      # |r|<0.5 即停，保留自然块
                break
            merges.append({"dist": round(float(best), 4),
                           "members": [cols[i] for i in clusters[bi] + clusters[bj]]})
            clusters[bi] = clusters[bi] + clusters[bj]
            del clusters[bj]
        res[scheme]["natural_blocks_absr_ge_0.5"] = [
            [cols[i] for i in v] for v in clusters.values() if len(v) > 1]
        res[scheme]["singletons"] = [cols[v[0]] for v in clusters.values() if len(v) == 1]

    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()

"""Q1 探针补充：逐指标的跨域可迁移性。

domain_confound.json 只给了 arxiv-vs-github 一对。本脚本在全部 7 个质量域上度量
每个指标被"域"解释的程度，用于判断哪些指标可以合法地做跨域比较。

两个度量（均在 pooled ecdf 归一化、方向统一后的值上计算）：
  eta2          : 域解释的方差占比（组间方差 / 总方差），越小越可跨域比较
  max_pair_sep  : 21 个域对中 |AUC-0.5| 的最大值，越小越可跨域比较

输出：workspace/data/q1_probe_transferability.json
种子：20260924
"""
from __future__ import annotations

import itertools
import json

import numpy as np

import q1_features as qf
from probe_q1_quality import auc_from_scores

OUT = qf.ROOT / "workspace/data/q1_probe_transferability.json"
RNG = np.random.default_rng(qf.SEED)
CAP = 4000   # 每域参与 AUC 计算的最大样本数，避免 O(n^2) 排序开销


def main() -> None:
    X, dom, meta = qf.load_all()
    cols, names = meta["columns"], meta["domains"]
    ref_mask = np.zeros(X.shape[0], dtype=bool)
    ref_mask[:meta["rows_per_file"]["A1"]] = True

    Z = qf.normalize(X, dom, "pooled", scheme="ecdf", ref_mask=ref_mask)
    U = qf.apply_direction(Z, cols)

    # 每域抽样（分层，固定种子），用于域对 AUC
    sub = {}
    for d in range(len(names)):
        idx = np.where(dom == d)[0]
        if len(idx) > CAP:
            idx = RNG.choice(idx, CAP, replace=False)
        sub[d] = idx

    out = {}
    for j, c in enumerate(cols):
        v = U[:, j]
        grand = v.mean()
        ssb = sum((dom == d).sum() * (v[dom == d].mean() - grand) ** 2
                  for d in range(len(names)))
        sst = float(((v - grand) ** 2).sum())
        eta2 = float(ssb / sst) if sst > 0 else 0.0

        seps = []
        for a, b in itertools.combinations(range(len(names)), 2):
            auc = auc_from_scores(v[sub[a]], v[sub[b]])
            seps.append(abs(auc - 0.5))
        out[c] = {
            "tier": qf.DIRECTION[c][1],
            "group": "pollution" if c in qf.POLLUTION_COLS else "value",
            "eta2_domain_explained": round(eta2, 5),
            "max_pair_separation": round(float(max(seps)), 4),
            "median_pair_separation": round(float(np.median(seps)), 4),
        }

    order = sorted(out, key=lambda c: out[c]["eta2_domain_explained"])
    res = {
        "schema_version": 1, "seed": qf.SEED, "n_rows": int(X.shape[0]),
        "domains": names, "per_domain_cap_for_auc": CAP,
        "normalization": "pooled ecdf + direction unified",
        "per_indicator": out,
        "ranked_by_eta2_ascending": order,
        "group_means": {
            g: {
                "eta2": round(float(np.mean([out[c]["eta2_domain_explained"]
                                             for c in out if out[c]["group"] == g])), 5),
                "max_pair_sep": round(float(np.mean([out[c]["max_pair_separation"]
                                                     for c in out if out[c]["group"] == g])), 4),
                "n": sum(1 for c in out if out[c]["group"] == g),
            } for g in ("pollution", "value")},
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()

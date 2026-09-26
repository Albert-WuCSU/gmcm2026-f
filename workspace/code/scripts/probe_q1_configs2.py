"""Q1 探针补充：在 dsir 逐 token 归一化后重评配置。

已证实 dsir_* 是按 token 求和的对数似然比（log(-dsir) ~ log(word_count) 相关 0.937），
故先除以词数再参与评价。本脚本比较：

  A     原始 dsir，全部 Tier C 取正（决策卡选项 A）
  R     原始 dsir 三合一 + 长度类非单调（前一轮的 R）
  PT    dsir 逐 token 化 + 三合一取正 + 长度类非单调   ← 正确预处理下的配置
  PT_no_nm  dsir 逐 token 化 + 三合一取正，长度类仍取正（隔离"非单调处理"的贡献）

输出：workspace/data/q1_probe_configs2.json
"""
from __future__ import annotations

import json

import numpy as np

import q1_features as qf
from probe_q1_quality import huber_mean, auc_from_scores
from probe_q1_configs import collapse_dsir, contra, DSIR, LEN3

OUT = qf.ROOT / "workspace/data/q1_probe_configs2.json"


def main() -> None:
    X, dom, meta = qf.load_all()
    cols, names = meta["columns"], meta["domains"]
    ref_mask = np.zeros(X.shape[0], dtype=bool)
    ref_mask[:meta["rows_per_file"]["A1"]] = True
    wc = X[:, cols.index("rps_doc_word_count")]

    Xpt = X.copy()
    for c in DSIR:
        Xpt[:, cols.index(c)] = X[:, cols.index(c)] / np.maximum(wc, 1.0)

    ia, ig = names.index("arxiv"), names.index("github")
    res = {"schema_version": 1, "n_rows": int(X.shape[0]), "domains": names,
           "dsir_preprocessing_note":
               "PT* 配置先做 dsir/word_count 逐 token 归一化；证据见 q1_probe_dsir_length.json",
           "configs": {}}

    specs = {
        "A_raw_all_plus": (X, {}, False),
        "R_raw_collapsed_nonmono": (X, {c: 0 for c in LEN3}, True),
        "PT_pertoken_collapsed_nonmono": (Xpt, {c: 0 for c in LEN3}, True),
        "PT_pertoken_collapsed_len_plus": (Xpt, {}, True),
    }

    for nm, (Xu, ov, coll) in specs.items():
        Z = qf.normalize(Xu, dom, "pooled", scheme="ecdf", ref_mask=ref_mask)
        U = qf.apply_direction(Z, cols, tier_c_override=ov)
        cc = cols
        if coll:
            U, cc = collapse_dsir(U, cols)
        q = U.mean(1)
        dv = np.array([huber_mean(q[dom == d]) for d in range(len(names))])
        order = [names[i] for i in np.argsort(-dv)]
        res["configs"][nm] = {
            "n_indicator_columns": len(cc),
            "direction_consistency": contra(U, cc),
            "domain_order_best_to_worst": order,
            "domain_huber": {n: round(float(v), 5) for n, v in zip(names, dv)},
            "domain_range": round(float(dv.max() - dv.min()), 6),
            "auc_arxiv_vs_github_of_Q": round(auc_from_scores(q[dom == ia], q[dom == ig]), 4),
            "ranks": {d: order.index(d) + 1 for d in names},
        }

    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()

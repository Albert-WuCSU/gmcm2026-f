"""CANONICAL 变更的范围内一致性核验（AGENTS.md: Change Impact and Auditing）。

核验两件事：
  1) q1_features.build_canonical() 复现探针 PT 配置的数值
     （强矛盾对 0 / 域间极差 0.1757 / AUC 0.9741）
  2) PRE_DECISION_OVERRIDE 能复现决策前配置 A 的数值
     （强矛盾对 10 / 域间极差 0.1532 / AUC 0.9838）
若不一致则报错退出，避免带着漂移的规格进入 G3。

输出：workspace/data/q1_canonical_verification.json
"""
from __future__ import annotations

import json

import numpy as np

import q1_features as qf
from probe_q1_quality import huber_mean, auc_from_scores

OUT = qf.ROOT / "workspace/data/q1_canonical_verification.json"
TOL = 5e-4

EXPECTED = {
    "canonical_PT": {"n_cols": 20, "n_contra_lt_08": 0,
                     "domain_range": 0.1757, "auc": 0.9741},
    "pre_decision_A": {"n_cols": 22, "n_contra_lt_08": 10,
                       "domain_range": 0.1532, "auc": 0.9838},
}


def measure(U: np.ndarray, cols: list[str], dom, names) -> dict:
    C = np.corrcoef(U, rowvar=False)
    n8 = sum(1 for i in range(len(cols)) for j in range(i + 1, len(cols))
             if C[i, j] < -0.8)
    q = U.mean(1)
    dv = np.array([huber_mean(q[dom == d]) for d in range(len(names))])
    ia, ig = names.index("arxiv"), names.index("github")
    return {"n_cols": len(cols), "n_contra_lt_08": n8,
            "domain_range": round(float(dv.max() - dv.min()), 4),
            "auc": round(auc_from_scores(q[dom == ia], q[dom == ig]), 4),
            "domain_order": [names[i] for i in np.argsort(-dv)]}


def main() -> None:
    X, dom, meta = qf.load_all()
    cols, names = meta["columns"], meta["domains"]
    ref_mask = np.zeros(X.shape[0], dtype=bool)
    ref_mask[:meta["rows_per_file"]["A1"]] = True

    got = {}

    U, cc = qf.build_canonical(X, dom, cols, ref_mask=ref_mask)
    got["canonical_PT"] = measure(U, cc, dom, names)

    Z = qf.normalize(X, dom, "pooled", scheme="ecdf", ref_mask=ref_mask)
    Ua = qf.apply_direction(Z, cols, tier_c_override=qf.PRE_DECISION_OVERRIDE)
    got["pre_decision_A"] = measure(Ua, cols, dom, names)

    # 消融臂也须可构造
    Uab, ccab = qf.build_canonical(X, dom, cols, ref_mask=ref_mask,
                                   population="per_domain")
    got["canonical_ablation_per_domain"] = measure(Uab, ccab, dom, names)

    failures = []
    for key, exp in EXPECTED.items():
        g = got[key]
        for k, v in exp.items():
            if isinstance(v, int):
                if g[k] != v:
                    failures.append(f"{key}.{k}: 期望 {v}, 实得 {g[k]}")
            elif abs(g[k] - v) > TOL:
                failures.append(f"{key}.{k}: 期望 {v}, 实得 {g[k]} (容差 {TOL})")

    res = {"schema_version": 1, "n_rows": int(X.shape[0]),
           "canonical_spec": qf.CANONICAL, "expected": EXPECTED,
           "measured": got, "failures": failures,
           "verdict": "PASS" if not failures else "FAIL"}
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")

    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "domain_order"}
                      for k, v in got.items()}, ensure_ascii=False, indent=1))
    print("canonical 域序:", " > ".join(got["canonical_PT"]["domain_order"]))
    if failures:
        print("FAIL:")
        for f in failures:
            print("  -", f)
        raise SystemExit(1)
    print("一致性核验 PASS ->", OUT)


if __name__ == "__main__":
    main()

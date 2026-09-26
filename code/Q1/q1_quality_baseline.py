"""M0 — 质量侧 usable_baseline（HD-2=B 指定）。

方法：canonical 20 列方向统一后**等权平均**，域级用 Huber 均值（主报）与 10% 截尾均值（对照）
聚合，附 B=400 的 bootstrap 95% 区间。

范围：本脚本只实现 M0。M1 的门控合成在 q1_quality_main.py。
口径：主报 pooled+ecdf；同时跑 per_domain+ecdf 消融臂（决策 q1_normalization_population=A 的附带要求）。

输出：
  results/Q1/experiments/round1/tables/q1a_domain_quality.csv      （M0 行）
  results/Q1/experiments/round1/tables/q1a_ablation_per_domain.csv （M0 行）
  results/Q1/experiments/round1/metrics/q1_quality_M0.json

种子 20260924。
"""
from __future__ import annotations

import time

import numpy as np

import q1_common as C


def equal_weight(U: np.ndarray, w: np.ndarray) -> np.ndarray:
    """加权平均。基准 w = 1/m 即等权（M0 的定义）。"""
    return U @ w


def run_arm(U: np.ndarray, dom: np.ndarray, names: list[str],
            rng: np.random.Generator) -> dict:
    q = equal_weight(U, np.ones(U.shape[1]) / U.shape[1])
    dt = C.domain_table(q, dom, names, rng)
    ia, ig = names.index("arxiv"), names.index("github")
    return {
        "domain": dt,
        "distinguishability": C.distinguishable_pairs(dt, names),
        "degeneracy": C.degeneracy(q),
        "auc_Q_recovering_domain_arxiv_vs_github": C.auc(q[dom == ia], q[dom == ig]),
        "sample_quantiles": {f"p{p}": float(np.quantile(q, p / 100))
                             for p in (1, 5, 25, 50, 75, 95, 99)},
        "_q": q,
    }


def main() -> None:
    t0 = time.time()
    C.ensure_dirs()
    rng = np.random.default_rng(C.SEED)

    arms, cols, dom, names, meta = C.load_quality()
    assert len(cols) == 20, f"canonical 应为 20 列，实得 {len(cols)}"

    res = {
        "schema_version": 1, "method_id": "M0", "role": "usable_baseline",
        "subtasks": ["Q1a", "Q1b"], "seed": C.SEED,
        "definition": "canonical 20 列等权平均；域级 Huber（主报）/10% 截尾（对照）+ bootstrap B=400",
        "columns": cols, "n_rows": int(meta["n_rows"]),
        "rows_skipped_nan": meta["rows_skipped_nan"],
        "baseline_source": "HD-2=B 指定",
    }

    out = {}
    for pop in ("pooled", "per_domain"):
        out[pop] = run_arm(arms[pop], dom, names, rng)

    # 权重扰动（主口径）：±10%、40 次
    res["perturbation_weights"] = C.perturb_weights(
        arms["pooled"], dom, names, equal_weight, rng)

    # 运行时须监测的探针条件
    Cm = np.corrcoef(arms["pooled"], rowvar=False)
    off = Cm[~np.eye(len(cols), dtype=bool)]
    res["probe_monitors"] = {
        "direction_table_internal_consistency": {
            "n_pairs_lt_-0.8": int(sum(1 for i in range(len(cols))
                                       for j in range(i + 1, len(cols)) if Cm[i, j] < -0.8)),
            "n_pairs_lt_-0.5": int(sum(1 for i in range(len(cols))
                                       for j in range(i + 1, len(cols)) if Cm[i, j] < -0.5)),
            "expected_lt_-0.8": 0,
        },
        "indicator_redundancy": {
            "max_abs_offdiag_corr": float(np.abs(off).max()),
            "corr_condition_number": float(np.linalg.cond(Cm)),
        },
        "naive_minmax_not_used": C.qf.CANONICAL["scheme"] == "ecdf",
        "frac_unique_words_uncorrected": True,  # 决策 q1_frac_unique_words_treatment=no_treatment
    }
    n8 = res["probe_monitors"]["direction_table_internal_consistency"]["n_pairs_lt_-0.8"]
    res["warnings"] = [] if n8 == 0 else [f"方向表出现 {n8} 对 r<-0.8，与 canonical 核验不一致"]

    for pop in ("pooled", "per_domain"):
        out[pop].pop("_q")
    res["arms"] = out
    res["execution_time_seconds"] = round(time.time() - t0, 1)

    C.write_json(C.METRICS / "q1_quality_M0.json", res)

    hdr = ["method", "population", "domain", "n", "huber", "trimmed10", "median",
           "ci95_lo", "ci95_hi", "half_width"]
    for pop, fn in (("pooled", "q1a_domain_quality.csv"),
                    ("per_domain", "q1a_ablation_per_domain.csv")):
        rows = [["M0", pop, d, v["n"], round(v["huber"], 6), round(v["trimmed10"], 6),
                 round(v["median"], 6), round(v["ci95_lo"], 6), round(v["ci95_hi"], 6),
                 round(v["half_width"], 6)]
                for d, v in out[pop]["domain"]["per_domain"].items()]
        C.write_csv(C.TABLES / fn, hdr, rows)

    p = out["pooled"]
    print(f"M0 完成 {res['execution_time_seconds']}s")
    print("  域序:", " > ".join(p["domain"]["order_best_to_worst"]))
    print(f"  域间极差 {p['domain']['domain_range']:.4f} | "
          f"可分辨域对 {p['distinguishability']['n_pairs_distinguishable']}/21 | "
          f"AUC {p['auc_Q_recovering_domain_arxiv_vs_github']:.4f}")
    print(f"  消融臂 per_domain 极差 {out['per_domain']['domain']['domain_range']:.4f} | "
          f"AUC {out['per_domain']['auc_Q_recovering_domain_arxiv_vs_github']:.4f}")
    if res["warnings"]:
        print("  WARN:", res["warnings"])


if __name__ == "__main__":
    main()

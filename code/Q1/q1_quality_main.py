"""M1 — 质量侧 main_candidate。

方法：语义分组 V/P + **门控合成 Q = V·(1−P)**。
  V = 价值组 14 列均值（canonical 20 列口径；探针里的 16 列是 22 列口径）
  P = 污染组 6 列的污染度均值 = mean(1 − U[:, P列])
  差值式 Q = V − P **已据证据排除，本脚本不实现**（跨零使 CV=1.44e6；负 Q 与 Q3 的
  g(Q)=γQ^4、γe^{6Q} 不相容）。

Q1b 冲突判据：**一律分位数锚定**，四候选全算 × 三分位锚点（p70/p75/p80），
  落表供首轮实验后的第二张决策卡。绝对阈版（0.75 硬阈）冲突率恰为 0.0，不实现。

V/P 分组是**语义划分**，不得声称由相关结构导出（组内相关 0.051/0.026 与组间 0.016 同量级）；
本脚本据此输出组内/组间平均相关供论文的语义论证。

输出：
  tables/q1a_domain_quality.csv（追加 M1 行）、tables/q1a_ablation_per_domain.csv（追加）
  tables/q1b_conflict_rates.csv、tables/q1b_conflict_examples.csv
  metrics/q1_quality_M1.json

种子 20260924。
"""
from __future__ import annotations

import time

import numpy as np

import q1_common as C

ANCHORS = (70, 75, 80)


def gated(U: np.ndarray, w: np.ndarray, v_idx: list[int], p_idx: list[int]) -> np.ndarray:
    """门控合成。w 为 20 列权重（扰动用），组内按 w 重新归一化。"""
    wv, wp = w[v_idx], w[p_idx]
    V = U[:, v_idx] @ (wv / wv.sum())
    P = (1.0 - U[:, p_idx]) @ (wp / wp.sum())
    return V * (1.0 - P)


def vp_parts(U: np.ndarray, v_idx: list[int], p_idx: list[int]):
    V = U[:, v_idx].mean(1)
    P = (1.0 - U[:, p_idx]).mean(1)
    return V, P


def conflict_rates(U: np.ndarray, V: np.ndarray, P: np.ndarray) -> dict:
    """判据 × 三个锚点，全部分位数锚定。绝对阈版不实现（冲突率恰为 0.0）。

    决策 q1b_conflict_criterion = CD2@p75 为主报，CD1/CD3 为已声明的敏感性臂。
    CD1 的固定阈 0.25 对锚点零响应（评审 F1），按决策的 required_fix 改为 MAD 自身
    分位数锚定；同时保留固定阈版作对照，以便与首轮及探针数值衔接。
    """
    out = {}
    mad = np.abs(U - np.median(U, axis=1, keepdims=True)).mean(1)
    for a in ANCHORS:
        qv, qp = np.quantile(V, a / 100), np.quantile(P, a / 100)
        n_hi = (U >= np.quantile(U, a / 100, axis=0)).sum(1)
        n_lo = (U <= np.quantile(U, 1 - a / 100, axis=0)).sum(1)
        out[f"p{a}"] = {
            "CD2_high_value_and_high_pollution": float(np.mean((V > qv) & (P > qp))),
            "CD1_indicator_MAD_anchored": float(np.mean(mad > np.quantile(mad, a / 100))),
            "CD1_indicator_MAD_gt_0.25_fixed_ref": float(np.mean(mad > 0.25)),
            "CD3_ge5_high_and_ge5_low": float(np.mean((n_hi >= 5) & (n_lo >= 5))),
            "CD3_ge3_high_and_ge3_low": float(np.mean((n_hi >= 3) & (n_lo >= 3))),
        }
    return out


def conflict_examples(U: np.ndarray, cols: list[str], V: np.ndarray, P: np.ndarray,
                      dom: np.ndarray, names: list[str], meta: dict,
                      per_domain: int = 3) -> list[list]:
    """每域取 CD2(p75) 下 V·P 乘积最高的若干条，落可回溯的行定位与指标值。

    行定位：load_all() 的流式顺序为 A1 -> A2 -> A3，故 (file, row_in_file) 可复现定位。
    AI 不对冲突成因作物理解释，只落可核验的取值。
    """
    qv, qp = np.quantile(V, 0.75), np.quantile(P, 0.75)
    mask = (V > qv) & (P > qp)
    rpf = meta["rows_per_file"]
    bounds = [("A1", 0, rpf["A1"]),
              ("A2", rpf["A1"], rpf["A1"] + rpf["A2"]),
              ("A3", rpf["A1"] + rpf["A2"], rpf["A1"] + rpf["A2"] + rpf["A3"])]

    def locate(i: int) -> tuple[str, int]:
        for tag, lo, hi in bounds:
            if lo <= i < hi:
                return tag, i - lo
        return "?", i

    rows = []
    for d, nm in enumerate(names):
        idx = np.flatnonzero(mask & (dom == d))
        if len(idx) == 0:
            continue
        for i in idx[np.argsort(-(V[idx] * P[idx]))[:per_domain]]:
            tag, off = locate(int(i))
            rows.append([nm, tag, off, int(i), round(float(V[i]), 5), round(float(P[i]), 5)]
                        + [round(float(U[i, j]), 5) for j in range(len(cols))])
    return rows


def run_arm(U: np.ndarray, cols: list[str], dom: np.ndarray, names: list[str],
            v_idx: list[int], p_idx: list[int], rng: np.random.Generator) -> dict:
    q = gated(U, np.ones(U.shape[1]), v_idx, p_idx)
    V, P = vp_parts(U, v_idx, p_idx)
    dt = C.domain_table(q, dom, names, rng)
    ia, ig = names.index("arxiv"), names.index("github")
    return {
        "domain": dt,
        "distinguishability": C.distinguishable_pairs(dt, names),
        "degeneracy": C.degeneracy(q),
        "auc_Q_recovering_domain_arxiv_vs_github": C.auc(q[dom == ia], q[dom == ig]),
        "V_summary": {"mean": float(V.mean()), "std": float(V.std()),
                      "p75": float(np.quantile(V, .75))},
        "P_summary": {"mean": float(P.mean()), "std": float(P.std()),
                      "p75": float(np.quantile(P, .75))},
        "corr_V_vs_P": float(np.corrcoef(V, P)[0, 1]),
        "conflict_rates": conflict_rates(U, V, P),
        "_q": q, "_V": V, "_P": P,
    }


def group_cohesion(U: np.ndarray, v_idx: list[int], p_idx: list[int]) -> dict:
    """组内/组间平均相关。CONDITIONAL 项：分组不具相关内聚性，须以语义论证。"""
    Cm = np.corrcoef(U, rowvar=False)

    def mean_pairs(a, b, same):
        vals = [Cm[i, j] for i in a for j in b if (i < j if same else True)]
        return float(np.mean(vals)) if vals else float("nan")

    return {"within_value": mean_pairs(v_idx, v_idx, True),
            "within_pollution": mean_pairs(p_idx, p_idx, True),
            "between": mean_pairs(v_idx, p_idx, False),
            "interpretation": "组内与组间同量级 => 分组为语义划分，不得声称由相关结构导出"}


def main() -> None:
    t0 = time.time()
    C.ensure_dirs()
    rng = np.random.default_rng(C.SEED)

    arms, cols, dom, names, meta = C.load_quality()
    assert len(cols) == 20, f"canonical 应为 20 列，实得 {len(cols)}"
    v_idx, p_idx = C.vp_split(cols)

    res = {
        "schema_version": 1, "method_id": "M1", "role": "main_candidate",
        "subtasks": ["Q1a", "Q1b"], "seed": C.SEED,
        "definition": "语义分组 V/P + 门控合成 Q = V·(1-P)；冲突判据分位数锚定",
        "columns": cols, "n_rows": int(meta["n_rows"]),
        "value_columns": [cols[j] for j in v_idx],
        "pollution_columns": [cols[j] for j in p_idx],
        "excluded_variant": {
            "form": "Q = V - P",
            "reason": "跨零使 CV=1.44e6、基尼 8.17e5；负 Q 与 Q3 的 γQ^4、γe^{6Q} 不相容",
            "implemented": False},
        "excluded_conflict_criterion": {
            "form": "绝对阈 V>0.75 ∧ P>0.75", "reason": "冲突率恰为 0.0（16 列均值 p75 仅 0.567）",
            "implemented": False},
        "conflict_criterion_decision": {
            "decision_id": "q1b_conflict_criterion", "choice": "CD2@p75",
            "primary_key": "CD2_high_value_and_high_pollution", "primary_anchor": "p75",
            "sensitivity_arms": ["CD1_indicator_MAD_anchored", "CD3_ge5_high_and_ge5_low",
                                 "CD3_ge3_high_and_ge3_low"],
            "note": "CD1 已按决策的 required_fix 改为 MAD 分位数锚定；固定阈 0.25 版仅作衔接对照"},
        "claim_scope_decision": {
            "decision_id": "q1a_book_wikipedia_claim_scope", "choice": "report_indistinguishable",
            "prohibited_claim": "不得声称 book 与 wikipedia 的先后方向",
            "scope_limit": "仅限该对；c4~commoncrawl 照常报方向"},
    }

    out = {pop: run_arm(arms[pop], cols, dom, names, v_idx, p_idx, rng)
           for pop in ("pooled", "per_domain")}

    res["group_cohesion"] = group_cohesion(arms["pooled"], v_idx, p_idx)

    # 扰动一：20 列权重 ±10%，40 次
    # gated() 内部按 V/P 组重归一化，故传入权重的整体尺度无影响（不需再乘列数）
    res["perturbation_weights"] = C.perturb_weights(
        arms["pooled"], dom, names, lambda U, w: gated(U, w, v_idx, p_idx), rng)

    # 扰动二：V/P **分组权重** ±10%（探针未测，G3 补测项）
    q_base = out["pooled"]["_q"]
    Vb, Pb = out["pooled"]["_V"], out["pooled"]["_P"]
    hub_base = np.array([C.huber_mean(q_base[dom == d]) for d in range(len(names))])
    rank_base = list(np.argsort(np.argsort(-hub_base)))
    taus, shifts = [], []
    for _ in range(C.PERT_REPS):
        gv, gp = 1.0 + rng.uniform(-C.PERT_FRAC, C.PERT_FRAC, 2)
        q = (gv * Vb) * (1.0 - gp * Pb)
        hub = np.array([C.huber_mean(q[dom == d]) for d in range(len(names))])
        rank = list(np.argsort(np.argsort(-hub)))
        taus.append(C.kendall_tau(rank_base, rank))
        shifts.append(int(np.max(np.abs(np.array(rank_base) - np.array(rank)))))
    res["perturbation_group_weights"] = {
        "perturbation": f"Q = (gv·V)·(1 - gp·P)，gv/gp ~ U(0.9,1.1)，reps={C.PERT_REPS}",
        "domain_rank_kendall_tau_mean": float(np.mean(taus)),
        "domain_rank_kendall_tau_min": float(np.min(taus)),
        "domain_rank_max_position_change_max": int(max(shifts)),
        "note": ("探针未测项，按代码计划 §4.6 在 G3 补测。"
                 "**口径说明**：gv 是全局乘子，对 Q 是严格单调变换，域序恒不变；"
                 "故本项实质只检验 gp 的敏感性，不可解读为『V 权重也不敏感』。"
                 "V 组内各列权重的敏感性由上一项 perturbation_weights（20 列 ±10%）覆盖。"),
        "effective_factor": "gp only"}

    # 扰动三：冲突判据的分位锚点敏感性（已含在 conflict_rates 的三锚点中）
    res["conflict_anchor_sensitivity"] = out["pooled"]["conflict_rates"]

    # fallback 触发条件评估
    Cm = np.corrcoef(arms["pooled"], rowvar=False)
    n8 = int(sum(1 for i in range(len(cols)) for j in range(i + 1, len(cols))
                 if Cm[i, j] < -0.8))
    cd2 = out["pooled"]["conflict_rates"]["p75"]["CD2_high_value_and_high_pollution"]
    cond1 = n8 >= 3
    cond2 = not (0.01 < cd2 < 0.50)
    res["fallback_trigger"] = {
        "fallback_id": "M2",
        "condition": "n_pairs_lt_-0.8 >= 3 OR M1 conflict_rate outside (0.01, 0.50)",
        "observed": bool(cond1 or cond2),
        "evidence": {"n_pairs_lt_-0.8": n8, "condition1_triggered": bool(cond1),
                     "conflict_rate_CD2_p75": cd2, "condition2_triggered": bool(cond2)},
        "action": ("未触发，M2 保持休眠" if not (cond1 or cond2)
                   else "已触发：须提交使用者决定是否激活 M2；AI 不得自行激活"),
    }
    res["warnings"] = ([] if not (cond1 or cond2)
                       else ["fallback 触发条件成立，须人工裁定"])

    # 冲突样本（可回溯）
    ex_rows = conflict_examples(arms["pooled"], cols, Vb, Pb, dom, names, meta)
    C.write_csv(C.TABLES / "q1b_conflict_examples.csv",
                ["domain", "source_file", "row_in_file", "row_in_stream", "V", "P"] + cols,
                ex_rows)

    # 冲突率表：四判据 × 三锚点 × 两口径
    crows = []
    for pop in ("pooled", "per_domain"):
        for a, d in out[pop]["conflict_rates"].items():
            for crit, rate in d.items():
                crows.append([pop, a, crit, round(rate, 6),
                              "OK" if 0.0 < rate < 1.0 else "DEGENERATE"])
    C.write_csv(C.TABLES / "q1b_conflict_rates.csv",
                ["population", "anchor", "criterion", "conflict_rate", "non_degeneracy"], crows)

    # 域级表：追加 M1 行到 M0 已建的表
    hdr = ["method", "population", "domain", "n", "huber", "trimmed10", "median",
           "ci95_lo", "ci95_hi", "half_width"]
    for pop, fn in (("pooled", "q1a_domain_quality.csv"),
                    ("per_domain", "q1a_ablation_per_domain.csv")):
        path = C.TABLES / fn
        prev = []
        if path.exists():
            import csv as _csv
            with open(path, newline="", encoding="utf-8-sig") as f:
                r = list(_csv.reader(f))
            prev = [row for row in r[1:] if row and row[0] != "M1"]
        rows = prev + [["M1", pop, d, v["n"], round(v["huber"], 6), round(v["trimmed10"], 6),
                        round(v["median"], 6), round(v["ci95_lo"], 6), round(v["ci95_hi"], 6),
                        round(v["half_width"], 6)]
                       for d, v in out[pop]["domain"]["per_domain"].items()]
        C.write_csv(path, hdr, rows)

    for pop in ("pooled", "per_domain"):
        for k in ("_q", "_V", "_P"):
            out[pop].pop(k)
    res["arms"] = out
    res["execution_time_seconds"] = round(time.time() - t0, 1)
    C.write_json(C.METRICS / "q1_quality_M1.json", res)

    p = out["pooled"]
    print(f"M1 完成 {res['execution_time_seconds']}s")
    print("  域序:", " > ".join(p["domain"]["order_best_to_worst"]))
    print(f"  域间极差 {p['domain']['domain_range']:.4f} | "
          f"可分辨域对 {p['distinguishability']['n_pairs_distinguishable']}/21 | "
          f"AUC {p['auc_Q_recovering_domain_arxiv_vs_github']:.4f}")
    print(f"  corr(V,P) {p['corr_V_vs_P']:.4f} | CD2@p75 冲突率 {cd2:.4f}")
    print(f"  fallback 触发: {res['fallback_trigger']['observed']} "
          f"(r<-0.8 对数={n8}) -> {res['fallback_trigger']['action']}")
    print(f"  冲突样本落盘 {len(ex_rows)} 条")


if __name__ == "__main__":
    main()

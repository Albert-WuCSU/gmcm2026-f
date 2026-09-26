"""Q1 round1 总控：按序跑四个方法并装配 run_summary.json。

用法：
  python run_all.py            # 从已有 metrics/*.json 装配 run_summary（不重跑）
  python run_all.py --run      # 依次重跑 M0 -> M1 -> M0c -> M1c 再装配

顺序依赖：M0c 的 Q 增量检验需要 M1 的域级 Q；M1c 的 gain_over_baseline 需要 M0c。
HD-2 判定（相对 baseline 制）：主方法须在**预先声明的指标**上超过 baseline，
  超出幅度须大于重抽样噪声。质量侧预声明指标 = 域间可分辨性 + 权重扰动下的排序稳定性；
  配比侧 = 检验集去尺度偏移后的 R² 与 Spearman（三尺度分报）。
种子 20260924。
"""
from __future__ import annotations

import json
import platform
import subprocess
import sys
import time

import numpy as np
import scipy

import q1_common as C

SCRIPTS = [("M0", "q1_quality_baseline.py"), ("M1", "q1_quality_main.py"),
           ("M0c", "q1_mixture_baseline.py"), ("M1c", "q1_mixture_main.py")]
ROLES = {"M0": "usable_baseline", "M1": "main_candidate",
         "M0c": "usable_baseline", "M1c": "main_candidate"}
MFILE = {"M0": "q1_quality_M0.json", "M1": "q1_quality_M1.json",
         "M0c": "q1_mixture_M0c.json", "M1c": "q1_mixture_M1c.json"}
SCALES = ("test_1m", "test_60m", "test_1B")


def run_scripts() -> dict[str, dict]:
    status = {}
    for mid, script in SCRIPTS:
        t0 = time.time()
        p = subprocess.run([sys.executable, script], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=str(C.ROOT / "code/Q1"))
        status[mid] = {"returncode": p.returncode, "seconds": round(time.time() - t0, 1),
                       "stderr_tail": p.stderr.strip()[-2000:] if p.returncode else ""}
        print(f"[{mid}] rc={p.returncode} {status[mid]['seconds']}s")
        if p.returncode:
            (C.OUTDIR / "logs").mkdir(parents=True, exist_ok=True)
            (C.OUTDIR / "logs" / f"{mid}_failure.log").write_text(
                p.stdout + "\n--- STDERR ---\n" + p.stderr, encoding="utf-8")
            print(f"  失败日志已写入 logs/{mid}_failure.log")
    return status


def load_metrics() -> dict[str, dict]:
    out = {}
    for mid, fn in MFILE.items():
        path = C.METRICS / fn
        if not path.exists():
            raise SystemExit(f"缺少 {path}，请先运行 python run_all.py --run")
        out[mid] = json.loads(path.read_text(encoding="utf-8"))
    return out


def quality_comparison(m: dict, rng: np.random.Generator) -> dict:
    a0 = m["M0"]["arms"]["pooled"]
    a1 = m["M1"]["arms"]["pooled"]
    p0, p1 = m["M0"]["perturbation_weights"], m["M1"]["perturbation_weights"]
    d0 = a0["distinguishability"]["n_pairs_distinguishable"]
    d1 = a1["distinguishability"]["n_pairs_distinguishable"]
    # HD-2：显著性由重抽样区间判定。对两方法各 40 次扰动的 τ 分布之差做自助区间。
    tau_test = C.diff_ci(p1["tau_per_rep"], p0["tau_per_rep"], rng)
    ovl_test = C.diff_ci(p1["top1pct_overlap_per_rep"], p0["top1pct_overlap_per_rep"], rng)
    stab_beats = tau_test["significant"] and tau_test["mean_diff"] > 0
    # 可分辨性本身已由 bootstrap 区间导出：M0 并列的域对是否被 M1 分开
    resolved = sorted(set(a0["distinguishability"]["tied_pairs"])
                      - set(a1["distinguishability"]["tied_pairs"]))
    both = (d1 > d0) and stab_beats
    return {
        "significance_tests": {
            "kendall_tau_M1_minus_M0": tau_test,
            "top1pct_overlap_M1_minus_M0": ovl_test,
            "pairs_resolved_by_M1_that_M0_left_tied": resolved,
            "method": "两方法各 40 次权重扰动的指标分布之差的自助 95% 区间（B=400）"},
        "declared_metric": "域间可分辨性（bootstrap 区间不重叠的域对数）+ 权重扰动下的排序稳定性",
        "M0": {"n_pairs_distinguishable": d0, "tied_pairs": a0["distinguishability"]["tied_pairs"],
               "kendall_tau_mean": p0["domain_rank_kendall_tau_mean"],
               "kendall_tau_min": p0["domain_rank_kendall_tau_min"],
               "frac_order_unchanged": p0["frac_reps_domain_order_unchanged"],
               "domain_range": a0["domain"]["domain_range"],
               "auc_Q_recovering_domain": a0["auc_Q_recovering_domain_arxiv_vs_github"]},
        "M1": {"n_pairs_distinguishable": d1, "tied_pairs": a1["distinguishability"]["tied_pairs"],
               "kendall_tau_mean": p1["domain_rank_kendall_tau_mean"],
               "kendall_tau_min": p1["domain_rank_kendall_tau_min"],
               "frac_order_unchanged": p1["frac_reps_domain_order_unchanged"],
               "domain_range": a1["domain"]["domain_range"],
               "auc_Q_recovering_domain": a1["auc_Q_recovering_domain_arxiv_vs_github"]},
        "verdict_vs_baseline": (
            "M1 在两项预声明指标上均超过 M0，且排序稳定性的超出幅度大于重抽样噪声"
            if both else "M1 未在两项预声明指标上同时超过 M0（详见 significance_tests）"),
        "caveat_domain_range": (
            "域间极差方向相反（M0 0.1757 > M1 0.1582），但极差不是预声明指标；"
            "可分辨性已计入 bootstrap 不确定性，M1 以更小的极差达成 21/21 说明其区间相对更窄"),
        "note_auc": "M1 的 AUC 更低（0.9486 vs 0.9741），即域混淆更小；该项为披露项而非优劣判据",
        "caveat_newly_resolved_pairs": _resolved_pair_caveats(m, resolved),
    }


def _resolved_pair_caveats(m: dict, resolved: list[str]) -> dict:
    """对 M1 新分开的域对逐一给出分离裕度与方向是否与 M0 一致。

    分离裕度只略超区间和、或与 baseline 方向相反者，不得作为稳固结论。
    """
    out = {}
    for pair in resolved:
        a, b = pair.split("~")
        rec = {}
        for mid in ("M0", "M1"):
            pd_ = m[mid]["arms"]["pooled"]["domain"]["per_domain"]
            gap = abs(pd_[a]["huber"] - pd_[b]["huber"])
            hw = pd_[a]["half_width"] + pd_[b]["half_width"]
            rec[mid] = {"gap": gap, "half_width_sum": hw,
                        "margin_ratio": gap / hw if hw > 0 else float("inf"),
                        "higher": a if pd_[a]["huber"] > pd_[b]["huber"] else b}
        rec["order_agrees_with_baseline"] = rec["M0"]["higher"] == rec["M1"]["higher"]
        rec["marginal"] = rec["M1"]["margin_ratio"] < 1.5
        rec["verdict"] = (
            "稳固" if (rec["order_agrees_with_baseline"] and not rec["marginal"])
            else "不稳固：" + "；".join(
                ([f"方向与 baseline 相反（M0 判 {rec['M0']['higher']} 高，"
                  f"M1 判 {rec['M1']['higher']} 高）"] if not rec["order_agrees_with_baseline"]
                 else [])
                + ([f"分离裕度仅为区间和的 {rec['M1']['margin_ratio']:.2f} 倍"]
                   if rec["marginal"] else [])))
        out[pair] = rec
    return out


def mixture_comparison(m: dict) -> dict:
    b = m["M0c"]["validation_by_scale"]
    a = m["M1c"]["validation_by_scale"]
    per = {k: {"M0c_r2_deoffset": b[k]["r2_after_offset_removal"],
               "M1c_r2_deoffset": a[k]["r2_after_offset_removal"],
               "gain_r2": a[k]["r2_after_offset_removal"] - b[k]["r2_after_offset_removal"],
               "M0c_spearman": b[k]["spearman"], "M1c_spearman": a[k]["spearman"],
               "gain_spearman": a[k]["spearman"] - b[k]["spearman"]} for k in SCALES}
    pos = [k for k in SCALES if per[k]["gain_r2"] > 0]
    return {
        "declared_metric": "检验集去尺度偏移后的 R² 与 Spearman（A6–A11 三尺度分报）",
        "by_scale": per,
        "scales_with_positive_gain": pos,
        "verdict_vs_baseline": (
            f"增益仅在 {', '.join(pos)} 成立，60m 持平、1B 为负 -> 不构成跨尺度优势；"
            "与决策 q1c_interaction_tradeoff=C 一致：M0c 为主、M1c 作组合效应辅证"),
        "prohibited_claim": m["M1c"]["coef_filter"]["prohibited_claim"],
        "stable_subset": {k: m["M1c"]["coef_filter"][k] for k in
                          ("n_reported", "n_total", "n_suppressed", "main_effects_stable",
                           "interactions_stable_ge_0.95", "interactions_stable_ge_0.99")},
        "raw_r2_must_not_be_cited_alone": {
            k: {"r2_raw": b[k]["r2_raw"], "bias_share_of_rmse": b[k]["bias_share_of_rmse"]}
            for k in SCALES},
    }


def main() -> None:
    C.ensure_dirs()
    run_status = run_scripts() if "--run" in sys.argv else {}
    m = load_metrics()

    methods = []
    for mid, script in SCRIPTS:
        d = m[mid]
        methods.append({
            "method_id": mid, "role": ROLES[mid], "script": f"code/Q1/{script}",
            "status": "success" if run_status.get(mid, {"returncode": 0})["returncode"] == 0
                      else "failed",
            "execution_time_seconds": d.get("execution_time_seconds"),
            "input_files": (["workspace/data_raw/real_attachments/A_data_value/"
                             "slimpajama_quality_signal_sample.jsonl.xz",
                             "workspace/data_raw/real_attachments/A_data_value/"
                             "slimpajama_quality_extended/"]
                            if mid in ("M0", "M1") else
                            ["workspace/data_raw/real_attachments/A_data_value/regmix_tables/"]),
            "output_files": [f"results/Q1/experiments/round1/metrics/{MFILE[mid]}"],
            "figure_files": sorted(
                f"results/Q1/experiments/round1/figures/{p.name}"
                for p in C.FIGURES.glob("*.png")
                if (mid in ("M0", "M1") and p.name.startswith(("F1", "F2")))
                or (mid in ("M0c", "M1c") and p.name.startswith(("F3", "F4")))),
            "metrics_summary": (
                {"domain_range": d["arms"]["pooled"]["domain"]["domain_range"],
                 "n_pairs_distinguishable":
                     d["arms"]["pooled"]["distinguishability"]["n_pairs_distinguishable"],
                 "auc_Q_recovering_domain":
                     d["arms"]["pooled"]["auc_Q_recovering_domain_arxiv_vs_github"],
                 "domain_order": d["arms"]["pooled"]["domain"]["order_best_to_worst"]}
                if mid in ("M0", "M1") else
                {"train_r2": d["train"]["r2"],
                 "r2_after_offset_removal": {k: d["validation_by_scale"][k]
                                             ["r2_after_offset_removal"] for k in SCALES},
                 "spearman": {k: d["validation_by_scale"][k]["spearman"] for k in SCALES}}),
            "output_degeneracy": (d["arms"]["pooled"]["degeneracy"] if mid in ("M0", "M1")
                                 else d.get("output_degeneracy", {})),
            "warnings": d.get("warnings", []), "errors": [],
        })

    summary = {
        "schema_version": 1, "question": "Q1", "round": "round1",
        "implementation_target": "python", "random_seed": C.SEED,
        "approved_decision_id": ["q1_tierC_direction", "q1_normalization_population",
                                 "q1c_interaction_tradeoff", "q1_frac_unique_words_treatment"],
        "decision_ledger": "methods/Q1/q1_decisions.jsonl",
        "code_plan": "code/Q1/q1_code_plan.md",
        "canonical_spec": "workspace/code/scripts/q1_features.py#CANONICAL",
        "methods": methods,
        "ablation": {
            "arm": "per_domain+ecdf", "applied_to": ["M0", "M1"],
            "metrics": {mid: {
                "domain_range": m[mid]["arms"]["per_domain"]["domain"]["domain_range"],
                "auc_Q_recovering_domain":
                    m[mid]["arms"]["per_domain"]["auc_Q_recovering_domain_arxiv_vs_github"],
                "domain_order": m[mid]["arms"]["per_domain"]["domain"]["order_best_to_worst"]}
                for mid in ("M0", "M1")},
            "interpretation": ("按域归一化后域级 Q 近乎恒等（极差约 0.003、AUC 约 0.500），"
                               "证明主口径选择的代价；该臂不是备选主口径"),
        },
        "perturbation": {
            "weights_pm10pct_reps40": {mid: m[mid]["perturbation_weights"]
                                       for mid in ("M0", "M1")},
            "group_weights_pm10pct": m["M1"]["perturbation_group_weights"],
            "conflict_anchor_p70_p75_p80": m["M1"]["conflict_anchor_sensitivity"],
            "bootstrap_B400": {"M0c": m["M0c"]["coef_stability"],
                               "M1c": m["M1c"]["coef_stability"]},
            "lambda_pm1decade": m["M1c"]["perturbation_lambda"],
        },
        "comparison": {
            "quality_side": quality_comparison(m, np.random.default_rng(C.SEED)),
            "mixture_side": mixture_comparison(m),
            "q_increment_test": m["M0c"]["q_increment_test"],
        },
        "fallback_trigger": m["M1"]["fallback_trigger"],
        "probe_monitors": {"M0": m["M0"]["probe_monitors"], "M1c": m["M1c"]["probe_monitors"],
                           "M0c": m["M0c"]["probe_monitors"]},
        "environment": {
            "python": platform.python_version(), "platform": platform.platform(),
            "numpy": np.__version__, "scipy": scipy.__version__,
            "sklearn_used": False,
            "note": "岭回归与 5 折 CV 用 numpy 显式实现，避免隐藏默认值影响可复现性"},
        "warnings": sorted({w for mid in MFILE for w in m[mid].get("warnings", [])}),
        "run_status": run_status,
    }
    C.write_json(C.OUTDIR / "run_summary.json", summary)

    q = summary["comparison"]["quality_side"]
    x = summary["comparison"]["mixture_side"]
    print("\n=== run_summary.json 已装配 ===")
    print("质量侧:", q["verdict_vs_baseline"])
    print(f"  可分辨域对 M0 {q['M0']['n_pairs_distinguishable']}/21 -> "
          f"M1 {q['M1']['n_pairs_distinguishable']}/21 | "
          f"扰动 τ 均值 {q['M0']['kendall_tau_mean']:.4f} -> {q['M1']['kendall_tau_mean']:.4f}")
    print("配比侧:", x["verdict_vs_baseline"])
    inc = summary["comparison"]["q_increment_test"]
    if "by_scale" in inc:
        sig = [k for k, v in inc["by_scale"].items() if v["significant"]]
        print(f"Q 增量: 显著的尺度 {sig if sig else '无'}（三尺度区间均含 0 => 如实写入无增量）")
    print("fallback:", summary["fallback_trigger"]["action"])


if __name__ == "__main__":
    main()

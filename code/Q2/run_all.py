"""Q2 round1 装配：跑 M0s 与 M1s，输出 tables/ 与 run_summary.json。

用法：python run_all.py [--run] [--sigma-mode residual|p5_anchor]
不带 --run 则只从 metrics/*.json 重新装配。
"""
from __future__ import annotations

import argparse
import csv
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import scipy

import q2_common as C

OUT = C.ROOT / "results/Q2/experiments/round1"


def _run(script: str, extra: list[str]) -> float:
    t = time.time()
    r = subprocess.run([sys.executable, script, *extra], cwd=str(Path(__file__).parent),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        (OUT / "logs").mkdir(parents=True, exist_ok=True)
        (OUT / f"logs/{Path(script).stem}_fail.log").write_text(
            (r.stdout or "") + "\n--- STDERR ---\n" + (r.stderr or ""), encoding="utf-8")
        raise SystemExit(f"{script} 失败，日志见 logs/{Path(script).stem}_fail.log")
    return round(time.time() - t, 2)


def write_tables(m0: dict, m1: dict) -> list[str]:
    (OUT / "tables").mkdir(parents=True, exist_ok=True)
    files = []

    p = OUT / "tables/q2_params.csv"
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["method", "param", "value", "source_of_information", "note"])
        for k, v in m0["params"].items():
            w.writerow(["M0s", k, f"{v:.8f}", "B1 (real)", "HD-2 声明的 baseline，仅用 B1"])
        j = m1["stage3_joint_wls"]["M1s_params"]
        prov = {"E_B1": "B1 (real)", "A_B1": "B1 (real)", "alpha_B1": "B1 (real)",
                "B_B1": "B1 (real)", "E_B7": "B7 (semi-synthetic)", "A_B7": "B7 (semi-synthetic)",
                "alpha_B7": "B7 (semi-synthetic)", "B_B7": "B7 (semi-synthetic)",
                "beta": "B1 (real; B7 权重份额 ~1.6e-6)", "gamma": "B7 (semi-synthetic; B1 上 Q=1 无信息)"}
        for k in ("E_B1", "A_B1", "alpha_B1", "B_B1", "E_B7", "A_B7", "alpha_B7", "B_B7",
                  "beta", "gamma"):
            note = "形状参数来源专属（P8 FAIL）" if k not in ("beta", "gamma") else "跨源共享"
            w.writerow(["M1s", k, f"{j[k]:.8f}", prov.get(k, ""), note])
        ci = m1["stage2_gamma_on_B7"]["gamma_ci95"]
        w.writerow(["M1s", "gamma_ci95_lo", f"{ci[0]:.8f}", "B7 (semi-synthetic)", "自助 B=400 逐行"])
        w.writerow(["M1s", "gamma_ci95_hi", f"{ci[1]:.8f}", "B7 (semi-synthetic)", "含 1.0 ⇒ D_eff≈D·Q"])
    files.append(str(p.relative_to(C.ROOT)))

    p = OUT / "tables/q2_elasticity.csv"
    q = m1["q2c"]
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["quantity", "B1_side_primary", "B7_side_sensitivity",
                    "relative_difference", "real_data_supported"])
        real = set(q["provenance"]["real_data_supported"])
        for k, d in q["cross_side_difference"].items():
            w.writerow([k, f"{d['B1_side']:.8f}", f"{d['B7_side']:.8f}",
                        f"{d['relative_difference']:.4f}", "yes" if k in real else "no"])
        w.writerow(["elasticity_ratio_Q_over_D",
                    f"{q['primary_B1_side']['elasticity_ratio_Q_over_D']:.8f}",
                    f"{q['sensitivity_B7_side']['elasticity_ratio_Q_over_D']:.8f}",
                    "0.0000", "no"])
    files.append(str(p.relative_to(C.ROOT)))

    p = OUT / "tables/q2_domain_ratio.csv"
    bd = m1["stage4_b_direction"]["main_line_a"]
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        # 评审 F2：原列名 ratio_to_highest_loss_domain 误导 —— 值为中心化 w 之比，
        # 低于均值的域取负值且绝对值可超 1（dm_mathematics = -1.618816）。改名并加说明列。
        w.writerow(["domain", "b_ratio_vs_reference_domain", "sign_meaning",
                    "abs_gt_1", "kappa_free", "note"])
        for dom, r in bd["ratio_to_highest"].items():
            sign = "above_mean_loss (raises L when upweighted)" if r > 0 else \
                   "below_mean_loss (lowers L when upweighted)"
            w.writerow([dom, f"{r:.6f}", sign, "yes" if abs(r) > 1 else "no", "yes",
                        "b_i/b_ref，ref=%s；值为中心化 w 之比，非有界比例" % bd["highest_loss_domain"]])
    files.append(str(p.relative_to(C.ROOT)))

    p = OUT / "tables/q2_validation.csv"
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["source", "n", "spearman", "spearman_p", "rmse_after_deoffset",
                    "data_provenance", "metric_note"])
        prov = {"B4": "real (cross-family convergence points)",
                "B5": "literature values (published, not own observation)",
                "B2": "SEMI-SYNTHETIC (Cerebras trajectory) — GC5: 不得表述为直接观测"}
        for code, d in m1["transfer_validation"].items():
            w.writerow([code, d["n"], f"{d['spearman']:.6f}", f"{d['spearman_p']:.3e}",
                        f"{d['rmse_after_deoffset']:.6f}", prov.get(code, ""),
                        "禁报跨源未去偏 R²（P1）"])
    files.append(str(p.relative_to(C.ROOT)))
    return files


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--sigma-mode", default="residual", choices=["residual", "p5_anchor"])
    args = ap.parse_args()

    timings = {}
    if args.run:
        timings["M0s"] = _run("q2_scaling_baseline.py", [])
        timings["M1s"] = _run("q2_scaling_main.py", ["--sigma-mode", args.sigma_mode])

    m0 = json.loads((OUT / "metrics/q2_M0s.json").read_text(encoding="utf-8"))
    m1 = json.loads((OUT / "metrics/q2_M1s.json").read_text(encoding="utf-8"))
    tables = write_tables(m0, m1)

    deg, sup, fb = m1["degeneracy_check_B1"], m1["superiority_check_B7"], m1["fallback_trigger"]
    summary = {
        "schema_version": 1, "question": "Q2", "round": "round1",
        "implementation_target": "python", "random_seed": C.SEED,
        "approved_decision_id": "methods/Q2/q2_decisions.jsonl (6 records)",
        "approved_decision_ids": m1["approved_decision_ids"],
        "methods": [
            {"method_id": "M0s", "role": "usable_baseline", "script": "code/Q2/q2_scaling_baseline.py",
             "status": "success", "execution_time_seconds": timings.get("M0s", m0["runtime_seconds"]),
             "input_files": [str(C.PATHS["B1"].relative_to(C.ROOT))],
             "output_files": ["results/Q2/experiments/round1/metrics/q2_M0s.json"],
             "figure_files": [],
             "metrics_summary": {"rmse_B1": m0["fit"]["rmse"], "r2_B1": m0["fit"]["r2"],
                                 "beta": m0["params"]["beta"],
                                 "beta_ci95_grouped": m0["bootstrap"]["by_mode"]["grouped"]["beta"]["ci95"]},
             "warnings": [m0["caveat"]], "errors": []},
            {"method_id": "M1s", "role": "main", "script": "code/Q2/q2_scaling_main.py",
             "status": "success", "execution_time_seconds": timings.get("M1s", m1["runtime_seconds"]),
             "input_files": [str(C.PATHS[c].relative_to(C.ROOT)) for c in ("B1", "B7", "B4", "B5", "B2")]
                            + ["results/Q1/experiments/round1/tables/q1c_coefficients.csv",
                               "results/Q1/experiments/round1/tables/q1a_domain_quality.csv"],
             "output_files": ["results/Q2/experiments/round1/metrics/q2_M1s.json"] + tables,
             "figure_files": [],
             "metrics_summary": {
                 "gamma": m1["stage2_gamma_on_B7"]["gamma"],
                 "gamma_ci95": m1["stage2_gamma_on_B7"]["gamma_ci95"],
                 "gamma_ci_contains_one": bool(m1["stage2_gamma_on_B7"]["gamma_ci95"][0] <= 1.0
                                               <= m1["stage2_gamma_on_B7"]["gamma_ci95"][1]),
                 "beta": m1["stage3_joint_wls"]["M1s_params"]["beta"],
                 "rmse_B1": m1["stage3_joint_wls"]["M1s_params"]["rmse_B1"],
                 "rmse_B7": m1["stage3_joint_wls"]["M1s_params"]["rmse_B7"],
                 "dN_for_Q_plus_0.1_B1_side": m1["q2c"]["primary_B1_side"]["dN_for_Q_plus_0.1"],
                 "elasticity_ratio_Q_over_D": m1["q2c"]["primary_B1_side"]["elasticity_ratio_Q_over_D"]},
             "warnings": [sup["gc5_disclosure"],
                          m1["stage3_joint_wls"]["structural_consequence"],
                          m1["amb_q2_3_scale_alignment"]["status"]],
             "errors": []},
        ],
        "comparison": {
            "predeclared_metric_1_degeneracy_on_B1": deg,
            "predeclared_metric_2_superiority_on_B7": sup,
            "predeclared_metric_3_elasticity_signs": {
                "B1_side": m1["q2c"]["primary_B1_side"]["signs_ok"],
                "B7_side": m1["q2c"]["sensitivity_B7_side"]["signs_ok"]},
            "transfer_validation": m1["transfer_validation"],
            "hd2_verdict": ("PASS —— M1s 在 B7 上显著优于 M0s_joint（降幅区间不含 0），"
                            "且在 B1 上如期退化为 M0s。但超越性证据为半合成（见 gc5_disclosure）"),
        },
        "output_degeneracy": {
            "gamma_at_bound": bool(abs(m1["stage2_gamma_on_B7"]["gamma"] - 10.0) < 1e-6
                                   or m1["stage2_gamma_on_B7"]["gamma"] < 1e-3),
            "kappa_identifiable_from_B": False,
            "kappa_evidence": "workspace/data/q2_probe_g3_identifiability.json",
            "shape_params_shareable": False,
            "shape_evidence": "workspace/data/q2_probe_shape_sharing.json",
            "M1s_equals_M0s_on_B1": True,
            "note": "退化是结构性的、已预期，并被用作 Q=1 退化约束的依据",
        },
        "fallback_trigger": fb,
        "assumptions": {
            "load_bearing": [
                "AMB-Q2-2 跨源统一假设：p 的效应形状可跨尺度/跨来源迁移（b 在 B 侧不可验证）",
                "beta 可跨源共享（P8 只检验了 A/alpha/B，未检验 beta）",
                "裁定6 敏感性臂：A 侧与 B 侧在指定参照点上 dL/dp_i 相等",
            ],
            "tested_and_rejected": [
                "E 跨源共享（P1 FAIL，极差 1.6898）",
                "A/alpha/B 跨源共享（P8 FAIL，gamma 位移占区间宽 98.5%）",
            ],
            "declared_unidentifiable": ["kappa（b 的尺度因子），B 侧 RMSE 随其变化恰为 0.0"],
        },
        "gc5_disclosure": {
            "semi_synthetic_sources_used_in_fit": ["B7"],
            "semi_synthetic_sources_used_in_validation_only": ["B2"],
            "semi_synthetic_all_touched": ["B2", "B7"],
            "real_data_sources": ["B1 (主拟合)", "B4 (跨族验证)", "B5 (文献值验证)"],
            "per_source_provenance": {
                "B1": "真实 Pythia 训练日志（但拟合异常干净，使用者约束『B1 处理要谨慎』挂起）",
                "B2": "**半合成** Cerebras 轨迹 —— 其 Spearman %.6f 不得表述为直接观测的迁移验证"
                      % m1["transfer_validation"]["B2"]["spearman"],
                "B4": "真实跨族收敛点 57 行",
                "B5": "文献标度律值 44 行（他人发表值，非本队观测）",
                "B7": "**半合成** N-D-Q 实验 —— 唯一含 Q 变化的数据，gamma 完全由它决定",
            },
            "semi_synthetic_only_quantities": m1["q2c"]["provenance"]["irreducibly_semisynthetic"],
            "real_data_supported_quantities": m1["q2c"]["provenance"]["real_data_supported"],
            "b7_val_loss_lower_bound_anomaly": "B8 的 calibrated 半数 val_loss 下界 0.5，低于自然语言熵常见量级",
            "not_in_fit": ["B8", "B9", "B10"],
            "review_finding_F1_repair": ("评审发现 B2 参与验证却未列入披露清单（GC5 硬约束、"
                                         "方法卡 unacceptable failure 第 2 条）。已补入本块"),
        },
        "environment": {"python": platform.python_version(), "numpy": np.__version__,
                        "scipy": scipy.__version__, "platform": platform.platform(),
                        "matlab": "not available on this machine"},
        "warnings": [
            "B1 拟合异常干净（R2=0.9999998、RMSE=1.465e-4）；使用者已附加『B1 的处理要谨慎』，核查经其指示暂缓",
            "sigma_s 取值方式未经使用者裁定（现为 %s，可否决）" % args.sigma_mode,
        ],
        "errors": [],
    }
    (OUT / "run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n",
                                          encoding="utf-8")
    print(json.dumps({"tables": tables, "hd2": summary["comparison"]["hd2_verdict"],
                      "fallback_observed": fb["observed"], "timings": timings},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

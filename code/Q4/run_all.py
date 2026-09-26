"""Q4 round1 编排:跑 M1a + M0a + 桥接 + 前沿 MC + C8 聚合,写 run_summary 与 metrics/tables。

用法: cd code/Q4 && PYTHONIOENCODING=utf-8 python run_all.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from q4_analysis import c8_aggregate, fit_bridge, frontier_mc, m0a_baseline, m1a_attribution, yi_bias_probe
from q4_common import B_BOOT, HORIZON_MONTHS, ROOT, SEED, load_c1, load_q2_params

OUTDIR = ROOT / "results" / "Q4" / "experiments" / "round1"


def main() -> None:
    t0 = time.perf_counter()
    rng = np.random.default_rng(SEED)
    for sub in ("metrics", "tables", "figures"):
        (OUTDIR / sub).mkdir(parents=True, exist_ok=True)

    c1 = load_c1()
    q2 = load_q2_params()
    print(f"C1 {len(c1)} rows | Q2 params from {q2['source']}")

    att = m1a_attribution(c1, rng)
    print(f"M1a: scale_share={att['main_spec_decile_month']['scale_share']:.4f} "
          f"tech_share={att['main_spec_decile_month']['tech_share']:.4f} "
          f"M2a_triggered={att['m2a_fallback_triggered']}")

    yi = yi_bias_probe(c1, rng)
    print(f"yi bias: tech_points_diff={yi.get('tech_points_diff_jia_minus_yi')} "
          f"interpretable={yi.get('share_interpretable')}")

    base = m0a_baseline(c1)
    print(f"M0a: slope={base['slope_per_month']} h12={base['predictions']['h12']['point']}")

    br = fit_bridge(rng)
    print(f"bridge: slope={br['slope']} monotone={br['monotone_decreasing']} rmse={br['rmse']}")

    fr = frontier_mc(c1, br, att, q2, rng)
    print(f"frontier neutral h12: median={fr['scenarios']['neutral']['h12']['median']} "
          f"lo80={fr['scenarios']['neutral']['h12']['lo80']} "
          f"criterion_passed={fr['user_criterion']['passed']}")

    c8 = c8_aggregate()
    print(f"C8: {c8['n_dirs_used']} dirs, {c8['n_bbh_subtasks']} BBH subtasks")

    # metrics
    (OUTDIR / "metrics" / "q4_M1a.json").write_text(
        json.dumps({"attribution": att, "yi_bias_probe": yi, "bridge": br,
                    "frontier": fr, "c8": c8, "q2_params": q2},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTDIR / "metrics" / "q4_M0a.json").write_text(
        json.dumps(base, ensure_ascii=False, indent=2), encoding="utf-8")

    # tables
    pd.DataFrame([{"spec": k, **v} for k, v in att["sensitivity_specs"].items()]).to_csv(
        OUTDIR / "tables" / "q4_spec_sensitivity.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"month": k, "q90": v} for k, v in base["q90_by_month"].items()]).to_csv(
        OUTDIR / "tables" / "q4_frontier_path.csv", index=False, encoding="utf-8-sig")
    rows = []
    for sc, d in fr["scenarios"].items():
        for h in ("h12", "h24"):
            rows.append({"scenario": sc, "horizon": h, **d[h]})
    pd.DataFrame(rows).to_csv(OUTDIR / "tables" / "q4_frontier_scenarios.csv",
                              index=False, encoding="utf-8-sig")
    pd.DataFrame([{"tier": k, **v} for k, v in br["tiers"].items()]).to_csv(
        OUTDIR / "tables" / "q4_bridge_tiers.csv", index=False, encoding="utf-8-sig")
    grp = [{"group": k, **{kk: vv for kk, vv in v.items() if not isinstance(vv, dict)}}
           for k, v in att["by_type_group"].items()]
    pd.DataFrame(grp).to_csv(OUTDIR / "tables" / "q4_by_type_group.csv",
                             index=False, encoding="utf-8-sig")

    main_spec = att["main_spec_decile_month"]
    summary = {
        "schema_version": 1,
        "question_id": "Q4",
        "round": 1,
        "gate_target": "G3",
        "approved_methods": {"main": "M1a", "usable_baseline": "M0a",
                             "conditional_fallback": "M2a"},
        "approved_decision_ids": ["q4_primary_defense_target", "q4_scale_channel_definition",
                                  "q4_acceptance_criteria_and_budget",
                                  "q4_fn_spec_and_method_choice"],
        "status": "SUCCESS",
        "seed": SEED,
        "bootstrap_b": B_BOOT,
        "judged_horizon_months": HORIZON_MONTHS,
        "inputs": {
            "C1": "workspace/data_raw/.../leaderboard_cleaned.csv",
            "C4": "workspace/data_raw/.../epoch_all_ai_models.csv",
            "C6": "workspace/data_raw/.../loss_benchmark_bridge_expanded.csv",
            "C8": "workspace/data_raw/.../detailed_results/ (全量)",
            "Q2_params": q2["source"],
        },
        "outputs": {
            "metrics": ["metrics/q4_M1a.json", "metrics/q4_M0a.json"],
            "tables": ["tables/q4_spec_sensitivity.csv", "tables/q4_frontier_path.csv",
                       "tables/q4_frontier_scenarios.csv", "tables/q4_bridge_tiers.csv",
                       "tables/q4_by_type_group.csv"],
            "figures": [],
        },
        "metric_summary": {
            "scale_share": round(main_spec["scale_share"], 4),
            "scale_share_ci95": main_spec["scale_share_ci95"],
            "tech_share": round(main_spec["tech_share"], 4),
            "tech_share_ci95": main_spec["tech_share_ci95"],
            "scale_points": round(main_spec["scale_points"], 4),
            "tech_points": round(main_spec["tech_points"], 4),
            "total_points": round(main_spec["total_points"], 4),
            "baseline_slope_per_month": base["slope_per_month"],
            "baseline_h12_point": base["predictions"]["h12"]["point"],
            "frontier_neutral_h12_median": fr["scenarios"]["neutral"]["h12"]["median"],
            "frontier_neutral_h12_lo80": fr["scenarios"]["neutral"]["h12"]["lo80"],
            "user_criterion_passed": fr["user_criterion"]["passed"],
            "bridge_slope": br["slope"],
            "c8_dirs_used": c8["n_dirs_used"],
        },
        "fallback_trigger_state": {
            "M2a": att["m2a_fallback_triggered"],
            "note": att["m2a_note"],
        },
        "warnings": [
            "P6 CONDITIONAL:技术份额对 f(N) 规格敏感(极差/区间宽 = 1.99)。裁定 C 要求主口径 A + 规格 B 一并报告。",
            "规格 B(线性 log N)下 scale_share 为负、占比口径破 —— 须在正文如实报告，不得只报主口径。",
            "乙侧偏误子集 total 可能为负(B5) ⇒ 只报绝对点数差与符号，不得当占比读。",
            "桥接 High 层 n=7，方向对但 p 不显著；不得解读为 High 层质量更差(F10)。",
            "24 个月视界未经裁定作主报；饱和形态在 9.1 个月窗口内不可检验。",
            "figures 本轮为空，如实记录。",
        ],
        "environment": {"python": "3.14.6", "numpy": np.__version__, "pandas": pd.__version__},
        "elapsed_seconds": round(time.perf_counter() - t0, 1),
        "generated_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
    }
    (OUTDIR / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote {OUTDIR.relative_to(ROOT)} ({summary['elapsed_seconds']}s)")


if __name__ == "__main__":
    main()

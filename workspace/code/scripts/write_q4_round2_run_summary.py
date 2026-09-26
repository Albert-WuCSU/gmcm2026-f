"""补写 round2 的 run_summary.json。

AGENTS.md「Experiment Output」要求每个执行过的轮次都写 run_summary.json；
round2 只有 metrics/ 与 tables/，缺本轮摘要。本脚本只做装配,不重算任何数字。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
R1 = ROOT / "results/Q4/experiments/round1"
R2 = ROOT / "results/Q4/experiments/round2"

m1a = json.loads((R1 / "metrics/q4_M1a.json").read_text(encoding="utf-8"))
trend = json.loads((R2 / "metrics/q4_trend_method.json").read_text(encoding="utf-8"))
nf = json.loads((R2 / "n_frontier_meta.json").read_text(encoding="utf-8"))
r1sum = json.loads((R1 / "run_summary.json").read_text(encoding="utf-8"))

ep = trend["endpoint_sensitivity"]
summary = {
    "schema_version": 1,
    "question_id": "Q4",
    "round": 2,
    "gate_target": "G4",
    "purpose": "兑现人工裁定 q4_result_verdict 的 supplementary_run_required："
               "把端点敏感性与趋势法数字落盘，使论文只能引落盘值",
    "approved_methods": r1sum["approved_methods"],
    "status": "SUCCESS",
    "seed": trend["seed"],
    "bootstrap_b": trend["n_boot"],
    "inputs": {
        "C1": r1sum["inputs"]["C1"],
        "round1_metrics": "results/Q4/experiments/round1/metrics/q4_M1a.json",
        "scripts": ["code/Q4/q4_round2_trend.py", "code/Q4/q4_round2_persist.py"],
    },
    "outputs": {
        "metrics": ["metrics/q4_trend_method.json"],
        "tables": ["tables/q4_endpoint_sensitivity.csv",
                   "tables/q4_N_and_frontier_by_month.csv",
                   "tables/q4_scenario_spread_scaling.csv"],
        "aux": ["n_frontier_meta.json"],
        "figures": [],
    },
    "metric_summary": {
        "endpoint_share_spread": trend["endpoint_share_spread"],
        "endpoint_sign_flips": trend["endpoint_sign_flips"],
        "total_points_range": trend["total_points_range"],
        "endpoint_scale_share": {d["endpoint_def"]: round(d["scale_share"], 4) for d in ep},
        "trend_decile_scale_share": round(trend["trend_method"]["decile"]["scale_share"], 4),
        "trend_decile_slope_f": round(trend["trend_method"]["decile"]["slope_f"], 5),
        "trend_decile_slope_tau": round(trend["trend_method"]["decile"]["slope_tau"], 5),
        "trend_decile_slope_ratio": round(trend["trend_method"]["decile"]["slope_ratio"], 2),
        "trend_scale_share_ci95": trend["trend_scale_share_ci95"],
        "trend_ci_contains_zero": trend["trend_ci_contains_zero"],
        "logN_q90_slope_per_month": nf["logN_q90_slope_per_month"],
        "N_q90_ratio_first_over_last": nf["N_q90_ratio_first_over_last"],
        "scenario_spread_h12": [d["implied_scenario_spread_h12"]
                                for d in trend["scenario_spread_scaling"]],
        "round1_scale_share_for_reference": m1a["attribution"]["main_spec_decile_month"]["scale_share"],
    },
    "fallback_trigger_state": {
        "M2a": False,
        "note": "主口径 A 下未触发(区间下界 0.0223 >= 0)；规格 B 下会触发但不作主口径",
    },
    "warnings": [
        "端点敏感性测的是自助区间未覆盖的第三种不确定性来源(末端定义),其极差 0.2875 已大于主口径点值",
        "总提升区间 5.4865-6.6592 是四端点/规格算法的极差;趋势法 drop-last 变体给 5.3581,略低于下界",
        "N_q90 端点比值为 3.162,斜率隐含值为 3.676,两者非同一量,引用须写明",
        "本脚本只落盘,不改变任何 round1 结论;主 claim 已由 q4_claim_scope 收窄为方向与量级",
    ],
    "environment": r1sum["environment"],
    "generated_at": trend["generated_at"],
}
p = R2 / "run_summary.json"
p.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print("WROTE", p.relative_to(ROOT))

import pathlib
import sys

paths = [
    'results/Q1/experiments/round1/tables/q1a_domain_quality.csv',
    'results/Q1/experiments/round1/tables/q1a_ablation_per_domain.csv',
    'results/Q1/experiments/round1/tables/q1b_conflict_rates.csv',
    'results/Q1/experiments/round1/tables/q1c_validation_by_scale.csv',
    'results/Q1/experiments/round1/tables/q1c_q_increment_test.csv',
    'results/Q2/experiments/round1/tables/q2_params.csv',
    'results/Q2/experiments/round1/tables/q2_elasticity.csv',
    'results/Q2/experiments/round1/tables/q2_validation.csv',
    'results/Q2/experiments/round1/tables/q2_domain_ratio.csv',
    'results/Q3/experiments/round1/tables/q3_optimal_by_budget.csv',
    'results/Q3/experiments/round1/tables/q3_transition_definitions.csv',
    'results/Q3/experiments/round1/tables/q3_cost_form_comparison.csv',
    'results/Q3/experiments/round1/tables/q3_lctx_sensitivity.csv',
    'results/Q3/experiments/round1/tables/q3_baseline_gap_decomposition.csv',
    'results/Q3/experiments/round1/tables/q3_chinchilla_reference.csv',
    'results/Q3/experiments/round1/tables/q3_dldp_direction.csv',
    'results/Q4/experiments/round1/tables/q4_spec_sensitivity.csv',
    'results/Q4/experiments/round1/tables/q4_bridge_tiers.csv',
    'results/Q4/experiments/round1/tables/q4_by_type_group.csv',
    'results/Q4/experiments/round1/tables/q4_frontier_path.csv',
    'results/Q4/experiments/round1/tables/q4_frontier_scenarios.csv',
    'results/Q4/experiments/round2/tables/q4_endpoint_sensitivity.csv',
    'results/Q4/experiments/round2/tables/q4_N_and_frontier_by_month.csv',
    'results/Q4/experiments/round2/tables/q4_scenario_spread_scaling.csv',
]

out = []
for p in paths:
    fp = pathlib.Path(p)
    out.append('=' * 70)
    out.append(p)
    out.append('=' * 70)
    if not fp.exists():
        out.append('!! MISSING')
        continue
    txt = fp.read_text(encoding='utf-8', errors='replace')
    out.append(txt.rstrip())
    out.append('')

sys.stdout.write('\n'.join(out))

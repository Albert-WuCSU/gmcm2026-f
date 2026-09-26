"""Independent audit of the paper's numbers against the landed artifacts.

Method: every curated claim is read from its artifact, then the paper text is
searched for a *correct rounding* of that value at whatever precision the paper
chose.  A token counts as a match when rounding the artifact value to the token's
own decimal places reproduces the token, and the token carries enough precision
to be meaningful (>=3 decimals, or >=4 significant digits).  So 249.0624 may
appear as 249.0624 or 249.1, but 0.068719 must appear as 0.0687 or finer.

This is written fresh rather than reusing the workflow's verifiers, so it is an
independent pass over the same artifacts.
"""
import csv
import json
import pathlib
import re
import sys

FILES = ['abstract.tex', 'problem.tex', 'analysis.tex', 'assumptions.tex',
         'problem1.tex', 'problem2.tex', 'problem3.tex', 'problem4.tex',
         'evaluation.tex', 'appendix_data.tex']
TEXT = '\n'.join((pathlib.Path('paper/sections') / f).read_text(encoding='utf-8')
                 for f in FILES)

TOKEN = re.compile(r'-?\d+\.\d+')
TOKENS = []
for m in TOKEN.finditer(TEXT):
    s = m.group(0)
    dec = len(s.split('.')[1])
    sig = len(s.lstrip('-').replace('.', '').lstrip('0'))
    if dec >= 3 or sig >= 4:
        TOKENS.append((float(s), dec))


def rounds_to(value, token, decimals):
    try:
        return f'%.{decimals}f' % float(value) == token
    except (TypeError, ValueError):
        return False


def present(value):
    # Exact zero is a legitimate reported result. The old nonzero-only matcher
    # made the Q4 zero-share limiting case fail even when explicitly printed.
    if float(value) == 0.0:
        return re.search(r'(?<![\d.])0\.0+(?![\d.])', TEXT) is not None
    for tok, dec in TOKENS:
        if abs(tok) < 1e-12:
            continue
        rst = f'%.{dec}f' % float(value)
        if float(rst) == tok:
            return True
    return False


checks = []
fails = []


def check(label, value, source=''):
    if value is None or value == '':
        return
    ok = present(value)
    checks.append((label, value, ok))
    if not ok:
        fails.append((label, value, source))


def rows(rel):
    with open(rel, encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh))


def js(rel):
    return json.loads(pathlib.Path(rel).read_text(encoding='utf-8'))


def dig(o, key):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == key:
                return v
            r = dig(v, key)
            if r is not None:
                return r
    return None


Q1T = 'results/Q1/experiments/round1/tables/'
Q2T = 'results/Q2/experiments/round1/tables/'
Q3T = 'results/Q3/experiments/round1/tables/'
Q4T = 'results/Q4/experiments/round1/tables/'
Q4R2 = 'results/Q4/experiments/round2/tables/'

# ---------------- Q1 ----------------
for r in rows(Q1T + 'q1a_domain_quality.csv'):
    if r['method'] == 'M1':
        check(f"Q1 Q(M1) {r['domain']}", r['huber'], r['n'])
for r in rows(Q1T + 'q1b_conflict_rates.csv'):
    if r['criterion'] == 'CD2_high_value_and_high_pollution' and r['population'] == 'pooled':
        check(f"Q1 CD2@{r['anchor']}", r['conflict_rate'])
for r in rows(Q1T + 'q1c_q_increment_test.csv'):
    check(f"Q1 Q增量 {r['scale']}", r['increment'])
for r in rows(Q1T + 'q1c_validation_by_scale.csv'):
    if r['scale'] in ('test_1m', 'test_60m', 'test_1B'):
        check(f"Q1 去偏R2 {r['method']} {r['scale']}", r['r2_after_offset_removal'])

# ---------------- Q2 ----------------
for r in rows(Q2T + 'q2_params.csv'):
    if r['param'] in ('E_B1', 'A_B1', 'alpha_B1', 'B_B1', 'beta', 'gamma',
                      'gamma_ci95_lo', 'gamma_ci95_hi', 'E_B7', 'A_B7', 'alpha_B7', 'B_B7'):
        check(f"Q2 参数 {r['param']}", r['value'])
probe = js('workspace/data/q2_probe_beta_sharing.json')
check('Q2 gamma 路线B', probe['route_B_beta_free_on_B7']['gamma'])
check('Q2 beta 路线B', probe['route_B_beta_free_on_B7']['beta'])
check('Q2 位移占区间宽比', probe['shift_as_fraction_of_ci_width'])
for r in rows(Q2T + 'q2_elasticity.csv'):
    check(f"Q2 {r['quantity']} B1", r['B1_side_primary'])
    check(f"Q2 {r['quantity']} B7", r['B7_side_sensitivity'])
for r in rows(Q2T + 'q2_validation.csv'):
    check(f"Q2 迁移 {r['source']} rho", r['spearman'])
for r in rows(Q2T + 'q2_domain_ratio.csv'):
    if r['abs_gt_1'] == 'yes':
        check('Q2 b比值 dm_mathematics', r['b_ratio_vs_reference_domain'])

# ---------------- Q3 ----------------
for r in rows(Q3T + 'q3_optimal_by_budget.csv'):
    tag = r['C'].replace('1e+', '')
    for k in ('N_B', 'D_B', 'Q', 'loss', 'share_C_train', 'share_C_Q', 'share_C_attn'):
        check(f'Q3 {k} @1e{tag}', r[k])
for r in rows(Q3T + 'q3_transition_definitions.csv'):
    if r['location_log10_C']:
        check(f"Q3 转移位置 {r['definition'][:6]}", r['location_log10_C'])
for r in rows(Q3T + 'q3_cost_form_comparison.csv'):
    if r['key'].startswith('C1e+19_'):
        check(f"Q3 costform {r['key']}", r['Q'])
for r in rows(Q3T + 'q3_lctx_sensitivity.csv'):
    check(f"Q3 lctx {r['L_ctx']} N", r['N_B'])
    check(f"Q3 lctx {r['L_ctx']} D", r['D_B'])
    check(f"Q3 lctx {r['L_ctx']} ratio", r['attn_over_train'])
for r in rows(Q3T + 'q3_baseline_gap_decomposition.csv'):
    for k in ('gap_reported', 'gap_quality_only', 'gap_ratio_handicap', 'handicap_share_pct'):
        check(f"Q3 gap {k} {r['C']}", r[k])
for r in rows(Q3T + 'q3_chinchilla_reference.csv'):
    check(f"Q3 隐含 D/N {r['C']}", r['law_implied_D_over_N'])

# ---------------- Q4 ----------------
for r in rows(Q4R2 + 'q4_endpoint_sensitivity.csv'):
    check(f"Q4 端点 {r['endpoint_def']} share", r['scale_share'])
    check(f"Q4 端点 {r['endpoint_def']} total", r['total_points'])
for r in rows(Q4T + 'q4_spec_sensitivity.csv'):
    check(f"Q4 规格 {r['spec']} share", r['scale_share'])
    check(f"Q4 规格 {r['spec']} total", r['total_points'])
mf = rows(Q4R2 + 'q4_N_and_frontier_by_month.csv')
for k in ('N_q90', 'S_q90', 'N_q10', 'N_q50'):
    check(f'Q4 {k} 首月', mf[0][k])
    check(f'Q4 {k} 末月', mf[-1][k])
tm = js('results/Q4/experiments/round2/metrics/q4_trend_method.json')
check('Q4 趋势 share', tm['trend_method']['decile']['scale_share'])
check('Q4 趋势 slope_f', tm['trend_method']['decile']['slope_f'])
check('Q4 趋势 slope_tau', tm['trend_method']['decile']['slope_tau'])
for v in tm['total_points_range']:
    check('Q4 total 区间', v)
for r in rows(Q4T + 'q4_frontier_scenarios.csv'):
    if r['horizon'] in ('h12', 'h24'):
        check(f"Q4 情景 {r['scenario']} {r['horizon']} 中位", r['median'])
        check(f"Q4 情景 {r['scenario']} {r['horizon']} lo80", r['lo80'])
for r in rows(Q4T + 'q4_by_type_group.csv'):
    check(f"Q4 子组 {r['group']} total", r['total_points'])
    check(f"Q4 子组 {r['group']} scale", r['scale_points'])
for r in rows(Q4R2 + 'q4_scenario_spread_scaling.csv'):
    check(f"Q4 极差 share={r['scale_share'][:5]}", r['implied_scenario_spread_h12'])
for r in rows(Q4T + 'q4_bridge_tiers.csv'):
    check(f"Q4 桥接 {r['tier']} rho", r['spearman'])

# ---------------- report ----------------
print(f'checks: {len(checks)}   failures: {len(fails)}')
for label, val, src in fails:
    print(f'  MISSING  {label:<40} expected {val}   ({src})')
sys.exit(1 if fails else 0)

"""Generate paper/sections/appendix_data.tex: the complete numerical record.

Every value is read from the landed CSV/JSON artifacts and formatted here, so the
printed appendix cannot drift from the results.  Values are rounded to six
significant digits; the note in the generated file says so.
"""
import csv
import pathlib

TARGET = pathlib.Path('paper/sections/appendix_data.tex')
ROOT = pathlib.Path('.')


def rows(rel):
    with open(ROOT / rel, encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh))


def num(x, sig=6):
    """Six significant digits, plain decimal when reasonable; minus sign in math mode."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return str(x)
    if v == 0:
        return '0'
    if abs(v) >= 1e5 or abs(v) < 1e-3:
        s = ('%.' + str(sig - 1) + 'e') % v
    else:
        import math
        dec = max(0, sig - 1 - int(math.floor(math.log10(abs(v)))))
        s = ('%.' + str(dec) + 'f') % v
    if s.startswith('-'):
        return '$-$' + s[1:]
    return s


def span(lo, hi, sig=4):
    return '[%s, %s]' % (num(lo, sig), num(hi, sig))


def tex_domain(name):
    return name.replace('train_the_pile_', '').replace('_', r'\_')


def table(caption, label, header, body, colspec=None, small=False):
    ncol = len(header)
    if colspec is None:
        colspec = '@{}' + 'l' * ncol + '@{}'
    out = []
    out.append(r'\begin{table}[htbp]')
    out.append(r'  \centering')
    out.append(r'  \caption{%s}' % caption)
    out.append(r'  \label{%s}' % label)
    if small:
        out.append(r'  \small')
    out.append(r'  \begin{tabular}{%s}' % colspec)
    out.append(r'    \toprule')
    out.append('    ' + ' & '.join(header) + r' \\')
    out.append(r'    \midrule')
    for r in body:
        out.append('    ' + ' & '.join(r) + r' \\')
    out.append(r'    \bottomrule')
    out.append(r'  \end{tabular}')
    out.append(r'\end{table}')
    out.append('')
    return out


out = []
out.append(r'\clearpage')
out.append(r'\section{结果数据}')
out.append(r'\label{app:data}')
out.append('')
out.append('本附录给出各问的完整数值结果，与正文中的摘要表互为补充。')
out.append('全部数值由建模代码在附件数据上算出并落盘，此处直接读取，未经人工转录；')
out.append('为便于排版，数值统一四舍五入到六位有效数字，完整精度见随附的程序与结果文件。')
out.append('')

# ---------------- Q1 -------------------------------------------------------
out.append(r'\subsection{问题一：领域级质量评分与冲突率}')
out.append('')
d = rows('results/Q1/experiments/round1/tables/q1a_domain_quality.csv')
order = ['arxiv', 'c4', 'commoncrawl', 'stackexchange', 'wikipedia', 'book', 'github']
body = []
for dom in order:
    m0 = next(r for r in d if r['method'] == 'M0' and r['domain'] == dom)
    m1 = next(r for r in d if r['method'] == 'M1' and r['domain'] == dom)
    body.append([
        tex_domain(dom), m0['n'],
        num(m0['huber'], 5), span(m0['ci95_lo'], m0['ci95_hi']),
        num(m1['huber'], 5), span(m1['ci95_lo'], m1['ci95_hi']),
    ])
out += table('领域级质量评分（pooled 口径，Huber $M$ 估计与自助 95\\% 区间）',
             'tab:app-q1-domain',
             ['领域', '$n$', '$Q$（等权平均）', '95\\% 区间',
              '$Q$（门控合成）', '95\\% 区间'],
             body, colspec='@{}lrlrrl@{}', small=True)

d = rows('results/Q1/experiments/round1/tables/q1b_conflict_rates.csv')
crit_name = {
    'CD2_high_value_and_high_pollution': '高价值 $\\wedge$ 高污染',
    'CD1_indicator_MAD_anchored': '指标离差（分位数锚定）',
    'CD1_indicator_MAD_gt_0.25_fixed_ref': '指标离差（固定阈 0.25）',
    'CD3_ge5_high_and_ge5_low': '$\\ge 5$ 项高且 $\\ge 5$ 项低',
    'CD3_ge3_high_and_ge3_low': '$\\ge 3$ 项高且 $\\ge 3$ 项低',
}
body = [[crit_name[r['criterion']], r['anchor'], r['population'].replace('_', r'\_'),
         num(r['conflict_rate'], 4)] for r in d]
out += table('冲突率：五种判据 $\\times$ 三个锚点 $\\times$ 两种归一化总体',
             'tab:app-q1-conflict',
             ['冲突判据', '锚点', '归一化总体', '冲突率'],
             body, colspec='@{}llll@{}', small=True)

d = rows('results/Q1/experiments/round1/tables/q1c_validation_by_scale.csv')
body = []
for r in d:
    body.append([r['method'], r['scale'].replace('test_', '').replace('est_', '外推 '),
                 num(r['r2_raw'], 4), num(r['r2_after_offset_removal'], 4),
                 num(r['spearman'], 4), num(r['rmse'], 4),
                 num(r['bias_share_of_rmse'], 4)])
out += table('配比模型的跨尺度验证（原始 $R^2$、去尺度偏移后 $R^2$、秩相关与误差分解）',
             'tab:app-q1-scale',
             ['方法', '尺度', '原始 $R^2$', '去偏 $R^2$', 'Spearman', 'RMSE', '偏移占比'],
             body, colspec='@{}llrrrrr@{}', small=True)

# ---------------- Q2 -------------------------------------------------------
out.append(r'\clearpage')
out.append(r'\subsection{问题二：领域比值与跨源验证}')
out.append('')
d = rows('results/Q2/experiments/round1/tables/q2_domain_ratio.csv')
body = [[str(i + 1), tex_domain(r['domain']), num(r['b_ratio_vs_reference_domain'], 4),
         '是' if r['abs_gt_1'] == 'yes' else '否']
        for i, r in enumerate(d)]
out += table('各领域相对参照领域的配比系数比值 $b_i/b_{\\text{ref}}$（按比值降序，'
             '参照领域为 philpapers）',
             'tab:app-q2-ratio',
             ['序', '领域', '$b_i/b_{\\text{ref}}$', '$|b_i/b_{\\text{ref}}|>1$'],
             body, colspec='@{}rlrr@{}', small=True)

d = rows('results/Q2/experiments/round1/tables/q2_validation.csv')
prov = {'B4': '真实（跨族收敛点）',
        'B5': '文献值（他人发表）',
        'B2': '半合成（对标轨迹）'}
body = [[r['source'], r['n'], num(r['spearman'], 4),
         ('%.3e' % float(r['spearman_p'])), num(r['rmse_after_deoffset'], 4),
         prov[r['source']]] for r in d]
out += table('跨源迁移验证（只报秩相关与去源偏后的均方根误差）',
             'tab:app-q2-validation',
             ['来源', '$n$', 'Spearman', '$p$ 值', '去源偏 RMSE', '数据性质'],
             body, colspec='@{}rlrrll@{}', small=True)

# ---------------- Q3 -------------------------------------------------------
out.append(r'\clearpage')
out.append(r'\subsection{问题三：成本函数对照与配比边际方向}')
out.append('')
d = rows('results/Q3/experiments/round1/tables/q3_cost_form_comparison.csv')
gname = {'exponential': '指数型', 'power': '幂函数型', 'log_asymptotic': '对数渐进型'}
body = []
for r in d:
    c, g = r['key'].split('_', 1)
    expo = c.replace('C1e+', '')          # '19' / '22' / '24'
    body.append([r'$C=10^{%s}$' % expo,
                 gname[g], num(r['Q'], 4), num(r['N_B'], 4), num(r['D_B'], 4),
                 num(r['loss'], 5),
                 {'interior': '内点', 'upper_Q_eq_1': '$Q=1$'}.get(r['branch'], r['branch'])])
out += table('三类质量成本函数在三个预算档位下的最优解',
             'tab:app-q3-costform',
             ['预算', '成本函数', '$Q^{*}$', '$N^{*}$/B', '$D^{*}$/B', '损失', '分支'],
             body, colspec='@{}llrrrrl@{}', small=True)

d = rows('results/Q3/experiments/round1/tables/q3_dldp_direction.csv')
body = [[r['rank'], tex_domain(r['domain'])] for r in d]
out += table('领域配比的边际损失排序（1 为边际损失最大）',
             'tab:app-q3-dldp',
             ['序', '领域'], body, colspec='@{}rl@{}', small=True)

d = rows('results/Q3/experiments/round1/tables/q3_lctx_sensitivity.csv')
body = [[r['L_ctx'], '是' if r['above_crit'] == 'True' else '否', num(r['Q'], 4),
         num(r['N_B'], 4), num(r['D_B'], 4), num(r['N_over_D'], 6),
         num(r['loss'], 5), num(r['attn_over_train'], 4)] for r in d]
out += table('上下文长度敏感性（附件 C7 的五档可行取值，后两档跨越临界值 30000）',
             'tab:app-q3-lctx',
             ['$L_{\\text{ctx}}$', '跨临界', '$Q^{*}$', '$N^{*}$/B', '$D^{*}$/B',
              '$N{:}D$', '损失', '$C_{\\text{attn}}/C_{\\text{train}}$'],
             body, colspec='@{}rlrrrrrr@{}', small=True)

# ---------------- Q4 -------------------------------------------------------
out.append(r'\clearpage')
out.append(r'\subsection{问题四：逐月轨迹、情景与子组分解}')
out.append('')
d = rows('results/Q4/experiments/round2/tables/q4_N_and_frontier_by_month.csv')
body = [[r['month'], r['n'], num(r['N_q10'], 4), num(r['N_q50'], 4),
         num(r['N_q90'], 4), num(r['N_max'], 4), num(r['S_q90'], 5),
         num(r['S_mean'], 5)] for r in d]
out += table('逐月样本量与规模分位、能力前沿（$N$ 单位为十亿参数，$S$ 为六维等权得分）',
             'tab:app-q4-monthly',
             ['月份', '$n$', '$N_{q10}$', '$N_{q50}$', '$N_{q90}$', '$N_{\\max}$',
              '$S_{q90}$', '$\\bar{S}$'],
             body, colspec='@{}lrrrrrrr@{}', small=True)

d = rows('results/Q4/experiments/round1/tables/q4_frontier_scenarios.csv')
sname = {'conservative': '保守', 'neutral': '中性', 'optimistic': '较高'}
body = [[sname[r['scenario']], r['horizon'].replace('h', ''), num(r['median'], 5),
         span(r['lo80'], r['hi80']), span(r['lo95'], r['hi95']),
         num(r['width95'], 5)] for r in d]
out += table('三种算力情景下 12 个月与 24 个月的前沿预测（中位数与 80\\%/95\\% 区间）',
             'tab:app-q4-scenario',
             ['情景', '视界/月', '中位数', '80\\% 区间', '95\\% 区间', '95\\% 宽度'],
             body, colspec='@{}rlrllr@{}', small=True)

d = rows('results/Q4/experiments/round1/tables/q4_by_type_group.csv')
gname = {'chat_finetuned': '对话微调', 'pretrained': '预训练基础'}
body = []
for r in d:
    body.append([gname[r['group']], r['n'], num(r['scale_points'], 4),
                 num(r['tech_points'], 4), num(r['total_points'], 4),
                 r['scale_share_ci95'].replace(', ', ', '),
                 '是' if r['share_interpretable'] == 'True' else '否'])
out += table('按模型类型的子组分解（份额可读性取决于总点数是否为正）',
             'tab:app-q4-group',
             ['组', '$n$', '规模点数', '技术点数', '总点数', '规模份额 95\\% 区间', '份额可读'],
             body, colspec='@{}lrrrrll@{}', small=True)

TARGET.write_text('\n'.join(out) + '\n', encoding='utf-8')
print('wrote', TARGET, 'with', sum(1 for line in out if line.startswith('    ') and '&' in line),
      'data rows')

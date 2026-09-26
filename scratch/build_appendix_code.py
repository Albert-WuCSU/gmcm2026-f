"""Generate paper/sections/appendix_code.tex from the real modeling sources.

Extracts top-level symbols by name so the printed code is byte-identical to the
code that produced the landed results (no hand transcription).
"""
import ast
import pathlib
import textwrap

TARGET = pathlib.Path('paper/sections/appendix_code.tex')

# (appendix subsection title, [(relative path, symbol name, printed label)])
PLAN = [
    ('问题一：质量指标规范化与门控合成', [
        ('workspace/code/scripts/q1_features.py', 'DIRECTION', '指标方向表（三层可信度）'),
        ('workspace/code/scripts/q1_features.py', 'normalize', '经验分位数归一化'),
        ('workspace/code/scripts/q1_features.py', 'apply_direction', '方向统一'),
        ('workspace/code/scripts/q1_features.py', 'per_token_dsir', 'dsir 逐 token 归一化'),
        ('workspace/code/scripts/q1_features.py', 'collapse_dsir', 'dsir 三列合一'),
        ('workspace/code/scripts/q1_features.py', 'build_canonical', '规范化主入口'),
        ('code/Q1/q1_common.py', 'vp_split', '价值组 / 污染组划分'),
        ('code/Q1/q1_quality_main.py', 'gated', '门控合成 Q = V·(1−P)'),
        ('code/Q1/q1_quality_main.py', 'conflict_rates', '冲突判据与冲突率'),
        ('code/Q1/q1_common.py', 'huber_mean', '域级 Huber M 估计'),
        ('code/Q1/q1_mixture_baseline.py', 'build_Q_corpus', '域级质量到配比域的跨体系映射'),
    ]),
    ('问题二：广义标度律的参数估计', [
        ('code/Q2/q2_common.py', 'fit_classic', '经典标度律拟合（baseline）'),
        ('code/Q2/q2_common.py', 'fit_gamma_on_b7', '给定 β 后由 B7 反解 γ'),
        ('code/Q2/q2_common.py', 'fit_joint_wls', '联合加权最小二乘'),
        ('code/Q2/q2_scaling_main.py', 'validate_transfer', '跨源迁移验证'),
    ]),
    ('问题三：分段 KKT 求解与结构性转移识别', [
        ('code/Q3/q3_common.py', 'g_value', '三类质量成本函数 g(Q)'),
        ('code/Q3/q3_common.py', 'g_prime', 'g 的导数'),
        ('code/Q3/q3_common.py', 'Model.loss', '目标函数'),
        ('code/Q3/q3_common.py', 'Model.cost_parts', '三类算力开销分解'),
        ('code/Q3/q3_common.py', 'Model.R1', 'KKT 约减式 (R1)'),
        ('code/Q3/q3_common.py', 'Model.R2', 'KKT 约减式 (R2)'),
        ('code/Q3/q3_common.py', 'Model.branch_interior', '内点分支 Q < 1'),
        ('code/Q3/q3_common.py', 'Model.branch_upper', '边界分支 Q = 1'),
        ('code/Q3/q3_common.py', 'Model.kkt_audit', 'KKT 五项硬判据'),
        ('code/Q3/q3_common.py', 'Model.active_set', '活跃约束集'),
        ('code/Q3/q3_common.py', 'Model.solve_kkt', '分支枚举与最优分支选择'),
        ('code/Q3/q3_optimize_main.py', 'locate_active_set_change', '转移点二分定位'),
        ('code/Q3/q3_optimize_main.py', 'definition_D', '定义 D 的步长敏感性'),
        ('code/Q3/q3_optimize_main.py', 'derivative_at_saturation', '饱和点导数符号'),
        ('code/Q3/q3_optimize_baseline.py', 'gap_decomposition', 'baseline 差距三数分解'),
    ]),
    ('问题四：演进分解、桥接与前沿预测', [
        ('code/Q4/q4_common.py', 'decompose', '规模通道 / 技术通道分解'),
        ('code/Q4/q4_analysis.py', 'm1a_attribution', '主口径归因'),
        ('code/Q4/q4_analysis.py', 'fit_bridge', 'Loss → Benchmark 桥接'),
        ('code/Q4/q4_analysis.py', 'frontier_mc', '前沿预测蒙特卡洛'),
        ('code/Q4/q4_round2_trend.py', 'trend', '趋势法月斜率与份额'),
    ]),
]


def extract(path, symbol):
    src = pathlib.Path(path).read_text(encoding='utf-8')
    lines = src.splitlines()
    tree = ast.parse(src)

    def walk(body, prefix):
        for node in body:
            if isinstance(node, ast.ClassDef):
                for sub in walk(node.body, prefix + node.name + '.'):
                    yield sub
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield prefix + node.name, node
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for t in targets:
                    if isinstance(t, ast.Name):
                        yield prefix + t.id, node

    for name, node in walk(tree.body, ''):
        if name == symbol:
            return '\n'.join(lines[node.lineno - 1:node.end_lineno])
    raise KeyError('symbol %r not found in %s' % (symbol, path))


out = []
out.append('% 本文件由 scratch/build_appendix_code.py 从建模源码逐符号抽取生成，请勿手工编辑。')
out.append(r'\clearpage')
out.append(r'\section{核心算法程序}')
out.append(r'\label{app:code}')
out.append('')
out.append(r'本节按子问题列出建模与求解的核心程序，由 \texttt{scratch/build\_appendix\_code.py}')
out.append('从实际运行的源文件中按符号抽取，未经人工转录。省略的部分为输入输出装配、')
out.append('绘图与结果落盘代码，其路径在各问的方法说明中给出；行内注释保留原样。')
out.append('')

for idx, (title, items) in enumerate(PLAN, start=1):
    out.append('\\subsection{%s}' % title)
    out.append('')
    for path, symbol, label in items:
        code = extract(path, symbol)
        code = textwrap.dedent(code)
        shown = symbol.split('.')[-1]
        out.append('\\subsubsection*{%s（\\texttt{%s}）}'
                   % (label, shown.replace('_', r'\_')))
        out.append('')
        out.append('\\begin{lstlisting}[language=Python]')
        out.append(code.rstrip('\n'))
        out.append('\\end{lstlisting}')
        out.append('')

TARGET.write_text('\n'.join(out), encoding='utf-8')

n_lines = 0
for title, items in PLAN:
    sub = 0
    for path, symbol, label in items:
        n = len(extract(path, symbol).splitlines())
        sub += n
        print('   %4d  %s' % (n, symbol))
    print('  ---- %s: %d lines' % (title, sub))
    n_lines += sub
print('wrote', TARGET, 'with', n_lines, 'code lines across',
      sum(len(items) for _, items in PLAN), 'symbols')

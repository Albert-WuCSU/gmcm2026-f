"""Repair problem1.tex after the punctuation-normaliser bug.

The normaliser used to restore math before code blocks, which left \\x01 placeholders
inside every figure, table and equation of problem1.tex.  The corrupted placeholders
cannot be mapped back to their math, so the file is rebuilt from the last commit
(which predates the corruption) and the intended changes are re-applied here.
"""
import pathlib
import subprocess
import sys

sys.path.insert(0, 'scratch')
from normalize_cjk_punct import normalise  # noqa: E402

P = pathlib.Path('paper/sections/problem1.tex')

subprocess.run(['git', 'checkout', 'HEAD', '--', str(P)], check=True)
t = P.read_text(encoding='utf-8')
assert '\x01' not in t and '\x02' not in t, 'the committed version is itself corrupted'
print(f'restored from HEAD: {len(t)} chars, no placeholders')

FIXES = [
    # A3: Q1 promised something Q3 does not deliver
    ('消解规则相应地不是删除而是标注：冲突样本在问题三中按质量上界处理，\n'
     '其比例作为质量提升成本的敏感参数。',
     '消解规则相应地不是删除而是标注：冲突样本保留在样本集中，但在涉及质量提升的\n'
     '成本口径中宜按质量上界处理。本文未对冲突比例另设敏感臂，该处置只作口径声明。'),
    # B2: do not reuse gamma for the cost-function amplitude
    (r'与问题三中 $g(Q)=\gamma Q^{4}$', r'与问题三中 $g(Q)=5\times10^{9}Q^{4}$'),
    # B4: Huber k must not collide with k = 6 + eta*L_ctx
    (r'领域级聚合取 Huber $M$ 估计（$k=1.345$）',
     r'领域级聚合取 Huber $M$ 估计（稳健化参数 $k_{\mathrm{H}}=1.345$）'),
    (r'式~\eqref{eq:q1-huber} 中 $k=1.345$，',
     r'式~\eqref{eq:q1-huber} 中 $k_{\mathrm{H}}=1.345$，'),
    (r'\hat Q_d=\arg\min_{m}\sum_{x\in d}\rho_k\!\left(',
     r'\hat Q_d=\arg\min_{m}\sum_{x\in d}\rho_{k_{\mathrm{H}}}\!\left('),
    ('    r^{2}/2, & |r|\\le k,\\\\\n    k|r|-k^{2}/2, & |r|>k,',
     '    r^{2}/2, & |r|\\le k_{\\mathrm{H}},\\\\\n'
     '    k_{\\mathrm{H}}|r|-k_{\\mathrm{H}}^{2}/2, & |r|>k_{\\mathrm{H}},'),
    (r'\rho_k(r)=', r'\rho_{k_{\mathrm{H}}}(r)='),
    # B5: bootstrap count B must not collide with the data-term coefficient B
    (r'区间由 $B=400$ 次自助重抽样给出', r'区间由 $B_{\mathrm{boot}}=400$ 次自助重抽样给出'),
    (r'（$B=400$，Huber', r'（$B_{\mathrm{boot}}=400$，Huber'),
    (r'（$B=400$，', r'（$B_{\mathrm{boot}}=400$，'),
    (r'$B=4000$ 与 $B=40000$', r'$B_{\mathrm{boot}}=4000$ 与 $B_{\mathrm{boot}}=40000$'),
    (r'而 $B=400$ 下上界极差', r'而 $B_{\mathrm{boot}}=400$ 下上界极差'),
    (r'该格在 $B=400$ 下不可判定', r'该格在 $B_{\mathrm{boot}}=400$ 下不可判定'),
    # D1: the domain Q is a cross-check for Q2, not a substitute
    ('供问题二使用的领域级 $Q$、', '领域级 $Q$（供问题二对照，其刻度对齐见问题二）、'),
]

missed = []
for old, new in FIXES:
    if old in t:
        t = t.replace(old, new)
    else:
        missed.append(old[:70])

t, _ = normalise(t)
residue = t.count('\x01') + t.count('\x02')
P.write_text(t, encoding='utf-8')
print(f're-applied {len(FIXES) - len(missed)}/{len(FIXES)} fixes; '
      f'placeholders in result: {residue}')
if missed:
    print('MISSED:')
    for m in missed:
        print('  ', repr(m))
    sys.exit(1)
if residue:
    sys.exit(2)

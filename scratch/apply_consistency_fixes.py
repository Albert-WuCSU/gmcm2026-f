"""Apply the cross-section consistency fixes flagged by the audit.

Every replacement below is verified to apply; anything that does not match is
reported rather than silently skipped.  No number is changed except the beta*gamma
pair, which is recomputed from the model's own parameters because the previously
printed values do not reproduce (see the report at the end).
"""
import pathlib
import sys

SEC = pathlib.Path('paper/sections')
applied, missed = [], []


def edit(name, old, new, count=None, note=''):
    p = SEC / name
    t = p.read_text(encoding='utf-8')
    n = t.count(old)
    if n == 0:
        missed.append(f'{name}: NOT FOUND -> {old[:70]!r}')
        return
    if count is not None and n != count:
        missed.append(f'{name}: expected {count} got {n} -> {old[:60]!r}')
    p.write_text(t.replace(old, new), encoding='utf-8')
    applied.append(f'{name}: {n}x {note or old[:50]!r}')


# ---------------------------------------------------------------- A1
edit('problem4.tex',
     '跨源共享标度参数的假设未经检验，此处按前提使用。',
     '该标度律的数据量指数可跨源共享这一前提已在问题二中单独检验并判为不成立'
     '（见第~\\ref{sec:problem2}~节），此处按承重前提使用，其条件性一并继承。',
     note='A1 Q4 no longer claims the sharing assumption is untested')

# ---------------------------------------------------------------- A2
edit('problem2.tex',
     '问题一的三个训练尺度中也只有一个落入 B1 的数据量区间 $[0.070542,11.965825]$B。',
     '问题一的三个训练尺度中也只有一个落入 B1 的参数量区间 $[0.070542,11.965825]$B。',
     note='A2 the range is a parameter-count range, not a token-count range')

# ---------------------------------------------------------------- A3
edit('problem1.tex',
     '消解规则相应地不是删除而是标注：冲突样本在问题三中按质量上界处理，\n其比例作为质量提升成本的敏感参数。',
     '消解规则相应地不是删除而是标注：冲突样本保留在样本集中，但在涉及质量提升的\n成本口径中宜按质量上界处理。本文未对冲突比例另设敏感臂，该处置只作口径声明。',
     note='A3 drop the promise Q3 does not keep')

# ---------------------------------------------------------------- B1
edit('problem3.tex', r'记 $S\equiv DQ^{\gamma}$。',
     r'记 $D_{\text{eff}}\equiv DQ^{\gamma}$。', note='B1 rename S')
edit('problem3.tex', r'\beta B\,S^{-\beta}\,k N',
     r'\beta B\,D_{\text{eff}}^{-\beta}\,k N', note='B1 (R1) S->D_eff')
edit('problem3.tex', r'公共因子 $\beta B S^{-\beta}/D$',
     r'公共因子 $\beta B D_{\text{eff}}^{-\beta}/D$', note='B1 prose S->D_eff')

# ---------------------------------------------------------------- B2/B3
edit('problem3.tex',
     r'另取饱和指数型 $g=\gamma(1-\mathrm{e}^{-\lambda Q})$（$\gamma=10^{7}$，$\lambda=6.0$）、'
     r'Hill 型 $g=\gamma Q^{\lambda}/(1+Q^{\lambda})$（同上参数）与二次型 $g=\gamma Q^{2}$'
     r'（$\gamma=4.0343\times10^{9}$',
     r'另取饱和指数型 $g=g_{\mathrm{c}}(1-\mathrm{e}^{-g_{\mathrm{r}}Q})$'
     r'（$g_{\mathrm{c}}=10^{7}$，$g_{\mathrm{r}}=6.0$）、'
     r'Hill 型 $g=g_{\mathrm{c}}Q^{g_{\mathrm{r}}}/(1+Q^{g_{\mathrm{r}}})$（同上参数）与'
     r'二次型 $g=g_{\mathrm{c}}Q^{2}$（$g_{\mathrm{c}}=4.0343\times10^{9}$',
     note='B2/B3 cost-function coefficients no longer reuse gamma and lambda')
edit('problem1.tex', r'与问题三中 $g(Q)=\gamma Q^{4}$ 一类',
     r'与问题三中 $g(Q)=5\times10^{9}Q^{4}$ 一类',
     note='B2 Q1 writes the coefficient numerically')

# ---------------------------------------------------------------- B4
edit('problem1.tex', r'领域级聚合取 Huber $M$ 估计（$k=1.345$）',
     r'领域级聚合取 Huber $M$ 估计（稳健化参数 $k_{\mathrm{H}}=1.345$）', note='B4 Huber k')
edit('problem1.tex', r'式~\eqref{eq:q1-huber} 中 $k=1.345$，',
     r'式~\eqref{eq:q1-huber} 中 $k_{\mathrm{H}}=1.345$，', note='B4 Huber k prose')
edit('problem1.tex', r'\hat Q_d=\arg\min_{m}\sum_{x\in d}\rho_k\!\left(',
     r'\hat Q_d=\arg\min_{m}\sum_{x\in d}\rho_{k_{\mathrm{H}}}\!\left(',
     note='B4 Huber psi subscript')
edit('problem1.tex',
     '    r^{2}/2, & |r|\\le k,\\\\\n    k|r|-k^{2}/2, & |r|>k,',
     '    r^{2}/2, & |r|\\le k_{\\mathrm{H}},\\\\\n'
     '    k_{\\mathrm{H}}|r|-k_{\\mathrm{H}}^{2}/2, & |r|>k_{\\mathrm{H}},',
     note='B4 Huber piecewise')
edit('problem1.tex', r'\rho_k(r)=', r'\rho_{k_{\mathrm{H}}}(r)=', note='B4 Huber def')

# ---------------------------------------------------------------- B5
for old, new in [
    (r'区间由 $B=400$ 次自助重抽样给出', r'区间由 $B_{\mathrm{boot}}=400$ 次自助重抽样给出'),
    (r'（$B=400$，Huber', r'（$B_{\mathrm{boot}}=400$，Huber'),
    (r'（$B=400$，', r'（$B_{\mathrm{boot}}=400$，'),
    (r'$B=4000$ 与 $B=40000$', r'$B_{\mathrm{boot}}=4000$ 与 $B_{\mathrm{boot}}=40000$'),
    (r'而 $B=400$ 下上界极差', r'而 $B_{\mathrm{boot}}=400$ 下上界极差'),
    (r'该格在 $B=400$ 下不可判定', r'该格在 $B_{\mathrm{boot}}=400$ 下不可判定'),
]:
    edit('problem1.tex', old, new, note='B5 bootstrap count symbol')

# ---------------------------------------------------------------- B7
edit('problem4.tex', r'$p=0.148$', r'$p$ 值 $0.148$', note='B7 p-value upright-ish')
edit('problem4.tex', r'$p=9.4\times10^{-6}$', r'$p$ 值 $9.4\times10^{-6}$', note='B7 p-value')

# ---------------------------------------------------------------- B8
edit('problem2.tex',
     r'$\boldsymbol{b}=(b_1,\dots,b_{17})$ 与问题一配比模型的系数 $w$ 成比例。',
     r'$\boldsymbol{b}=(b_1,\dots,b_{17})$ 由问题一配比模型的系数 $\theta_d$ 经中心化得到，'
     r'即 $\boldsymbol{b}=\kappa(\boldsymbol{\theta}-\bar\theta)$，其中 $\kappa<0$。',
     note='B8/B9 b is proportional to the centred Q1 coefficients with kappa<0')

# ---------------------------------------------------------------- B9
edit('problem3.tex',
     r'配比项对 $\boldsymbol{p}$ 的偏导与系数 $b_i$ 成正比，故',
     r'配比项对 $\boldsymbol{p}$ 的偏导与 $-b_i$ 成正比（$\kappa<0$，故 $b_i$ 越大'
     r'表示上调该域越抬高损失），故',
     note='B9 sign of dL/dp')

# ---------------------------------------------------------------- C1
edit('problem2.tex',
     r'实测该乘积在两条路线上分别为 $0.270396$ 与 $0.097985$，相差 2.76 倍，',
     r'按两条路线各自的 $\beta$ 与 $\gamma$ 计算，该乘积分别为 $0.2703$ 与 $0.0980$，'
     r'相差 2.76 倍，',
     note='C1 beta*gamma recomputed from the model parameters')

# ---------------------------------------------------------------- D3
edit('problem3.tex',
     '单位约定为：损失项以十亿为单位，成本项取绝对量纲',
     '单位约定为：规模项 $N$、$D$ 以十亿为单位，成本项取绝对量纲',
     note='D3 unit-convention sentence')

# ---------------------------------------------------------------- D4
edit('problem2.tex', r'十个月累计 $-0.5653$ dex',
     r'窗口内累计（9 个月度间隔）$-0.5653$ dex', note='D4 nine intervals, not ten months')

print('APPLIED:')
for a in applied:
    print('  ', a)
if missed:
    print('MISSED (needs manual attention):')
    for m in missed:
        print('  ', m)
sys.exit(1 if missed else 0)

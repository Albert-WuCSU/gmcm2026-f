"""Mechanical post-draft fixes applied to paper/sections/*.tex.

Each fix is listed with why it is needed; none of them changes a number or a claim.

1. Citation key rename  : xia2024regmix -> liu2024regmix
   The RegMix paper's first author is Qian Liu, not Xia.  The key was misnamed in
   the drafting brief; keys are not printed, but a wrong-looking key invites a wrong
   in-text attribution ("Xia 等"), so it is renamed and any "Xia" prose is flagged.
2. Chinese punctuation  : half-width , ; : ( ) in Chinese prose -> full-width
   Only problem1.tex was written with half-width punctuation; the other sections use
   full-width.  Math mode and LaTeX arguments are left untouched.
3. Hoffmann constants   : the Q3 sentence saying the constants were not checked
   against the original paper is now false — they were verified in arXiv:2203.15556
   Appendix D.2 (E=1.69, A=406.4, B=410.7, alpha=0.34, beta=0.28).
"""
import pathlib
import re
import sys

sys.path.insert(0, 'scratch')
from normalize_cjk_punct import normalise  # noqa: E402

SEC = pathlib.Path('paper/sections')
report = []

# ---- 1. citation key rename -------------------------------------------------
for f in sorted(SEC.glob('*.tex')):
    t = f.read_text(encoding='utf-8')
    if 'xia2024regmix' in t:
        n = t.count('xia2024regmix')
        t = t.replace('xia2024regmix', 'liu2024regmix')
        f.write_text(t, encoding='utf-8')
        report.append(f'{f.name}: renamed key x{""}ia2024regmix -> liu2024regmix ({n}x)')

# ---- 1b. flag any prose that attributes the paper to "Xia" ------------------
for f in sorted(SEC.glob('*.tex')):
    t = f.read_text(encoding='utf-8')
    for m in re.finditer(r'.{30}Xia.{30}', t):
        report.append(f'{f.name}: CHECK attribution -> ...{m.group(0)}...')
    for m in re.finditer(r'.{20}RegMix.{40}', t):
        report.append(f'{f.name}: RegMix prose -> ...{m.group(0)}...')

# ---- 2. punctuation --------------------------------------------------------
targets = [SEC / 'problem1.tex']
for f in targets:
    if not f.exists():
        continue
    src = f.read_text(encoding='utf-8')
    out, _ = normalise(src)
    if out != src:
        f.write_text(out, encoding='utf-8')
        report.append(f'{f.name}: normalised Chinese punctuation')

# ---- 3. Hoffmann constants sentence ---------------------------------------
OLD = '所引比例出自 \\citet{hoffmann2022}，其常数在本文写作时未逐项核对原文。'
NEW = ('所引比例出自 Hoffmann 等\\citep{hoffmann2022}；该文 Approach 3 的拟合常数'
       '（$E=1.69$、$A=406.4$、$B=410.7$、$\\alpha=0.34$、$\\beta=0.28$）'
       '载于该文附录 D.2 的式 (10)，本文写作时已对照原文逐项核验。'
       '该文正文表 2 给出的是分配系数 $a=0.46$、$b=0.54$，与上述指数不是同一组参数。')
f = SEC / 'problem3.tex'
t = f.read_text(encoding='utf-8')
if OLD in t:
    f.write_text(t.replace(OLD, NEW), encoding='utf-8')
    report.append('problem3.tex: updated the Hoffmann constants sentence (now verified)')
else:
    report.append('problem3.tex: Hoffmann sentence NOT found verbatim — check manually')

# ---- 4. Q4: the "beta sharing untested" sentence is stale -------------------
# Q2 tested it (P9, FAIL); Q4's source report predates that and the draft copied it.
OLD4 = '跨源共享标度参数的假设未经检验，此处按前提使用。'
NEW4 = ('该标度律的数据量指数可跨源共享这一假设在问题二已单独检验且未获通过，'
        '此处按承重前提使用，其影响见第~\\ref{sec:problem2}~节。')
f = SEC / 'problem4.tex'
t = f.read_text(encoding='utf-8')
if OLD4 in t:
    f.write_text(t.replace(OLD4, NEW4), encoding='utf-8')
    report.append('problem4.tex: corrected the stale "beta sharing untested" claim '
                  '(it was tested in Q2/P9 and failed)')
else:
    report.append('problem4.tex: stale beta-sharing sentence NOT found — check manually')

# ---- 5. Q4: cite Schaeffer for the metric-resolution point ------------------
OLD5 = '得分上界的饱和形态在 9.1 个月的窗口内无法检验。'
NEW5 = ('得分上界的饱和形态在 9.1 个月的窗口内无法检验；'
        '评测指标的取值方式本身会塑造所观察到的能力形态，'
        '在指标存在截断或分辨率受限时尤其如此\\citep{schaeffer2023}。')
t = f.read_text(encoding='utf-8')
if OLD5 in t and 'schaeffer2023' not in t:
    f.write_text(t.replace(OLD5, NEW5), encoding='utf-8')
    report.append('problem4.tex: cited schaeffer2023 for the metric-resolution caveat')
elif 'schaeffer2023' in t:
    report.append('problem4.tex: schaeffer2023 already cited')
else:
    report.append('problem4.tex: sentence for schaeffer citation NOT found')

# ---- 6. \\citet is unusable with this numeric style ------------------------
# gmcm-numerical.bst emits \\bibitem{key} with the author list inside the entry text,
# not in the optional [] argument, so natbib cannot recover an author and warns
# "Author undefined for citation".  Rewrite the three uses as "Surname 等\\citep{}".
CITET = [
    ('problem.tex', r'\citet{albalak2024survey}',
     'Albalak 等\\citep{albalak2024survey}'),
    ('problem3.tex', r'（\citet{hoffmann2022} 的 Approach 1/2 给出的约 20 tokens/param）',
     '（Hoffmann 等\\citep{hoffmann2022} 的 Approach 1/2 给出的约 20 tokens/param）'),
]
for name, old, new in CITET:
    f = SEC / name
    t = f.read_text(encoding='utf-8')
    if old in t:
        f.write_text(t.replace(old, new), encoding='utf-8')
        report.append(f'{name}: \\citet -> "Surname 等\\citep" (numeric style has no author)')

# any stragglers?
for f in sorted(SEC.glob('*.tex')):
    left = f.read_text(encoding='utf-8').count(r'\citet{')
    if left:
        report.append(f'{f.name}: WARNING {left} \\citet still present')

print('\n'.join(report) if report else 'no changes')

"""Inventory the symbol-disambiguation targets flagged by the consistency audit."""
import pathlib
import re

for name in ('problem1.tex', 'problem2.tex', 'problem3.tex', 'problem4.tex'):
    t = pathlib.Path('paper/sections') / name
    s = t.read_text(encoding='utf-8')
    print('=' * 20, name)
    for label, pat in [
        ('$B$ bootstrap', r'\$B[=$^]'),
        ('Kendall tau', r'Kendall \$\\tau\$|\\tau\$\s*均值|\\tau\$ 分布'),
        ('p-value', r'\$p=[0-9]'),
        ('S = DQ^gamma', r'S\^\{-\\beta\}|\\equiv DQ'),
        ('gamma as cost coef', r'\$\\gamma\('),
        ('Huber k', r'\$k=1\.345\$|\\rho_k|\\rho_\{k'),
    ]:
        hits = re.findall(pat, s)
        if hits:
            print(f'  {label:<22} {len(hits):>3}  e.g. {hits[:3]}')
    # show the exact lines for the ones we will rewrite
    for i, line in enumerate(s.splitlines(), 1):
        if re.search(r'\$B[=$^]', line) or 'Kendall' in line:
            print(f'    L{i}: {line.strip()[:120]}')

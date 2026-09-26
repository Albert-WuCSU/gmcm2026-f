import io, re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

t = io.open('paper/sections/problem1.tex', encoding='utf-8').read()
lines = t.split('\n')
inside = False
for i, l in enumerate(lines, 1):
    if r'\begin{tabular}' in l:
        inside = True
    if inside:
        has_cjk = bool(re.search(r'[　-鿿]', l))
        has_punct = bool(re.search(r'[,;:()]', l))
        if has_cjk and has_punct:
            print(i, l)
    if r'\end{tabular}' in l:
        inside = False

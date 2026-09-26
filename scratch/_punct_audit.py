"""Measure half-width vs full-width punctuation usage per section file."""
import re
import pathlib
import sys

CJK = r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]'

files = sorted(pathlib.Path('paper/sections').glob('*.tex'))
out = []
for f in files:
    t = f.read_text(encoding='utf-8')
    # strip comment lines and math, so we count prose punctuation only
    prose = '\n'.join(l for l in t.splitlines() if not l.lstrip().startswith('%'))
    prose = re.sub(r'\$[^$]*\$', ' MATH ', prose)
    prose = re.sub(r'\\begin\{(equation|align|tabular|longtable|lstlisting)\}.*?'
                   r'\\end\{\1\}', ' BLOCK ', prose, flags=re.S)
    half = {p: len(re.findall(re.escape(p), prose)) for p in [',', ';', ':']}
    full = {p: len(re.findall(re.escape(p), prose)) for p in ['，', '；', '：']}
    cjk_after_half = {}
    for p in [',', ';', ':']:
        cjk_after_half[p] = len(re.findall(re.escape(p) + r'\s*' + CJK, prose))
    out.append((f.name, half, full, cjk_after_half))

for name, half, full, cah in out:
    print(f'{name:<22} half={half}  full={full}  half-adjacent-to-CJK={cah}')

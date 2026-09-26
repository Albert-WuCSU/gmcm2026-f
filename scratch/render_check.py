"""Compile paper/main.pdf and rasterise a few pages for visual review.

Usage: python scratch/render_check.py [page ...]
Writes /tmp/papercheck/pg-NN.png and prints the compile summary.
"""
import os
import pathlib
import re
import subprocess
import sys

MIKTEX = r'D:\Users\luqianwu\AppData\Local\Programs\MiKTeX\miktex\bin\x64'
ENV = dict(os.environ, PATH=MIKTEX + os.pathsep + os.environ.get('PATH', ''))
PAPER = pathlib.Path('paper')
OUT = pathlib.Path('scratch/render_check')
OUT.mkdir(parents=True, exist_ok=True)


def sh(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=ENV)


def main():
    for cmd in (['xelatex', '-interaction=nonstopmode', 'main.tex'],
                ['bibtex', 'main'],
                ['xelatex', '-interaction=nonstopmode', 'main.tex'],
                ['xelatex', '-interaction=nonstopmode', 'main.tex']):
        r = sh(cmd, PAPER)
        print(f'{cmd[0]:<8} exit={r.returncode}')

    log = (PAPER / 'main.log').read_text(encoding='utf-8', errors='replace')
    errs = [l for l in log.splitlines() if l.startswith('!')]
    print('errors:', errs if errs else 'none')
    warns = {}
    for pat in ('undefined', 'multiply-defined', 'Overfull', 'Underfull',
                'Citation', 'Reference'):
        warns[pat] = sum(1 for l in log.splitlines() if pat.lower() in l.lower())
    print('warnings:', warns)
    m = re.search(r'Output written on main\.pdf \((\d+) pages', log)
    n_pages = int(m.group(1)) if m else 0
    print('pages:', n_pages)

    pages = [int(a) for a in sys.argv[1:]] or [1, 2, 3]
    for p in pages:
        sh(['mgs', '-q', '-dNOPAUSE', '-dBATCH', '-dSAFER', '-sDEVICE=png16m',
            '-r100', f'-dFirstPage={p}', f'-dLastPage={p}',
            f'-sOutputFile={OUT}/pg-{p:02d}.png', 'main.pdf'], PAPER)
    print('rasters in', OUT)


if __name__ == '__main__':
    main()

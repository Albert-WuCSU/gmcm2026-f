"""Stage the project for GitHub and prove the teammates' workflow works from the staged tree.

Three verifications, all run on an *exported copy* of the committed tree, never in place:
  1. figure scripts     : run all five paper-figure scripts and compare every produced
                          figure byte-for-byte with the committed one.  This is what the
                          teammates will do, so it is tested exactly that way.
  2. LaTeX              : full xelatex + bibtex chain, report errors and page count.
  3. skills present     : every skill directory exists in all three trees.

Run from the repository root:  python scratch/stage_for_github.py [--verify]
"""
import hashlib
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path('.').resolve()
MIKTEX = pathlib.Path(r'D:\Users\luqianwu\AppData\Local\Programs\MiKTeX\miktex\bin\x64')
XELATEX = str(MIKTEX / 'xelatex.exe')
BIBTEX = str(MIKTEX / 'bibtex.exe')

FORBIDDEN = [
    'F题/real_attachments/',
    'workspace/data_raw/',
    'scratch/data_desc_hidden',
    'scratch/data_desc_visible.txt',
    'scratch/data_description.txt',
    'paper/.git/',
    '.mathmodeling-skills/',
]
REQUIRED = [
    'paper/sections/problem4.tex', 'paper/sections/abstract.tex',
    'paper/sections/appendix_code.tex', 'paper/sections/appendix_data.tex',
    'paper/reference.bib', 'paper/main.pdf',
    'code/figstyle.py', 'code/paper_framework_figures.py',
    'code/Q1/q1_paper_figures.py', 'code/Q2/q2_paper_figures.py',
    'code/Q3/q3_paper_figures.py', 'code/Q4/q4_paper_figures.py',
    'planning/HANDOFF.md', 'planning/manifests/Q1.json',
    'AGENTS.md', 'CLAUDE.md', '.gitignore',
]
FIGURE_SCRIPTS = [
    'code/paper_framework_figures.py',
    'code/Q1/q1_paper_figures.py',
    'code/Q2/q2_paper_figures.py',
    'code/Q3/q3_paper_figures.py',
    'code/Q4/q4_paper_figures.py',
]
SKILL_TREES = ['.claude/skills', '.codex/skills', '.agents/skills']


def run(cmd, cwd=None, env=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, env=env,
                          shell=isinstance(cmd, str),
                          encoding='utf-8', errors='replace')


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def stage():
    if not (ROOT / '.git').exists():
        run(['git', 'init', '-b', 'main'], cwd=ROOT)
    run(['git', 'add', '-A'], cwd=ROOT)
    listed = run(['git', 'status', '--porcelain'], cwd=ROOT).stdout.splitlines()
    staged = [l[3:].strip().strip('"') for l in listed if l.strip()]
    return staged


def export(staged, dest):
    for rel in staged:
        src = ROOT / rel
        if src.is_file():
            dst = dest / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def main():
    staged = stage()
    print(f'staged entries: {len(staged)}')
    bad = [p for p in staged if any(p.startswith(f) for f in FORBIDDEN)]
    print('forbidden staged :', bad or 'none')
    missing = [p for p in REQUIRED if p not in staged and not (ROOT / p).exists()]
    print('required missing :', missing or 'none')

    # skills present in all three trees?
    for tree in SKILL_TREES:
        n = len(list((ROOT / tree).glob('*/SKILL.md')))
        print(f'{tree:<16} skills: {n}')
    if bad or missing:
        print('ABORT')
        return 1

    total = sum((ROOT / p).stat().st_size for p in staged if (ROOT / p).is_file())
    print(f'total tracked bytes: {total/1e6:.1f} MB')

    if '--verify' not in sys.argv:
        return 0

    tmp = pathlib.Path(tempfile.mkdtemp(prefix='repo_verify_'))
    export(staged, tmp)
    print('exported to', tmp)

    # ---- 1. figure scripts -------------------------------------------------
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    print('\n[1] figure scripts in the exported tree')
    for script in FIGURE_SCRIPTS:
        before = {p.name: sha(p) for p in (tmp / 'paper/figures').glob('*')}
        r = run([sys.executable, script], cwd=tmp, env=env)
        after = {p.name: sha(p) for p in (tmp / 'paper/figures').glob('*')}
        changed = sorted(k for k in after if before.get(k) != after[k])
        status = 'OK ' if r.returncode == 0 else 'FAIL'
        print(f'  {status} {script:<38} exit={r.returncode} '
              f'changed={len(changed)} new={len(set(after)-set(before))}')
        if r.returncode != 0:
            print(r.stderr[-800:])

    # ---- 2. LaTeX ----------------------------------------------------------
    print('\n[2] LaTeX build in the exported tree')
    for cmd in ([XELATEX, '-interaction=nonstopmode', 'main.tex'],
                [BIBTEX, 'main'],
                [XELATEX, '-interaction=nonstopmode', 'main.tex'],
                [XELATEX, '-interaction=nonstopmode', 'main.tex']):
        r = run(cmd, cwd=tmp / 'paper')
        print(f'  {pathlib.Path(cmd[0]).name:<12} exit={r.returncode}')
    log = (tmp / 'paper' / 'main.log')
    if log.exists():
        t = log.read_text(encoding='utf-8', errors='replace')
        errs = [l for l in t.splitlines() if l.startswith('!')]
        print('  log errors     :', errs or 'none')
        undef = [l for l in t.splitlines() if re.search(r'undefined', l, re.I)]
        print('  undefined refs :', len(undef))
        m = re.search(r'Output written on main\.pdf \((\d+) pages', t)
        print('  pages          :', m.group(1) if m else '?')
    return 0


if __name__ == '__main__':
    sys.exit(main())

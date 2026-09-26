"""Mirror the paper sources into GMCM2026-Overleaf/ so the upload package stays current.

Copies LaTeX sources and the 18 paper figures; leaves docs/ and fonts/ (already present)
untouched.  Verifies afterwards that both trees agree on every mirrored file.
"""
import hashlib
import pathlib
import shutil

SRC = pathlib.Path('paper')
DST = pathlib.Path('GMCM2026-Overleaf')

FILES = ['main.tex', 'anonymous.tex', 'config.tex', 'reference.bib',
         'gmcm2026.cls', 'gmcm-numerical.bst', '.latexmkrc', '.gitignore',
         'build.sh', 'build.bat', 'LICENSE', 'README.md', 'review_2026-09-26.md']
GLOBS = [('sections', '*.tex'), ('figures', '*.pdf'), ('fonts', 'DejaVuSansMono*')]


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


copied = []
for name in FILES:
    s = SRC / name
    if s.exists():
        shutil.copy2(s, DST / name)
        copied.append(name)
for sub, pat in GLOBS:
    (DST / sub).mkdir(exist_ok=True)
    for s in sorted((SRC / sub).glob(pat)):
        shutil.copy2(s, DST / sub / s.name)
        copied.append(f'{sub}/{s.name}')

# compare back
bad = []
for name in copied:
    if digest(SRC / name) != digest(DST / name):
        bad.append(name)
print(f'mirrored {len(copied)} files; mismatches: {bad if bad else "none"}')

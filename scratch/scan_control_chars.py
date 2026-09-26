"""Scan the paper sources for stray control characters.

Cause: the Bash tool collapses backslash pairs inside heredocs, so a heredoc-banner
edit that wrote \\beta arrived as \beta in a non-raw Python string and became the
backspace byte 0x08.  Any edit made through a heredoc must be checked for this.
"""
import pathlib
import re

BAD = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')
found = 0
for p in sorted(pathlib.Path('paper').rglob('*.tex')):
    t = p.read_text(encoding='utf-8')
    for m in BAD.finditer(t):
        line = t[:m.start()].count('\n') + 1
        ctx = t[max(0, m.start() - 45):m.start() + 25].replace('\n', ' | ')
        print(f'{p}:{line}: byte 0x{ord(m.group(0)):02x}  ...{ctx}...')
        found += 1
print('total stray control chars:', found)

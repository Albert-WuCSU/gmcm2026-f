"""Repair the backspace byte that a heredoc edit left in problem2.tex."""
import pathlib

p = pathlib.Path('paper/sections/problem2.tex')
t = p.read_text(encoding='utf-8')
n = t.count('\x08eta')
t = t.replace('\x08eta', '\\beta')
p.write_text(t, encoding='utf-8')
print(f'replaced {n} corrupted byte(s) with \\beta')

import re
left = re.findall(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', t)
print('stray control chars remaining in this file:', len(left))

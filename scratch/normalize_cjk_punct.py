"""Normalise Chinese punctuation in a section file.

Only punctuation that sits in Chinese prose is converted; math mode, LaTeX
command arguments and ASCII numeric lists are left untouched.  Run with
--dry to print the planned changes without writing.
"""
import pathlib
import re
import sys

CJK = r'\u4e00-\u9fff\u3000-\u303f'
# characters that may legitimately follow a Chinese-clause punctuation mark
FOLLOWS = CJK + r'\uff0c\u3002\uff1b\uff1a\u3001\uff09\uff08\x01'


def normalise(text):
    # 1. protect inline math
    maths = []

    def stash(m):
        maths.append(m.group(0))
        return '\x01%d\x01' % (len(maths) - 1)

    t = re.sub(r'\$[^$\n]*\$', stash, text)

    # 2. protect display/verbatim blocks
    blocks = []

    def stash_block(m):
        blocks.append(m.group(0))
        return '\x02%d\x02' % (len(blocks) - 1)

    t = re.sub(r'\\begin\{(equation\*?|align\*?|tabular|longtable|lstlisting|table|figure)\}'
               r'.*?\\end\{\1\}', stash_block, t, flags=re.S)

    n = {}
    # 3. clause punctuation: previous char is CJK or end-of-math placeholder,
    #    or the next non-space char is CJK / end-of-math placeholder
    for half, full in [(',', '\uff0c'), (';', '\uff1b'), (':', '\uff1a')]:
        pat_a = re.compile(r'(?<=[' + CJK + r'\x01])' + re.escape(half))
        pat_b = re.compile(re.escape(half) + r'(?=\s*[' + FOLLOWS + r'])')
        before = t
        t = pat_a.sub(full, t)
        n[half] = len(before) - len(t)
        t = pat_b.sub(full, t)

    # 4. full stop after CJK
    before = t
    t = re.sub(r'(?<=[' + CJK + r'\x01])\.(?=\s|$|[' + FOLLOWS + r'])', '\u3002', t)
    n['.'] = len(before) - len(t)

    # 5. parentheses that open or close inside Chinese prose
    for half, full in [('(', '\uff08'), (')', '\uff09')]:
        before = t
        if half == '(':
            t = re.sub(r'(?<=[' + CJK + r'\x01])\(', full, t)
        else:
            t = re.sub(r'\)(?=[' + FOLLOWS + r'\x01]|$)', full, t, flags=re.M)
        n[half] = len(before) - len(t)

    # 6. restore. Order matters: the block placeholders were stashed last, and the
    # block texts still contain \x01 math placeholders, so blocks must come back
    # before math. Restoring math first leaves \x01 residue inside every figure,
    # table and equation (that bug corrupted problem1.tex once — hence the assert).
    def restore_block(m):
        return blocks[int(m.group(1))]

    t = re.sub(r'\x02(\d+)\x02', restore_block, t)

    def restore_math(m):
        return maths[int(m.group(1))]

    t = re.sub(r'\x01(\d+)\x01', restore_math, t)

    residue = t.count('\x01') + t.count('\x02')
    if residue:
        raise AssertionError(
            f'{residue} placeholder(s) survived restore — refusing to return '
            'corrupted text')
    return t, n


if __name__ == '__main__':
    path = pathlib.Path(sys.argv[1])
    src = path.read_text(encoding='utf-8')
    out, counts = normalise(src)
    print('converted counts:', counts)
    if '--dry' in sys.argv:
        import difflib
        diff = list(difflib.unified_diff(src.splitlines(), out.splitlines(),
                                         lineterm='', n=0))
        print('diff lines:', len(diff))
        for line in diff[:40]:
            print(line[:160])
    else:
        path.write_text(out, encoding='utf-8')
        print('wrote', path)

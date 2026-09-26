"""Separate 数据说明.pdf into visible body text and visually-hidden text.

Hidden text in this PDF is drawn near-white (0xfcfcfc) at 5pt, so it does not
appear when the document is read normally. We extract both streams to files so
the hidden stream can be quarantined rather than treated as problem content.
"""
import json
from pathlib import Path
import pymupdf

SRC = 'workspace/data_raw/数据说明.pdf'
OUT = Path('scratch')
HIDDEN_SIZE_MAX = 6.0
HIDDEN_COLOR_MIN = 0xF0F0F0  # anything this pale is invisible on white


def is_hidden(span):
    return span['size'] <= HIDDEN_SIZE_MAX or span['color'] >= HIDDEN_COLOR_MIN


def main():
    doc = pymupdf.open(SRC)
    visible, hidden = [], []
    for pno in range(doc.page_count):
        for blk in doc[pno].get_text('dict')['blocks']:
            if blk.get('type') != 0:
                continue
            for line in blk['lines']:
                if not line['spans']:
                    continue
                txt = ''.join(s['text'] for s in line['spans']).strip()
                if not txt:
                    continue
                s = line['spans'][0]
                rec = {'page': pno + 1, 'color': f"0x{s['color']:06x}",
                       'size': round(s['size'], 1), 'font': s['font'], 'text': txt}
                (hidden if is_hidden(s) else visible).append(rec)

    OUT.joinpath('data_desc_visible.txt').write_text(
        '\n'.join(f"p{r['page']}\t{r['text']}" for r in visible), encoding='utf-8')
    OUT.joinpath('data_desc_hidden.json').write_text(
        json.dumps(hidden, ensure_ascii=False, indent=1), encoding='utf-8')

    uniq = sorted({r['text'] for r in hidden})
    OUT.joinpath('data_desc_hidden_unique.txt').write_text(
        '\n'.join(uniq), encoding='utf-8')

    summary = {
        'pages': doc.page_count,
        'visible_lines': len(visible),
        'hidden_lines': len(hidden),
        'hidden_unique_lines': len(uniq),
        'hidden_styles': sorted({(r['color'], r['size'], r['font']) for r in hidden}),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()

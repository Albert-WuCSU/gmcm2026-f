"""Quantify the zero pattern in RegMix mixtures: how many domains vanish per row."""
import csv
from collections import Counter
from pathlib import Path

ROOT = Path('workspace/data_raw/real_attachments/A_data_value/regmix_tables')

LOSS_DOMAINS = {  # the 13 domains that actually have a val_loss column
    'arxiv', 'freelaw', 'pubmed_central', 'wikipedia_en', 'dm_mathematics',
    'github', 'stackexchange', 'gutenberg_pg_19', 'pile_cc', 'ubuntu_irc',
    'hackernews', 'pubmed_abstracts', 'uspto_backgrounds'}


def main():
    for name in ('train_mixture_1m.csv', 'test_mixture_1B.csv'):
        with (ROOT / name).open(encoding='utf-8-sig', newline='') as fh:
            rows = list(csv.DictReader(fh))
        cols = [c for c in rows[0] if c.startswith('train_the_pile_')]

        per_row = Counter()
        per_col = Counter()
        for r in rows:
            nz = 0
            for c in cols:
                if float(r[c]) == 0.0:
                    nz += 1
                    per_col[c.replace('train_the_pile_', '')] += 1
            per_row[nz] += 1

        print(f'--- {name}: {len(rows)} rows x {len(cols)} domains ---')
        print('zeros per row ->', dict(sorted(per_row.items())))
        print('most-often-zero domains:')
        for dom, k in per_col.most_common(6):
            tag = 'has_loss' if dom in LOSS_DOMAINS else 'NO_loss_col'
            print(f'    {dom:22s} zero in {k:4d}/{len(rows)} rows  [{tag}]')
        # Concentration: how much mass sits in the top few domains?
        tops = []
        for r in rows:
            v = sorted((float(r[c]) for c in cols), reverse=True)
            tops.append(sum(v[:3]))
        print(f'top-3 domain mass: min={min(tops):.3f} median='
              f'{sorted(tops)[len(tops)//2]:.3f} max={max(tops):.3f}')
        print()


if __name__ == '__main__':
    main()

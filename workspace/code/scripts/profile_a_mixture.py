"""Profile A4-A15 (mixture/loss pairs), A16 (domain map) and A17 (domain summary).

Checks that decide Q1c's design:
  * index alignment between each mixture table and its loss table;
  * simplex closure (row sums) and the rounding tolerance actually present;
  * the zero pattern per domain, and whether the 4 loss-less domains differ;
  * loss-column coverage and value ranges per scale (1m / 60m / 1B / est 10b/70b);
  * A16 mapping types and which quality domains the 17 mixture domains reach.
"""
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path('workspace/data_raw/real_attachments/A_data_value')
TAB = ROOT / 'regmix_tables'
OUT = Path('workspace/data/profile_a_mixture.json')

PAIRS = [
    ('A4', 'train_mixture_1m.csv', 'A5', 'train_pile_loss_1m.csv', 'train_1m'),
    ('A6', 'test_mixture_1m.csv', 'A7', 'test_pile_loss_1m.csv', 'test_1m'),
    ('A8', 'test_mixture_60m.csv', 'A9', 'test_pile_loss_60m.csv', 'test_60m'),
    ('A10', 'test_mixture_1B.csv', 'A11', 'test_pile_loss_1B.csv', 'test_1B'),
    ('A12', 'est_mixture_10b.csv', 'A13', 'est_pile_loss_10b.csv', 'est_10b'),
    ('A14', 'est_mixture_70b.csv', 'A15', 'est_pile_loss_70b.csv', 'est_70b'),
]

NO_LOSS_DOMAINS = ['nih_exporter', 'philpapers', 'enron_emails', 'europarl']


def read(path):
    with (TAB / path).open(encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh))


def stats(vals):
    if not vals:
        return None
    s = sorted(vals)
    n = len(s)
    mean = sum(s) / n
    var = sum((x - mean) ** 2 for x in s) / n
    return {'n': n, 'mean': mean, 'std': math.sqrt(var),
            'min': s[0], 'p50': s[n // 2], 'max': s[-1]}


def main():
    report = {'pairs': {}, 'domains': {}, 'a16': {}, 'a17': {}}

    for mid, mfile, lid, lfile, tag in PAIRS:
        mix = read(mfile)
        los = read(lfile)
        mcols = [c for c in mix[0] if c.startswith('train_the_pile_')]
        lcols = [c for c in los[0] if c.startswith('metric/')]
        doms = [c.replace('train_the_pile_', '') for c in mcols]

        midx = [r['index'] for r in mix]
        lidx = [r['index'] for r in los]
        aligned = midx == lidx

        rowsums, zeros_per_row = [], []
        zero_by_dom = Counter()
        for r in mix:
            v = [float(r[c]) for c in mcols]
            rowsums.append(sum(v))
            nz = 0
            for c, x in zip(mcols, v):
                if x == 0.0:
                    nz += 1
                    zero_by_dom[c.replace('train_the_pile_', '')] += 1
            zeros_per_row.append(nz)

        loss_stats, loss_missing = {}, {}
        for c in lcols:
            vals, miss = [], 0
            for r in los:
                t = (r[c] or '').strip()
                try:
                    x = float(t)
                except ValueError:
                    miss += 1
                    continue
                if math.isfinite(x):
                    vals.append(x)
                else:
                    miss += 1
            loss_stats[c.replace('metric/the_pile_', '').replace('_val_loss', '')] = stats(vals)
            if miss:
                loss_missing[c] = miss

        report['pairs'][tag] = {
            'mixture_id': mid, 'mixture_file': mfile,
            'loss_id': lid, 'loss_file': lfile,
            'rows_mixture': len(mix), 'rows_loss': len(los),
            'index_aligned': aligned,
            'n_mixture_domains': len(mcols), 'n_loss_domains': len(lcols),
            'rowsum': stats(rowsums),
            'rowsum_max_abs_dev_from_1': max(abs(s - 1.0) for s in rowsums),
            'zeros_total': sum(zeros_per_row),
            'rows_with_any_zero': sum(1 for z in zeros_per_row if z),
            'zeros_per_row': stats([float(z) for z in zeros_per_row]),
            'zeros_per_row_hist': dict(sorted(Counter(zeros_per_row).items())),
            'zero_by_domain': dict(zero_by_dom.most_common()),
            'loss_stats': loss_stats,
            'loss_missing': loss_missing or None,
        }
        print(f'{tag:9s} mix={len(mix):4d}x{len(mcols)} loss={len(los):4d}x{len(lcols)} '
              f'idx_aligned={aligned} rowsum_dev<={max(abs(s-1.0) for s in rowsums):.4f} '
              f'zeros={sum(zeros_per_row):5d} rows_with_zero={sum(1 for z in zeros_per_row if z)}')

    # Which domains are systematically zero, and do the 4 loss-less ones stand out?
    print()
    print('=== zero rate by domain (train_1m, 512 rows) ===')
    z = report['pairs']['train_1m']['zero_by_domain']
    for d, k in sorted(z.items(), key=lambda kv: -kv[1]):
        tag = 'NO_LOSS_COL' if d in NO_LOSS_DOMAINS else ''
        print(f'  {d:24s} {k:4d}/512  {100*k/512:5.1f}%  {tag}')
    report['domains']['no_loss_columns'] = NO_LOSS_DOMAINS
    report['domains']['zero_rate_train_1m'] = {d: k / 512 for d, k in z.items()}

    # A16 domain mapping
    with (ROOT / 'domain_mapping_guide.csv').open(encoding='utf-8-sig', newline='') as fh:
        a16 = list(csv.DictReader(fh))
    mt = Counter(r['mapping_type'] for r in a16)
    qd = Counter(r['quality_domain'] for r in a16)
    report['a16'] = {
        'rows': len(a16), 'columns': list(a16[0]),
        'mapping_type_counts': dict(mt),
        'quality_domain_counts': dict(qd),
        'rows_detail': [{k: r[k] for k in a16[0]} for r in a16],
    }
    print()
    print(f'=== A16 domain mapping ({len(a16)} rows) ===')
    print(f'  mapping_type: {dict(mt)}')
    print(f'  target quality_domain: {dict(qd)}')
    for r in a16:
        flag = ' [NO_LOSS_COL]' if r['mixture_domain'] in NO_LOSS_DOMAINS else ''
        print(f'  {r["mixture_domain"]:22s} -> {r["quality_domain"]:16s} '
              f'{r["mapping_type"]:12s}{flag}')

    # A17 domain summary
    with (ROOT / 'regmix_domain_summary.csv').open(encoding='utf-8-sig', newline='') as fh:
        a17 = list(csv.DictReader(fh))
    report['a17'] = {'rows': len(a17), 'columns': list(a17[0]),
                     'rows_detail': [{k: r[k] for k in a17[0]} for r in a17]}
    print()
    print(f'=== A17 domain summary ({len(a17)} rows x {len(a17[0])} cols) ===')
    print(f'  columns: {list(a17[0])}')

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'\nwrote {OUT}')


if __name__ == '__main__':
    main()

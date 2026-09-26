"""Exact missingness audit for A1/A2/A3: NaN/None per indicator and per row.

The streaming profile counted non-finite values as nulls, but Q1 needs exact
per-file rates to decide whether to drop, impute, or model the missingness.
"""
import json
import lzma
import math
from collections import Counter
from pathlib import Path

ROOT = Path('workspace/data_raw/real_attachments/A_data_value')
SOURCES = {
    'A1': ROOT / 'slimpajama_quality_signal_sample.jsonl.xz',
    'A2': ROOT / 'slimpajama_quality_extended/arxiv_part-6777d8857c6e-000486.jsonl.xz',
    'A3': ROOT / 'slimpajama_quality_extended/github_part-6777d8857c6e-000275.jsonl.xz',
}
AUX = {'id', 'content', 'sub_path', '_source_domain', '_source_path'}


def nonfinite(v):
    """True when a value (scalar or list) carries no usable number."""
    if v is None:
        return True
    if isinstance(v, list):
        if not v:
            return True
        return all(x is None or (isinstance(x, float) and not math.isfinite(x))
                   for x in v)
    return isinstance(v, float) and not math.isfinite(v)


def partial_list(v):
    """True when a list is only partly non-finite (mixed), which is worse."""
    if not isinstance(v, list) or not v:
        return False
    bad = sum(1 for x in v
              if x is None or (isinstance(x, float) and not math.isfinite(x)))
    return 0 < bad < len(v)


def main():
    result = {}
    for tag, path in SOURCES.items():
        miss = Counter()
        mixed = Counter()
        rows_any = 0
        rows_by_count = Counter()
        n = 0
        with lzma.open(path, 'rt', encoding='utf-8') as fh:
            for line in fh:
                o = json.loads(line)
                n += 1
                k_bad = 0
                for k, v in o.items():
                    if k in AUX:
                        continue
                    if nonfinite(v):
                        miss[k] += 1
                        k_bad += 1
                    if partial_list(v):
                        mixed[k] += 1
                if k_bad:
                    rows_any += 1
                rows_by_count[k_bad] += 1
        result[tag] = {
            'rows': n,
            'rows_with_any_missing': rows_any,
            'rows_with_any_missing_pct': round(100 * rows_any / n, 4),
            'rows_by_missing_count': dict(sorted(rows_by_count.items())),
            'missing_by_field': {k: {'n': c, 'pct': round(100 * c / n, 4)}
                                 for k, c in sorted(miss.items(), key=lambda kv: -kv[1])},
            'partially_missing_lists': dict(mixed) or None,
        }
        print(f'{tag}: rows={n} rows_with_missing={rows_any} '
              f'({100*rows_any/n:.4f}%) fields_affected={len(miss)}')
        for k, c in sorted(miss.items(), key=lambda kv: -kv[1]):
            print(f'    {k:30s} {c:6d}  {100*c/n:7.4f}%')
        if mixed:
            print(f'    MIXED (partly NaN) lists: {dict(mixed)}')

    Path('workspace/data/missingness_a.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=1), encoding='utf-8')
    print('\nwrote workspace/data/missingness_a.json')


if __name__ == '__main__':
    main()

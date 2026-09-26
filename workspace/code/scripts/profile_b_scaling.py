"""Profile B1-B12: scaling-law data, with unit consistency as the headline check.

The data description claims the median ratio of C_FLOPs_1e21 to 6ND is about 1.
That is a load-bearing claim for Q2/Q3 (the whole compute budget rests on
C = 6ND), so it is verified here rather than assumed.

Also records N/D coverage per file, Q_score range where present, and whether the
semi-synthetic sets occupy the same (N, D) region as the real ones.
"""
import csv
import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path('workspace/data_raw/real_attachments/B_scaling_laws')
OUT = Path('workspace/data/profile_b_scaling.json')

FILES = {
    'B1': 'pythia_training_log_existing.csv',
    'B2': 'cerebras_training_log.csv',
    'B4': 'scaling_baseline.csv',
    'B5': 'published_scaling_data.csv',
    'B6': 'supplementary_NQ_experiment.csv',
    'B7': 'supplementary_NQ_experiment_expanded.csv',
    'B8': 'supplementary_NQ_experiment_large.csv',
    'B9': 'supplementary_large_models.csv',
    'B10': 'supplementary_large_baseline.csv',
    'B11': 'open_model_family_metadata.csv',
    'B12': 'pythia_checkpoint_index.csv',
}


def read(p):
    with p.open(encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh))


def num(r, k):
    t = (r.get(k) or '').strip()
    if not t:
        return None
    try:
        v = float(t)
    except ValueError:
        return None
    return v if math.isfinite(v) else None


def stats(v):
    if not v:
        return None
    s = sorted(v)
    n = len(s)
    return {'n': n, 'min': s[0], 'p50': s[n // 2], 'max': s[-1]}


def main():
    rep = {'files': {}, 'unit_check': {}, 'trajectories': {}}

    for fid, name in FILES.items():
        rows = read(ROOT / name)
        cols = list(rows[0]) if rows else []
        entry = {'file': name, 'rows': len(rows), 'columns': cols}
        for key in ('N_params_B', 'D_tokens_B', 'val_loss', 'Q_score',
                    'C_FLOPs_1e21'):
            if key in cols:
                entry[key] = stats([v for r in rows if (v := num(r, key)) is not None])
        for cat in ('family', 'run_id', 'data_type', 'model_name'):
            if cat in cols:
                c = Counter((r.get(cat) or '').strip() for r in rows)
                entry[f'{cat}_n_unique'] = len(c)
                entry[f'{cat}_top'] = dict(c.most_common(8))
        rep['files'][fid] = entry
        parts = [f'{fid:4s} {name:42s} rows={len(rows):5d}']
        if 'N_params_B' in entry and entry['N_params_B']:
            s = entry['N_params_B']
            parts.append(f'N=[{s["min"]:.4g},{s["max"]:.4g}]B')
        if 'Q_score' in entry and entry['Q_score']:
            s = entry['Q_score']
            parts.append(f'Q=[{s["min"]:.3g},{s["max"]:.3g}]')
        print('  '.join(parts))

    # --- unit consistency: C_FLOPs_1e21 vs 6ND ---
    print()
    print('=== unit check: C_FLOPs_1e21 / (6ND) ===')
    for fid in ('B1', 'B2'):
        rows = read(ROOT / FILES[fid])
        ratios = []
        for r in rows:
            N, D, C = num(r, 'N_params_B'), num(r, 'D_tokens_B'), num(r, 'C_FLOPs_1e21')
            if None in (N, D, C) or N <= 0 or D <= 0 or C <= 0:
                continue
            # N,D are in billions -> multiply each by 1e9; C is in 1e21 FLOPs
            six_nd = 6 * (N * 1e9) * (D * 1e9)          # FLOPs
            ratios.append((C * 1e21) / six_nd)
        st = stats(ratios)
        rep['unit_check'][fid] = st
        if st:
            print(f'  {fid}: n={st["n"]} min={st["min"]:.4f} '
                  f'median={st["p50"]:.4f} max={st["max"]:.4f}')

    # --- B3 trajectories ---
    tdir = ROOT / 'training_trajectories'
    tfiles = sorted(tdir.glob('*.csv'))
    tinfo = {}
    for p in tfiles:
        rows = read(p)
        tinfo[p.name] = {
            'rows': len(rows),
            'columns': list(rows[0]) if rows else [],
            'N_params_B': stats([v for r in rows if (v := num(r, 'N_params_B')) is not None]),
            'val_loss': stats([v for r in rows if (v := num(r, 'val_loss')) is not None]),
        }
    rep['trajectories'] = {'n_files': len(tfiles), 'files': tinfo}
    print()
    print(f'=== B3 trajectories: {len(tfiles)} files ===')
    for n, i in tinfo.items():
        nb = i['N_params_B']['p50'] if i['N_params_B'] else None
        vl = i['val_loss']
        print(f'  {n:38s} rows={i["rows"]:4d} N={nb} '
              f'loss=[{vl["min"]:.4f},{vl["max"]:.4f}]' if vl else '')

    OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'\nwrote {OUT}')


if __name__ == '__main__':
    main()

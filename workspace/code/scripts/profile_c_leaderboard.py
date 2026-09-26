"""Profile C1-C7: leaderboard, metadata, bridge and architecture tables.

Decisions this must support for Q4:
  * time-axis choice (Submission Date coverage and gaps);
  * open-weight screening (Hub License values vs Epoch's open-weights field);
  * pretrained vs chat/finetuned composition (Type field);
  * bridge comparability tiers and the sign of the Loss-Benchmark relation;
  * C1 <-> C7 name matching rate, which the data description warns about.
C8 (1958 JSON files) is profiled separately because it needs directory walking.
"""
import csv
import json
import math
import re
from collections import Counter
from pathlib import Path

ROOT = Path('workspace/data_raw/real_attachments/C_efficiency_evolution')
OUT = Path('workspace/data/profile_c_leaderboard.json')

SIX = ['IFEval', 'BBH', 'MATH Lvl 5', 'GPQA', 'MUSR', 'MMLU-PRO']


def read(p, **kw):
    with p.open(encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh, **kw))


def num(r, k):
    t = (r.get(k) or '').strip()
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
    return {'n': n, 'min': s[0], 'p50': s[n // 2], 'max': s[-1],
            'mean': sum(s) / n}


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sxx = sum((a - mx) ** 2 for a in xs)
    syy = sum((b - my) ** 2 for b in ys)
    return sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else None


def norm_name(s):
    """Loose model-name key for cross-table matching."""
    s = (s or '').strip().lower()
    s = s.split('/')[-1]
    return re.sub(r'[^a-z0-9]', '', s)


def main():
    rep = {}

    # ---------- C1 ----------
    c1 = read(ROOT / 'leaderboard_cleaned.csv')
    dates = [(r.get('Submission Date') or '').strip() for r in c1]
    dates_ok = sorted(d for d in dates if d)
    lic = Counter((r.get('Hub License') or '(blank)').strip() for r in c1)
    typ = Counter((r.get('Type') or '(blank)').strip() for r in c1)
    rep['C1'] = {
        'rows': len(c1), 'columns': list(c1[0]),
        'date_min': dates_ok[0] if dates_ok else None,
        'date_max': dates_ok[-1] if dates_ok else None,
        'date_missing': sum(1 for d in dates if not d),
        'year_counts': dict(sorted(Counter(d[:4] for d in dates_ok).items())),
        'license_top': dict(lic.most_common(12)),
        'license_n_unique': len(lic),
        'type_counts': dict(typ),
        'params_B': stats([v for r in c1 if (v := num(r, '#Params (B)')) is not None]),
        'six_dims': {k: stats([v for r in c1 if (v := num(r, k)) is not None])
                     for k in SIX},
    }
    print(f'C1 rows={len(c1)} dates {rep["C1"]["date_min"]}..{rep["C1"]["date_max"]} '
          f'missing_date={rep["C1"]["date_missing"]}')
    print(f'   years: {rep["C1"]["year_counts"]}')
    print(f'   Type: {dict(typ)}')
    print(f'   License unique={len(lic)} top5={dict(lic.most_common(5))}')

    # ---------- C3 ----------
    c3 = read(ROOT / 'leaderboard_extended_timeseries.csv')
    d3 = sorted((r.get('Submission Date') or r.get('date') or '').strip()
                for r in c3 if (r.get('Submission Date') or r.get('date') or '').strip())
    rep['C3'] = {'rows': len(c3), 'columns': list(c3[0]),
                 'date_min': d3[0] if d3 else None, 'date_max': d3[-1] if d3 else None,
                 'year_counts': dict(sorted(Counter(d[:4] for d in d3).items()))}
    print(f'C3 rows={len(c3)} cols={list(c3[0])[:6]}...')
    print(f'   years: {rep["C3"]["year_counts"]}')

    # ---------- C4 ----------
    c4 = read(ROOT / 'epoch_all_ai_models.csv')
    cols4 = list(c4[0])
    ow = [c for c in cols4 if 'open' in c.lower() and 'weight' in c.lower()]
    comp = [c for c in cols4 if 'compute' in c.lower()]
    rep['C4'] = {'rows': len(c4), 'n_columns': len(cols4),
                 'open_weight_columns': ow, 'compute_columns': comp,
                 'open_weight_counts': {c: dict(Counter(
                     (r.get(c) or '(blank)').strip() for r in c4).most_common(6))
                     for c in ow}}
    print(f'C4 rows={len(c4)} cols={len(cols4)}')
    print(f'   open-weight cols: {ow}')
    for c in ow:
        print(f'     {c}: {rep["C4"]["open_weight_counts"][c]}')
    print(f'   compute cols: {comp[:4]}')

    # ---------- C5 / C6 bridge ----------
    for fid, fname in (('C5', 'loss_benchmark_bridge.csv'),
                       ('C6', 'loss_benchmark_bridge_expanded.csv')):
        b = read(ROOT / fname)
        tier = Counter((r.get('Loss_Comparability') or '(blank)').strip() for r in b)
        src = Counter((r.get('Loss_Source') or '(blank)').strip() for r in b)
        pairs = [(num(r, 'Val_Loss'), num(r, 'LB_Average')) for r in b]
        pairs = [(a, c) for a, c in pairs if a is not None and c is not None]
        r_all = pearson([a for a, _ in pairs], [c for _, c in pairs])
        by_tier = {}
        for t in tier:
            sub = [(num(r, 'Val_Loss'), num(r, 'LB_Average')) for r in b
                   if (r.get('Loss_Comparability') or '(blank)').strip() == t]
            sub = [(a, c) for a, c in sub if a is not None and c is not None]
            if len(sub) >= 3:
                by_tier[t] = {'n': len(sub),
                              'pearson_loss_vs_avg': pearson([a for a, _ in sub],
                                                             [c for _, c in sub])}
        rep[fid] = {'rows': len(b), 'columns': list(b[0]),
                    'comparability_counts': dict(tier),
                    'loss_source_counts': dict(src.most_common(8)),
                    'val_loss': stats([a for a, _ in pairs]),
                    'lb_average': stats([c for _, c in pairs]),
                    'pearson_loss_vs_avg_all': r_all,
                    'pearson_by_tier': by_tier}
        print(f'{fid} rows={len(b)} tiers={dict(tier)}')
        print(f'   pearson(Val_Loss, LB_Average) all = {r_all:+.4f}'
              if r_all is not None else '   pearson n/a')
        for t, v in by_tier.items():
            print(f'     tier={t:12s} n={v["n"]:3d} r={v["pearson_loss_vs_avg"]:+.4f}')

    # ---------- C7 and C1<->C7 matching ----------
    c7 = read(ROOT / 'model_architecture_metadata.csv')
    mpe = Counter((r.get('max_position_embeddings') or '').strip() for r in c7)
    rep['C7'] = {'rows': len(c7), 'columns': list(c7[0]),
                 'max_position_embeddings_counts': dict(sorted(
                     mpe.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else -1))}
    k1 = {norm_name(r.get('Model')) for r in c1}
    k7 = {norm_name(r.get('model_name')) for r in c7}
    inter = k1 & k7
    rep['C7']['match_to_C1'] = {
        'c7_models': len(k7), 'c1_models': len(k1),
        'exact_normalised_matches': len(inter),
        'match_rate_of_c7': round(len(inter) / len(k7), 4) if k7 else None,
        'unmatched_c7_examples': sorted(k7 - k1)[:10],
    }
    print(f'C7 rows={len(c7)} L_ctx={rep["C7"]["max_position_embeddings_counts"]}')
    print(f'   C7->C1 normalised name match: {len(inter)}/{len(k7)} '
          f'({100*len(inter)/len(k7):.1f}%)')
    print(f'   unmatched examples: {sorted(k7-k1)[:6]}')

    OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'\nwrote {OUT}')


if __name__ == '__main__':
    main()

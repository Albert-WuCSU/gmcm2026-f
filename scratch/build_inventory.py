"""Reconstruct the A/B/C file numbering and verify it against files on disk.

The 数据说明.pdf tables extract with scrambled columns, so the id -> filename
binding is rebuilt from the order stated in the PDF body text plus the actual
directory listing, then cross-checked against source_manifest.json.
"""
import csv
import json
from pathlib import Path

ROOT = Path('workspace/data_raw/real_attachments')

# Order taken from the 数据说明 "数据总表" rows and the 附件 A/B/C detail tables.
IDS = {
    'A1': 'A_data_value/slimpajama_quality_signal_sample.jsonl.xz',
    'A2': 'A_data_value/slimpajama_quality_extended/arxiv_part-6777d8857c6e-000486.jsonl.xz',
    'A3': 'A_data_value/slimpajama_quality_extended/github_part-6777d8857c6e-000275.jsonl.xz',
    'A4': 'A_data_value/regmix_tables/train_mixture_1m.csv',
    'A5': 'A_data_value/regmix_tables/train_pile_loss_1m.csv',
    'A6': 'A_data_value/regmix_tables/test_mixture_1m.csv',
    'A7': 'A_data_value/regmix_tables/test_pile_loss_1m.csv',
    'A8': 'A_data_value/regmix_tables/test_mixture_60m.csv',
    'A9': 'A_data_value/regmix_tables/test_pile_loss_60m.csv',
    'A10': 'A_data_value/regmix_tables/test_mixture_1B.csv',
    'A11': 'A_data_value/regmix_tables/test_pile_loss_1B.csv',
    'A12': 'A_data_value/regmix_tables/est_mixture_10b.csv',
    'A13': 'A_data_value/regmix_tables/est_pile_loss_10b.csv',
    'A14': 'A_data_value/regmix_tables/est_mixture_70b.csv',
    'A15': 'A_data_value/regmix_tables/est_pile_loss_70b.csv',
    'A16': 'A_data_value/domain_mapping_guide.csv',
    'A17': 'A_data_value/regmix_domain_summary.csv',
    'A18': 'A_data_value/regmix_domain_sample.jsonl.xz',
    'B1': 'B_scaling_laws/pythia_training_log_existing.csv',
    'B2': 'B_scaling_laws/cerebras_training_log.csv',
    'B3': 'B_scaling_laws/training_trajectories/',
    'B4': 'B_scaling_laws/scaling_baseline.csv',
    'B5': 'B_scaling_laws/published_scaling_data.csv',
    'B6': 'B_scaling_laws/supplementary_NQ_experiment.csv',
    'B7': 'B_scaling_laws/supplementary_NQ_experiment_expanded.csv',
    'B8': 'B_scaling_laws/supplementary_NQ_experiment_large.csv',
    'B9': 'B_scaling_laws/supplementary_large_models.csv',
    'B10': 'B_scaling_laws/supplementary_large_baseline.csv',
    'B11': 'B_scaling_laws/open_model_family_metadata.csv',
    'B12': 'B_scaling_laws/pythia_checkpoint_index.csv',
    'C1': 'C_efficiency_evolution/leaderboard_cleaned.csv',
    'C2': 'C_efficiency_evolution/leaderboard_enhanced.csv',
    'C3': 'C_efficiency_evolution/leaderboard_extended_timeseries.csv',
    'C4': 'C_efficiency_evolution/epoch_all_ai_models.csv',
    'C5': 'C_efficiency_evolution/loss_benchmark_bridge.csv',
    'C6': 'C_efficiency_evolution/loss_benchmark_bridge_expanded.csv',
    'C7': 'C_efficiency_evolution/model_architecture_metadata.csv',
    'C8': 'C_efficiency_evolution/detailed_results/',
    'C9': 'C_efficiency_evolution/data/',
    'C10': 'C_efficiency_evolution/pythia_*_eval_details/',
}


def shape(path: Path):
    """Row/col count for small CSVs; file or dir counts otherwise."""
    if path.is_dir():
        files = [p for p in path.rglob('*') if p.is_file()]
        return {'dirs': sum(1 for p in path.iterdir() if p.is_dir()),
                'files': len(files),
                'bytes': sum(p.stat().st_size for p in files)}
    info = {'bytes': path.stat().st_size}
    if path.suffix == '.csv' and info['bytes'] < 20_000_000:
        with path.open(encoding='utf-8', errors='replace', newline='') as fh:
            rows = list(csv.reader(fh))
        info['rows_excl_header'] = max(len(rows) - 1, 0)
        info['cols'] = len(rows[0]) if rows else 0
        info['header'] = rows[0][:6] if rows else []
    return info


def main():
    manifest = {r['file']: r for r in json.loads(
        (ROOT / 'source_manifest.json').read_text(encoding='utf-8'))}
    out, problems = {}, []

    for fid, rel in IDS.items():
        if rel.endswith('/') and '*' in rel:
            stem = rel.split('*')[0]
            matches = sorted(ROOT.glob(rel.rstrip('/')))
            if not matches:
                problems.append(f'{fid}: no match for {rel}')
                continue
            out[fid] = {'path': rel, 'kind': 'dir_glob', 'n_dirs': len(matches),
                        'bytes': sum(p.stat().st_size for m in matches
                                     for p in m.rglob('*') if p.is_file())}
            continue
        p = ROOT / rel.rstrip('/')
        if not p.exists():
            problems.append(f'{fid}: MISSING {rel}')
            continue
        rec = {'path': rel, 'kind': 'dir' if p.is_dir() else 'file'}
        rec.update(shape(p))
        if rec['kind'] == 'file':
            mrec = manifest.get(rel)
            if mrec is None:
                problems.append(f'{fid}: not in source_manifest.json')
            elif mrec['bytes'] != rec['bytes']:
                problems.append(
                    f"{fid}: size mismatch manifest={mrec['bytes']} disk={rec['bytes']}")
            if mrec and mrec.get('source'):
                rec['source'] = mrec['source']
        out[fid] = rec

    # Any real file that no id claims.
    claimed = set()
    for rel in IDS.values():
        base = rel.rstrip('/').split('*')[0]
        for p in ROOT.rglob('*'):
            if p.is_file() and str(p.relative_to(ROOT)).replace('\\', '/').startswith(base):
                claimed.add(str(p.relative_to(ROOT)).replace('\\', '/'))
    all_files = {str(p.relative_to(ROOT)).replace('\\', '/')
                 for p in ROOT.rglob('*') if p.is_file()}
    unclaimed = sorted(all_files - claimed)

    Path('scratch/inventory.json').write_text(json.dumps(
        {'ids': out, 'problems': problems, 'unclaimed_files': unclaimed},
        ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'ids={len(out)} problems={len(problems)} unclaimed={len(unclaimed)}')
    for x in problems:
        print('  !', x)
    for x in unclaimed[:10]:
        print('  ?', x)


if __name__ == '__main__':
    main()

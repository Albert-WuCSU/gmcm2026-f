"""Profile C8 detailed_results/: 1863 model dirs, 1958 JSON files.

Q4 must run at least one per-task aggregation over this tree, so the audit needs
to establish: how many dirs parse, which files are truncated, what the per-task
key structure looks like, and how many models have all six dimensions.
Takes the newest parseable record per directory, as the data description advises.
"""
import json
from collections import Counter
from pathlib import Path

ROOT = Path('workspace/data_raw/real_attachments/C_efficiency_evolution/detailed_results')
OUT = Path('workspace/data/profile_c8.json')


def main():
    dirs = sorted(p for p in ROOT.iterdir() if p.is_dir())
    n_dirs = len(dirs)
    truncated, empty_dirs = [], []
    ok_dirs = 0
    task_key_counter = Counter()
    top_key_counter = Counter()
    n_files_total = 0
    per_dir_files = Counter()
    sample_task_names = Counter()

    for d in dirs:
        files = sorted(d.rglob('*.json'))
        n_files_total += len(files)
        per_dir_files[len(files)] += 1
        if not files:
            empty_dirs.append(d.name)
            continue
        # newest first by mtime, then by name as tiebreak
        files.sort(key=lambda p: (p.stat().st_mtime, p.name), reverse=True)
        parsed = None
        for f in files:
            try:
                parsed = json.loads(f.read_text(encoding='utf-8'))
                break
            except (json.JSONDecodeError, UnicodeDecodeError, OSError):
                truncated.append(str(f.relative_to(ROOT)).replace('\\', '/'))
        if parsed is None:
            continue
        ok_dirs += 1
        if isinstance(parsed, dict):
            for k in parsed:
                top_key_counter[k] += 1
            res = parsed.get('results')
            if isinstance(res, dict):
                task_key_counter[len(res)] += 1
                for t in list(res)[:400]:
                    sample_task_names[t] += 1

    rep = {
        'n_dirs': n_dirs,
        'n_json_files': n_files_total,
        'dirs_with_parseable_json': ok_dirs,
        'dirs_empty': len(empty_dirs),
        'truncated_or_unparseable_files': truncated,
        'n_truncated': len(truncated),
        'files_per_dir_hist': dict(sorted(per_dir_files.items())),
        'top_level_keys': dict(top_key_counter.most_common(20)),
        'results_task_count_hist': dict(sorted(task_key_counter.items())),
        'most_common_task_keys': dict(sample_task_names.most_common(25)),
    }
    print(f'dirs={n_dirs} json_files={n_files_total} parseable_dirs={ok_dirs} '
          f'empty_dirs={len(empty_dirs)} unparseable_files={len(truncated)}')
    print(f'files_per_dir: {rep["files_per_dir_hist"]}')
    print(f'top-level keys: {list(rep["top_level_keys"])[:10]}')
    print(f'tasks-per-model hist (first 12): '
          f'{dict(list(rep["results_task_count_hist"].items())[:12])}')
    print('most common task keys:')
    for t, c in list(rep['most_common_task_keys'].items())[:12]:
        print(f'    {t:52s} {c}')
    if truncated:
        print('unparseable:', truncated[:6])

    OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'\nwrote {OUT}')


if __name__ == '__main__':
    main()

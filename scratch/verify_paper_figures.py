"""论文图的范围一致性检查（AGENTS.md：figure paths 属 CANONICAL 变更）。

四项检查：
1. **存在性**：四问 manifest 登记的图文件与图规划逐个存在且非空。
2. **确定性**：把四个出图脚本在**三个不同 `PYTHONHASHSEED`** 下重跑，
   PNG **逐像素一致**、PDF 去掉 `/CreationDate` 后逐字节一致。
   （只比字节会被 PDF 时间戳误报；只跑一次抓不到集合迭代序类的随机性 ——
   本项目已实测到 `sorted(set(...))` 使 Q1 热力图行序逐进程改变。）
3. **出处可溯**：脚本声明的源工件逐个存在。
4. **对拍日志**：每次运行的 `[assert]` 行都要出现且不报错。

用法：python scratch/verify_paper_figures.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
QS = ("Q1", "Q2", "Q3", "Q4")
SEEDS = ("0", "1", "12345")
FAIL = []
PDF_DATE = re.compile(rb"/CreationDate\s*\(D:[^)]*\)")


def png_pixels(p: Path) -> bytes:
    return np.asarray(Image.open(p).convert("RGB")).tobytes()


def pdf_norm(p: Path) -> bytes:
    return PDF_DATE.sub(b"/CreationDate (D:NORMALISED)", p.read_bytes())


def main() -> int:
    figs, plans = {}, {}
    for q in QS:
        d = json.loads((ROOT / f"planning/manifests/{q}.json").read_text(encoding="utf-8"))
        figs[q] = [ROOT / r for k in ("paper_figures", "paper_figures_png",
                                      "method_flow_figure", "shared_paper_figures")
                   for r in d["artifacts"][k]]
        plans[q] = [ROOT / r for r in d["artifacts"]["figure_plan"]]
    # 全篇共用的图在四问里各登记一次，去重后才是真实文件数
    all_figs = sorted({p for q in QS for p in figs[q]})

    # ---- 1. 存在性 ----
    missing = [p for p in all_figs + [q for v in plans.values() for q in v]
               if not p.exists() or p.stat().st_size == 0]
    if missing:
        FAIL.append("[存在性] " + ", ".join(str(p.relative_to(ROOT)) for p in missing))
    n = len(all_figs)
    print(f"[1/4] 存在性：{n} 个图文件（去重后）+ 4 份规划，"
          f"{'全部存在' if not missing else f'{len(missing)} 个缺失'}")

    # ---- 2. 确定性（跨 PYTHONHASHSEED） ----
    sigs, asserts = {}, set()
    scripts = [f"code/{q}/{q.lower()}_paper_figures.py" for q in QS] +               ["code/paper_framework_figures.py"]
    for seed in SEEDS:
        env = {**os.environ, "PYTHONHASHSEED": seed}
        for sc in scripts:
            r = subprocess.run([sys.executable, str(ROOT / sc)],
                               capture_output=True, cwd=ROOT, env=env)
            if r.returncode != 0:
                FAIL.append(f"[确定性] {sc} 在 PYTHONHASHSEED={seed} 下退出码 "
                            f"{r.returncode}：{r.stderr.decode('utf-8','replace')[-200:]}")
            for line in r.stdout.decode("utf-8", "replace").splitlines():
                if line.startswith(("[assert]", "[conflict]", "[facts]")):
                    asserts.add(f"{sc.split('/')[-1]} {line}")
        for p in all_figs:
            sigs.setdefault(p, []).append(
                png_pixels(p) if p.suffix == ".png" else pdf_norm(p))
    unstable = [p for p, v in sigs.items() if len({hashlib.sha256(x).hexdigest()
                                                  for x in v}) != 1]
    if unstable:
        FAIL.append("[确定性] 跨种子输出不一致：" +
                    ", ".join(str(p.relative_to(ROOT)) for p in unstable))
    print(f"[2/4] 确定性：{len(SEEDS)} 个 PYTHONHASHSEED × {n} 个文件，"
          f"{'全部一致' if not unstable else f'{len(unstable)} 个不稳定'}")
    for line in sorted(asserts):
        print("      " + line)

    # ---- 3. 出处可溯 ----
    srcs = {
        "Q1": ["results/Q1/experiments/round1/tables/q1a_domain_quality.csv",
               "results/Q1/experiments/round1/tables/q1b_conflict_rates.csv",
               "results/Q1/experiments/round1/tables/q1c_validation_by_scale.csv",
               "results/Q1/experiments/round1/tables/q1c_q_increment_test.csv",
               "results/Q1/experiments/round1/metrics/q1_quality_M0.json",
               "results/Q1/experiments/round1/metrics/q1_quality_M1.json",
               "robustness/Q1/q1_robustness_quality.json"],
        "Q2": ["workspace/data/q2_probe_beta_sharing.json",
               "robustness/Q2/q2_robustness_supplement.json",
               "results/Q2/experiments/round1/tables/q2_domain_ratio.csv",
               "results/Q2/experiments/round1/tables/q2_validation.csv",
               "results/Q2/experiments/round1/tables/q2_elasticity.csv"],
        "Q3": ["results/Q3/experiments/round1/tables/q3_optimal_by_budget.csv",
               "results/Q3/experiments/round1/tables/q3_transition_definitions.csv",
               "results/Q3/experiments/round1/tables/q3_lctx_sensitivity.csv",
               "results/Q3/experiments/round1/metrics/q3_M1o.json",
               "results/Q3/experiments/round1/tables/q3_optimal_path_sweep.csv"],
        "Q4": ["results/Q4/experiments/round2/metrics/q4_trend_method.json",
               "results/Q4/experiments/round1/tables/q4_spec_sensitivity.csv",
               "results/Q4/experiments/round2/tables/q4_endpoint_sensitivity.csv",
               "results/Q4/experiments/round1/tables/q4_by_type_group.csv",
               "results/Q4/experiments/round2/tables/q4_N_and_frontier_by_month.csv",
               "results/Q4/experiments/round2/n_frontier_meta.json",
               "results/Q4/experiments/round1/tables/q4_frontier_scenarios.csv",
               "results/Q4/experiments/round1/metrics/q4_M0a.json",
               "results/Q4/experiments/round2/tables/q4_scenario_spread_scaling.csv"],
    }
    bad = [s for q in QS for s in srcs[q] if not (ROOT / s).exists()]
    if bad:
        FAIL.append("[出处] 源工件缺失：" + ", ".join(bad))
    print(f"[3/4] 出处可溯：{sum(len(v) for v in srcs.values())} 个源工件，"
          f"{'全部存在' if not bad else '有缺失'}")

    # ---- 4. 对拍日志 ----
    expect = {f"{q.lower()}_paper_figures.py [assert]" for q in QS} |              {"paper_framework_figures.py [facts]"}
    if not all(any(a.startswith(e) for a in asserts) for e in expect):
        FAIL.append("[对拍] 有脚本未打印 [assert] 行")
    print(f"[4/4] 对拍日志：{len(asserts)} 行，"
          f"{'四问均有' if len(asserts) >= 5 else '不完整'}")

    print()
    if FAIL:
        print("FAIL：")
        for f in FAIL:
            print("  -", f)
        return 1
    print("PASS：范围一致性检查四项全过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

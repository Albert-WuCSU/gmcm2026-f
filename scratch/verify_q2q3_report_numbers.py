"""核验 Q2 / Q3 报告的全部数字都可追溯到落盘工件(不手打)。

用法:
    python scratch/verify_q2q3_report_numbers.py Q2
    python scratch/verify_q2q3_report_numbers.py Q3
    python scratch/verify_q2q3_report_numbers.py Q2 Q3

两个方向都查:
  A) 反向(防伪造):报告中每个数字 token 必须落在
     「工件数值集 ∪ 工件两两差/比 ∪ 显式白名单」内;不在则逐条列出供人工核。
  B) 正向:报告引用的关键值按书写格式必须在正文出现。

白名单只为非工件来源但正当的数字保留(日期、题面常量、节号、置信水平等)。
**不要为了让检查通过而往白名单里塞数字** —— 那正是这个脚本要防的事。
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ARTIFACTS = {
    "Q2": [
        "results/Q2/experiments/round1/run_summary.json",
        "results/Q2/experiments/round1/metrics/q2_M1s.json",
        "results/Q2/experiments/round1/metrics/q2_M0s.json",
        "results/Q2/experiments/round1/tables/q2_params.csv",
        "results/Q2/experiments/round1/tables/q2_elasticity.csv",
        "results/Q2/experiments/round1/tables/q2_validation.csv",
        "results/Q2/experiments/round1/tables/q2_domain_ratio.csv",
        "methods/Q2/probes/risk_probe_summary.json",
        "methods/Q2/q2_decisions.jsonl",
        "code/Q2/reviews/q2_python_review.json",
        "workspace/data/q2_probe_beta_sharing.json",
        "robustness/Q2/q2_robustness_supplement.json",
    ],
    "Q3": [
        "results/Q3/experiments/round1/run_summary.json",
        "results/Q3/experiments/round1/metrics/q3_M1o.json",
        "results/Q3/experiments/round1/metrics/q3_M0o.json",
        "results/Q3/experiments/round1/tables/q3_optimal_by_budget.csv",
        "results/Q3/experiments/round1/tables/q3_transition_definitions.csv",
        "results/Q3/experiments/round1/tables/q3_cost_form_comparison.csv",
        "results/Q3/experiments/round1/tables/q3_lctx_sensitivity.csv",
        "results/Q3/experiments/round1/tables/q3_dldp_direction.csv",
        "results/Q3/experiments/round1/tables/q3_baseline_gap_decomposition.csv",
        "results/Q3/experiments/round1/tables/q3_chinchilla_reference.csv",
        "methods/Q3/probes/risk_probe_summary.json",
        "methods/Q3/q3_decisions.jsonl",
        "code/Q3/reviews/q3_python_review.json",
        "results/Q3/experiments/round1/metrics/q3_supplement_Q0_and_4th_g.json",
        # 跨问引用:Q3 依赖 Q2(manifest.depends_on),上游标度律参数与
        # amb_q2_3_scale_alignment.q1_empirical_domain_Q_range 都取自此处
        "results/Q2/experiments/round1/metrics/q2_M1s.json",
    ],
}

REPORTS = {
    "Q2": ["robustness/Q2/q2_robustness_report.md",
           "results/Q2/reports/q2_final_result_analysis.md",
           "planning/choice_cards/q2_round1_verdict_card.md"],
    "Q3": ["robustness/Q3/q3_robustness_report.md",
           "results/Q3/reports/q3_final_result_analysis.md",
           "planning/choice_cards/q3_round1_verdict_card.md"],
}

# 非工件来源但正当的数字。**只在这些确实不是工件产物时才加。**
WHITELIST_EXACT = {
    # 题面 / 口径常量
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "12", "24", "100",
    "0.5", "0.50", "0.05", "0.01", "0.35", "0.9", "0.90", "0.95", "0.975", "0.025",
    "1e-6", "1e-14", "1e-12", "0.001", "6.0", "4.0", "10.0", "1e7", "5e9", "2e9",
    "0.34", "0.28", "1.69", "406.4", "410.7", "2048", "4096", "8192", "32768",
    "131072", "30000", "20260924", "20260925",
    # 置信水平 / 样本量 / 步长
    "80", "95", "99", "1000", "2000", "4000", "0.25", "0.125",
    # 年份与月份
    "2024", "2025", "2026", "06", "07", "08", "09", "11", "03", "19", "22",
    "1e19", "1e22", "1e24", "21.5", "22.75",
}
WHITELIST_PATTERNS = [
    re.compile(r"^\d{4}$"),
    re.compile(r"^\d{2}$"),
    re.compile(r"^\d+(e|E)-?\d+$"),
    re.compile(r"^1e\d+$"),
]


def leaves(obj):
    """JSON 数值叶子 + 字符串里嵌的数字(评审 detail 里的 lo80 之类)。"""
    if isinstance(obj, dict):
        for v in obj.values():
            yield from leaves(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from leaves(v)
    elif isinstance(obj, bool):
        return
    elif isinstance(obj, (int, float)):
        yield float(obj)
    elif isinstance(obj, str):
        for m in re.findall(r"-?\d+(?:\.\d+)?(?:[eE]-?\d+)?", obj):
            try:
                yield float(m)
            except ValueError:
                pass


def jsonl_leaves(p: Path):
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield from leaves(json.loads(line))


def raw_literals(q: str) -> set[str]:
    """工件文件正文里**逐字出现**的数字字面量(含全精度与科学计数)。

    报告直接抄全精度值时用得上:只要该字符串在工件里逐字存在即可追溯。
    同时收符号被剥掉的形式(报告 token 提取时去掉了负号)。
    """
    out: set[str] = set()
    pat = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")
    for rel in ARTIFACTS[q]:
        p = ROOT / rel
        if not p.exists():
            continue
        for m in pat.findall(p.read_text(encoding="utf-8", errors="replace")):
            out.add(m)
            out.add(m.lstrip("-"))
    return out


def artifact_numbers(q: str) -> set[float]:
    out: set[float] = set()
    for rel in ARTIFACTS[q]:
        p = ROOT / rel
        if not p.exists():
            print(f"  !! artifact missing: {rel}")
            continue
        if p.suffix == ".jsonl":
            out |= set(jsonl_leaves(p))
        elif p.suffix == ".json":
            out |= set(leaves(json.loads(p.read_text(encoding="utf-8"))))
        else:
            for row in csv.DictReader(p.read_text(encoding="utf-8-sig").splitlines()):
                for v in row.values():
                    try:
                        out.add(float(v))
                    except (TypeError, ValueError):
                        pass
    return out


def derived(nums: set[float]) -> set[float]:
    key = sorted(n for n in nums if abs(n) > 1e-9)
    out: set[float] = set()
    for a in key:
        for b in key:
            out.add(abs(a - b))
            if abs(b) > 1e-12:
                out.add(a / b)
    return out


def forms(v: float) -> set[str]:
    f: set[str] = set()
    for x in (v, abs(v)):
        for p in (0, 1, 2, 3, 4, 5, 6):
            f.add(f"{x:.{p}f}")
        for p in (1, 2, 3):
            e = f"{x:.{p}e}"
            f.add(e)
            f.add(e.replace("e-0", "e-").replace("e+0", "e+"))
        f.add(f"{x:g}")
    return f


def norm(s: str) -> str:
    for ch in ("−", "–", "—"):
        s = s.replace(ch, "-")
    return s


def check(q: str) -> int:
    nums = artifact_numbers(q)
    if not nums:
        print(f"[{q}] NO ARTIFACTS FOUND — refusing to report success")
        return 1
    universe: set[str] = set()
    for v in nums | derived(nums):
        universe |= forms(v)
    universe |= WHITELIST_EXACT
    universe |= raw_literals(q)

    unexplained_total = 0
    for rel in REPORTS[q]:
        p = ROOT / rel
        if not p.exists():
            print(f"[{q}] (not yet written) {rel}")
            continue
        raw = p.read_text(encoding="utf-8")
        toks = re.findall(r"\d+(?:\.\d+)?(?:[eE]-?\d+)?", norm(raw))
        unknown = []
        for tk in sorted(set(toks)):
            if tk in universe:
                continue
            if any(pat.match(tk) for pat in WHITELIST_PATTERNS):
                continue
            unknown.append(tk)
        unexplained_total += len(unknown)
        print(f"[{q}] {Path(rel).name}: tokens={len(set(toks))} unexplained={len(unknown)}")
        for tk in unknown:
            m = re.search(r".{0,50}" + re.escape(tk) + r".{0,30}", norm(raw))
            ctx = m.group(0).replace("\n", " ") if m else ""
            print(f"      ? {tk!r}  ...{ctx}...")
    return unexplained_total


def main() -> None:
    qs = sys.argv[1:] or ["Q2", "Q3"]
    bad = sum(check(q) for q in qs)
    print()
    print("ALL NUMBERS TRACEABLE" if bad == 0 else f"REVIEW NEEDED: {bad} unexplained token(s)")


if __name__ == "__main__":
    main()

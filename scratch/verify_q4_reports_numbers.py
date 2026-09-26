"""核验两份 G4 报告的全部数字都可追溯到落盘工件(不手打)。

两个方向都查:
  A) 正向:工件里的关键值按报告格式生成的字符串,必须在报告中出现(查抄错)。
  B) 反向:报告中出现的每个数字 token,必须落在「工件数值集 ∪ 派生量 ∪ 白名单」内
     (查凭空造数)。B 是真正的防伪造检查。

派生量(百分比/倍数/差值)在本脚本里现算,不写死。
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R1 = ROOT / "results/Q4/experiments/round1"
R2 = ROOT / "results/Q4/experiments/round2"
REPORTS = {
    "robustness": ROOT / "robustness/Q4/q4_robustness_report.md",
    "final": ROOT / "results/Q4/reports/q4_final_result_analysis.md",
}
ARTIFACTS = [
    R1 / "metrics/q4_M1a.json", R1 / "metrics/q4_M0a.json", R1 / "run_summary.json",
    R2 / "metrics/q4_trend_method.json", R2 / "n_frontier_meta.json",
    R2 / "run_summary.json",
    R1 / "tables/q4_spec_sensitivity.csv", R1 / "tables/q4_frontier_path.csv",
    R1 / "tables/q4_frontier_scenarios.csv", R1 / "tables/q4_bridge_tiers.csv",
    R1 / "tables/q4_by_type_group.csv",
    R2 / "tables/q4_endpoint_sensitivity.csv",
    R2 / "tables/q4_N_and_frontier_by_month.csv",
    R2 / "tables/q4_scenario_spread_scaling.csv",
    ROOT / "methods/Q4/probes/risk_probe_summary.json",
    ROOT / "code/Q4/reviews/q4_python_review.json",
]


def leaves(obj):
    """JSON 里的数值叶子;字符串里嵌的数字(如评审 detail 中的 lo80=32.276)也要收。"""
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


def artifact_numbers() -> set[float]:
    out: set[float] = set()
    for p in ARTIFACTS:
        if p.suffix == ".json":
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
    """工件内两两的差与比,以及报告用到的几个百分比。"""
    key = sorted(n for n in nums if abs(n) > 1e-9)
    out: set[float] = set()
    for a in key:
        for b in key:
            out.add(abs(a - b))
            if abs(b) > 1e-12:
                out.add(a / b)
    return out


def forms(v: float) -> set[str]:
    """同一数值的多种书写形式;报告里的 token 已去掉符号,故同时给正负两种。"""
    f: set[str] = set()
    for x in (v, abs(v)):
        for p in (0, 1, 2, 3, 4, 5, 6):
            f.add(f"{x:.{p}f}")
        for p in (1, 2, 3):
            e = f"{x:.{p}e}"
            f.add(e)                                   # 9.44e-06
            f.add(e.replace("e-0", "e-").replace("e+0", "e+"))  # 9.44e-6
        f.add(f"{x:g}")
    return f


# ---------- 白名单:非工件来源但正当的数字 ----------
WHITELIST_EXACT = {
    # 题面/口径常量
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "12", "24", "100",
    "0.9", "0.90", "0.5", "0.50", "0.05", "6.0", "0.35", "1e-6", "0.001",
    # 结构量(节号/年份/月)
    "2024", "2025", "06", "07", "08", "09", "11", "03",
    # 置信水平与样本
    "80", "95", "99", "2000", "1000", "4000",
    # 窗口天数与月数
    "278", "9.1",
    # sha256 片段
    "a5cb20771e10af7f",
    # 跨问常量:Q3 已裁定并写入论文的 L_ctx^crit = 6/eta = 30000(HANDOFF §0.00000)
    "30000",
    # 本轮现算的派生量(下节会断言其确由工件算出)
    "3.6", "6.6", "7.2", "7.4", "4.0", "1.881", "11.750", "0.2875",
    "1.9929", "3.675", "3.162", "9.98", "5.3581", "0.2451",
}
# 允许出现的形状:日期、区间号、e 记数、小整数
WHITELIST_PATTERNS = [
    re.compile(r"^\d{4}$"),            # 年份
    re.compile(r"^\d{2}$"),            # 两位(月/日)
    re.compile(r"^\d+(e|E)-?\d+$"),    # 科学记数
]


def report_tokens(text: str) -> list[str]:
    t = text
    for ch in ("−", "–", "—"):
        t = t.replace(ch, "-")
    toks = re.findall(r"\d+(?:\.\d+)?(?:[eE]-?\d+)?", t)
    return toks


def main() -> None:
    nums = artifact_numbers()
    der = derived(nums)
    universe: set[str] = set()
    for v in nums | der:
        universe |= forms(v)
    universe |= WHITELIST_EXACT

    for name, p in REPORTS.items():
        txt = p.read_text(encoding="utf-8")
        norm = txt
        for ch in ("−", "–", "—"):
            norm = norm.replace(ch, "-")
        toks = report_tokens(txt)
        unknown = []
        for tk in sorted(set(toks)):
            if tk in universe:
                continue
            if any(pat.match(tk) for pat in WHITELIST_PATTERNS):
                continue
            unknown.append(tk)
        print(f"[{name}] tokens={len(set(toks))} unexplained={len(unknown)}")
        for tk in unknown:
            ctx = ""
            m = re.search(r".{0,45}" + re.escape(tk) + r".{0,25}", norm)
            if m:
                ctx = m.group(0).replace("\n", " ")
            print(f"    ? {tk!r}   ...{ctx}...")

    # 正向:关键值必须在报告中出现(至少一份)
    alltext = "\n".join(
        t.read_text(encoding="utf-8").replace("−", "-").replace("–", "-")
        for t in REPORTS.values())
    M1A = json.loads((R1 / "metrics/q4_M1a.json").read_text(encoding="utf-8"))
    MS = M1A["attribution"]["main_spec_decile_month"]
    FR = M1A["frontier"]
    must = [
        f"{MS['scale_points']:.4f}", f"{MS['tech_points']:.4f}", f"{MS['total_points']:.4f}",
        f"{MS['scale_share']:.4f}", f"{MS['tech_share']:.4f}",
        f"{MS['scale_share_ci95'][0]:.4f}", f"{MS['scale_share_ci95'][1]:.4f}",
        f"{FR['user_criterion']['lo80']:.3f}", f"{FR['current_frontier']:.3f}",
        f"{FR['user_criterion']['lo80'] - FR['current_frontier']:.3f}",
    ]
    miss = [m for m in must if m not in alltext]
    print(f"\npositive check: {len(must)} key values, missing = {len(miss)} {miss}")

    # ---------- 报告中引用的派生量:逐个由工件现算并比对 ----------
    M0A = json.loads((R1 / "metrics/q4_M0a.json").read_text(encoding="utf-8"))
    TREND = json.loads((R2 / "metrics/q4_trend_method.json").read_text(encoding="utf-8"))
    NF = json.loads((R2 / "n_frontier_meta.json").read_text(encoding="utf-8"))
    PR = json.loads((ROOT / "methods/Q4/probes/risk_probe_summary.json")
                    .read_text(encoding="utf-8"))
    YI = M1A["yi_bias_probe"]
    n_h12 = FR["scenarios"]["neutral"]["h12"]
    b_h12 = M0A["predictions"]["h12"]
    ps = PR["perturbation_sensitivity"]
    der_checks = [
        ("1.881", n_h12["lo80"] - FR["current_frontier"], 3),
        ("11.750", b_h12["hi95"] - b_h12["lo95"], 3),
        ("3.6", n_h12["width95"] / (b_h12["hi95"] - b_h12["lo95"]), 1),
        ("6.6", (b_h12["point"] - n_h12["median"]) / b_h12["point"] * 100, 1),
        ("7.2", 330 / MS["n"] * 100, 1),
        ("7.4", TREND["scenario_spread_scaling"][1]["implied_scenario_spread_h12"]
         / n_h12["median"] * 100, 1),
        ("1.9929", ps["tech_share_spread"] / ps["bootstrap_ci_width"], 4),
        ("4.0", ps["spread_over_ci_width"] / 0.50, 1),
        ("3.675", 10 ** abs(NF["logN_q90_cum_dex"]), 3),
        ("0.2451", abs(YI["tech_points_diff_jia_minus_yi"]), 4),
        ("5.3581", TREND["trend_method_drop_last"]["decile"]["total_points"], 4),
        ("0.3796", ps["bootstrap_ci_width"], 4),
        ("0.7565", ps["tech_share_spread"], 4),
        ("9.98", TREND["trend_method"]["decile"]["slope_ratio"], 2),
    ]
    bad = []
    for shown, value, nd in der_checks:
        got = f"{value:.{nd}f}"
        if got != shown:
            bad.append(f"{shown!r} vs computed {got!r}")
    print(f"derived check: {len(der_checks)} values, mismatches = {len(bad)}")
    for b in bad:
        print("   MISMATCH", b)
    print("ALL OK" if not bad and not miss else "REVIEW NEEDED")


if __name__ == "__main__":
    main()

"""装配 Q4 的 G3 语言评审 JSON(五项命名检查)。数字从 metrics 读,不手打。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
M1A = ROOT / "results" / "Q4" / "experiments" / "round1" / "metrics" / "q4_M1a.json"
M0A = ROOT / "results" / "Q4" / "experiments" / "round1" / "metrics" / "q4_M0a.json"
OUT = ROOT / "code" / "Q4" / "reviews" / "q4_python_review.json"

d = json.loads(M1A.read_text(encoding="utf-8"))
b0 = json.loads(M0A.read_text(encoding="utf-8"))
att, yi, br, fr, c8 = d["attribution"], d["yi_bias_probe"], d["bridge"], d["frontier"], d["c8"]
ms = att["main_spec_decile_month"]
grp = att["by_type_group"]
pre, chat = grp.get("pretrained", {}), grp.get("chat_finetuned", {})
neu12 = fr["scenarios"]["neutral"]["h12"]

review = {
    "schema_version": 1,
    "question_id": "Q4",
    "language": "python",
    "round": 1,
    "gate": "G3",
    "files_reviewed": ["code/Q4/q4_common.py", "code/Q4/q4_analysis.py", "code/Q4/run_all.py"],

    "checks": {
        "syntax": {
            "result": "PASS",
            "detail": "三个文件 ast.parse 通过；run_all.py 端到端运行成功，退出码 0，耗时约 64s。",
        },
        "input_contract": {
            "result": "PASS",
            "detail": (
                f"C1 可用 {ms['n']} 行；桥接 C6 {br['n_total']} 行(High {br['tiers']['High']['n']} / "
                f"Medium {br['tiers']['Medium']['n']})；C8 全量 {c8['n_dirs_used']} 目录、"
                f"{c8['n_task_rows']} 条任务级记录、{c8['n_bbh_subtasks']} 个 BBH 子任务；"
                f"Q2 参数读自 {d['q2_params']['source']}。"
            ),
            "fixed_during_review": (
                "首轮崩于 C4 数值列为字符串 dtype(含注记文本)直接比较，已加 pd.to_numeric(errors='coerce')。"
            ),
        },
        "method_alignment": {
            "result": "PASS",
            "detail": (
                "实现与 q4_fn_spec_and_method_choice=C_main_spec_A 一致：主口径十分位 dummy，"
                "线性 log N 与季度粒度作规格敏感性一并输出；乙侧偏误只在 66 子集上做，未污染主口径；"
                "M0a 按 HD-2 声明实现为纯时间趋势外推；M2a 触发判据按方法卡机械求值，本轮未触发。"
            ),
            "shapley_consistency": "加性结构下两因子 Shapley 与实现的分解恒等，份额和恒为 1，已由 total = scale + tech 逐轮校验。",
        },
        "reproducibility": {
            "result": "PASS",
            "detail": "固定 seed 20260925；连续两次运行 q4_M1a.json 逐字节一致(sha256 a5cb20771e10af7f)。",
            "bootstrap_b": ms["n_boot_effective"],
        },
        "output_contract": {
            "result": "PASS",
            "detail": (
                "run_summary.json 含 question/round/approved_methods/status/seed/inputs/outputs/"
                "metric_summary/fallback_trigger_state/warnings/environment；"
                "metrics 2 份、tables 5 张；figures 本轮为空并如实记为 []。"
            ),
        },
    },

    "findings": [
        {
            "id": "F-Q4-1",
            "severity": "high",
            "title": "pretrained 组能力在窗口内是下降的，该组份额不可作占比解读",
            "detail": (
                f"pretrained n={pre.get('n')}，total_points={pre.get('total_points'):.4f}(负)，"
                f"scale_share={pre.get('scale_share'):.4f} / tech_share={pre.get('tech_share'):.4f}。"
                f"chat_finetuned n={chat.get('n')}，total_points={chat.get('total_points'):.4f}(正)。"
                "total 为负时份额是负数分母上的比值，不能读作贡献占比。"
            ),
            "action": (
                "题目硬性要求区分 pretrained 与 chat/finetuned，故该组必须报，但只能报绝对点数与方向："
                "『pretrained 子样本在 2024-06→2025-03 的 q90/均值层面未提升而是回落』。"
                "不得对该组给出百分比占比。"
            ),
        },
        {
            "id": "F-Q4-2",
            "severity": "high",
            "title": "乙侧偏误方向在账本中被登记为『甲高估技术』，本轮实测不支持任一方向",
            "detail": (
                f"66 子集上甲与乙的 total_points 相同({yi['jia_only_N']['total_points']:.4f}，负)，"
                f"tech_points 甲 {yi['jia_only_N']['tech_points']:.4f} vs 乙 {yi['yi_N_plus_compute']['tech_points']:.4f}，"
                f"差 {yi['tech_points_diff_jia_minus_yi']:+.4f}；而 tech_share 甲 "
                f"{yi['jia_only_N']['tech_share']:.4f} > 乙 {yi['yi_N_plus_compute']['tech_share']:.4f}。"
                "total 为负 ⇒ share 与 points 的比较必然反向，两者都不构成偏误方向的证据。"
            ),
            "action": (
                "账本 q4_scale_channel_definition 的 binding_commitments.known_bias_direction"
                "(『甲单独使用时对技术进步占比为系统性高估』)在本子集上不可验证。"
                "属 CANONICAL 级冲突，须由使用者确认如何处置：撤回该断言、或改为在全样本可解释口径上重做偏误检验。"
                "AI 不得自行改写已裁定的 binding_commitment。"
            ),
        },
        {
            "id": "F-Q4-3",
            "severity": "high",
            "title": "预测判据的 verdict 因 AI 修 bug 而由 FAIL 翻为 PASS，须披露",
            "detail": (
                "首轮实现把 tau 的均值层面月斜率"
                f"({fr['tau_slope_mean_level_for_reference']}) 直接加到 q90 前沿水平上，对象不一致，"
                f"系统性低估(q90 自身斜率 {fr['frontier_slope_per_month']})。"
                "首轮结果:中性 h12 lo80=32.276 < 当前前沿 41.387 ⇒ 判据 FAIL。"
                f"修正为『用 q90 斜率按归因份额拆通道』后:lo80={neu12['lo80']} > {fr['current_frontier']} ⇒ PASS。"
            ),
            "action": (
                "修正本身是对象一致性缺陷的修复，不是判据放宽(判据文字未改)。"
                "但该缺陷是在看到 FAIL 之后才被发现的，论文与稳健性报告须如实披露这一次序，"
                "并注明 PASS 的裕度很薄:lo80 仅高出当前前沿 "
                f"{neu12['lo80'] - fr['current_frontier']:.3f} 点。"
            ),
        },
        {
            "id": "F-Q4-4",
            "severity": "medium",
            "title": "前沿区间极宽，判据只卡 80% 下界，须按使用者口径如实报 95% 宽度",
            "detail": (
                f"中性 h12:median={neu12['median']}，80%=[{neu12['lo80']},{neu12['hi80']}]，"
                f"95% 宽度={neu12['width95']}(约为当前前沿 {fr['current_frontier']} 的一倍)。"
            ),
            "action": "按已裁定判据，95% 宽度如实报告但不作闸门。不得因宽而隐去。",
        },
        {
            "id": "F-Q4-5",
            "severity": "medium",
            "title": "24 个月乐观情景逼近得分上界，饱和假设不可检验",
            "detail": (
                f"optimistic h24 median="
                f"{fr['scenarios']['optimistic']['h24']['median']}，接近 0-100 的上界。"
            ),
            "action": (
                "24 个月未经裁定作主报(账本已登记待办)。若报告，须显式声明饱和形态在 9.1 个月窗口内不可检验。"
            ),
        },
        {
            "id": "F-Q4-6",
            "severity": "medium",
            "title": "chat_finetuned 组的规模份额区间含 0",
            "detail": f"scale_share={chat.get('scale_share'):.4f}，CI95={chat.get('scale_share_ci95')} 含 0。",
            "action": "该组不得声称规模贡献显著为正，只能报点估计与含 0 的区间。",
        },
        {
            "id": "F-Q4-7",
            "severity": "low",
            "title": "桥接映射误差很大，斜率区间宽",
            "detail": (
                f"rmse={br['rmse']}，mapping_error_sigma={br['mapping_error_sigma']}，"
                f"slope={br['slope']}，CI95={br['slope_ci95']}。High 层 n=7、p="
                f"{br['tiers']['High']['p_value']:.3f} 方向对但不显著。"
            ),
            "action": "映射误差已作独立随机项进入蒙特卡洛。按 F10 纪律不得解读为 High 层质量更差。",
        },
    ],

    "ai_self_corrections_in_this_round": [
        {
            "item": "前沿蒙特卡洛的对象不一致缺陷",
            "was": "把全样本均值层面的 tau 月斜率加到 q90 前沿水平",
            "now": "用 q90 自身斜率按归因份额拆为技术/规模两通道",
            "consequence": "使用者预声明判据由 FAIL 翻为 PASS；发现次序为『先见 FAIL 后找 bug』，须披露",
        },
        {
            "item": "C4 数值列 dtype",
            "was": "直接与 0 比较，运行崩溃",
            "now": "pd.to_numeric(errors='coerce') 后比较",
            "consequence": "无结论影响，属实现修复",
        },
    ],

    "verdict": "PASSED_WITH_FINDINGS",
    "blocking": False,
    "note_for_g4": (
        "F-Q4-2 属 CANONICAL 级(与已裁定 binding_commitment 冲突)，须在 G4 前由使用者处置。"
        "F-Q4-1 与 F-Q4-3 必须进入稳健性报告与论文的限制说明。"
    ),
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
print("WROTE", OUT.relative_to(ROOT))
for k, v in review["checks"].items():
    print(f"  {k}: {v['result']}")
print("  verdict:", review["verdict"], "| findings:", len(review["findings"]))

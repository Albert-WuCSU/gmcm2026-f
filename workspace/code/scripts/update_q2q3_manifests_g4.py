"""Q2 与 Q3 过 G4：登记工件、追加 gate_history、改写待办与 next_action。

依据：methods/Q2/q2_decisions.jsonl（11 条）与 methods/Q3/q3_decisions.jsonl（9 条），
三类裁定（result / stability / claim_scope）齐备，且 G4 补算已落盘。
AI 只做机械更新，不新增或改写任何裁定文字。

幂等：gate_history 按 gate 去重；artifacts 为赋值。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TS = "2026-09-25T22:25:00+08:00"

SPEC = {
    "Q2": {
        "status": "g4_passed_round1_final_paper_figures_pending",
        "artifacts": {
            "robustness_report": "robustness/Q2/q2_robustness_report.md",
            "robustness_supplement": "robustness/Q2/q2_robustness_supplement.json",
            "final_result_analysis": "results/Q2/reports/q2_final_result_analysis.md",
            "choice_card_round1_verdict": "planning/choice_cards/q2_round1_verdict_card.md",
            "probe_beta_sharing": "workspace/data/q2_probe_beta_sharing.json",
            "supplement_script": "workspace/code/scripts/probe_q2_beta_sharing_and_perturbation.py",
            "number_provenance_check": "scratch/verify_q2q3_report_numbers.py",
        },
        "verdicts": {
            "result": "supplement_two_gaps_then_finalize",
            "stability": "supplement_beta_probe_then_restate",
            "claim_scope": "keep_3A_but_condition_on_beta_report_both_routes",
            "domain_ratio_reporting": "full_table_with_semantic_disclaimer",
        },
        "decision_count": 11,
        "note": ("补做 P9（beta 跨源共享）判 FAIL ⇒ 人工裁定 q2_claim_scope_conditioned_v2 "
                 "把 gamma≈1 的结论条件化于「beta 取自 B1」并同报两条路线；"
                 "原 q2_claim_scope 保留（append-only），其 binding_commitments 被 v2 替换。"
                 "扰动/消融套件 P9b–P9g 全部 PASS"),
        "g4_summary": {
            "main_claim": "L = E_s + A·N^-alpha + B·(D·Q^gamma·exp(b^T z_p))^-beta；"
                          "三项预声明判据全 PASS（B1 退化 1.0122362405611505e-08 < 1e-6；"
                          "B7 超越性降幅区间 [0.03623599521238617, 0.04778072085097522] 不含 0；弹性符号两侧成立）",
            "conditioned_claim": "在 B7 设计刻度上、且 beta 取自 B1（0.279878）这一承重假设下，"
                                 "gamma=0.9659128363851796，CI95 [0.8838599505464407, 1.055546203294626] 含 1.0"
                                 " ⇒ D_eff ≈ D·Q（质量按比例放大有效 token 数）",
            "conditionality": "若 beta 在 B7 上自由，gamma=1.1797809819428589，"
                              "CI95 [1.0884410240653102, 1.2833591244752791] 不含 1.0；"
                              "B7 rmse 0.07638383467565217 -> 0.06954428026035765（放开 beta 反而更好 9%）",
            "p9_verdict": "FAIL（预声明判据：gamma 位移 0.2138681455576793 = 其区间宽的 1.2456917320652514 倍，阈 0.5）",
            "must_write_limits": [
                "P9 的预声明判据判 FAIL 必须进正文，不得只进附录",
                "必须同报 gamma 两条路线（含 1.0 与不含 1.0）",
                "不得改为只报 beta*gamma（实测该量同样路线依赖：0.270396 vs 0.097985，差 2.76 倍）",
                "beta 跨源共享须表述为承重假设，取 B1 值的理由不构成 P9 未发生",
                "超越性证据完全建立在半合成 B7 上（GC5）",
                "AMB-Q2-3 尺度对齐未解决，gamma 的解释绑定在 B7 设计刻度上",
                "kappa 不可辨识且随参照点变，绝对量级须带参照点",
                "B2 不得表述为直接观测的迁移验证；B5 须注明是他人发表值",
            ],
        },
        "todos": [
            "beta 跨源共享已检验并判 FAIL ⇒ gamma≈1 条件化；正文须同报两条路线且披露该 FAIL",
            "P9d 已量化「B1 处理要谨慎」的影响（gamma 位移 0.039812 = 区间宽的 23%），但不构成对该约束的裁定；该约束仍挂起",
            "B7 的生成机制是否有循环性未检查（Q4 的桥接有对应检查，Q2 无）—— 建议论文声明该不确定性",
            "AMB-Q2-3 尺度对齐未解决：gamma 的解释绑定在 B7 设计刻度上，不得移植到 Q1 的经验 Q",
            "kappa 严格不可辨识且随参照点变（1B run 内 -14.215132486372847 到 -1.6413），绝对量级须带参照点",
            "sigma_s 取值方式为 AI_PROPOSAL_UNCONFIRMED（可否决）；P9e 显示其影响可忽略（gamma 位移 0.000341）",
            "禁止报跨源未去偏的 R²；不得表述为「联合拟合提升了估计」；不得同时声称 Q↔D 替代率随位置变化",
            "不得把 2.0000 当作本轮弹性比估计；gamma 的两个值（0.9659128363851796 / 0.9659129389937917）引用须说明来源",
            "方法卡 Fallback 节仍用 B1 口径且「全部成立/或」自相矛盾 —— 引用以 run_summary 为准",
            "缺失 benchmark 用可比样本子集或层次模型，不得填 0",
            "figures 为空；论文图另在 paper/figures/ 制作",
            "G5 前必须按模板目录内的修改说明把届数由第二十二届改为第二十三届",
            "Q2 侧 G4 已过，无阻塞项",
        ],
        "next_action": {
            "owner": "human",
            "skill": "figure-table-planner",
            "target": "paper",
            "reason": "Q2 与 Q3 的 G4 均已过、Q4 已过，四问 G4 全部关闭，Q4/Q3/Q2/Q1 侧无阻塞项。"
                      "剩余工作：① 论文可视化（Q1/Q2/Q3 的 paper/figures/ 均为欠账，Q3 有三个现成抓手："
                      "最优路径相图、三定义转移点对比图、L_ctx 跨临界规模压缩图）；"
                      "② G5 动笔前必须按模板目录内的修改说明把 LaTeX 模板届数由第二十二届改为第二十三届；"
                      "③ 论文引用须遵守各问 manifest 的 must_write_limits。",
        },
    },
    "Q3": {
        "status": "g4_passed_round1_final_paper_figures_pending",
        "artifacts": {
            "robustness_report": "robustness/Q3/q3_robustness_report.md",
            "final_result_analysis": "results/Q3/reports/q3_final_result_analysis.md",
            "choice_card_round1_verdict": "planning/choice_cards/q3_round1_verdict_card.md",
            "supplement_metrics": "results/Q3/experiments/round1/metrics/q3_supplement_Q0_and_4th_g.json",
            "supplement_script": "workspace/code/scripts/probe_q3_Q0_and_fourth_g.py",
            "number_provenance_check": "scratch/verify_q2q3_report_numbers.py",
        },
        "verdicts": {
            "baseline_definition_f4": "keep_M0o_as_declared_baseline_report_three_numbers",
            "result": "supplement_Q0_sensitivity_and_4th_cost_form_then_finalize",
            "stability": "supplement_Q0_sensitivity_then_restate",
            "claim_scope": "claim_three_transition_scale_dldp",
            "fourth_cost_form": "no_candidate_adopted_report_analysis_only",
            "stability_v2": "add_Q0_sensitivity_result_not_load_bearing",
        },
        "decision_count": 9,
        "note": ("F4 裁定维持 M0o（D/N=20）为官方 baseline、三数同报（依据：M0o 独立于本律，"
                 "M0o' 是本律自身的退化分支）。补做 Q0 敏感性（判 NOT_LOAD_BEARING）"
                 "与第四类 g 三候选分析（裁定不采用，只作分析报告）"),
        "g4_summary": {
            "main_claim": "存在结构性转移；主定义（活跃约束集变化）位置 log10 C = 21.405181884765625，"
                          "不依赖阈值与步长；三定义三答案（A 21.405181884765625 / C 22.625 / D 判不出）；"
                          "形态为连续饱和而非突跳",
            "supporting_claims": [
                "跨 L_ctx^crit 压缩规模而非重排配比：N* -54.83512125256155%、D* -53.37880146895937%、N:D 仅 3.22%",
                "dL/dp 只报符号与域间排序（dL/dp_i ÷ dL/dp_j = b_i/b_j，kappa 无关）",
                "成本函数影响集中在低预算档：Q* 极差 0.46095601286892085 全部来自 1e19",
            ],
            "f4_resolution": "维持 M0o（D/N=20）；三数同报 gap_reported / gap_quality_only / gap_ratio_handicap；"
                             "handicap 占报告差距 32.10322783409671% / 27.65840772632896% / 34.00830933287415%；"
                             "M0o' 保持 diagnostic_reference_NOT_baseline，不得作为官方 baseline 报出",
            "q0_sensitivity": "扫 [0.223306, 0.381496]：Q* 极差 0.011711868561441796、转移位置移动 0.0059814453125 "
                              "⇒ NOT_LOAD_BEARING_IN_TESTED_RANGE；但 Q0=0.35 未经使用者裁定的状态不变",
            "fourth_cost_form": "三候选均未进入主 claim（裁定 A）。C1 饱和指数型与 C2 Hill 型均使 Q*≡1、"
                                "NO_TRANSITION（会消灭核心发现）；C3 二次型产生双侧转移但定义 A 定位失败（nan）"
                                "且左支依赖未裁定的 Q0",
            "must_write_limits": [
                "L_ctx_crit = 30000 仅为两类成本相等的临界尺度，不是最优上下文长度",
                "不得笼统写「各档预算最优质量恒为 1」——低预算档明确不是（0.6460174872692858 / 0.5390439871310791）",
                "饱和点 dQ*/dlogC 由正转零（上游写的「由负转零」是符号错误）",
                "1e24 为外推：N 3.4059903063249575×、D 12.574318155320217×，不得表述为可靠预测",
                "Chinchilla 对照不构成外部锚点；常数未经原文核验（constants_verified_against_paper=false）",
                "Q0 = 0.35 未经使用者裁定；第四类 g 的候选结果不得当作主结果报出",
                "上游三处过期数字不得引用：隐含 D/N 用 79.59104144631574/155.5004609503274/243.02074222002932"
                "（非 32.06/62.64/97.89）；N:D 变化用 3.22%（非 3.12%）；Python 用 3.14.6（非 3.13.7）",
            ],
        },
        "todos": [
            "F4 已裁定（A）：维持 M0o，三数同报；M0o' 不得作为官方 baseline 报出",
            "Q0 实测非承重（扫 Q1 实测范围内 Q* 极差 0.011711868561441796），但 Q0=0.35 未经裁定的状态不变，须在论文声明",
            "第四类 g 已作分析、不采用；不得表述为「给定三类 g 是最优选择」，只能说它们不被这两个方向的改进取代",
            "上游三处过期数字不得引用（见 must_write_limits 末条）",
            "符号错误只在 planning/choice_cards/q3_method_card.md 的定义 B 行，不在方法卡；结论「由正转零」本身正确",
            "Chinchilla 常数引用前须核 Hoffmann et al. 2022 原文",
            "AMB-Q2-3 尺度对齐未解决，沿用 Q2 的限制",
            "P5 的 WEAK_EFFECT 不得读成「L_ctx 不重要」：N* 与 D* 各自腰斩（-54.83512125256155% / -53.37880146895937%）",
            "高预算档外推须结合 B9/B10 可信度边界；不得表述为可靠预测",
            "figures 仅 2 张 Type 1 诊断图（diag_ 前缀，未冒充论文图）；论文图另在 paper/figures/ 制作",
            "G5 前必须按模板目录内的修改说明把届数由第二十二届改为第二十三届",
            "Q3 侧 G4 已过，无阻塞项",
        ],
        "next_action": {
            "owner": "human",
            "skill": "figure-table-planner",
            "target": "paper",
            "reason": "Q3 的 G4 已过，四问 G4 全部关闭。剩余工作：论文可视化与 G5 前置（模板届数）。"
                      "Q3 有三个现成抓手：最优路径相图（log10 C 轴上 N*/D*/Q* + 饱和点 21.405181884765625 标注 "
                      "+ 活跃集分区着色）、三定义转移点对比图（A 21.405181884765625 / C 22.625 / D 判不出）、"
                      "L_ctx 跨临界的规模压缩（N*/D* 腰斩但 N:D 几乎不动）。",
        },
    },
}


def main() -> None:
    for q, spec in SPEC.items():
        p = ROOT / f"planning/manifests/{q}.json"
        m = json.loads(p.read_text(encoding="utf-8"))

        missing = []
        for k, v in spec["artifacts"].items():
            for rel in (v if isinstance(v, list) else [v]):
                if not (ROOT / rel).exists():
                    missing.append(rel)
        if missing:
            raise SystemExit(f"[{q}] 拒绝写入：登记路径不存在 {missing}")

        m["current_gate"] = "G4"
        m["status"] = spec["status"]
        m["artifacts"].update(spec["artifacts"])
        m["blockers"] = []
        hist = m.setdefault("gate_history", [])
        if not any(h.get("gate") == "G4" for h in hist):
            hist.append({
                "gate": "G4", "result": "PASSED", "at": TS,
                "basis": ["methods/%s/%s_decisions.jsonl" % (q, q.lower()),
                          spec["artifacts"]["robustness_report"],
                          spec["artifacts"]["final_result_analysis"],
                          "results/%s/experiments/round1/run_summary.json" % q,
                          "code/%s/reviews/%s_python_review.json" % (q, q.lower())],
                "verdicts": spec["verdicts"],
                "decision_count": spec["decision_count"],
                "note": spec["note"],
            })
        m["g4_summary"] = spec["g4_summary"]
        m["carried_forward_todos"] = spec["todos"]
        m["next_action"] = spec["next_action"]
        m["updated_at"] = TS

        p.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{q}: gate={m['current_gate']} status={m['status']} "
              f"history={[h['gate']+':'+h['result'] for h in hist]} "
              f"artifacts={len(m['artifacts'])} todos={len(spec['todos'])}")


if __name__ == "__main__":
    main()

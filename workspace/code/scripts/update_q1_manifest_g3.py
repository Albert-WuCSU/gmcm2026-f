"""G3 通过后更新 manifest：登记实验与评审工件，推进 gate 到 G3。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "planning/manifests/Q1.json"
TS = "2026-09-24T21:15:00+08:00"


def main() -> None:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    m["artifacts"]["latest_run"] = "results/Q1/experiments/round1/run_summary.json"
    m["artifacts"]["code_review"] = "code/Q1/reviews/q1_python_review.json"
    m["artifacts"]["code_dir"] = "code/Q1/"
    m["current_gate"] = "G3"
    m["status"] = "round1_reviewed_awaiting_second_decision_card"
    if not any(g["gate"] == "G3" for g in m["gate_history"]):
        m["gate_history"].append({
            "gate": "G3", "result": "PASSED", "at": TS,
            "basis": ["results/Q1/experiments/round1/run_summary.json",
                      "code/Q1/reviews/q1_python_review.json"],
            "note": ("M0/M1/M0c/M1c 四法实跑成功，per_domain 消融臂与五类扰动齐备；"
                     "评审五项命名检查全 PASS，3 条 findings 均为 minor/info 不阻塞。"
                     "质量侧 M1 在两项预声明指标上超过 M0（可分辨域对 19->21/21；"
                     "扰动 τ 0.9595->0.9976，差值区间 [0.019,0.057] 不含 0）。"
                     "配比侧增益为尺度局部（1m +0.070、60m -0.005、1B -0.046），"
                     "与决策 C 一致。Q 增量检验三尺度区间均含 0，零结果如实记录。"
                     "fallback M2 未触发，保持休眠。")})
    m["next_action"] = {
        "owner": "human",
        "skill": "decision-prompt-builder -> modeler-decision-logger",
        "reason": ("首轮实验已完成，须使用者裁定第二张决策卡的两项："
                   "① Q1b 冲突判据选哪个（CD2@p75=0.0408 / CD1=0.3031 / "
                   "CD3-5=0.3667 / CD3-3=0.6584）；"
                   "② book~wikipedia 的表述口径（M1 新分开但裕度仅 1.12 倍且方向与 M0 相反）"),
    }
    m["updated_at"] = TS
    for t in ("[G3 硬性] 实验设计四件套：M0/M1/M0c/M1c + 消融（per_domain 归一化臂）+ 参数扰动",):
        if t in m["carried_forward_todos"]:
            m["carried_forward_todos"][m["carried_forward_todos"].index(t)] = \
                "[已完成·round1] 实验四件套 + 消融臂 + 五类扰动，见 run_summary.json"
    m["carried_forward_todos"].append(
        "[新增·零结果须如实写入] Q 增量检验：17 维 p 加入域级 Q_corpus 后三尺度增量为 "
        "+0.0003/-0.0002/-0.0008，95% 区间均含 0 => 无显著增量。成因：Q_corpus 由 6/17 映射域的 "
        "p 加权构成，与 p 构造性相关（映射域配比质量中位仅 0.5995，5 行为 0 已剔除）。"
        "这是对题目『是否引入 Q 由参赛队伍论证』的有证据回答，不是失败。")
    MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("gate:", m["current_gate"], "| status:", m["status"])
    print("next:", m["next_action"]["skill"])


if __name__ == "__main__":
    main()

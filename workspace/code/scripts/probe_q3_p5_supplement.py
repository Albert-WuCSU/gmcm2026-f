"""P5 补充：L_ctx 是否等价于预算缩放。含一条 AI 自述断言的更正。"""
from __future__ import annotations

import json
from pathlib import Path

import probe_q3_optimization as P

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "workspace/data/q3_probe_optimization.json"


def main() -> None:
    res = json.loads(OUT.read_text(encoding="utf-8"))
    rows = {}
    for L in P.L_CTX_FEASIBLE:
        s1 = P.solve(1e22, "exponential", L_ctx=L)
        scale = 6.0 / (6.0 + P.ETA * L)
        s2 = P.solve(1e22 * scale, "exponential", L_ctx=0.0)
        rows[str(L)] = {
            "attn_over_train": float(P.ETA * L / 6.0),
            "actual": {"Q": s1["Q"], "N_B": s1["N_B"], "D_B": s1["D_B"], "N_over_D": s1["N_over_D"]},
            "budget_rescaled_equivalent": {"Q": s2["Q"], "N_B": s2["N_B"], "D_B": s2["D_B"],
                                           "N_over_D": s2["N_over_D"]},
            "N_over_D_relative_gap": float(abs(s1["N_over_D"] - s2["N_over_D"]) / s2["N_over_D"]),
        }
    base = rows[str(P.L_CTX_FEASIBLE[0])]["actual"]
    top = rows[str(P.L_CTX_FEASIBLE[-1])]["actual"]
    res["probes"]["P5_L_ctx_crossing_crit"]["supplement_budget_rescaling_test"] = {
        "question": "L_ctx 是否只等价于把有效预算缩放 6/(6+eta*L_ctx)？",
        "by_L_ctx": rows,
        "ai_claim_correction": ("AI 曾断言『L_ctx 只是整体缩放有效预算、不改变 N 与 D 的权衡结构』。"
                               "实测该等价仅近似成立，且随 L_ctx 增大而失效："
                               "相对差 2048 时 1.97e-2、32768 时 1.96e-1、131072 时 3.34e-1。"
                               "成因：C_Q = D*[g(Q)-g(Q0)] 只随 D 标度、不随 N*D 标度，"
                               "故 (6+eta*L_ctx) 只缩放前两项，C_Q 破坏等价性，"
                               "其相对权重随有效预算缩小而上升。该断言已更正，不得按强版本写入论文。"),
        "measured_finding": ("L_ctx 由 2048 升至 131072（跨过 L_ctx_crit=30000）时："
                            "N* 由 %.3fB 降至 %.3fB（-%.1f%%）、D* 由 %.1fB 降至 %.1fB（-%.1f%%），"
                            "而 N:D 比值仅由 %.4f 变为 %.4f（相对变化 %.2f%%）。"
                            "即跨临界显著压缩可负担规模，但几乎不改变 N 与 D 的相对配比。"
                            % (base["N_B"], top["N_B"], (1 - top["N_B"] / base["N_B"]) * 100,
                               base["D_B"], top["D_B"], (1 - top["D_B"] / base["D_B"]) * 100,
                               base["N_over_D"], top["N_over_D"],
                               abs(top["N_over_D"] - base["N_over_D"]) / base["N_over_D"] * 100)),
        "refines_writing_red_line": ("红线『30000 不是最优上下文长度』仍成立且应保留。"
                                     "可补充的实测内容是：跨临界的后果是规模压缩而非配比重排 —— "
                                     "这是比『最优配置显著偏移』更准确的表述"),
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(rows, ensure_ascii=False, indent=1))
    print("OK")


if __name__ == "__main__":
    main()

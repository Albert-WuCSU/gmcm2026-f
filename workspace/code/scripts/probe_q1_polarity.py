"""Q1 风险探针 / 前置：二分类对 (ad_en, fluency_en) 的极性判定。

问题：A1 的 ad_en / fluency_en 是长度 2 的 logits 对，两位相关 -0.985 / -0.980。
标量化取 margin = pos1 - pos0 后，二者与 fineweb_edu 均为正相关（+0.208 / +0.279）。
若 pos1 代表"是广告"，则 margin 越大越像广告，却与教育价值正相关 —— 矛盾。
因此必须回看原文确定哪一位对应"广告/不流畅"。

本脚本不做建模，只导出 margin 两端的真实文本片段供人工语义核验。
输出：workspace/data/q1_polarity_evidence.json
种子：20260924（不涉随机，仅登记）
"""
import json
import lzma
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
A1 = ROOT / "workspace/data_raw/real_attachments/A_data_value/slimpajama_quality_signal_sample.jsonl.xz"
OUT = ROOT / "workspace/data/q1_polarity_evidence.json"

FIELDS = ["ad_en", "fluency_en"]
K = 6          # 每端取 6 条
SNIP = 420     # 每条正文截断长度


def main() -> None:
    rows = []
    with lzma.open(A1, "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            rec = {"id": r["id"], "dom": r["_source_domain"],
                   "content": r["content"]}
            ok = True
            for fld in FIELDS:
                v = r.get(fld)
                if not isinstance(v, list) or len(v) != 2 or v[0] is None or v[1] is None:
                    ok = False
                    break
                rec[fld] = float(v[1]) - float(v[0])   # margin = pos1 - pos0
            if ok:
                rows.append(rec)

    result = {"n_rows": len(rows), "margin_definition": "pos1 - pos0",
              "fields": {}}

    for fld in FIELDS:
        rows.sort(key=lambda r: r[fld])
        low = rows[:K]
        high = rows[-K:]
        result["fields"][fld] = {
            "lowest_margin": [
                {"id": r["id"], "domain": r["dom"], "margin": round(r[fld], 4),
                 "content_head": r["content"][:SNIP].replace("\n", " ⏎ ")}
                for r in low
            ],
            "highest_margin": [
                {"id": r["id"], "domain": r["dom"], "margin": round(r[fld], 4),
                 "content_head": r["content"][:SNIP].replace("\n", " ⏎ ")}
                for r in high
            ],
            "margin_quantiles": {
                "min": round(rows[0][fld], 4),
                "p25": round(rows[len(rows) // 4][fld], 4),
                "p50": round(rows[len(rows) // 2][fld], 4),
                "p75": round(rows[3 * len(rows) // 4][fld], 4),
                "max": round(rows[-1][fld], 4),
            },
            "frac_margin_positive": round(
                sum(1 for r in rows if r[fld] > 0) / len(rows), 4),
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"wrote {OUT}  n_rows={len(rows)}")


if __name__ == "__main__":
    main()

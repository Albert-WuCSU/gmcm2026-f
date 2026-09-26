"""M0s（usable_baseline）：经典标度律 L = E + A*N^-alpha + B*D^-beta，仅用 B1。

HD-2 明文声明的 Q2 baseline。输出 metrics/q2_M0s.json。
自助：B1 按 N 分组（8 组，诚实口径）+ 逐行（对照）。
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

import q2_common as C

OUT = C.ROOT / "results/Q2/experiments/round1"
B_BOOT = 400


def main() -> None:
    t0 = time.time()
    (OUT / "metrics").mkdir(parents=True, exist_ok=True)
    b1 = C.load_nd("B1")

    p = C.fit_classic(b1["N"], b1["D"], b1["L"])
    pred = C.predict_classic(p, b1["N"], b1["D"])
    r2 = 1.0 - np.sum((b1["L"] - pred) ** 2) / np.sum((b1["L"] - b1["L"].mean()) ** 2)

    boots = {}
    for mode in ("grouped", "row"):
        rng = np.random.default_rng(C.SEED)
        acc = {k: [] for k in ("E", "A", "alpha", "B", "beta")}
        for _ in range(B_BOOT):
            idx = C.boot_indices(b1["group"], rng, mode)
            try:
                q = C.fit_classic(b1["N"][idx], b1["D"][idx], b1["L"][idx], seed=int(rng.integers(1e9)))
            except Exception:
                continue
            for k in acc:
                acc[k].append(q[k])
        boots[mode] = {k: {"ci95": C.ci95(np.array(v)), "n_ok": len(v)} for k, v in acc.items()}

    res = {
        "schema_version": 1, "method_id": "M0s", "role": "usable_baseline",
        "form": "L = E + A*N^-alpha + B*D^-beta",
        "data": {"source": "B1", "file": str(C.PATHS["B1"].relative_to(C.ROOT)),
                 "n": b1["n"], "n_dropped": b1["n_dropped"],
                 "n_N_groups": int(len(set(b1["group"].tolist())))},
        "params": {k: v for k, v in p.items() if k != "rmse"},
        "fit": {"rmse": p["rmse"], "r2": float(r2)},
        "bootstrap": {"B": B_BOOT, "seed": C.SEED, "by_mode": boots,
                      "grouping_note": ("B1 的 run_id 每行唯一(1176)，按 run_id 分组等于逐行重抽样(空操作)；"
                                        "真实相关结构是 N(仅 8 取值，同一 N 内为训练轨迹、行间强相关)。"
                                        "grouped 为诚实口径，row 仅作对照、会低估不确定性")},
        "elasticity_signs": {
            "dL_dN_negative_all": bool(np.all(-p["A"] * p["alpha"] * b1["N"] ** (-p["alpha"] - 1) < 0)),
            "dL_dD_negative_all": bool(np.all(-p["B"] * p["beta"] * b1["D"] ** (-p["beta"] - 1) < 0)),
        },
        "caveat": ("B1 拟合异常干净(R2=%.7f, RMSE=%.3e)，对真实训练日志不寻常。"
                   "使用者已就『B1 的处理要谨慎』附加约束，该项核查经其指示暂缓") % (r2, p["rmse"]),
        "runtime_seconds": round(time.time() - t0, 2),
    }
    (OUT / "metrics/q2_M0s.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n",
                                             encoding="utf-8")
    print(json.dumps({"M0s": res["params"], "rmse": p["rmse"], "r2": float(r2),
                      "beta_ci95_grouped": boots["grouped"]["beta"]["ci95"],
                      "beta_ci95_row": boots["row"]["beta"]["ci95"],
                      "runtime_s": res["runtime_seconds"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

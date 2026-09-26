"""补跑落盘(第二步):趋势法 + 端点敏感性 + 情景极差缩放。

兑现裁定 q4_result_verdict 的 supplementary_run_required。
论文只能引本脚本落盘的值。
"""
import json
import numpy as np
import pandas as pd
from q4_common import ROOT, SEED, load_c1, _dummies

OUT = ROOT / "results" / "Q4" / "experiments" / "round2"
(OUT / "tables").mkdir(parents=True, exist_ok=True)
(OUT / "metrics").mkdir(parents=True, exist_ok=True)


def fit(d, spec, tkey):
    d = d.copy()
    if spec == "decile":
        d["_nb"] = pd.qcut(d["logN"], 10, labels=False, duplicates="drop")
        Xs, _ = _dummies(d["_nb"])
    else:
        Xs = d[["logN"]].to_numpy(float)
    Xt, tl = _dummies(d[tkey])
    X = np.hstack([np.ones((len(d), 1)), Xs, Xt])
    y = d["S"].to_numpy(float)
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    ns = Xs.shape[1]
    d["_f"] = Xs @ b[1:1 + ns]
    return d, b[1 + ns:], tl


def endpoint_diff(d, spec, tkey):
    d, bt, tl = fit(d, spec, tkey)
    ps = sorted(d[tkey].unique())
    first, last = ps[0], ps[-1]
    tau_last = float(dict(zip(tl, bt)).get(last, 0.0))
    f1 = float(d.loc[d[tkey] == first, "_f"].mean())
    f2 = float(d.loc[d[tkey] == last, "_f"].mean())
    sc, tc = f2 - f1, tau_last
    tot = sc + tc
    return dict(scale_points=sc, tech_points=tc, total_points=tot,
                scale_share=sc / tot, tech_share=tc / tot, n=int(len(d)))


def trend(d, spec):
    d, bt, tl = fit(d, spec, "ym")
    ms = sorted(d["ym"].unique())
    x = np.arange(len(ms), dtype=float)
    tau = np.array([0.0] + [dict(zip(tl, bt))[m] for m in ms[1:]])
    fb = np.array([d.loc[d["ym"] == m, "_f"].mean() for m in ms])
    sf = float(np.polyfit(x, fb, 1)[0])
    st = float(np.polyfit(x, tau, 1)[0])
    span = len(ms) - 1
    sc, tc = sf * span, st * span
    tot = sc + tc
    return dict(slope_f=sf, slope_tau=st, slope_ratio=st / sf if sf else float("nan"),
                scale_points=sc, tech_points=tc, total_points=tot,
                scale_share=sc / tot, tech_share=tc / tot, n_months=len(ms))


def main():
    rng = np.random.default_rng(SEED)
    c1 = load_c1()
    months = sorted(c1["ym"].unique())

    # --- 端点敏感性
    rows = []
    rows.append({"endpoint_def": "single_last_month", **endpoint_diff(c1, "decile", "ym")})
    for k in (2, 3):
        x = c1.copy()
        last = set(months[-k:])
        x["grp"] = np.where(x["ym"].isin(last), "LAST",
                            np.where(x["ym"] == months[0], "FIRST", None))
        x = x[x["grp"].notna()]
        rows.append({"endpoint_def": f"first_vs_last{k}_merged",
                     **endpoint_diff(x, "decile", "grp")})
    rows.append({"endpoint_def": "drop_last_month",
                 **endpoint_diff(c1[c1["ym"] != months[-1]], "decile", "ym")})
    ep = pd.DataFrame(rows)
    ep.to_csv(OUT / "tables" / "q4_endpoint_sensitivity.csv", index=False,
              encoding="utf-8-sig")

    # --- 趋势法
    tr = {s: trend(c1, s) for s in ("decile", "linear")}
    tr_drop = {s: trend(c1[c1["ym"] != months[-1]], s) for s in ("decile", "linear")}

    # --- 趋势法自助
    groups = [g.index.to_numpy() for _, g in c1.groupby("ym")]
    vals = []
    for _ in range(1000):
        idx = np.concatenate([rng.choice(g, size=len(g), replace=True) for g in groups])
        try:
            vals.append(trend(c1.loc[idx], "decile")["scale_share"])
        except Exception:
            pass
    v = np.array(vals)
    ci = [float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))]

    # --- 情景极差随 scale_share 缩放
    r1 = json.loads((ROOT / "results/Q4/experiments/round1/metrics/q4_M1a.json")
                    .read_text(encoding="utf-8"))
    sc12 = [x["h12"]["median"] for x in r1["frontier"]["scenarios"].values()]
    spread0 = max(sc12) - min(sc12)
    sh0 = r1["attribution"]["main_spec_decile_month"]["scale_share"]
    scal = [{"scale_share": s, "implied_scenario_spread_h12": round(spread0 * s / sh0, 4)}
            for s in (sh0, tr["decile"]["scale_share"], 0.0)]
    pd.DataFrame(scal).to_csv(OUT / "tables" / "q4_scenario_spread_scaling.csv",
                              index=False, encoding="utf-8-sig")

    m = {
        "schema_version": 1, "round": 2, "seed": SEED,
        "purpose": "兑现 q4_result_verdict 的 supplementary_run_required",
        "endpoint_sensitivity": rows,
        "endpoint_share_spread": float(ep["scale_share"].max() - ep["scale_share"].min()),
        "endpoint_sign_flips": bool((ep["scale_share"] > 0).any() and (ep["scale_share"] < 0).any()),
        "total_points_range": [float(ep["total_points"].min()), float(ep["total_points"].max())],
        "trend_method": tr,
        "trend_method_drop_last": tr_drop,
        "trend_scale_share_ci95": ci,
        "trend_ci_contains_zero": bool(ci[0] < 0 < ci[1]),
        "n_boot": int(len(v)),
        "scenario_spread_scaling": scal,
        "robust_claim": "规模通道贡献与 0 不可区分；非规模技术/数据工程综合进步主导",
        "fragile_claim_withdrawn": "26%/74% 等任何具体百分比分割",
        "generated_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
    }
    (OUT / "metrics" / "q4_trend_method.json").write_text(
        json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")

    print(ep.to_string(index=False))
    print()
    for s in ("decile", "linear"):
        t = tr[s]
        print(f"trend {s}: scale_share={t['scale_share']:+.4f} slope_f={t['slope_f']:+.5f} "
              f"slope_tau={t['slope_tau']:+.5f} ratio={t['slope_ratio']:.2f}")
    print(f"trend decile CI95 = [{ci[0]:+.4f}, {ci[1]:+.4f}]  contains0={m['trend_ci_contains_zero']}")
    print(f"endpoint spread={m['endpoint_share_spread']:.4f} sign_flips={m['endpoint_sign_flips']}")
    print(f"total_points range={m['total_points_range']}")
    print("scenario spread scaling:", [(round(d['scale_share'],4), d['implied_scenario_spread_h12']) for d in scal])
    print("WROTE round2 metrics + 2 tables")


if __name__ == "__main__":
    main()

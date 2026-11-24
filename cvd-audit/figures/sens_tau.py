import os
import pandas as pd

CSV = "data/processed/texts.csv"
OUT = "data/processed/sensitivity_tau.csv"
TAUS = [1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 10.0]

d = pd.read_csv(CSV)
m = d[~d["bg_unknown"].astype(bool)].copy()   # hanya latar terukur
n = len(m)
print(f"Elemen total: {len(d)}, terukur: {n}")

rows = []
for tau in TAUS:
    any_mask = pd.Series(False, index=m.index)
    for cvd in ("protan", "deutan", "tritan"):
        # runtuh: beda warna normal >= tau, tetapi di bawah simulasi < tau
        lost = (m["de_normal"] >= tau) & (m[f"de_{cvd}"] < tau)
        any_mask |= lost
        rows.append({"tau": tau, "cvd": cvd, "n_measurable": n,
                     "n_collapse": int(lost.sum()),
                     "rate": lost.sum() / n if n else 0.0})
    rows.append({"tau": tau, "cvd": "any", "n_measurable": n,
                 "n_collapse": int(any_mask.sum()),
                 "rate": any_mask.sum() / n if n else 0.0})

out = pd.DataFrame(rows)
os.makedirs("data/processed", exist_ok=True)
out.to_csv(OUT, index=False)
print(out.pivot(index="tau", columns="cvd", values="n_collapse"))
print("saved", OUT)
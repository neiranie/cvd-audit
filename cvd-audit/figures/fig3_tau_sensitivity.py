import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter

df = pd.read_csv("data/processed/sensitivity_tau.csv")

os.makedirs("figures", exist_ok=True)
fig, ax = plt.subplots(figsize=(3.4, 2.6), dpi=300)

styles = {"protan": "-o", "deutan": "--s", "tritan": ":^"}
for cvd, st in styles.items():
    g = df[df["cvd"] == cvd].sort_values("tau")
    ax.plot(g["tau"], g["rate"] * 100, st, color="black",
            ms=3, lw=0.9, label=cvd)

ax.set_xscale("log")
ax.set_xticks(sorted(df["tau"].unique()))
ax.get_xaxis().set_major_formatter(ScalarFormatter())
ax.set_xlabel("Threshold τ (ΔE00)", fontsize=7)
ax.set_ylabel("Text losing color difference (%)", fontsize=7)
ax.tick_params(labelsize=6.5)
ax.grid(True, lw=0.3, alpha=0.6)
ax.legend(fontsize=6.5, frameon=False)

fig.savefig("figures/fig3_tau_sensitivity.png", bbox_inches="tight", dpi=300)
print("saved figures/fig3_tau_sensitivity.png")
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

os.makedirs("figures", exist_ok=True)

steps = [
    ("Page\ncapture", "rendered page,\ndesktop viewport"),
    ("Extraction", "text, links,\neffective background"),
    ("CVD\nsimulation", "protan, deutan,\ntritan"),
    ("Metrics", "contrast, ΔE00,\ncolor-only fault"),
    ("Report", "tables, figures,\nflagged items"),
]

fig, ax = plt.subplots(figsize=(3.4, 4.2), dpi=300)
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis("off")

n = len(steps)
box_h, gap = 1.35, 0.55
top = 9.7
for i, (title, sub) in enumerate(steps):
    y = top - i * (box_h + gap) - box_h
    ax.add_patch(FancyBboxPatch((0.6, y), 8.8, box_h,
                                boxstyle="round,pad=0.02,rounding_size=0.15",
                                fc="#EEEEEE", ec="black", lw=0.8))
    ax.text(2.6, y + box_h / 2, title, ha="center", va="center",
            fontsize=7.5, fontweight="bold")
    ax.text(6.6, y + box_h / 2, sub, ha="center", va="center", fontsize=6.5)
    if i < n - 1:
        ax.add_patch(FancyArrowPatch((5, y), (5, y - gap),
                                     arrowstyle="-|>", mutation_scale=8,
                                     lw=0.8, color="black"))

fig.savefig("figures/fig1_pipeline.png", bbox_inches="tight", dpi=300)
print("saved figures/fig1_pipeline.png")
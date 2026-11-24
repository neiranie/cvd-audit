import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CSV = "data/processed/texts.csv"
TOP = 10

d = pd.read_csv(CSV)
total = len(d)

# hanya elemen dengan latar yang bisa diukur
m = d[~d["bg_unknown"].astype(bool)].copy()
fail = m[~m["pass_normal"].astype(bool)].copy()

fail["cr"] = fail["cr_normal"].round(2)
g = (fail.groupby(["cr", "font_size", "font_weight"])
         .size().reset_index(name="n")
         .sort_values("n", ascending=False))

print(f"Total elemen teks       : {total}")
print(f"Latar tidak terukur     : {total - len(m)} ({(total-len(m))/total:.1%})")
print(f"Terukur                 : {len(m)}")
print(f"Gagal AA (terukur)      : {len(fail)} ({len(fail)/max(len(m),1):.1%})")
print(f"Kombinasi gaya yang gagal: {len(g)}")
if len(g):
    print(f"Elemen di {min(TOP,len(g))} kombinasi teratas: "
          f"{g.head(TOP)['n'].sum()} ({g.head(TOP)['n'].sum()/len(fail):.1%} dari yang gagal)")

top = g.head(TOP).iloc[::-1]
labels = [f"{r.cr:.2f}:1 | {int(r.font_size)} px / {int(r.font_weight)}"
          for r in top.itertuples()]

os.makedirs("figures", exist_ok=True)
fig, ax = plt.subplots(figsize=(3.4, 3.0), dpi=300)
bars = ax.barh(range(len(top)), top["n"], color="#999999",
               edgecolor="black", lw=0.6)
ax.set_yticks(range(len(top)))
ax.set_yticklabels(labels, fontsize=6)
for b, n in zip(bars, top["n"]):
    ax.text(b.get_width() + max(top["n"]) * 0.01, b.get_y() + b.get_height() / 2,
            str(int(n)), va="center", fontsize=6)
ax.set_xlabel("Failing text elements (count)", fontsize=7)
ax.tick_params(axis="x", labelsize=6.5)
ax.set_xlim(0, max(top["n"]) * 1.12)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)

fig.savefig("figures/fig2_fail_styles.png", bbox_inches="tight", dpi=300)
print("saved figures/fig2_fail_styles.png")
import pandas as pd

P = "data/processed/"
d = pd.read_csv(P + "texts.csv")
for c in ("bg_unknown", "pass_normal", "lost_under_cvd"):
    d[c] = d[c].astype(bool)


def summarize(g, name):
    n = len(g)
    m = g[~g["bg_unknown"]]
    nm = len(m)
    fail = m[~m["pass_normal"]]
    print(f"\n== {name} ==")
    print(f"text elements        : {n}")
    if n:
        print(f"not measurable       : {n - nm} ({(n - nm) / n:.1%})")
    print(f"measurable           : {nm}")
    if nm:
        print(f"fail AA (measurable) : {len(fail)} ({len(fail) / nm:.1%})")
        print(f"lost under CVD       : {int(m['lost_under_cvd'].sum())} "
              f"({m['lost_under_cvd'].mean():.1%})")
    if len(fail):
        f = fail.assign(cr=fail["cr_normal"].round(2))
        grp = (f.groupby(["cr", "font_size", "font_weight"])
                .size().sort_values(ascending=False))
        print(f"unique failing style combinations: {len(grp)}")
        (cr, fs, fw), top = next(iter(grp.items()))
        print(f"top combination: {cr}:1, {fs}px/{fw} -> {top} elements "
              f"({top / len(fail):.1%} of failures)")


for pt, g in d.groupby("page_type"):
    summarize(g, f"page type: {pt}")
summarize(d, "ALL PAGES")
print("\nfiles per page type:", d.groupby("page_type")["file"].nunique().to_dict())

print("\n== links.csv ==")
try:
    l = pd.read_csv(P + "links.csv")
    print(len(l), "rows; columns:", list(l.columns))
    print(l.head(3).T)
except Exception as e:
    print("error:", e)

print("\n== page_summary.csv ==")
print(open(P + "page_summary.csv").read())
print("== fault_injection.json ==")
print(open(P + "fault_injection.json").read())
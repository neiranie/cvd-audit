"""Turn raw extraction JSON into element-level metrics and page-level summaries."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from .color import CVD_TYPES, rgb255_to_rgb, simulate_cvd, delta_e2000
from .contrast import contrast_ratio, aa_threshold
from .cues import DEFAULT_TAU, evaluate_pair, link_has_non_color_cue


def audit_texts(raw: dict, severity: float = 1.0, tau: float = DEFAULT_TAU) -> pd.DataFrame:
    rows = []
    for t in raw["texts"]:
        fg, bg = rgb255_to_rgb(t["fg"]), rgb255_to_rgb(t["bg"])
        thr = aa_threshold(t["fontSize"], t["fontWeight"])
        cr = contrast_ratio(fg, bg)
        row = dict(tag=t["tag"], cls=t["cls"], text_len=t["textLen"], font_size=t["fontSize"],
                   font_weight=t["fontWeight"], bg_unknown=t["bgUnknown"], opacity=t["opacity"],
                   threshold=thr, cr_normal=cr, pass_normal=cr >= thr,
                   de_normal=delta_e2000(fg, bg))
        for k in CVD_TYPES:
            fs, bs = simulate_cvd(fg, k, severity), simulate_cvd(bg, k, severity)
            row[f"cr_{k}"] = contrast_ratio(fs, bs)
            row[f"pass_{k}"] = row[f"cr_{k}"] >= thr
            row[f"de_{k}"] = delta_e2000(fs, bs)
        row["lost_under_cvd"] = bool(row["pass_normal"] and not all(row[f"pass_{k}"] for k in CVD_TYPES))
        rows.append(row)
    return pd.DataFrame(rows)


def audit_links(raw: dict, severity: float = 1.0, tau: float = DEFAULT_TAU) -> pd.DataFrame:
    rows = []
    for l in raw["links"]:
        a, b = rgb255_to_rgb(l["fg"]), rgb255_to_rgb(l["blockFg"])
        res = evaluate_pair(a, b, tau, severity)
        cue = link_has_non_color_cue(l)
        row = dict(link_text=l["linkText"], has_non_color_cue=cue,
                   link_text_contrast=contrast_ratio(a, b), de_normal=res.de_normal,
                   bg_unknown=l["bgUnknown"], opacity=l["opacity"])
        for k in CVD_TYPES:
            row[f"de_{k}"] = res.de_sim[k]
            row[f"collapsed_{k}"] = res.collapsed[k]
        row["collapsed_any"] = res.collapsed_any
        row["color_only_fault"] = bool((not cue) and res.collapsed_any)
        rows.append(row)
    return pd.DataFrame(rows)


def summarize(texts: pd.DataFrame, links: pd.DataFrame) -> dict:
    """Pass/fail statistics use only elements whose background could be measured."""
    s = dict(n_text=len(texts), n_links_in_text=len(links))
    if len(texts):
        known = texts[~texts.bg_unknown]
        s["pct_bg_unknown"] = 100 * texts.bg_unknown.mean()
        s["n_text_measurable"] = len(known)
        if len(known):
            s["pct_text_fail_aa_normal"] = 100 * (~known.pass_normal).mean()
            s["pct_text_lost_under_cvd"] = 100 * known.lost_under_cvd.mean()
    if len(links):
        s["pct_links_color_only"] = 100 * (~links.has_non_color_cue).mean()
        s["pct_links_color_only_fault"] = 100 * links.color_only_fault.mean()
    return s


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("raw_dir"); ap.add_argument("out_dir")
    ap.add_argument("--tau", type=float, default=None)
    ap.add_argument("--severity", type=float, default=1.0)
    a = ap.parse_args(argv)
    tau = DEFAULT_TAU if a.tau is None else a.tau
    if a.tau is None:
        print(f"NOTICE: tau={tau} is a PLACEHOLDER; justify it with literature before publication.", file=sys.stderr)
    out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    all_t, all_l, summ = [], [], []
    for f in sorted(Path(a.raw_dir).rglob("*.json")):
        raw = json.loads(f.read_text(encoding="utf-8"))
        if raw.get("blocked") or "texts" not in raw:
            continue
        t, l = audit_texts(raw, a.severity, tau), audit_links(raw, a.severity, tau)
        meta = dict(file=str(f.relative_to(a.raw_dir)), site=raw.get("site"), page_type=raw.get("page_type"))
        for df in (t, l):
            for k, v in meta.items():
                df[k] = v
        all_t.append(t); all_l.append(l); summ.append({**meta, **summarize(t, l)})
    if not summ:
        print("No usable raw files found."); return 1
    pd.concat(all_t).to_csv(out / "texts.csv", index=False)
    pd.concat(all_l).to_csv(out / "links.csv", index=False)
    pd.DataFrame(summ).to_csv(out / "page_summary.csv", index=False)
    print(f"Wrote {len(summ)} page summaries to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

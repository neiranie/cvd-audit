"""Sensitivity analysis: how the results change with CVD severity and the threshold tau.

Usage:  python -m cvd_audit.sensitivity data/raw data/processed
Pools all captured pages. Elements with an unmeasurable background are excluded.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import pandas as pd
from .audit import audit_texts, audit_links
from .color import CVD_TYPES

SEVERITIES = [0.3, 0.6, 1.0]
TAUS = [2.0, 3.0, 5.0, 10.0]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("raw_dir", nargs="?", default="data/raw")
    ap.add_argument("out_dir", nargs="?", default="data/processed")
    a = ap.parse_args(argv)

    raws = []
    for f in sorted(Path(a.raw_dir).rglob("*.json")):
        raw = json.loads(f.read_text(encoding="utf-8"))
        if raw.get("blocked") or "texts" not in raw:
            continue
        raws.append(raw)
    if not raws:
        print("No usable raw files found."); return 1

    rows = []
    for sev in SEVERITIES:
        for tau in TAUS:
            n_known = lost = collapsed = n_links = n_fault = 0
            for raw in raws:
                t = audit_texts(raw, sev, tau)
                if len(t):
                    k = t[~t.bg_unknown]
                    n_known += len(k)
                    lost += int(k.lost_under_cvd.sum())
                    hit = pd.Series(False, index=k.index)
                    for c in CVD_TYPES:
                        hit |= (k.de_normal >= tau) & (k[f"de_{c}"] < tau)
                    collapsed += int(hit.sum())
                l = audit_links(raw, sev, tau)
                if len(l):
                    n_links += len(l)
                    n_fault += int(l.color_only_fault.sum())
            pct = lambda x, n: round(100 * x / n, 2) if n else None
            rows.append(dict(severity=sev, tau=tau, texts_measurable=n_known,
                             pct_lost_under_cvd=pct(lost, n_known),
                             pct_text_bg_collapsed=pct(collapsed, n_known),
                             links_in_text=n_links, color_only_faults=n_fault))
    df = pd.DataFrame(rows)
    out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "sensitivity.csv", index=False)
    print(f"Pages used: {len(raws)}")
    print(df.to_string(index=False))
    print(f"\nSaved: {out / 'sensitivity.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
"""Move newest captured JSON files from Downloads into data/raw/<site>/<page>_NN.json, then build the report.

python -m cvd_audit.ingest            # ingest + report (English) + open
"""
import json, shutil, sys, webbrowser
from pathlib import Path
from .report import build

CURRENT_VERSION = 3

def main():
    dl = Path.home() / "Downloads"
    files = sorted(dl.glob("*_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    moved = 0
    for f in files:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if "texts" not in d or "links" not in d or d.get("method") not in ("manual_bookmark", "manual_devtools"):
            continue
        site, page = d.get("site", "unknown"), d.get("page_type", "page")
        dest_dir = Path("data/raw") / site; dest_dir.mkdir(parents=True, exist_ok=True)
        n = len(list(dest_dir.glob(f"{page}_*.json")))
        dest = dest_dir / f"{page}_{n:02d}.json"
        shutil.move(str(f), dest); moved += 1
        print(f"Moved: {f.name} -> {dest}")
        v = d.get("version", 0)
        if v >= CURRENT_VERSION:
            print(f"  Capture code version {v}: up to date.")
        else:
            print(f"  WARNING: this file was made by an OLD capture button (version {v}, current is {CURRENT_VERSION}).")
            print("  Delete the old 'Capture colors' bookmark, run 'python -m cvd_audit.snippet',")
            print("  and drag the new button from data\\install_button.html to the bookmarks bar.")
    if not moved:
        print("No new capture files in Downloads. Click the 'Capture colors' bookmark in Chrome first.")
    out = Path("data/processed/report.html"); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build("data/raw", 5.0, 1.0, "en"), encoding="utf-8")
    print(f"Report: {out.resolve()}")
    webbrowser.open(out.resolve().as_uri())

if __name__ == "__main__":
    sys.exit(main())
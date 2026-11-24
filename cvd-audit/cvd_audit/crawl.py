"""Polite crawler. Reads config/sites.toml; saves raw extraction JSON + screenshot.

Rules built in (do not remove): honour robots.txt, identify yourself in the
user agent, wait between requests, and STOP a site when it blocks you
(no evasion of captchas or bot detection). No login, no transactions.
"""
from __future__ import annotations
import argparse, json, time, tomllib, datetime as dt
from pathlib import Path
from urllib import robotparser
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from .extract import extract

BLOCK_HINTS = ("captcha", "verify you are", "access denied", "unusual traffic", "robot")
# Soft blocks: normal-looking error pages (HTTP 200) shown to automated browsers.
BLOCK_TEXT_HINTS = ("halaman tidak tersedia", "silakan log in dan coba lagi", "captcha",
                    "unusual traffic", "access denied", "verify you are")


def robots_ok(url: str, ua: str) -> bool:
    p = urlparse(url)
    rp = robotparser.RobotFileParser(f"{p.scheme}://{p.netloc}/robots.txt")
    try:
        rp.read()
    except Exception:
        return False  # cannot read robots.txt -> be conservative
    return rp.can_fetch(ua, url)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default="config/sites.toml")
    ap.add_argument("--out", default="data/raw")
    ap.add_argument("--site", default=None, help="crawl only this site name")
    ap.add_argument("--headed", action="store_true", help="show the browser window")
    a = ap.parse_args(argv)
    cfg = tomllib.loads(Path(a.config).read_text(encoding="utf-8"))
    c = cfg["crawl"]
    ua = c["user_agent"]
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not a.headed)
        ctx = browser.new_context(user_agent=ua, locale="id-ID",
                                  viewport={"width": c["viewport_width"], "height": c["viewport_height"]})
        for site in cfg["sites"]:
            if a.site and site["name"] != a.site:
                continue
            for i, pg in enumerate(site["pages"]):
                url = pg["url"]
                if url.startswith("TODO"):
                    print(f"[skip] {site['name']}/{pg['type']}: url not set"); continue
                stem = f"{pg['type']}_{i:02d}"
                out_dir = Path(a.out) / site["name"]; out_dir.mkdir(parents=True, exist_ok=True)
                meta = dict(site=site["name"], page_type=pg["type"], url=url,
                            fetched_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                            user_agent=ua, viewport=[c["viewport_width"], c["viewport_height"]])
                if c.get("respect_robots", True) and not robots_ok(url, ua):
                    (out_dir / f"{stem}.json").write_text(json.dumps({**meta, "blocked": "robots.txt"}))
                    print(f"[robots] disallowed: {url}"); continue
                page = ctx.new_page()
                try:
                    resp = page.goto(url, wait_until="load", timeout=60000)
                    page.wait_for_timeout(c.get("settle_ms", 4000))
                    # Ordinary dialogs (language/cookie notice) a human would dismiss.
                    # NOT for captchas or bot checks: those stop the crawl below.
                    for label in site.get("dismiss_texts", []):
                        try:
                            page.get_by_text(label, exact=True).first.click(timeout=3000)
                            page.wait_for_timeout(c.get("settle_ms", 4000))
                        except Exception:
                            pass
                    status = resp.status if resp else None
                    title = (page.title() or "").lower()
                    if (status and status >= 400) or any(h in title for h in BLOCK_HINTS):
                        (out_dir / f"{stem}.json").write_text(json.dumps({**meta, "blocked": f"status={status} title={title!r}"}))
                        print(f"[blocked] {url} (status {status}); stopping this site (no evasion).")
                        page.close(); break
                    raw = extract(page)
                    body = (page.inner_text("body") or "")[:1500].lower()
                    if len(raw["texts"]) < 30 and any(h in body for h in BLOCK_TEXT_HINTS):
                        (out_dir / f"{stem}.json").write_text(json.dumps({**meta, "blocked": "soft block (error/verification page)"}))
                        print(f"[blocked] {url}: error/verification page instead of content; stopping this site (no evasion).")
                        page.close(); break
                    page.screenshot(path=str(out_dir / f"{stem}.png"))
                    (out_dir / f"{stem}.json").write_text(json.dumps({**meta, **raw}))
                    print(f"[ok] {url}: {len(raw['texts'])} text, {len(raw['links'])} links")
                except Exception as e:
                    print(f"[error] {url}: {e}")
                finally:
                    page.close()
                time.sleep(c["delay_seconds"])
        browser.close()


if __name__ == "__main__":
    main()

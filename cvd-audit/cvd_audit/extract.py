"""Run the in-page extractor (extract.js) with a Playwright page."""
from pathlib import Path

_JS = (Path(__file__).parent / "extract.js").read_text(encoding="utf-8")


def extract(page) -> dict:
    return page.evaluate(_JS)

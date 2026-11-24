import pytest
from playwright.sync_api import sync_playwright
from cvd_audit.extract import extract


@pytest.fixture(scope="module")
def page():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page(); yield p; b.close()


def test_alpha_background_is_composited_over_white(page):
    page.set_content("<body><div style='background:rgba(0,0,0,.5)'><p style='color:#000'>hello world text</p></div></body>")
    t = extract(page)["texts"][0]
    assert all(abs(c - 127.5) <= 1 for c in t["bg"])


def test_background_image_is_flagged_unknown(page):
    page.set_content("<body><div style='background-image:linear-gradient(red,blue)'><p>hello world text</p></div></body>")
    assert extract(page)["texts"][0]["bgUnknown"] is True


def test_hidden_text_is_ignored(page):
    page.set_content("<body><p style='display:none'>secret</p><p style='visibility:hidden'>secret</p><p>shown</p></body>")
    assert [t["textLen"] for t in extract(page)["texts"]] == [5]


def test_link_in_running_text_vs_standalone_link(page):
    page.set_content("<body><p>This sentence has an <a href='#'>embedded link</a> inside it.</p><nav><a href='#'>Menu</a></nav></body>")
    links = extract(page)["links"]
    assert len(links) == 1 and links[0]["linkText"] == "embedded link"

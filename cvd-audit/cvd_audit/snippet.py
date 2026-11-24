"""Manual-capture helpers (a human browses; no automation).

python -m cvd_audit.snippet  writes:
  data/capture_snippet.js      (old way: paste into DevTools Console)
  data/install_button.html     (easy way: drag the button to the Chrome bookmarks bar, click it on any page)
"""
import re, urllib.parse
from pathlib import Path

JS = (Path(__file__).parent / "extract.js").read_text(encoding="utf-8")
HEADER = """// EDIT these two values before each capture:
const META = { site: 'shopee', page_type: 'home' };
"""
BODY = (
    "(function (data) {\n"
    "  try { copy(data); } catch (e) {}\n"
    "  const a = document.createElement('a');\n"
    "  a.href = URL.createObjectURL(new Blob([data], { type: 'application/json' }));\n"
    "  a.download = META.site + '_' + META.page_type + '.json';\n"
    "  document.body.appendChild(a); a.click(); a.remove();\n"
    "  console.log('Downloaded ' + a.download + ' to your Downloads folder');\n"
    "})(JSON.stringify(Object.assign({ method: 'manual_devtools', fetched_at: new Date().toISOString(), "
    "viewport: [innerWidth, innerHeight] }, META, (" + JS.strip() + ")())));\n"
)


def bookmarklet_code() -> str:
    """One-line JS. Asks for the page type, site comes from the address bar (shopee.co.id -> shopee)."""
    core = re.sub(r"\s//[^\n]*", "", JS.strip())          # drop trailing // comments
    core = re.sub(r"^\s*//[^\n]*\n", "", core, flags=re.M)   # drop full-line comments
    core = re.sub(r"\s*\n\s*", " ", core)
    return (
        "(function(){"
        "var pt=prompt('Page type? (home / listing / product / cart / checkout)','home');if(!pt)return;"
        "var host=location.hostname.replace(/^www\\./,'').split('.')[0];"
        "var META={site:host,page_type:pt};"
        "var data=JSON.stringify(Object.assign({method:'manual_bookmark',fetched_at:new Date().toISOString(),"
        "viewport:[innerWidth,innerHeight]},META,(" + core + ")()));"
        "var a=document.createElement('a');a.href=URL.createObjectURL(new Blob([data],{type:'application/json'}));"
        "a.download=META.site+'_'+META.page_type+'.json';document.body.appendChild(a);a.click();a.remove();"
        "alert('Done: '+a.download+' was saved to your Downloads folder.');"
        "})();"
    )


PAGE = """<!doctype html><html lang="en"><meta charset="utf-8"><title>Install the capture button</title>
<style>body{font:18px/1.7 system-ui,Arial;max-width:720px;margin:40px auto;padding:0 16px}
a.btn{display:inline-block;background:#1a56db;color:#fff;padding:12px 22px;border-radius:8px;text-decoration:none;font-weight:600}
.box{background:#f4f4f4;border-radius:8px;padding:12px 16px}</style>
<h1>Install the "Capture colors" button</h1>
<p>Drag the blue button below to the <b>bookmarks bar</b> in Chrome (the row under the address bar). Hold the mouse button, move, release.</p>
<p><a class="btn" href="__HREF__">Capture colors</a></p>
<div class="box">If the bookmarks bar is not visible, press <b>Ctrl+Shift+B</b>.</div>
<p>Once installed, open a Shopee page in Chrome and click <b>Capture colors</b> in the bookmarks bar.
Type the page type (for example <b>home</b>), press OK, and the file is saved to your Downloads folder.</p>
"""

if __name__ == "__main__":
    out = Path("data/capture_snippet.js")
    out.parent.mkdir(exist_ok=True)
    out.write_text(HEADER + BODY, encoding="utf-8")
    href = "javascript:" + urllib.parse.quote(bookmarklet_code(), safe="()'*!~._-")
    Path("data/install_button.html").write_text(PAGE.replace("__HREF__", href.replace('"', "&quot;")), encoding="utf-8")
    print(f"Wrote {out} and data/install_button.html")
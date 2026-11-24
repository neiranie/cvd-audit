"""Readable HTML report (English or Bahasa Indonesia) from raw capture JSON files.

Usage:  python -m cvd_audit.report data\\raw data\\processed\\laporan.html [--tau 5] [--lang en|id] [--open]
"""
from __future__ import annotations
import argparse, html, json, sys, webbrowser
from pathlib import Path
import pandas as pd
from .color import rgb255_to_rgb, simulate_cvd
from .audit import audit_texts, audit_links, summarize
from .cues import DEFAULT_TAU

E_ = html.escape

TXT = {
 "id": dict(
  title="Laporan audit warna untuk buta warna (CVD)", summary_all="Ringkasan semua halaman",
  c_page="Halaman", c_texts="Jumlah teks", c_unk="Latar tak terukur", c_fail="Gagal kontras AA",
  c_lost="Hilang di buta warna", c_links="Tautan hanya warna",
  read="Program membaca <b>{n}</b> teks. Sebanyak <b>{u}</b> ({up}) tidak dihitung karena latarnya tidak bisa diukur (ada gambar atau lapisan lain di belakangnya). Dari <b>{m}</b> teks yang bisa diukur, <b>{fp}</b> tidak memenuhi batas kontras WCAG AA pada penglihatan normal.",
  lost="Teks yang cukup kontras pada penglihatan normal tetapi tidak lagi memenuhi batas di bawah simulasi buta warna: <b>{p}</b>.",
  links="Dari <b>{n}</b> tautan di dalam kalimat, <b>{p}</b> hanya dibedakan dengan warna (tanpa garis bawah, cetak tebal, dan sejenisnya). Yang warnanya menyatu dengan teks sekitarnya di bawah buta warna: <b>{q}</b>.",
  h_fail="Teks yang kontrasnya kurang (dikelompokkan per gaya)", none="Tidak ada.",
  grp="{a} elemen gagal, tetapi hanya {b} kombinasi gaya yang berbeda. Satu aturan warna yang berulang di banyak kartu dihitung sebagai satu kombinasi.",
  t_cols=("Jumlah elemen","Kontras","Batas","Ukuran / tebal","Contoh elemen","Tampilan (normal, protan, deutan)"),
  h_links="Tautan yang hanya dibedakan dengan warna",
  l_cols=("Tautan","Beda warna normal (ΔE)","Beda warna deutan (ΔE)","Status"),
  same="warnanya sama dengan teks sekitar (tidak dibedakan warna, bahkan pada penglihatan normal)",
  merge="menyatu di buta warna", still="masih terbedakan", sw_link="tautan", sw_around="teks sekitar", sample="Contoh teks",
  note="<b>Catatan.</b> Ambang perbedaan warna τ = {tau} (ΔE2000) adalah <b>placeholder</b> sampai ditetapkan dari literatur. Simulasi buta warna memakai model Machado dkk. (2009); simulasi tritan hanya pendekatan. Ini hasil simulasi, bukan pengujian pada penyandang buta warna. Persentase kegagalan hanya dihitung dari teks yang latarnya bisa diukur. Teks di dalam gambar tidak terbaca.",
  empty="Tidak ada data mentah yang bisa dibaca.", done="Laporan ditulis:"),
 "en": dict(
  title="Color accessibility audit for color vision deficiency (CVD)", summary_all="Summary of all pages",
  c_page="Page", c_texts="Text elements", c_unk="Background not measurable", c_fail="Fail WCAG AA contrast",
  c_lost="Lost under simulated CVD", c_links="Color-only links",
  read="The tool read <b>{n}</b> text elements. <b>{u}</b> ({up}) were excluded because the background could not be measured (an image or another layer lies behind the text). Of the <b>{m}</b> measurable elements, <b>{fp}</b> do not meet the WCAG AA contrast threshold under normal vision.",
  lost="Text that passes the contrast threshold under normal vision but no longer passes under simulated CVD: <b>{p}</b>.",
  links="Of <b>{n}</b> inline links, <b>{p}</b> are distinguished by color alone (no underline, bold weight or similar cue). Links whose color collapses into the surrounding text under simulated CVD: <b>{q}</b>.",
  h_fail="Text with insufficient contrast (grouped by style)", none="None.",
  grp="{a} elements fail, but they share only {b} distinct style combinations. A color rule repeated across many cards is counted as one combination.",
  t_cols=("Elements","Contrast","Threshold","Size / weight","Example element","Appearance (normal, protan, deutan)"),
  h_links="Links distinguished by color alone",
  l_cols=("Link","Color difference, normal (ΔE)","Color difference, deutan (ΔE)","Status"),
  same="same color as surrounding text (no color difference even under normal vision)",
  merge="collapses under CVD", still="still distinguishable", sw_link="link", sw_around="surrounding text", sample="Sample text",
  note="<b>Note.</b> The color-difference threshold τ = {tau} (ΔE2000) is a <b>placeholder</b> until it is set from the literature. CVD is simulated with the Machado et al. (2009) model; the tritan simulation is only an approximation. These are simulation results, not tests with people who have CVD. Failure rates are computed only over text whose background could be measured. Text inside images is not read.",
  empty="No raw data could be read.", done="Report written:"),
}
CSS = """
body{font:16px/1.6 system-ui,Segoe UI,Arial,sans-serif;max-width:980px;margin:24px auto;padding:0 16px;color:#1b1b1b;background:#fff}
h1{font-size:1.6rem}h2{font-size:1.25rem;margin-top:2.2rem;border-bottom:2px solid #ddd;padding-bottom:4px}
h3{font-size:1.05rem;margin-top:1.6rem}
table{border-collapse:collapse;width:100%;margin:10px 0}th,td{border:1px solid #ccc;padding:6px 8px;text-align:left;vertical-align:middle;font-size:.95rem}
th{background:#f0f0f0}.note{background:#fff7d6;border:1px solid #e2c75a;padding:8px 12px;border-radius:6px;font-size:.92rem}
.big{font-size:1.05rem}.sw{display:inline-block;padding:3px 8px;border-radius:3px;border:1px solid #0002;width:140px;white-space:nowrap;text-align:center;box-sizing:border-box;margin:2px 0}
.lab{display:inline-block;width:56px}
.bad{color:#9b1c1c;font-weight:600}.ok{color:#1b6e2d;font-weight:600}.small{font-size:.85rem;color:#555}
"""


def hx(rgb255) -> str:
    return "#%02x%02x%02x" % tuple(int(round(max(0, min(255, v)))) for v in rgb255)


def sim(rgb255, kind: str) -> str:
    return hx(simulate_cvd(rgb255_to_rgb(rgb255), kind) * 255)


def swatches(fg, bg, label) -> str:
    cells = [("Normal", fg, bg), ("Protan", sim(fg, "protan"), sim(bg, "protan")),
             ("Deutan", sim(fg, "deutan"), sim(bg, "deutan"))]
    out = []
    for name, f, b in cells:
        f = f if isinstance(f, str) else hx(f)
        b = b if isinstance(b, str) else hx(b)
        out.append(f"<span class='small lab'>{name}</span><span class='sw' style='color:{f};background:{b}'>{E_(label)}</span>")
    return "<br>".join(out)


_DECIMAL = ","


def pct(x) -> str:
    return f"{x:.1f}%".replace(".", _DECIMAL)


def page_section(raw: dict, tau: float, severity: float, L: dict) -> tuple[str, dict]:
    t = audit_texts(raw, severity, tau)
    l = audit_links(raw, severity, tau)
    t["fg_hex"] = [hx(x["fg"]) for x in raw["texts"]]
    t["bg_hex"] = [hx(x["bg"]) for x in raw["texts"]]
    s = summarize(t, l)
    name = f"{raw.get('site','?')} / {raw.get('page_type','?')}"
    h = [f"<h2>{E_(name)}</h2>"]
    n_unk = int(t.bg_unknown.sum())
    h.append("<p class='big'>" + L["read"].format(n=len(t), u=n_unk, up=pct(s.get("pct_bg_unknown", 0)),
             m=s.get("n_text_measurable", 0), fp=pct(s.get("pct_text_fail_aa_normal", 0))) + "</p>")
    h.append("<p class='big'>" + L["lost"].format(p=pct(s.get("pct_text_lost_under_cvd", 0))) + "</p>")
    if len(l):
        h.append("<p class='big'>" + L["links"].format(n=len(l), p=pct(s.get("pct_links_color_only", 0)),
                 q=pct(s.get("pct_links_color_only_fault", 0))) + "</p>")
    f = t[(~t.pass_normal) & (~t.bg_unknown)]
    h.append(f"<h3>{L['h_fail']}</h3>")
    if f.empty:
        h.append(f"<p>{L['none']}</p>")
    else:
        g = (f.groupby(["fg_hex", "bg_hex", "font_size", "font_weight"], as_index=False)
              .agg(jumlah=("tag", "size"), kontras=("cr_normal", "min"), batas=("threshold", "first"),
                   ex_tag=("tag", "first"), ex_cls=("cls", "first"), ex_len=("text_len", "first"))
              .sort_values(["jumlah", "kontras"], ascending=[False, True]))
        h.append("<p class='small'>" + L["grp"].format(a=len(f), b=len(g)) + "</p>")
        h.append("<table><tr>" + "".join(f"<th>{c}</th>" for c in L["t_cols"]) + "</tr>")
        for _, r in g.head(12).iterrows():
            h.append(f"<tr><td>{r.jumlah}</td><td>{r.kontras:.2f}</td><td>{r.batas:.1f}</td>"
                     f"<td>{r.font_size:.0f}px / {int(r.font_weight)}</td>"
                     f"<td class='small'>&lt;{E_(str(r.ex_tag))}&gt;<br>class: {E_(str(r.ex_cls)[:40]) or '-'}<br>{int(r.ex_len)} chars</td>"
                     f"<td>{swatches(_rgb(r.fg_hex), _rgb(r.bg_hex), L['sample'])}</td></tr>")
        h.append("</table>")
    if len(l):
        l = l.copy()
        l["fg_hex"] = [hx(x["fg"]) for x in raw["links"]]
        l["blk_hex"] = [hx(x["blockFg"]) for x in raw["links"]]
        l["bg_hex"] = [hx(x["bg"]) for x in raw["links"]]
        o = l[~l.has_non_color_cue]
        h.append(f"<h3>{L['h_links']}</h3>")
        if o.empty:
            h.append(f"<p>{L['none']}</p>")
        else:
            h.append("<table><tr>" + "".join(f"<th>{c}</th>" for c in L["l_cols"]) + "</tr>")
            for _, r in o.head(15).iterrows():
                if r.de_normal < tau:
                    status = f"<span class='small'>{L['same']}</span>"
                elif r.collapsed_any:
                    status = f"<span class='bad'>{L['merge']}</span>"
                else:
                    status = f"<span class='ok'>{L['still']}</span>"
                h.append(f"<tr><td>{E_(str(r.link_text))}<br>"
                         f"<span class='sw' style='color:{r.fg_hex};background:{r.bg_hex}'>{L['sw_link']}</span><br>"
                         f"<span class='sw' style='color:{r.blk_hex};background:{r.bg_hex}'>{L['sw_around']}</span></td>"
                         f"<td>{r.de_normal:.1f}</td><td>{r.de_deutan:.1f}</td><td>{status}</td></tr>")
            h.append("</table>")
    row = dict(halaman=name, teks=len(t), tak_terukur=s.get("pct_bg_unknown", 0), gagal_aa=s.get("pct_text_fail_aa_normal", 0),
               hilang_cvd=s.get("pct_text_lost_under_cvd", 0), tautan_warna_saja=s.get("pct_links_color_only", 0))
    return "\n".join(h), row


def _rgb(hexstr: str):
    h = hexstr.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def build(raw_dir: str, tau: float, severity: float, lang: str = "en") -> str:
    global _DECIMAL
    _DECIMAL = "," if lang == "id" else "."
    L = TXT[lang]
    secs, rows = [], []
    for fpath in sorted(Path(raw_dir).rglob("*.json")):
        raw = json.loads(fpath.read_text(encoding="utf-8"))
        if raw.get("blocked") or "texts" not in raw:
            continue
        sec, row = page_section(raw, tau, severity, L)
        secs.append(sec); rows.append(row)
    if not rows:
        raise SystemExit(L["empty"])
    tbl = ["<table><tr>" + "".join(f"<th>{L[k]}</th>" for k in ("c_page","c_texts","c_unk","c_fail","c_lost","c_links")) + "</tr>"]
    for r in rows:
        tbl.append(f"<tr><td>{E_(r['halaman'])}</td><td>{r['teks']}</td><td>{pct(r['tak_terukur'])}</td><td>{pct(r['gagal_aa'])}</td>"
                   f"<td>{pct(r['hilang_cvd'])}</td><td>{pct(r['tautan_warna_saja'])}</td></tr>")
    tbl.append("</table>")
    note = "<div class='note'>" + L["note"].format(tau=tau) + "</div>"
    return (f"<!doctype html><html lang='{lang}'><meta charset='utf-8'><title>{L['title']}</title><style>{CSS}</style><body>"
            f"<h1>{L['title']}</h1>{note}<h2>{L['summary_all']}</h2>{''.join(tbl)}"
            f"{''.join(secs)}</body></html>")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("raw_dir"); ap.add_argument("out_html")
    ap.add_argument("--tau", type=float, default=DEFAULT_TAU); ap.add_argument("--severity", type=float, default=1.0)
    ap.add_argument("--lang", choices=["en", "id"], default="en"); ap.add_argument("--open", action="store_true")
    a = ap.parse_args(argv)
    out = Path(a.out_html); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(a.raw_dir, a.tau, a.severity, a.lang), encoding="utf-8")
    print(f"{TXT[a.lang]['done']} {out.resolve()}")
    if a.open:
        webbrowser.open(out.resolve().as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
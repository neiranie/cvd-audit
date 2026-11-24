"""Fault-injection validation of the DOM-extraction + detection pipeline.

Pages are generated with KNOWN faults (link without non-color cue AND a color pair
chosen to collapse under simulated deutan/protan). The pipeline must recover them
through a real browser, across different ways of writing the same color
(hex, CSS variable, color(srgb ...)).

SCOPE (state this in the paper): ground truth is defined by construction with the
same metric, so this validates the extraction/aggregation pipeline and its
robustness to CSS notation, NOT the perceptual validity of the metric.
Perceptual evidence comes from the secondary analysis of public human ratings.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
from playwright.sync_api import sync_playwright
from cvd_audit.color import rgb255_to_rgb, simulate_cvd, delta_e2000
from cvd_audit.extract import extract
from cvd_audit.audit import audit_links
from cvd_audit.cues import DEFAULT_TAU


def _de_vec(a, b):
    from skimage.color import rgb2lab, deltaE_ciede2000
    return deltaE_ciede2000(rgb2lab(a.reshape(1, -1, 3)), rgb2lab(b.reshape(1, -1, 3))).reshape(-1)


def _sim_vec(x, kind):
    from cvd_audit.color import srgb_to_linear, linear_to_srgb, cvd_matrix
    return linear_to_srgb(np.clip(srgb_to_linear(x) @ cvd_matrix(kind).T, 0, 1))


def find_pairs(rng, n_collapse=10, n_safe=10, batch=200_000, max_batches=200):
    """Vectorised random search for clear-cut collapse and safe color pairs."""
    collapse, safe = [], []
    for _ in range(max_batches):
        a, b = rng.random((batch, 3)), rng.random((batch, 3))
        dn = _de_vec(a, b)
        sims = {k: _de_vec(_sim_vec(a, k), _sim_vec(b, k)) for k in ("protan", "deutan", "tritan")}
        is_c = (dn >= 15) & (sims["protan"] <= 2) & (sims["deutan"] <= 2)
        is_s = (dn >= 25) & (np.minimum.reduce(list(sims.values())) >= 15)
        for i in np.flatnonzero(is_c)[: n_collapse - len(collapse)]:
            collapse.append((a[i], b[i]))
        for i in np.flatnonzero(is_s)[: n_safe - len(safe)]:
            safe.append((a[i], b[i]))
        if len(collapse) >= n_collapse and len(safe) >= n_safe:
            return collapse, safe
    raise RuntimeError(f"pair search failed: {len(collapse)} collapse, {len(safe)} safe")


def css_color(rgb, variant):
    r, g, b = (int(round(x * 255)) for x in rgb)
    if variant == "hex":
        return f"#{r:02x}{g:02x}{b:02x}"
    if variant == "srgb_fn":
        return f"color(srgb {r/255:.5f} {g/255:.5f} {b/255:.5f})"
    return f"rgb({r} {g} {b})"


def build_html(cases):
    css = ["body{font:16px/1.5 sans-serif;background:#fff}", ".t{margin:8px;padding:4px}"]
    body = []
    for i, c in enumerate(cases):
        txt, lnk = css_color(c["text"], c["variant"]), css_color(c["link"], c["variant"])
        if c["variant"] == "css_var":
            css.append(f".c{i}{{--t:{css_color(c['text'],'hex')};--l:{css_color(c['link'],'hex')}}}"
                       f" .c{i}{{color:var(--t)}} .c{i} a{{color:var(--l)}}")
        else:
            css.append(f".c{i}{{color:{txt}}} .c{i} a{{color:{lnk}}}")
        css.append(f".c{i} a{{text-decoration:{'underline' if c['underline'] else 'none'}}}")
        body.append(f"<p class='t c{i}'>Some surrounding sentence for context <a href='#{i}'>link{i}</a> and more words.</p>")
    return f"<!doctype html><meta charset=utf-8><style>{''.join(css)}</style><body>{''.join(body)}</body>"


def run(seed=0, n=10, out="data/processed/fault_injection.json"):
    rng = np.random.default_rng(seed)
    collapse, safe = find_pairs(rng, n, n)
    cases = []
    for variant in ("hex", "css_var", "srgb_fn"):
        for kind, pairs in (("collapse", collapse), ("safe", safe)):
            for underline in (False, True):
                for a, b in pairs:
                    cases.append(dict(variant=variant, pair=kind, underline=underline, text=a, link=b,
                                      truth=bool((kind == "collapse") and not underline)))
    html = build_html(cases)
    with sync_playwright() as pw:
        br = pw.chromium.launch(); page = br.new_page()
        page.set_content(html); raw = extract(page); br.close()
    assert len(raw["links"]) == len(cases), (len(raw["links"]), len(cases))
    df = audit_links(raw, tau=DEFAULT_TAU)
    pred = df.color_only_fault.to_numpy(); truth = np.array([c["truth"] for c in cases])
    tp, fp = int((pred & truth).sum()), int((pred & ~truth).sum())
    fn, tn = int((~pred & truth).sum()), int((~pred & ~truth).sum())
    err = max(abs(np.array(l["fg"]) - np.round(np.array(c["link"]) * 255)).max()
              for l, c in zip(raw["links"], cases))
    res = dict(n_links=len(cases), tp=tp, fp=fp, fn=fn, tn=tn,
               precision=tp / (tp + fp) if tp + fp else None, recall=tp / (tp + fn) if tp + fn else None,
               max_extracted_color_error_levels=float(err), tau=DEFAULT_TAU, seed=seed)
    per_variant = {}
    for v in ("hex", "css_var", "srgb_fn"):
        idx = [i for i, c in enumerate(cases) if c["variant"] == v]
        per_variant[v] = dict(correct=int((pred[idx] == truth[idx]).sum()), total=len(idx))
    res["per_variant"] = per_variant
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(res, indent=2))
    return res


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))

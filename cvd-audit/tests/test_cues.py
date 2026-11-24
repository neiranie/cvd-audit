from cvd_audit.color import hex_to_rgb
from cvd_audit.cues import evaluate_pair, link_has_non_color_cue

BASE = dict(decoration="none", blockDecoration="none", borderBottomWidth=0, borderBottomStyle="none",
            fontWeight=400, blockFontWeight=400, fontStyle="normal", blockFontStyle="normal")


def test_cue_detection():
    assert not link_has_non_color_cue(BASE)
    assert link_has_non_color_cue({**BASE, "decoration": "underline"})
    assert not link_has_non_color_cue({**BASE, "decoration": "underline", "blockDecoration": "underline"})
    assert link_has_non_color_cue({**BASE, "fontWeight": 700})
    assert not link_has_non_color_cue({**BASE, "fontWeight": 500})
    assert link_has_non_color_cue({**BASE, "borderBottomWidth": 1, "borderBottomStyle": "solid"})


def test_identical_colors_never_collapse():
    c = hex_to_rgb("#112233")
    assert not evaluate_pair(c, c).collapsed_any


def test_luminance_difference_survives_cvd():
    r = evaluate_pair(hex_to_rgb("#000000"), hex_to_rgb("#ffffff"))
    assert not r.collapsed_any

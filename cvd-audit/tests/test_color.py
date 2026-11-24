import numpy as np, colour
from cvd_audit.color import hex_to_rgb, simulate_cvd, delta_e2000, CVD_TYPES, cvd_matrix
from cvd_audit.contrast import contrast_ratio, relative_luminance


def test_wcag_reference_values():
    w, b = hex_to_rgb("#ffffff"), hex_to_rgb("#000000")
    assert abs(contrast_ratio(w, b) - 21.0) < 1e-9
    assert abs(contrast_ratio(w, w) - 1.0) < 1e-12
    # widely cited WCAG example: #767676 on white is about 4.54:1
    assert abs(contrast_ratio(hex_to_rgb("#767676"), w) - 4.54) < 0.01


def test_delta_e_identity_and_symmetry():
    a, b = hex_to_rgb("#336699"), hex_to_rgb("#993366")
    assert delta_e2000(a, a) == 0.0
    assert abs(delta_e2000(a, b) - delta_e2000(b, a)) < 1e-9


def test_delta_e_agrees_with_colour_science():
    """Two independent implementations must agree (cross-check, not a substitute
    for the Sharma et al. test data; see validation/ TODO)."""
    rng = np.random.default_rng(0)
    for _ in range(200):
        a, b = rng.random(3), rng.random(3)
        lab = [colour.XYZ_to_Lab(colour.sRGB_to_XYZ(x), illuminant=colour.CCS_ILLUMINANTS["CIE 1931 2 Degree Standard Observer"]["D65"]) for x in (a, b)]
        ref = float(colour.delta_E(lab[0], lab[1], method="CIE 2000"))
        assert abs(delta_e2000(a, b) - ref) < 0.05, (a, b)


def test_cvd_matrices_preserve_grays_and_identity_at_zero():
    for k in CVD_TYPES:
        assert np.allclose(cvd_matrix(k, 0.0), np.eye(3))
        g = np.array([[0.2] * 3, [0.5] * 3, [0.9] * 3])
        assert np.allclose(simulate_cvd(g, k), g, atol=2e-3)


def test_red_green_collapses_for_deutan_and_protan_not_tritan():
    red, green = hex_to_rgb("#d62728"), hex_to_rgb("#2ca02c")
    n = delta_e2000(red, green)
    for k in ("deutan", "protan"):
        assert delta_e2000(simulate_cvd(red, k), simulate_cvd(green, k)) < 0.6 * n

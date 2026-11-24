"""Color utilities: sRGB handling, CVD simulation (Machado et al. 2009), CIEDE2000.

All RGB arrays are float in [0, 1], sRGB-encoded, unless stated otherwise.
CVD simulation is applied in LINEAR RGB, as in the original model.
Note: colour-science warns that Machado tritan simulation is an approximation
(shift paradigm). Treat protan/deutan as primary and tritan as secondary.
"""
from __future__ import annotations
import warnings
import numpy as np
import colour
from skimage.color import rgb2lab, deltaE_ciede2000

CVD_TYPES = {
    "protan": "Protanomaly",
    "deutan": "Deuteranomaly",
    "tritan": "Tritanomaly",
}


def hex_to_rgb(h: str) -> np.ndarray:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=float) / 255.0


def rgb255_to_rgb(rgb255) -> np.ndarray:
    return np.clip(np.asarray(rgb255, dtype=float) / 255.0, 0.0, 1.0)


def srgb_to_linear(c: np.ndarray) -> np.ndarray:
    c = np.asarray(c, dtype=float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c: np.ndarray) -> np.ndarray:
    c = np.clip(np.asarray(c, dtype=float), 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def cvd_matrix(kind: str, severity: float = 1.0) -> np.ndarray:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return colour.blindness.matrix_cvd_Machado2009(CVD_TYPES[kind], severity)


def simulate_cvd(rgb: np.ndarray, kind: str, severity: float = 1.0) -> np.ndarray:
    """Simulate CVD on sRGB color(s) of shape (..., 3). Returns sRGB in [0, 1]."""
    lin = srgb_to_linear(rgb)
    out = lin @ cvd_matrix(kind, severity).T
    return linear_to_srgb(np.clip(out, 0.0, 1.0))


def to_lab(rgb: np.ndarray) -> np.ndarray:
    rgb = np.clip(np.asarray(rgb, dtype=float), 0.0, 1.0)
    return rgb2lab(rgb.reshape(1, 1, 3)).reshape(3)


def delta_e2000(rgb_a: np.ndarray, rgb_b: np.ndarray) -> float:
    """CIEDE2000 between two sRGB colors (D65 white, skimage Lab conversion)."""
    la = to_lab(rgb_a).reshape(1, 1, 3)
    lb = to_lab(rgb_b).reshape(1, 1, 3)
    return float(deltaE_ciede2000(la, lb)[0, 0])

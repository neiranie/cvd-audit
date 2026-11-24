"""WCAG 2.x relative luminance and contrast ratio.

Uses the sRGB linearization threshold 0.04045 (the corrected value; older WCAG
text prints 0.03928, which differs negligibly). Verify against the WCAG text you cite.
"""
from __future__ import annotations
import numpy as np
from .color import srgb_to_linear


def relative_luminance(rgb: np.ndarray) -> float:
    r, g, b = srgb_to_linear(np.asarray(rgb, dtype=float))
    return float(0.2126 * r + 0.7152 * g + 0.0722 * b)


def contrast_ratio(rgb_a: np.ndarray, rgb_b: np.ndarray) -> float:
    la, lb = relative_luminance(rgb_a), relative_luminance(rgb_b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def is_large_text(font_size_px: float, font_weight: float) -> bool:
    """WCAG large text: >= 18pt (24px) or >= 14pt (18.66px) and bold."""
    return font_size_px >= 24.0 or (font_size_px >= 18.66 and font_weight >= 700)


def aa_threshold(font_size_px: float, font_weight: float) -> float:
    return 3.0 if is_large_text(font_size_px, font_weight) else 4.5

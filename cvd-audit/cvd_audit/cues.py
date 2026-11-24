"""Color-dependent cue logic.

OPERATIONAL DEFINITIONS (to be justified in the manuscript):
  * A pair (a, b) "collapses" under a CVD type when its CIEDE2000 difference is
    >= tau for normal vision but < tau under simulated CVD.
  * A link inside a text block has a non-color cue if it is underlined while the
    surrounding text is not, has a bottom border, differs in font weight by
    >= WEIGHT_DIFF, or differs in font style.
  * A "color-only fault" = link without non-color cue AND collapsing in >= 1 CVD type.

DEFAULT_TAU is a PLACEHOLDER. Choose it from cited psychophysical literature
before publication, and run a sensitivity analysis over several tau values.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from .color import CVD_TYPES, simulate_cvd, delta_e2000

DEFAULT_TAU = 5.0  # PLACEHOLDER: cite or justify before publication
WEIGHT_DIFF = 300


@dataclass
class PairResult:
    de_normal: float
    de_sim: dict
    collapsed: dict

    @property
    def collapsed_any(self) -> bool:
        return any(self.collapsed.values())


def evaluate_pair(rgb_a, rgb_b, tau: float = DEFAULT_TAU, severity: float = 1.0,
                  kinds=tuple(CVD_TYPES)) -> PairResult:
    rgb_a, rgb_b = np.asarray(rgb_a, float), np.asarray(rgb_b, float)
    de_n = delta_e2000(rgb_a, rgb_b)
    de_s, col = {}, {}
    for k in kinds:
        de_s[k] = delta_e2000(simulate_cvd(rgb_a, k, severity), simulate_cvd(rgb_b, k, severity))
        col[k] = bool(de_n >= tau and de_s[k] < tau)
    return PairResult(de_n, de_s, col)


def link_has_non_color_cue(link: dict) -> bool:
    """`link` is one record from extract.js (`links` list)."""
    underline = "underline" in link["decoration"] and "underline" not in link["blockDecoration"]
    border = link["borderBottomWidth"] > 0 and link["borderBottomStyle"] not in ("none", "hidden")
    weight = abs(link["fontWeight"] - link["blockFontWeight"]) >= WEIGHT_DIFF
    style = link["fontStyle"] != link["blockFontStyle"]
    return bool(underline or border or weight or style)

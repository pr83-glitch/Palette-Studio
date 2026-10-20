# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 NXSTYNATE
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Pure colour conversions and palette diagnostics.

sRGB/linear conversions serve Blender COLOR property boundaries; OKLCH serves
palette_summary's diagnostic readout. WCAG luminance classifies dark palettes.
Mapping never derives or adjusts colours.
"""

import math


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


# =========================================================================
# sRGB <-> Linear sRGB
# =========================================================================

def _srgb_to_linear(c):
    """Single sRGB channel (0-1) to linear light."""
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(c):
    """Single linear light channel to sRGB (0-1)."""
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1.0 / 2.4)) - 0.055


def srgb_to_linear(rgb):
    """Convert an sRGB RGB tuple (0-1) to linear light.

    Needed wherever a palette value crosses into a Blender ``subtype='COLOR'``
    property: Blender stores and edits those in linear light, while theme files,
    hex codes and every value in the role table are sRGB. Skipping the
    conversion makes a swatch render too light (an sRGB value displayed as if
    it were linear).
    """
    return tuple(clamp(_srgb_to_linear(c)) for c in rgb[:3])


def linear_to_srgb(rgb):
    """Convert a linear-light RGB tuple (0-1) back to sRGB.

    The inverse of :func:`srgb_to_linear`; use it when reading a
    ``subtype='COLOR'`` property back into a hex code or a palette value.
    """
    return tuple(clamp(_linear_to_srgb(c)) for c in rgb[:3])


# =========================================================================
# Linear sRGB <-> Oklab
# =========================================================================

def _linear_rgb_to_oklab(r, g, b):
    """Convert linear sRGB (0-1) to Oklab (L, a, b)."""
    l_ = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m_ = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s_ = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b

    l_ = math.copysign(abs(l_) ** (1.0 / 3.0), l_) if l_ != 0 else 0.0
    m_ = math.copysign(abs(m_) ** (1.0 / 3.0), m_) if m_ != 0 else 0.0
    s_ = math.copysign(abs(s_) ** (1.0 / 3.0), s_) if s_ != 0 else 0.0

    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b_val = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_

    return (L, a, b_val)


# =========================================================================
# sRGB <-> OKLCH
# =========================================================================

def rgb_to_oklch(r, g, b):
    """
    Convert sRGB (0-1) to OKLCH.
    Returns (L, C, H) where L is 0-1, C >= 0, H is 0-360 degrees.
    """
    lr = _srgb_to_linear(r)
    lg = _srgb_to_linear(g)
    lb = _srgb_to_linear(b)

    L, a, b_val = _linear_rgb_to_oklab(lr, lg, lb)

    C = math.sqrt(a * a + b_val * b_val)
    H = math.degrees(math.atan2(b_val, a)) % 360.0

    return (L, C, H)


# =========================================================================
# Luminance & Contrast (sRGB-based, per WCAG)
# =========================================================================

def luminance(r, g, b):
    """Relative luminance per WCAG."""
    return 0.2126 * _srgb_to_linear(r) + 0.7152 * _srgb_to_linear(g) + 0.0722 * _srgb_to_linear(b)


def is_dark(rgb):
    """Return True if the color is considered dark."""
    return luminance(*rgb) < 0.18

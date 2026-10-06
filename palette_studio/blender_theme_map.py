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
Build the flat palette that ``apply.py`` writes into Blender.

Palette Studio uses the source theme's colours **exactly**. There is no
lightening, darkening, desaturation, contrast fixing or synthetic hue rotation
here any more: every value is a verbatim copy of one of the theme's own
colours (the 16 ANSI slots plus ``bg`` / ``fg`` / ``cursor`` / ``selection`` and
the Finetune picks).

The role -> slot mapping itself lives in :mod:`.color_roles`, so retuning a
role later is a one-line edit there rather than an edit among dozens of colour
derivations. This module only adds the three non-colour keys Blender needs
alongside the table:

* ``"dark"`` - luminance test on the theme background
* ``"ansi"`` - the untouched 16 ANSI colours
* ``"collection_colors"`` - the 8 Collection Color tag colours

``color_math`` is kept here for the luminance test and the debug summary only.
"""

from . import color_math as cm
from . import color_roles


def build_palette(palette_theme):
    """Resolve a normalized theme dict into the flat palette apply.py wants.

    Args:
        palette_theme: Dict with ``ansi`` (16 RGB tuples), ``bg``, ``fg`` and
            optionally ``cursor``, ``selection``, the accent-role overrides and
            the Finetune picks. See :mod:`.color_roles` for the slot list.

    Returns:
        Dict of palette key -> RGB or RGBA tuple, plus the ``dark``, ``ansi``
        and ``collection_colors`` keys.
    """
    palette = color_roles.resolve(palette_theme)
    palette["dark"] = cm.is_dark(palette_theme["bg"])
    palette["ansi"] = palette_theme["ansi"]
    palette["collection_colors"] = color_roles.resolve_collection_colors(palette_theme)
    # Raw palette background (sRGB). apply.py seeds the Finetune Background 1
    # swatch with it, since that role defaults to the palette's own background.
    palette["theme_bg"] = palette_theme.get("bg")
    return palette


def palette_summary(palette):
    """Return a human-readable summary of the palette for debugging."""
    lines = []
    for key, val in palette.items():
        if key in ("dark", "ansi", "collection_colors"):
            continue
        if isinstance(val, tuple):
            if len(val) == 3:
                r, g, b = val
                hexc = "#{:02x}{:02x}{:02x}".format(
                    int(r * 255), int(g * 255), int(b * 255)
                )
                L, C, H = cm.rgb_to_oklch(r, g, b)
                lines.append(f"  {key:25s} = {hexc}  L={L:.3f} C={C:.3f} H={H:.0f}")
            elif len(val) == 4:
                r, g, b, a = val
                hexc = "#{:02x}{:02x}{:02x} a={:.2f}".format(
                    int(r * 255), int(g * 255), int(b * 255), a
                )
                lines.append(f"  {key:25s} = {hexc}")
    return "\n".join(lines)

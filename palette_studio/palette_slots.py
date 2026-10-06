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
Palette slot definitions.

Kept in a standalone module (no bpy imports) so both ``__init__.py`` and
``prefs.py`` can import it while their own module is still being initialized.

IMPORTANT: the accent dropdowns build their enum items from this list
statically. Blender rejects ``EnumProperty(default=...)`` when ``items`` is a
callback function, so these must never be handed to Blender as a function.
"""

# The palette editor shows these slots in order.
# First 16 are ANSI, then the named extras.
PALETTE_SLOTS = [
    ("ansi_0",  "ANSI 0 — Black"),
    ("ansi_1",  "ANSI 1 — Red"),
    ("ansi_2",  "ANSI 2 — Green"),
    ("ansi_3",  "ANSI 3 — Yellow"),
    ("ansi_4",  "ANSI 4 — Blue"),
    ("ansi_5",  "ANSI 5 — Magenta"),
    ("ansi_6",  "ANSI 6 — Cyan"),
    ("ansi_7",  "ANSI 7 — White"),
    ("ansi_8",  "ANSI 8 — Bright Black"),
    ("ansi_9",  "ANSI 9 — Bright Red"),
    ("ansi_10", "ANSI 10 — Bright Green"),
    ("ansi_11", "ANSI 11 — Bright Yellow"),
    ("ansi_12", "ANSI 12 — Bright Blue"),
    ("ansi_13", "ANSI 13 — Bright Magenta"),
    ("ansi_14", "ANSI 14 — Bright Cyan"),
    ("ansi_15", "ANSI 15 — Bright White"),
    ("bg",      "Background"),
    ("fg",      "Foreground"),
    ("cursor",  "Cursor"),
    ("selection", "Selection"),
]


# Static enum items for Blender dropdowns (identifier, name, description).
ENUM_ITEMS = [(slot_id, label, "") for slot_id, label in PALETTE_SLOTS]


# Items for the Finetune colour dropdowns (Playhead Color, Axis Colors).
# The three accent roles come first so a control can follow whatever an accent
# resolves to, then every palette slot. Same static-list rule as above.
FINETUNE_COLOR_ITEMS = [
    ("accent_primary",   "Primary accent",   "Follow the Primary accent role"),
    ("accent_secondary", "Secondary accent", "Follow the Secondary accent role"),
    ("accent_tertiary",  "Tertiary accent",  "Follow the Tertiary accent role"),
] + ENUM_ITEMS


# Same list, with a leading "Theme Default" entry that leaves the colour to the
# palette derivation. Used by Finetune dropdowns whose stock value is computed
# (Selected Object / Active Object) rather than a fixed palette slot.
FINETUNE_COLOR_ITEMS_DEFAULTED = [
    ("default", "Theme Default", "Follow the palette-derived colour"),
] + FINETUNE_COLOR_ITEMS

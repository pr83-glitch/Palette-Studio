# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Pr83-Glitch
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
Declarative role -> palette-slot mapping (exact colours only).

Palette Studio never invents a colour. Every value written into Blender's
theme is one of the source theme's own colours, copied verbatim: the 16 ANSI
slots, the named background/foreground/cursor/selection colours, and the
Finetune picks. There is no lightening, darkening, desaturation, contrast
fixing or synthetic hue rotation anywhere in the pipeline any more — what used
to be ~150 OKLCH derivations in ``blender_theme_map.build_palette`` is now a
plain table in this module, so a role can be retuned by editing one line.

Slots
-----
``"bg"``, ``"fg"``, ``"cursor"``, ``"selection"``
    Named colours straight from the source theme.
``"ansi_0"`` ... ``"ansi_15"``
    The 16 ANSI colours. Readable aliases exist in ``SLOT_ALIASES``
    (``"yellow"`` -> ``"ansi_3"``) for readability, but the table below uses the
    canonical ids because those are the ids the Finetune dropdowns show.
``"accent_primary"``, ``"accent_secondary"``, ``"accent_tertiary"``
    The three accent roles. ``__init__._apply_accent_overrides()`` writes the
    user's dropdown pick into the theme dict before ``build_palette`` runs, so
    the chain in ``SLOT_CHAINS`` picks up the override and falls back to the
    default slot when no pick is set.
``"bg_primary"``, ``"bg_secondary"``, ``"outline_color"``, ``"outline_color_2"``, ``"outline_color_3"``
    The User Interface colour roles from Finetune. The three outline roles are
    slot dropdowns (defaults ``ansi_8``, ``bg`` and ``ansi_8``);
    ``bg_primary`` and ``bg_secondary`` are manual colour overrides that
    ``__init__._apply_accent_overrides()`` writes only while their Finetune
    toggle is on, so both fall through to the palette's own background until
    then. ``bg_secondary`` sits on top of ``bg_primary``, so rerouting
    Background 1 also moves the surfaces that Background 2 draws on.
    ``outline_color_2`` and ``outline_color_3`` are independently routable
    outline roles used by specific Blender widget families.
``"playhead_color"``, ``"keyframe_selected_color"``, ``"object_selected_color"``,
``"object_active_color"``, ``"axis_x_color"``, ``"axis_y_color"``, ``"axis_z_color"``
    Per-palette Finetune picks, resolved the same way.

Values
------
An entry in ``ROLE_MAP`` is either a slot id (RGB) or a ``(slot, alpha)`` pair
(RGBA). Alpha is the one value that is not a palette colour; keep it sparse.

Adding / changing a role
------------------------
1. Add or edit its line in ``ROLE_MAP`` (or ``COLLECTION_SLOTS`` /
   ``NODE_SLOTS`` / ``ICON_SLOTS``).
2. Add the key to the dict returned by ``blender_theme_map.build_palette`` only
   if it is a new *top-level* key — it already copies ``ROLE_MAP`` wholesale.
3. Consume it in ``apply.py`` with ``_set_color`` / ``_try_set``.

Known finetune candidates (deliberate consequences of using exact colours):
text-on-accent roles all resolve to ``fg``, so a theme whose ``fg`` is dim next
to a mid-tone accent can be hard to read; the dopesheet/timeline current-frame
ruler keeps ANSI 0 black; ``camera_passepartout`` is the Background 1 colour at a fixed alpha, and
``grid_line`` / ``wire_color`` stay pinned to ANSI 8 so line work never
collapses into the surface behind it.
"""

# ---------------------------------------------------------------------------
# Slots
# ---------------------------------------------------------------------------

#: Named theme colours, resolved directly from the normalized theme dict.
NAMED_SLOTS = ("bg", "fg", "cursor", "selection")

#: The 16 ANSI colours.
ANSI_SLOTS = tuple("ansi_%d" % i for i in range(16))

#: Every slot a role may point at directly.
THEME_SLOTS = NAMED_SLOTS + ANSI_SLOTS

#: Readable aliases -> canonical slot ids (purely cosmetic).
SLOT_ALIASES = {
    "black": "ansi_0",
    "red": "ansi_1",
    "green": "ansi_2",
    "yellow": "ansi_3",
    "blue": "ansi_4",
    "magenta": "ansi_5",
    "cyan": "ansi_6",
    "white": "ansi_7",
    "bright_black": "ansi_8",
    "bright_red": "ansi_9",
    "bright_green": "ansi_10",
    "bright_yellow": "ansi_11",
    "bright_blue": "ansi_12",
    "bright_magenta": "ansi_13",
    "bright_cyan": "ansi_14",
    "bright_white": "ansi_15",
}

#: Ordered fallback chain per slot. The first slot that the theme actually
#: provides wins. This is how a theme without a ``selection``/``cursor`` colour
#: (or without a Finetune pick) still resolves.
SLOT_CHAINS = {
    "bg": ("bg", "ansi_0"),
    "fg": ("fg", "ansi_7"),
    "cursor": ("cursor", "ansi_15"),
    "selection": ("selection", "ansi_4"),
    "accent_primary": ("accent_primary", "ansi_3"),
    "accent_secondary": ("accent_secondary", "ansi_6"),
    "accent_tertiary": ("accent_tertiary", "selection", "ansi_5"),
    "playhead_color": ("playhead_color", "ansi_2"),
    "keyframe_selected_color": ("keyframe_selected_color", "accent_primary", "ansi_3"),
    "object_selected_color": ("object_selected_color", "ansi_11"),
    "object_active_color": ("object_active_color", "ansi_3"),
    "axis_x_color": ("axis_x_color", "ansi_1"),
    "axis_y_color": ("axis_y_color", "ansi_2"),
    "axis_z_color": ("axis_z_color", "ansi_4"),
    # User Interface colours (Finetune). The first entry is the theme-dict key
    # written by __init__._apply_accent_overrides() while the matching control
    # overrides it; the rest is the fallback path while it is off. Background 2
    # follows Background 1, which itself falls back to the palette background.
    "bg_primary": ("bg_primary", "bg", "ansi_0"),
    "bg_secondary": ("bg_secondary", "bg_primary", "bg", "ansi_0"),
    "outline_color": ("outline_color", "ansi_8"),
    "outline_color_2": ("outline_color_2", "bg", "ansi_0"),
    "outline_color_3": ("outline_color_3", "ansi_8"),
}

#: Only reached if a theme supplies none of a slot's chain (malformed data).
LAST_RESORT = (0.5, 0.5, 0.5)


# ---------------------------------------------------------------------------
# Roles consumed by apply.py
# ---------------------------------------------------------------------------

#: Every derived palette key -> the palette slot that supplies its colour.
#: Keys and their RGB/RGBA shape match what apply.py already expects.
ROLE_MAP = {
    # -- Surfaces ----------------------------------------------------------
    "ui_bg": "bg_primary",            # editor, sidebar, activity bar
    "ui_panel": "bg_primary",         # panels use the same surface as the editor
    "ui_panel_header": "bg_primary",
    "ui_panel_sub": "bg_primary",
    "ui_card": "bg_secondary",        # popups and raised surfaces
    "ui_popup": "bg_secondary",
    "ui_border": "outline_color",
    "ui_separator": "outline_color",
    "ui_panel_outline": ("outline_color_2", 0.3),
    "outline_color_2": "outline_color_2",
    "outline_color_3": "outline_color_3",
    "editor_border": "outline_color",  # border between editors (5.x)
    "row_alternate": "bg_primary",     # list stripes follow the main surface

    # -- Viewport gradient -------------------------------------------------
    "viewport_gradient_low": "bg_primary",
    "viewport_gradient_high": "bg_primary",

    # -- Text (the theme's own foreground, no dimmed variants) -------------
    "ui_text": "fg",
    "ui_text_muted": "fg",
    "ui_text_disabled": "fg",
    "ui_text_highlight": "fg",
    "panel_text": "fg",
    "panel_title": "fg",
    "header_text": "fg",
    "widget_text": "fg",
    "button_text": "fg",
    "button_text_hi": "fg",
    "toolbar_text": "fg",
    "text_fg": "fg",

    # -- Accents -----------------------------------------------------------
    "ui_accent": "accent_primary",
    "ui_accent_hover": "accent_primary",
    "ui_accent_active": "accent_primary",
    "ui_accent_text": "fg",           # glyph drawn on an accent background
    "accent_secondary_text": "fg",
    "ui_accent_func": "ansi_4",       # functional accent: selection surfaces
    "ui_accent_func_hover": "ansi_4",
    "ui_accent_func_text": "fg",

    # -- Selection ---------------------------------------------------------
    "ui_selection": "selection",
    "ui_selection_text": "fg",

    # -- Widgets -----------------------------------------------------------
    "widget_bg": "bg_secondary",
    "widget_hover": "bg_secondary",
    "widget_active": "bg_secondary",
    "widget_outline": "outline_color",
    "option_check": "fg",             # checkmark / radio dot glyph
    "widget_item": "accent_primary",  # slider fill, indicator

    # -- Buttons / toolbar -------------------------------------------------
    "button_bg": "bg_secondary",
    "button_hover": "bg_secondary",
    "toolbar_bg": "bg_secondary",

    # -- Menu & pie --------------------------------------------------------
    "menu_accent": "accent_primary",
    "menu_highlight": "ansi_14",      # bright cyan: menu bar / pulldown hover
    "menu_highlight_text": "fg",
    "menu_item_sel": "ansi_14",
    "menu_item_sel_bg": "ansi_14",
    "menu_inner_sel": "ansi_14",
    "menu_text_sel": "fg",
    "menu_item_sel_text": "fg",
    "pie_item": "accent_tertiary",
    "pie_highlight": "ansi_2",        # green: the selected pie slice
    "pie_highlight_text": "fg",
    "tab_sel_text": "fg",
    "list_highlight": "selection",
    "list_highlight_text": "fg",

    # -- Input fields ------------------------------------------------------
    "input_bg": "bg_primary",
    "input_border": "outline_color",
    "input_text": "fg",

    # -- Scroll ------------------------------------------------------------
    "scroll_bg": "bg_primary",
    "scroll_handle": "cursor",
    "scroll_handle_hover": "bg_secondary",

    # -- Editor header -----------------------------------------------------
    "header_bg": "bg_primary",

    # -- Tabs --------------------------------------------------------------
    "tab_active_bg": "bg_primary",
    "tab_inactive_bg": "bg_secondary",
    "tab_outline": "outline_color",

    # -- Cursor ------------------------------------------------------------
    "ui_cursor": "cursor",
    "ui_text_sel_highlight": "ansi_4",   # in-field text selection highlight

    # -- 3D viewport -------------------------------------------------------
    "grid_line": "ansi_8",
    "grid_axis_x": "ansi_1",
    "grid_axis_y": "ansi_2",
    "grid_axis_z": "ansi_4",
    "wire_color": "ansi_8",
    "wire_edit": "accent_primary",
    "edit_wire": "ansi_0",            # unselected edit-mode wire: exact ANSI 0
    "edit_vertex": "ansi_0",          # unselected edit-mode vertices
    "vertex_color": "ansi_11",
    "edge_select": "accent_primary",
    "face_select": ("accent_primary", 0.35),
    "obj_selected": "ansi_11",
    "obj_active": "ansi_3",
    "object_selected_color": "object_selected_color",
    "object_active_color": "object_active_color",
    "outliner_active_obj": "bg_secondary",
    "bone_color": "ansi_7",           # exact ANSI 7 white
    "camera_passepartout": ("bg_primary", 0.9),
    "before_frame": "ansi_1",
    "after_frame": "accent_tertiary",
    "gizmo_x": "axis_x_color",
    "gizmo_y": "axis_y_color",
    "gizmo_z": "axis_z_color",
    "playhead_color": "playhead_color",
    "keyframe_selected_color": "keyframe_selected_color",

    # -- State -------------------------------------------------------------
    "info_color": "accent_tertiary",
    "warning_color": "ansi_4",
    "error_color": "ansi_1",
    "success_color": "ansi_2",

    # -- Node editor -------------------------------------------------------
    "node_bg": "bg_secondary",
    "node_frame": "bg_secondary",
    "node_selected": "selection",

    # -- NLA ---------------------------------------------------------------
    "nla_strip": "accent_primary",
    "nla_strip_selected": "ansi_11",
    "nla_transition": "accent_tertiary",
    "nla_meta": "accent_secondary",
    "nla_sound": "ansi_2",
    "nla_tweak": "ansi_1",
    "nla_tweak_dup": "ansi_9",

    # -- Text editor -------------------------------------------------------
    "text_bg": "bg_primary",
    "text_cursor": "cursor",
    "text_selection": "selection",
    "text_line_highlight": "bg_secondary",
    "text_line_numbers": "fg",

    # -- Icons -------------------------------------------------------------
    "icon_scene": "ansi_4",
    "icon_collection": "ansi_6",
    "icon_object": "accent_tertiary",
    "icon_object_data": "ansi_2",
    "icon_modifier": "accent_primary",
    "icon_shading": "accent_secondary",
    "icon_folder": "ansi_3",
    "icon_autokey": "ansi_1",

    # -- Semantic originals (kept for apply.py compatibility) --------------
    "accent_primary": "accent_primary",
    "accent_secondary": "accent_secondary",
    "accent_tertiary": "accent_tertiary",
    "danger": "ansi_1",
    "danger_bright": "ansi_9",
    "warning": "ansi_4",
    "success": "ansi_2",
    "success_bright": "ansi_10",
    "cyan": "ansi_6",
    "magenta": "accent_secondary",    # legacy name for the ANSI 6 family
    "bright_magenta": "ansi_13",
    "bright_yellow": "ansi_12",       # legacy name; this is bright blue
    "bright_cyan": "ansi_14",
    "bright_black": "ansi_8",
    "black": "ansi_0",
    "white": "ansi_15",
}


# ---------------------------------------------------------------------------
# Ordered sets
# ---------------------------------------------------------------------------

#: Blender's 8 Collection Color tags, in tag order.
COLLECTION_SLOTS = (
    "ansi_1",    # 1 red
    "ansi_3",    # 2 yellow
    "ansi_11",   # 3 bright yellow
    "ansi_2",    # 4 green
    "ansi_4",    # 5 blue
    "ansi_5",    # 6 magenta
    "ansi_13",   # 7 bright magenta
    "ansi_6",    # 8 cyan
)

#: Blender's node-type colors, one per node header category.
NODE_SLOTS = {
    "node_converter": "bg_secondary",
    "node_shader": "ansi_2",
    "node_input": "ansi_12",
    "node_output": "ansi_0",
    "node_color": "ansi_5",
    "node_filter": "ansi_6",
    "node_vector": "ansi_10",
    "node_texture": "ansi_13",
    "node_group": "ansi_15",
    "node_script": "ansi_9",
    "node_pattern": "ansi_3",
    "node_matte": "ansi_11",
    "node_distort": "ansi_4",
    "node_interface": "ansi_14",
    "node_layout": "bg_secondary",
}

#: Blender's collection-color icon overrides, in apply.py order.
ICON_SLOTS = {
    "icon_scene": "ansi_4",
    "icon_collection": "ansi_6",
    "icon_object": "accent_tertiary",
    "icon_object_data": "ansi_2",
    "icon_modifier": "accent_primary",
    "icon_shading": "accent_secondary",
    "icon_folder": "ansi_3",
    "icon_autokey": "ansi_1",
}


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------

def _as_color(color):
    """Theme colour -> RGB, or RGBA when it carries an alpha component.

    ANSI slots are RGBA while the Palette Editor's Quick Adjust alpha slider
    is below 1; the 4th component has to survive resolution to reach the
    theme fields ``apply.py`` writes. bg/fg/cursor/selection and the Finetune
    picks stay RGB.
    """
    return tuple(color[:4]) if len(color) > 3 else tuple(color[:3])


def _lookup(theme, slot_id):
    """Return the theme's raw colour for one slot id, or None."""
    if slot_id.startswith("ansi_"):
        try:
            index = int(slot_id[5:])
        except ValueError:
            return None
        ansi = theme.get("ansi") or ()
        if 0 <= index < len(ansi):
            color = ansi[index]
            if color:
                return _as_color(color)
        return None
    color = theme.get(slot_id)
    if color:
        return _as_color(color)
    return None


def resolve_slot(theme, slot_id):
    """Resolve one slot id to an exact RGB tuple.

    Aliases are expanded, then ``SLOT_CHAINS`` is walked until the theme
    supplies a colour. Returns ``LAST_RESORT`` for malformed data.
    """
    slot_id = SLOT_ALIASES.get(slot_id, slot_id)
    for candidate in SLOT_CHAINS.get(slot_id, (slot_id,)):
        color = _lookup(theme, candidate)
        if color:
            return color
    return LAST_RESORT


def resolve(theme, role_map=None):
    """Resolve every role in ``role_map`` (default: all of ``ROLE_MAP``).

    Returns ``{role: (r, g, b)}`` for plain slots and ``(r, g, b, a)`` for the
    roles declared as ``(slot, alpha)``. Slots carrying RGBA (an ANSI colour
    with Quick Adjust alpha applied) keep their 4th component. No colour maths
    is applied: values are the theme's own.
    """
    resolved = {}
    for key, spec in (ROLE_MAP if role_map is None else role_map).items():
        if isinstance(spec, (tuple, list)):
            slot, alpha = spec
            color = resolve_slot(theme, slot)
            # A role's own design alpha multiplies the palette's Quick Adjust
            # alpha, so both survive: face_select @ 0.35 on a half-transparent
            # ANSI slot resolves to 0.175.
            base = color[3] if len(color) > 3 else 1.0
            resolved[key] = (*color[:3], base * float(alpha))
        else:
            resolved[key] = resolve_slot(theme, spec)
    for key, slot in NODE_SLOTS.items():
        resolved[key] = resolve_slot(theme, slot)
    return resolved


def resolve_collection_colors(theme):
    """Return the 8 Collection Color tag colours as exact palette colours."""
    return [resolve_slot(theme, slot) for slot in COLLECTION_SLOTS]


def table_text():
    """Return the full role -> slot table as plain text (debugging/finetune)."""
    lines = ["%-28s %s" % (role, spec if not isinstance(spec, (tuple, list))
                           else "%s alpha=%g" % spec)
             for role, spec in ROLE_MAP.items()]
    lines += ["", "%-28s %s" % ("collection_colors", ", ".join(COLLECTION_SLOTS))]
    lines += ["%-28s %s" % ("node_*", ", ".join(NODE_SLOTS.values()))]
    return "\n".join(lines)

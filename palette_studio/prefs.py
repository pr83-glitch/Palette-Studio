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
Add-on preferences for the Palette.
"""

import bpy
import json
from bpy.props import (
    StringProperty,
    EnumProperty,
    BoolProperty,
    IntProperty,
    FloatProperty,
    FloatVectorProperty,
)

# Static enum items for the accent dropdowns. Blender rejects
# EnumProperty(default=...) when items is a callback function, so this is a
# plain list built once at import time.
from .palette_slots import ENUM_ITEMS as _ACCENT_ITEMS
from .palette_slots import FINETUNE_COLOR_ITEMS as _FINETUNE_COLOR_ITEMS
from .palette_slots import FINETUNE_COLOR_ITEMS_DEFAULTED as _FINETUNE_COLOR_ITEMS_DEFAULTED


# X/Y/Z axis defaults: ANSI 1 red, ANSI 2 green, ANSI 4 blue.
_AXIS_SLOT_DEFAULTS = (
    ("finetune_axis_x", "ansi_1"),
    ("finetune_axis_y", "ansi_2"),
    ("finetune_axis_z", "ansi_4"),
)

# Set while the axis dropdowns are written back to their defaults, so the
# property update callbacks do not re-enter the live-apply path.
_suppress_finetune_color_update = False


def _redraw_after_apply():
    """Tag every area for redraw so a live Finetune change shows immediately."""
    try:
        for win in bpy.context.window_manager.windows:
            for area in win.screen.areas:
                area.tag_redraw()
    except Exception:
        pass


def _reapply_loaded_palette(context, reset_axes=False):
    """Re-apply the palette loaded in the Palette Editor.

    Returns True when a palette was applied, False otherwise (nothing loaded,
    or the apply failed).

    Used by the live Finetune dropdowns. It never resets the axis colours:
    that only happens when a *different* palette is applied (see
    reset_axis_colors).
    """
    try:
        wm = context.window_manager
        if not wm.palette_studio_palette_loaded or not len(wm.palette_studio_palette):
            return False
    except Exception:
        return False

    try:
        from . import _build_theme_from_palette, blender_theme_map, apply
        prefs = context.preferences.addons[__package__].preferences
        palette_theme = _build_theme_from_palette(wm, prefs, reset_axes)
        palette = blender_theme_map.build_palette(palette_theme)
        apply.apply_theme_to_blender(palette)
    except Exception:
        return False

    _redraw_after_apply()
    return True


def reset_axis_colors(prefs=None):
    """Write the X/Y/Z axis dropdowns back to their ANSI defaults.

    Called on every palette/theme apply: an axis pick is a per-palette tweak,
    so switching palettes clears it. Playhead Color deliberately persists.
    """
    global _suppress_finetune_color_update
    if prefs is None:
        try:
            prefs = bpy.context.preferences.addons[__package__].preferences
        except Exception:
            return
    _suppress_finetune_color_update = True
    try:
        for prop, slot_id in _AXIS_SLOT_DEFAULTS:
            if getattr(prefs, prop, None) != slot_id:
                setattr(prefs, prop, slot_id)
    except Exception:
        pass
    finally:
        _suppress_finetune_color_update = False


def _on_accent_update(self, context):
    """Live-apply the accent role choices to the currently loaded palette.

    Only re-applies when a palette is loaded in the Palette Editor (that is
    where the dropdowns live). Never triggers on theme browsing.
    """
    _reapply_loaded_palette(context)


def _on_finetune_color_update(self, context):
    """Live-apply the Playhead / Axis colour picks to the loaded palette."""
    if _suppress_finetune_color_update:
        return
    _reapply_loaded_palette(context)


def _on_finetune_update(self, context):
    """Live-apply 3D viewport geometry sizes when Finetune values change."""
    try:
        prefs = context.preferences.addons[__package__].preferences
        v3d = context.preferences.themes[0].view_3d
        v3d.edge_width = prefs.finetune_edge_width
        v3d.vertex_size = prefs.finetune_vertex_size
        v3d.facedot_size = prefs.finetune_facedot_size
        v3d.outline_width = prefs.finetune_outline_width
    except Exception:
        return
    try:
        for win in bpy.context.window_manager.windows:
            for area in win.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
    except Exception:
        pass


# Guards programmatic writes to the Dopesheet text color properties so they
# don't re-trigger the update callback (which would recurse).
_suppress_dope_update = False

# Guards programmatic writes to the Grid color property.
_suppress_grid_update = False


def _on_roundness_update(self, context):
    """Live-apply the Roundness value to every theme roundness setting."""
    try:
        from .apply import apply_roundness
        theme = bpy.context.preferences.themes[0]
        apply_roundness(theme, self.finetune_roundness)
    except Exception:
        return
    try:
        for win in bpy.context.window_manager.windows:
            for area in win.screen.areas:
                area.tag_redraw()
    except Exception:
        pass


def _effective_dope_colors(prefs):
    """Return (text, selected) channel colors: custom override or theme default."""
    text = (prefs.finetune_dope_text
            if prefs.finetune_dope_text_custom else prefs.finetune_dope_text_def)
    sel = (prefs.finetune_dope_text_sel
           if prefs.finetune_dope_text_sel_custom else prefs.finetune_dope_text_sel_def)
    return tuple(text), tuple(sel)


def _on_dope_text_update(self, context):
    """Live-apply Dopesheet Channels text colors; keep swatches in sync."""
    global _suppress_dope_update
    if _suppress_dope_update:
        return
    try:
        prefs = context.preferences.addons[__package__].preferences
    except Exception:
        return

    text, sel = _effective_dope_colors(prefs)

    # Show the effective color in the swatch when not overridden.
    _suppress_dope_update = True
    try:
        if not prefs.finetune_dope_text_custom:
            prefs.finetune_dope_text = text
        if not prefs.finetune_dope_text_sel_custom:
            prefs.finetune_dope_text_sel = sel
    except Exception:
        pass
    finally:
        _suppress_dope_update = False

    try:
        ch = context.preferences.themes[0].regions.channels
        ch.text = text
        ch.text_selected = sel
    except Exception:
        pass

    try:
        for win in bpy.context.window_manager.windows:
            for area in win.screen.areas:
                area.tag_redraw()
    except Exception:
        pass


def seed_dope_defaults(text_rgb, selected_rgb):
    """Store the current palette's default channel text colors.

    Called by apply.py on every theme apply. Updates the hidden default colors,
    and refreshes the visible swatches unless the user has a custom override.
    """
    global _suppress_dope_update
    try:
        prefs = bpy.context.preferences.addons[__package__].preferences
    except Exception:
        return
    _suppress_dope_update = True
    try:
        prefs.finetune_dope_text_def = tuple(text_rgb[:3])
        prefs.finetune_dope_text_sel_def = tuple(selected_rgb[:3])
        if not prefs.finetune_dope_text_custom:
            prefs.finetune_dope_text = tuple(text_rgb[:3])
        if not prefs.finetune_dope_text_sel_custom:
            prefs.finetune_dope_text_sel = tuple(selected_rgb[:3])
    except Exception:
        pass
    finally:
        _suppress_dope_update = False


def _effective_grid_color(prefs):
    """Return grid color: custom override or theme default."""
    return tuple(prefs.finetune_grid
                 if prefs.finetune_grid_custom else prefs.finetune_grid_def)


def _on_grid_color_update(self, context):
    """Live-apply 3D viewport grid color; keep swatch in sync."""
    global _suppress_grid_update
    if _suppress_grid_update:
        return
    try:
        prefs = context.preferences.addons[__package__].preferences
    except Exception:
        return

    grid = _effective_grid_color(prefs)

    # Show the effective color in the swatch when not overridden.
    _suppress_grid_update = True
    try:
        if not prefs.finetune_grid_custom:
            prefs.finetune_grid = grid
    except Exception:
        pass
    finally:
        _suppress_grid_update = False

    # Apply RGBA directly — property is size=4.
    rgba = tuple(grid[:4])
    try:
        context.preferences.themes[0].view_3d.grid = rgba
    except Exception:
        try:
            context.preferences.themes[0].view_3d.grid = rgba[:3]
        except Exception:
            pass

    try:
        for win in bpy.context.window_manager.windows:
            for area in win.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
    except Exception:
        pass


def seed_grid_defaults(grid_rgba):
    """Store the current palette's default grid color (RGBA).

    Called by apply.py on every theme apply. Updates the hidden default color,
    and refreshes the visible swatch unless the user has a custom override.
    """
    global _suppress_grid_update
    try:
        prefs = bpy.context.preferences.addons[__package__].preferences
    except Exception:
        return
    _suppress_grid_update = True
    try:
        prefs.finetune_grid_def = tuple(grid_rgba[:4])
        if not prefs.finetune_grid_custom:
            prefs.finetune_grid = tuple(grid_rgba[:4])
    except Exception:
        pass
    finally:
        _suppress_grid_update = False


# Guards programmatic writes to the global text override properties.
_suppress_global_text_update = False


def _effective_global_text(prefs):
    """Return the text colour to force: the pick, or the palette default."""
    return tuple(prefs.finetune_text
                 if prefs.finetune_text_custom else prefs.finetune_text_def)


def _effective_global_text_sel(prefs):
    """Return the selected-text colour: the pick, or the palette default."""
    return tuple(prefs.finetune_text_sel
                 if prefs.finetune_text_sel_custom else prefs.finetune_text_sel_def)


def seed_global_text_defaults(text_rgb, selected_rgb):
    """Store the current palette's default text colours.

    Called by apply.py on every theme apply. Only refreshes the snapshot while
    the matching Custom toggle is off, so turning an override off falls back to
    the palette's own colours.
    """
    global _suppress_global_text_update
    try:
        prefs = bpy.context.preferences.addons[__package__].preferences
    except Exception:
        return
    _suppress_global_text_update = True
    try:
        prefs.finetune_text_def = tuple(text_rgb[:3])
        prefs.finetune_text_sel_def = tuple(selected_rgb[:3])
        if not prefs.finetune_text_custom:
            prefs.finetune_text = tuple(text_rgb[:3])
        if not prefs.finetune_text_sel_custom:
            prefs.finetune_text_sel = tuple(selected_rgb[:3])
    except Exception:
        pass
    finally:
        _suppress_global_text_update = False


def _on_global_text_update(self, context):
    """Live-apply the global Text / Text Selected overrides.

    With a palette loaded the whole palette is re-applied, so turning Custom
    off restores the palette-derived colours instead of leaving the pick stuck.
    Without a loaded palette the effective colours are written directly.
    """
    global _suppress_global_text_update
    if _suppress_global_text_update:
        return
    try:
        prefs = context.preferences.addons[__package__].preferences
    except Exception:
        return

    if _reapply_loaded_palette(context):
        return

    text = _effective_global_text(prefs)
    sel = _effective_global_text_sel(prefs)
    _suppress_global_text_update = True
    try:
        if not prefs.finetune_text_custom:
            prefs.finetune_text = text
        if not prefs.finetune_text_sel_custom:
            prefs.finetune_text_sel = sel
    except Exception:
        pass
    finally:
        _suppress_global_text_update = False
    try:
        from .apply import override_theme_text
        override_theme_text(context.preferences.themes[0], text=text, selected=sel)
    except Exception:
        pass
    _redraw_after_apply()


# Guards programmatic writes to the text-style properties.
_suppress_text_style_update = False

# Text styles managed by Finetune > Text Style. These live on
# `preferences.ui_styles` (Themes > User Interface > Text Style draws them),
# NOT on the Theme, so they are only forced when the Custom toggle is on.
_TEXT_STYLE_KEYS = ("panel_title", "widget", "tooltip")
# Text shadow is applied to these only; panel title keeps its own value
# (Blender's stock panel-title shadow is 3 / blur, widget and tooltip are 1).
_TEXT_SHADOW_KEYS = ("widget", "tooltip")


_SORT_ITEMS = [
    ('FAVOURITES', "Favourites First", "Show marked favourite palettes at the top"),
    ('POPULAR', "Popular First", "Show well-known themes at the top"),
    ('AZ', "A → Z", "Sort alphabetically"),
    ('ZA', "Z → A", "Sort reverse alphabetically"),
]

_FILTER_ITEMS = [
    ('ALL', "Show All", "Show every palette"),
    ('DARK', "Dark Themes", "Show only palettes with a dark background"),
    ('LIGHT', "Light Themes", "Show only palettes with a light background"),
]


def get_favorite_paths():
    """Return the persisted set of favourite palette paths."""
    try:
        prefs = bpy.context.preferences.addons[__package__].preferences
        values = json.loads(prefs.favorite_theme_paths or "[]")
        return {str(path) for path in values if path}
    except Exception:
        return set()


def _on_sort_update(self, context):
    """Re-sort the visible theme list when the persisted sort mode changes."""
    try:
        from . import _on_theme_sort_update
    except Exception:
        return
    _on_theme_sort_update(self, context)


def _on_filter_update(self, context):
    """Re-filter the visible theme list when the dark/light filter changes."""
    try:
        from . import _on_theme_sort_update
    except Exception:
        return
    _on_theme_sort_update(self, context)


def _on_source_update(self, context):
    """Re-filter the visible theme list when a theme source is toggled.

    The index is not rewritten here: toggling a source only hides or shows
    its already-cached themes. A not-yet-downloaded source stays empty until
    the user runs Load Themes.
    """
    try:
        from . import _on_theme_search_update
    except Exception:
        return
    _on_theme_search_update(self, context)


def _ui_text_styles():
    """Return [(key, ThemeFontStyle)] for the styles we manage."""
    try:
        styles = bpy.context.preferences.ui_styles
    except Exception:
        return []
    out = []
    for style in styles:
        for key in _TEXT_STYLE_KEYS:
            font_style = getattr(style, key, None)
            if font_style is not None:
                out.append((key, font_style))
    return out


def seed_text_style_defaults():
    """Snapshot Blender's own text-style values while we are not overriding.

    Called by apply.py on every theme apply. A default is only recorded while
    the matching Custom toggle is off, so the snapshot stays the user's
    original value and turning Custom off can restore it.
    """
    global _suppress_text_style_update
    try:
        prefs = bpy.context.preferences.addons[__package__].preferences
    except Exception:
        return

    font_custom = bool(getattr(prefs, "finetune_font_custom", False))
    shadow_custom = bool(getattr(prefs, "finetune_shadow_custom", False))
    if font_custom and shadow_custom:
        return

    representative = dict(_ui_text_styles()).get("widget")
    if representative is None:
        return

    _suppress_text_style_update = True
    try:
        if not font_custom:
            points = float(representative.points)
            prefs.finetune_font_size_def = points
            prefs.finetune_font_size = points
        if not shadow_custom:
            shadow = int(representative.shadow)
            prefs.finetune_text_shadow_def = shadow
            prefs.finetune_text_shadow = shadow
    except Exception:
        pass
    finally:
        _suppress_text_style_update = False


def apply_text_style(prefs=None):
    """Write the Finetune text-style values into preferences.ui_styles.

    Custom off -> the snapshot value is written back (so switching Custom off
    restores what the user had). Custom on -> the chosen value is enforced.
    Font size covers Panel Title + Widget + Tooltip; shadow only Widget and
    Tooltip.
    """
    if prefs is None:
        try:
            prefs = bpy.context.preferences.addons[__package__].preferences
        except Exception:
            return

    styles = _ui_text_styles()
    if not styles:
        return

    try:
        if prefs.finetune_font_custom:
            points = float(prefs.finetune_font_size)
        else:
            points = float(prefs.finetune_font_size_def)
        if prefs.finetune_shadow_custom:
            shadow = int(prefs.finetune_text_shadow)
        else:
            shadow = int(prefs.finetune_text_shadow_def)
    except Exception:
        return

    for key, font_style in styles:
        try:
            font_style.points = points
        except Exception:
            pass
        if key in _TEXT_SHADOW_KEYS:
            try:
                font_style.shadow = shadow
            except Exception:
                pass


def _on_text_style_update(self, context):
    """Live-apply the text-style controls; keep the fields in sync."""
    global _suppress_text_style_update
    if _suppress_text_style_update:
        return
    try:
        prefs = context.preferences.addons[__package__].preferences
    except Exception:
        return

    # With Custom off, show (and restore) Blender's own value.
    _suppress_text_style_update = True
    try:
        if not prefs.finetune_font_custom:
            prefs.finetune_font_size = prefs.finetune_font_size_def
        if not prefs.finetune_shadow_custom:
            prefs.finetune_text_shadow = prefs.finetune_text_shadow_def
    except Exception:
        pass
    finally:
        _suppress_text_style_update = False

    apply_text_style(prefs)

    try:
        for win in bpy.context.window_manager.windows:
            for area in win.screen.areas:
                area.tag_redraw()
    except Exception:
        pass


class PaletteStudioPrefs(bpy.types.AddonPreferences):
    bl_idname = __package__

    # --- Foldable section states ---
    show_browser: BoolProperty(
        name="Theme Browser",
        default=True,
    )
    show_palette_editor: BoolProperty(
        name="Palette Editor",
        default=False,
    )
    show_finetune: BoolProperty(
        name="Finetune",
        default=False,
    )
    show_settings: BoolProperty(
        name="Settings",
        default=False,
    )
    show_updates: BoolProperty(
        name="Updates",
        default=True,
    )

    # --- Source config ---
    source_mode: EnumProperty(
        name="Source Mode",
        description="Where to load themes from",
        items=[
            ('REMOTE', "Remote Repositories", "Download from public Git repositories"),
            ('LOCAL', "Local Folder", "Load from a local folder of theme files"),
        ],
        default='REMOTE',
    )

    # UI / get_enabled_sources() order: NvChad, iTerm2, base24.
    source_nvchad: BoolProperty(
        name="NvChad base46",
        description="Show ~105 themes from the NvChad base46 repository "
                    "(downloaded by Load Themes)",
        default=True,
        update=_on_source_update,
    )
    source_iterm: BoolProperty(
        name="iTerm2-Color-Schemes",
        description="Show ~250 schemes from the iTerm2-Color-Schemes repository "
                    "(downloaded by Load Themes)",
        default=False,
        update=_on_source_update,
    )
    source_base24: BoolProperty(
        name="base24",
        description="Show ~230 schemes from the tinted-theming base24 repository "
                    "(downloaded by Load Themes)",
        default=False,
        update=_on_source_update,
    )

    local_folder: StringProperty(
        name="Local Folder",
        description="Path to a folder containing theme files (.itermcolors, .yml, .yaml, .conf, .lua)",
        default="",
        subtype='DIR_PATH',
    )

    live_preview: BoolProperty(
        name="Live Preview",
        description="Preview themes instantly when clicking in the list (no disk writes)",
        default=True,
    )

    # --- Accent roles (which palette slot drives each accent) ---
    accent_primary: EnumProperty(
        name="Primary",
        description="Palette slot used as the primary (decorative) accent",
        items=_ACCENT_ITEMS,
        default='ansi_3',
        update=_on_accent_update,
    )
    accent_secondary: EnumProperty(
        name="Secondary",
        description="Palette slot used as the secondary accent (tabs, icons, strips, keys)",
        items=_ACCENT_ITEMS,
        default='ansi_6',
        update=_on_accent_update,
    )
    accent_tertiary: EnumProperty(
        name="Tertiary",
        description="Palette slot used as the tertiary accent (gizmos, handles, normals, channel groups)",
        items=_ACCENT_ITEMS,
        default='selection',
        update=_on_accent_update,
    )

    # --- Finetune: palette colours for the playhead and the gizmo axes ---
    finetune_playhead: EnumProperty(
        name="Playhead Color",
        description=(
            "Palette colour for the playhead (Themes > Animation > Playhead; on "
            "Blender 4.5 the per-editor current-frame colour)"
        ),
        items=_FINETUNE_COLOR_ITEMS,
        default='ansi_2',
        update=_on_finetune_color_update,
    )
    finetune_keyframe_selected: EnumProperty(
        name="Selected Keyframes",
        description=(
            "Palette colour for selected keyframes; defaults to the Primary "
            "accent and follows the selected palette slot"
        ),
        items=_FINETUNE_COLOR_ITEMS,
        default='accent_primary',
        update=_on_finetune_color_update,
    )
    finetune_axis_x: EnumProperty(
        name="X Axis",
        description="Palette colour for the X axis (Themes > User Interface > Axis & Gizmo Colors)",
        items=_FINETUNE_COLOR_ITEMS,
        default='ansi_1',
        update=_on_finetune_color_update,
    )
    finetune_axis_y: EnumProperty(
        name="Y Axis",
        description="Palette colour for the Y axis (Themes > User Interface > Axis & Gizmo Colors)",
        items=_FINETUNE_COLOR_ITEMS,
        default='ansi_2',
        update=_on_finetune_color_update,
    )
    finetune_axis_z: EnumProperty(
        name="Z Axis",
        description="Palette colour for the Z axis (Themes > User Interface > Axis & Gizmo Colors)",
        items=_FINETUNE_COLOR_ITEMS,
        default='ansi_4',
        update=_on_finetune_color_update,
    )
    finetune_object_selected: EnumProperty(
        name="Selected Object",
        description=(
            "Palette colour for selected objects (Themes > 3D Viewport > "
            "Object Selected). Theme Default keeps the derived colour"
        ),
        items=_FINETUNE_COLOR_ITEMS_DEFAULTED,
        default='default',
        update=_on_finetune_color_update,
    )
    finetune_active_object: EnumProperty(
        name="Active Object",
        description=(
            "Palette colour for the active object (Themes > 3D Viewport > "
            "Active Object). Theme Default keeps the derived colour"
        ),
        items=_FINETUNE_COLOR_ITEMS_DEFAULTED,
        default='default',
        update=_on_finetune_color_update,
    )

    # Internal marker: set by Load Themes, cleared by Unload. Lets the theme
    # list be restored after a restart without re-downloading. Not drawn.
    themes_loaded: BoolProperty(
        name="Themes Loaded",
        default=False,
        options={'HIDDEN'},
    )
    favorite_theme_paths: StringProperty(
        name="Favourite Palettes",
        description="JSON-encoded paths of palettes marked as favourites",
        default="[]",
        options={'HIDDEN'},
    )
    # One-shot marker: True after settings were copied from the legacy
    # "Palette Custom" add-on, so migration never clobbers later edits.
    migrated_from_legacy: BoolProperty(
        name="Migrated From Palette Custom",
        default=False,
        options={'HIDDEN'},
    )

    # --- Theme list sort (persisted here, not on WindowManager) ---
    # A WindowManager property is session-only and silently reset to
    # "Popular First" on every restart, so the sort lives in the add-on
    # preferences instead. Items must stay a static list: Blender rejects
    # EnumProperty default= when items is a callback.
    theme_sort: EnumProperty(
        name="Sort",
        description="Sort order for the theme list; Favourites First puts marked palettes on top",
        items=_SORT_ITEMS,
        default='POPULAR',
        update=_on_sort_update,
    )

    # --- Theme list filter (dark/light) ---
    theme_filter: EnumProperty(
        name="Filter",
        description="Show all palettes, or only dark/light ones",
        items=_FILTER_ITEMS,
        default='ALL',
        update=_on_filter_update,
    )

    # --- Finetune: 3D viewport geometry sizes ---
    finetune_edge_width: IntProperty(
        name="Edge Width",
        description="Width of edges in the 3D viewport",
        default=1, min=1, max=32,
        update=_on_finetune_update,
    )
    finetune_vertex_size: IntProperty(
        name="Vertex Size",
        description="Size of vertices in the 3D viewport",
        default=3, min=1, max=32,
        update=_on_finetune_update,
    )
    finetune_facedot_size: IntProperty(
        name="Face Dot Size",
        description="Size of face dots in the 3D viewport",
        default=3, min=1, max=10,
        update=_on_finetune_update,
    )
    finetune_outline_width: IntProperty(
        name="Outline Width",
        description="Width of the selection outline in the 3D viewport",
        default=1, min=1, max=5,
        update=_on_finetune_update,
    )
    finetune_roundness: FloatProperty(
        name="Border Radius",
        description=("Corner roundness for panels and every widget color set "
                     "(Themes > User Interface > Styles / Widgets)"),
        default=0.4, min=0.0, max=1.0,
        subtype='FACTOR',
        update=_on_roundness_update,
    )

    # --- Finetune: Text Style (Themes > User Interface > Text Style) ---
    # Stored in preferences.ui_styles, not in the Theme, hence the Custom
    # toggles: off = follow Blender's own value, on = enforce ours.
    finetune_font_custom: BoolProperty(
        name="Custom Font Size",
        description="Override the font size for Panel Title, Widget and Tooltip text",
        default=False,
        update=_on_text_style_update,
    )
    finetune_font_size: FloatProperty(
        name="Font Size",
        description="Font size for Panel Title, Widget and Tooltip text",
        default=11.0, min=6.0, max=32.0,
        update=_on_text_style_update,
    )
    finetune_font_size_def: FloatProperty(
        name="Default Font Size",
        default=11.0, min=6.0, max=32.0,
    )
    finetune_shadow_custom: BoolProperty(
        name="Custom Text Shadow",
        description="Override the text shadow size for Widget and Tooltip text",
        default=False,
        update=_on_text_style_update,
    )
    finetune_text_shadow: IntProperty(
        name="Text Shadow",
        description="Text shadow size for Widget and Tooltip text",
        default=1, min=0, max=6,
        update=_on_text_style_update,
    )
    finetune_text_shadow_def: IntProperty(
        name="Default Text Shadow",
        default=1, min=0, max=6,
    )

    # --- Finetune: Dopesheet/Timeline Channels text colors ---
    finetune_dope_text_custom: BoolProperty(
        name="Custom Channel Text",
        description="Override the theme's Channels region text color",
        default=False,
        update=_on_dope_text_update,
    )
    finetune_dope_text: FloatVectorProperty(
        name="Channel Text",
        description="Text color for the Dopesheet/Timeline Channels region",
        subtype='COLOR', size=3, min=0.0, max=1.0,
        default=(0.8, 0.8, 0.8),
        update=_on_dope_text_update,
    )
    finetune_dope_text_def: FloatVectorProperty(
        name="Default Channel Text",
        subtype='COLOR', size=3, min=0.0, max=1.0,
        default=(0.8, 0.8, 0.8),
    )
    finetune_dope_text_sel_custom: BoolProperty(
        name="Custom Selected Channel",
        description="Override the theme's Channels selected-text color",
        default=False,
        update=_on_dope_text_update,
    )
    finetune_dope_text_sel: FloatVectorProperty(
        name="Selected Channel Text",
        description="Selected-text color for the Dopesheet/Timeline Channels region",
        subtype='COLOR', size=3, min=0.0, max=1.0,
        default=(1.0, 1.0, 1.0),
        update=_on_dope_text_update,
    )
    finetune_dope_text_sel_def: FloatVectorProperty(
        name="Default Selected Channel Text",
        subtype='COLOR', size=3, min=0.0, max=1.0,
        default=(1.0, 1.0, 1.0),
    )

    # --- Finetune: 3D Viewport Grid color ---
    finetune_grid_custom: BoolProperty(
        name="Custom Grid Color",
        description="Override the theme's 3D Viewport grid color",
        default=False,
        update=_on_grid_color_update,
    )
    finetune_grid: FloatVectorProperty(
        name="Grid Color",
        description="Grid color for the 3D Viewport (Themes > 3D Viewport > Grid)",
        subtype='COLOR', size=4, min=0.0, max=1.0,
        default=(0.4, 0.4, 0.4, 1.0),
        update=_on_grid_color_update,
    )
    finetune_grid_def: FloatVectorProperty(
        name="Default Grid Color",
        subtype='COLOR', size=4, min=0.0, max=1.0,
        default=(0.4, 0.4, 0.4, 1.0),
    )

    # --- Finetune: global text colour overrides ---
    # These sweep every plain text / text-selected colour in the theme.
    # Turning Custom off re-applies the loaded palette, which restores the
    # palette-derived colours (see _on_global_text_update).
    finetune_text_custom: BoolProperty(
        name="Custom Text Color",
        description="Override every text colour in the theme (not selected text)",
        default=False,
        update=_on_global_text_update,
    )
    finetune_text: FloatVectorProperty(
        name="Text Color",
        description="Colour applied to every text label while the override is on",
        subtype='COLOR', size=3, min=0.0, max=1.0,
        default=(0.8, 0.8, 0.8),
        update=_on_global_text_update,
    )
    finetune_text_def: FloatVectorProperty(
        name="Default Text Color",
        subtype='COLOR', size=3, min=0.0, max=1.0,
        default=(0.8, 0.8, 0.8),
    )
    finetune_text_sel_custom: BoolProperty(
        name="Custom Text Selected Color",
        description="Override every selected-text colour in the theme",
        default=False,
        update=_on_global_text_update,
    )
    finetune_text_sel: FloatVectorProperty(
        name="Text Selected Color",
        description="Colour applied to every selected text while the override is on",
        subtype='COLOR', size=3, min=0.0, max=1.0,
        default=(1.0, 1.0, 1.0),
        update=_on_global_text_update,
    )
    finetune_text_sel_def: FloatVectorProperty(
        name="Default Text Selected Color",
        subtype='COLOR', size=3, min=0.0, max=1.0,
        default=(1.0, 1.0, 1.0),
    )

    # --- Add-on updates ---
    update_source_mode: EnumProperty(
        name="Update Source",
        description="Where to check for a newer Palette Studio release",
        items=[
            ('LOCAL', "Local ZIP Folder", "Check a folder of built .zip release packages"),
            ('GITHUB', "GitHub Releases", "Check the published GitHub repository (not enabled yet)"),
        ],
        default='LOCAL',
    )
    update_folder: StringProperty(
        name="Update Folder",
        description="Folder containing Palette Studio .zip release packages to update from",
        default="",
        subtype='DIR_PATH',
    )
    github_repo: StringProperty(
        name="GitHub Repository",
        description="Repository in owner/name form, used once the add-on is published",
        default="",
    )

    def get_enabled_sources(self):
        """Return list of enabled source keys."""
        sources = []
        if self.source_nvchad:
            sources.append("nvchad")
        if self.source_iterm:
            sources.append("iterm")
        if self.source_base24:
            sources.append("base24")
        return sources

    # ------------------------------------------------------------------
    # Section header helper
    # ------------------------------------------------------------------
    def _draw_section_header(self, layout, prop_name, label, icon):
        """Draw a foldable section header. Returns the box to draw into,
        or None if the section is collapsed."""
        is_open = getattr(self, prop_name)
        box = layout.box()
        row = box.row()
        row.alignment = 'LEFT'
        row.prop(
            self, prop_name,
            icon='TRIA_DOWN' if is_open else 'TRIA_RIGHT',
            text=label,
            emboss=False,
            icon_only=False,
        )
        # Put the section icon on the right side of the header
        sub = row.row()
        sub.alignment = 'RIGHT'
        sub.label(icon=icon)
        if is_open:
            return box
        return None

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------
    def draw(self, context):
        draw_sections(self.layout, self, context)


def draw_sections(layout, prefs, context):
    """Draw the add-on sections into any layout (preferences or N-panel)."""
    from . import _ensure_theme_list

    wm = context.window_manager

    # Restore a previously loaded list once per window (no network).
    _ensure_theme_list(context)

    # ==============================================================
    # 1. THEME BROWSER
    # ==============================================================
    box = prefs._draw_section_header(layout, "show_browser", "Palette Browser", 'COLOR')

    if box is not None:
        loaded = prefs.themes_loaded or bool(wm.palette_studio_themes)

        # Empty state — guide the user
        if not loaded:
            col = box.column(align=True)
            col.scale_y = 1.0
            col.label(text="No themes loaded yet.", icon='INFO')
            col.label(text="Press the button below to get started.")
            col.separator()
            # First run (or after Unload) — this is the only path that downloads.
            box.operator("palette_studio.refresh_repo", text="Load Themes", icon='IMPORT')
        else:
            # Loaded state — unload clears the list and deletes the downloads.
            box.operator("palette_studio.unload_themes", text="Unload", icon='TRASH')

        # Only show browser controls when themes are loaded
        if loaded:
            # Search + Sort on one row
            row = box.row(align=True)
            row.prop(wm, "palette_studio_theme_search", text="", icon='VIEWZOOM')
            row.prop(prefs, "theme_sort", text="")

            # Dark/Light filter between the controls and the list
            box.prop(prefs, "theme_filter", text="")

            # Theme list
            box.template_list(
                "PALETTE_STUDIO_UL_theme_list", "",
                wm, "palette_studio_themes",
                wm, "palette_studio_theme_active",
                rows=6,
            )

            if not wm.palette_studio_themes:
                box.label(text="No palettes match the current filter/search.", icon='INFO')
            else:
                selected = (
                    wm.palette_studio_themes[wm.palette_studio_theme_active]
                    if 0 <= wm.palette_studio_theme_active < len(wm.palette_studio_themes)
                    else None
                )
                row = box.row(align=True)
                row.operator(
                    "palette_studio.toggle_favourite",
                    text=("Unmark Favourite" if selected and selected.favorite
                          else "Mark Favourite"),
                    icon='SOLO_ON' if selected and selected.favorite else 'SOLO_OFF',
                )

                box.label(text=f"{len(wm.palette_studio_themes)} themes available")

                # Primary actions
                row = box.row(align=True)
                row.scale_y = 1.3
                row.operator("palette_studio.apply_theme", text="Apply", icon='CHECKMARK')
                row.operator("preferences.reset_default_theme", text="Reset", icon='LOOP_BACK')

                # Save reminder
                box.separator()
                note = box.row()
                note.alignment = 'CENTER'
                note.label(text="Save your preferences to keep the theme after restart.", icon='FILE_TICK')

    # ==============================================================
    # 1.1 FINETUNE
    # ==============================================================
    box = prefs._draw_section_header(layout, "show_finetune", "Finetune", 'VIEW3D')

    if box is not None:
        # Accent roles + animation colours — changing these applies live
        abox = box.box()
        abox.prop(prefs, "accent_primary", text="Primary")
        abox.prop(prefs, "accent_secondary", text="Secondary")
        abox.prop(prefs, "accent_tertiary", text="Tertiary")
        abox.separator()
        abox.prop(prefs, "finetune_playhead", text="Playhead Color")
        abox.prop(prefs, "finetune_keyframe_selected", text="Selected Keyframes")

        # 3D Viewport: axes, geometry sizes, grid colour
        box.separator()
        vbox = box.box()
        vbox.prop(prefs, "finetune_axis_x", text="X Axis")
        vbox.prop(prefs, "finetune_axis_y", text="Y Axis")
        vbox.prop(prefs, "finetune_axis_z", text="Z Axis")
        vbox.prop(prefs, "finetune_object_selected", text="Selected Object")
        vbox.prop(prefs, "finetune_active_object", text="Active Object")
        vbox.separator()
        vbox.prop(prefs, "finetune_edge_width")
        vbox.prop(prefs, "finetune_vertex_size")
        vbox.prop(prefs, "finetune_facedot_size")
        vbox.prop(prefs, "finetune_outline_width")
        vbox.separator()
        row = vbox.row(align=True)
        row.prop(prefs, "finetune_grid_custom", toggle=True, text="Grid Color")
        sub = row.row()
        sub.enabled = prefs.finetune_grid_custom
        sub.prop(prefs, "finetune_grid", text="")

        box.separator()
        rbox = box.box()
        rbox.prop(prefs, "finetune_roundness", slider=True)

        # Text: font size, global overrides, channel colours, shadow
        box.separator()
        tsbox = box.box()
        row = tsbox.row(align=True)
        row.prop(prefs, "finetune_font_custom", toggle=True, text="Font Size")
        sub = row.row()
        sub.enabled = prefs.finetune_font_custom
        sub.prop(prefs, "finetune_font_size")
        row = tsbox.row(align=True)
        row.prop(prefs, "finetune_text_custom", toggle=True, text="Text Color")
        sub = row.row()
        sub.enabled = prefs.finetune_text_custom
        sub.prop(prefs, "finetune_text", text="")
        row = tsbox.row(align=True)
        row.prop(prefs, "finetune_text_sel_custom", toggle=True, text="Text Selected")
        sub = row.row()
        sub.enabled = prefs.finetune_text_sel_custom
        sub.prop(prefs, "finetune_text_sel", text="")
        row = tsbox.row(align=True)
        row.prop(prefs, "finetune_dope_text_custom", toggle=True, text="Channel Text")
        sub = row.row()
        sub.enabled = prefs.finetune_dope_text_custom
        sub.prop(prefs, "finetune_dope_text", text="")
        row = tsbox.row(align=True)
        row.prop(prefs, "finetune_dope_text_sel_custom", toggle=True, text="Selected Channel")
        sub = row.row()
        sub.enabled = prefs.finetune_dope_text_sel_custom
        sub.prop(prefs, "finetune_dope_text_sel", text="")
        row = tsbox.row(align=True)
        row.prop(prefs, "finetune_shadow_custom", toggle=True, text="Text Shadow")
        sub = row.row()
        sub.enabled = prefs.finetune_shadow_custom
        sub.prop(prefs, "finetune_text_shadow")

    # ==============================================================
    # 1.2 PALETTE EDITOR
    # ==============================================================
    box = prefs._draw_section_header(layout, "show_palette_editor", "Palette Editor", 'BRUSHES_ALL')

    if box is not None:
        if wm.palette_studio_palette_loaded:
            box.label(text=f"Editing: {wm.palette_studio_palette_theme_name}")
            box.separator()

            for i, item in enumerate(wm.palette_studio_palette):
                row = box.row(align=True)
                row.label(text=item.label)
                row.prop(item, "color", text="")
                row.prop(item, "hex_value", text="")

            box.separator()

            # Swap
            sbox = box.box()
            sbox.label(text="Swap Colors", icon='UV_SYNC_SELECT')
            sbox.prop(wm, "palette_studio_palette_swap_a", text="Slot A")
            sbox.prop(wm, "palette_studio_palette_swap_b", text="Slot B")
            sbox.operator("palette_studio.swap_colors", text="Swap", icon='UV_SYNC_SELECT')

            box.separator()

            col = box.column(align=True)
            col.scale_y = 1.3
            col.operator("palette_studio.apply_custom", text="Apply Custom Palette", icon='CHECKMARK')

            box.operator("palette_studio.reset_palette", text="Reset to Original", icon='LOOP_BACK')
        else:
            box.label(text="Select a theme and load its palette to edit.")
            box.operator("palette_studio.load_palette", text="Edit Colors", icon='BRUSHES_ALL')

    # ==============================================================
    # 1.3 SETTINGS
    # ==============================================================
    box = prefs._draw_section_header(layout, "show_settings", "Settings", 'PREFERENCES')

    if box is not None:
        # Preview
        box.prop(prefs, "live_preview")

        # Theme sources
        box.separator()
        box.label(text="Theme Sources:", icon='WORLD')
        box.prop(prefs, "source_mode", text="")

        if prefs.source_mode == 'REMOTE':
            row = box.row(align=True)
            row.prop(prefs, "source_nvchad", toggle=True)
            row.prop(prefs, "source_iterm", toggle=True)
            row.prop(prefs, "source_base24", toggle=True)
        else:
            box.prop(prefs, "local_folder", text="")

        # Attribution (sources), kept inside Settings
        box.separator()
        attrib = box.row()
        attrib.alignment = 'CENTER'
        attrib.label(
            text="Themes sourced from NvChad, iTerm2 and base24 repositories."
                 " Themes are not made by NXSTYNATE"
        )

    # ==============================================================
    # 1.4 UPDATES
    # ==============================================================
    box = prefs._draw_section_header(layout, "show_updates", "Updates", 'FILE_REFRESH')

    if box is not None:
        try:
            from . import updater
            installed_version = updater.get_current_version()
        except Exception:
            installed_version = ""
        if installed_version:
            box.label(text=f"Palette Studio v{installed_version}", icon='INFO')

        box.prop(prefs, "update_source_mode", text="")

        if prefs.update_source_mode == 'GITHUB':
            box.prop(prefs, "github_repo", text="Repo")
            box.label(text="GitHub updates are not enabled yet.", icon='INFO')
        else:
            box.prop(prefs, "update_folder", text="")

        row = box.row()
        row.scale_y = 1.3
        row.operator("palette_studio.check_updates", text="Check for Updates", icon='FILE_REFRESH')

    # ==============================================================
    # SAVE CUSTOM THEME (under Settings)
    # ==============================================================
    layout.separator()
    save_row = layout.row()
    save_row.scale_y = 1.3
    save_row.enabled = wm.palette_studio_palette_loaded
    save_row.operator("palette_studio.save_theme", text="Save as New Theme", icon='FILE_TICK')


def register():
    from . import _register_class
    _register_class(PaletteStudioPrefs)


def unregister():
    try:
        bpy.utils.unregister_class(PaletteStudioPrefs)
    except Exception:
        pass

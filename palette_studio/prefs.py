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
import traceback
from contextlib import contextmanager
from functools import wraps
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
from . import color_math as cm


_update_suspensions = 0


def updates_suspended():
    return _update_suspensions > 0


@contextmanager
def suspend_updates():
    """Suppress live callbacks during registration, migration and restoration."""
    global _update_suspensions
    _update_suspensions += 1
    try:
        yield
    finally:
        _update_suspensions -= 1


def _guard_updates(callback):
    @wraps(callback)
    def guarded(self, context):
        if not updates_suspended():
            return callback(self, context)
    return guarded


# All Finetune colour pickers are `subtype='COLOR'` properties, which Blender
# holds in LINEAR light, while the palette and Blender's theme colour fields
# are sRGB. These helpers are the only conversion boundary: seed with
# `srgb_to_linear`, write to Blender with `linear_to_srgb`.
def _linear_from_srgb_rgba(rgba):
    """sRGB RGBA (palette/apply input) -> linear RGB + untouched alpha."""
    return (*cm.srgb_to_linear(rgba), *tuple(rgba[3:]))


def _srgb_from_linear_rgba(rgba):
    """Stored linear-light RGBA (COLOR property) -> sRGB RGB + untouched alpha."""
    return (*cm.linear_to_srgb(rgba), *tuple(rgba[3:]))


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
    if updates_suspended():
        return False
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
        result = apply.apply_theme_to_blender(palette)
        if result is not True:
            raise RuntimeError(result)
    except Exception:
        traceback.print_exc()
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


@_guard_updates
def _on_accent_update(self, context):
    """Live-apply the accent role choices to the currently loaded palette.

    Only re-applies when a palette is loaded in the Palette Editor (that is
    where the dropdowns live). Never triggers on theme browsing.
    """
    _reapply_loaded_palette(context)


@_guard_updates
def _on_look_style_update(self, context):
    from .look_styles import ROUNDNESS
    with suspend_updates():
        self.finetune_roundness = ROUNDNESS[self.look_style]
        if self.look_style == 'LAYERED':
            self.outline_color = self.outline_color_2 = self.outline_color_3 = 'bg'
        elif self.look_style == 'OUTLINED':
            self.outline_color_2 = 'fg'
            self.outline_color_3 = 'fg'
    # A style selection must not repaint a native preset without a loaded palette.
    _reapply_loaded_palette(context)


@_guard_updates
def _on_finetune_color_update(self, context):
    """Live-apply the Playhead / Axis colour picks to the loaded palette."""
    if _suppress_finetune_color_update:
        return
    _reapply_loaded_palette(context)


@_guard_updates
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

# Guards programmatic writes to the Background 1 / Background 2 overrides.
_suppress_bg_primary_update = False
_suppress_bg_secondary_update = False


@_guard_updates
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
    """Return (text, selected) channel colors in LINEAR light: custom override
    or theme default. Convert with ``cm.linear_to_srgb`` before writing to
    Blender, and with ``cm.srgb_to_linear`` when seeding from the palette."""
    text = (prefs.finetune_dope_text
            if prefs.finetune_dope_text_custom else prefs.finetune_dope_text_def)
    sel = (prefs.finetune_dope_text_sel
           if prefs.finetune_dope_text_sel_custom else prefs.finetune_dope_text_sel_def)
    return tuple(text), tuple(sel)


@_guard_updates
def _on_dope_text_update(self, context):
    """Live-apply Dopesheet Channels text colors; keep swatches in sync."""
    global _suppress_dope_update
    if _suppress_dope_update:
        return
    try:
        prefs = context.preferences.addons[__package__].preferences
    except Exception:
        return

    # Channel swatches retain their own values; global text overrides win at
    # application time, just as they do at the end of a full palette apply.
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

    from .apply import apply_channel_text
    effective_text = prefs.finetune_text if prefs.finetune_text_custom else text
    effective_sel = prefs.finetune_text_sel if prefs.finetune_text_sel_custom else sel
    apply_channel_text(context.preferences.themes[0],
                       cm.linear_to_srgb(effective_text), cm.linear_to_srgb(effective_sel))

    try:
        for win in bpy.context.window_manager.windows:
            for area in win.screen.areas:
                area.tag_redraw()
    except Exception:
        pass


def seed_dope_defaults(text_rgb, selected_rgb):
    """Store the current palette's default channel text colors.

    Called by apply.py on every theme apply with **sRGB** palette values. Updates
    the hidden default colors, and refreshes the visible swatches unless the
    user has a custom override. Stored as linear light (COLOR properties).
    """
    global _suppress_dope_update
    try:
        prefs = bpy.context.preferences.addons[__package__].preferences
    except Exception:
        return
    text_lin = cm.srgb_to_linear(text_rgb[:3])
    sel_lin = cm.srgb_to_linear(selected_rgb[:3])
    _suppress_dope_update = True
    try:
        prefs.finetune_dope_text_def = text_lin
        prefs.finetune_dope_text_sel_def = sel_lin
        if not prefs.finetune_dope_text_custom:
            prefs.finetune_dope_text = text_lin
        if not prefs.finetune_dope_text_sel_custom:
            prefs.finetune_dope_text_sel = sel_lin
    except Exception:
        pass
    finally:
        _suppress_dope_update = False


def _effective_grid_color(prefs):
    """Return the grid color in LINEAR light: custom override or theme default.

    Convert with ``_srgb_from_linear_rgba`` before writing to Blender.
    """
    return tuple(prefs.finetune_grid
                 if prefs.finetune_grid_custom else prefs.finetune_grid_def)


@_guard_updates
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

    # Apply RGBA directly — property is size=4. Linear -> sRGB for the theme.
    rgba = _srgb_from_linear_rgba(grid)
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


@_guard_updates
def _on_cam_passepartout_update(self, context):
    """Live-apply the camera passepartout pick.

    Palette-independent by design: the theme's passepartout always follows
    this persistent pick (default literal #000000), it never follows a
    palette and has no Custom/default pair. Reload snapshots are covered by
    suspend_updates, so no separate suppress flag is needed. COLOR property
    holds linear light; the theme field takes sRGB RGB (3-float RNA, no
    alpha).
    """
    try:
        prefs = context.preferences.addons[__package__].preferences
    except Exception:
        return
    rgb = cm.linear_to_srgb(tuple(prefs.finetune_cam_passepartout))
    try:
        context.preferences.themes[0].view_3d.camera_passepartout = rgb
    except Exception:
        pass
    _redraw_after_apply()


def seed_grid_defaults(grid_rgba):
    """Store the current palette's default grid color (sRGB RGBA from apply.py).

    Updates the hidden default color, and refreshes the visible swatch unless
    the user has a custom override. Stored as linear light + untouched alpha.
    """
    global _suppress_grid_update
    try:
        prefs = bpy.context.preferences.addons[__package__].preferences
    except Exception:
        return
    stored = _linear_from_srgb_rgba(grid_rgba[:4])
    _suppress_grid_update = True
    try:
        prefs.finetune_grid_def = stored
        if not prefs.finetune_grid_custom:
            prefs.finetune_grid = stored
    except Exception:
        pass
    finally:
        _suppress_grid_update = False


def seed_viewport_background_defaults(background, black):
    """Refresh palette-derived RGB swatches without overwriting custom picks."""
    prefs = bpy.context.preferences.addons[__package__].preferences
    with suspend_updates():
        for suffix, color in (('a', background), ('b', black)):
            stored = cm.srgb_to_linear(color[:3])
            setattr(prefs, 'finetune_gradient_' + suffix + '_def', stored)
            if not getattr(prefs, 'finetune_gradient_' + suffix + '_custom'):
                setattr(prefs, 'finetune_gradient_' + suffix, stored)


@_guard_updates
def _on_viewport_background_update(self, context):
    with suspend_updates():
        for suffix in ('a', 'b'):
            if not getattr(self, 'finetune_gradient_' + suffix + '_custom'):
                setattr(self, 'finetune_gradient_' + suffix,
                        tuple(getattr(self, 'finetune_gradient_' + suffix + '_def')))
    _reapply_loaded_palette(context)


def _effective_bg_primary(prefs):
    """Return Background 1 in LINEAR light: custom override or palette bg.

    Convert with ``cm.linear_to_srgb`` before writing to Blender or to the
    theme dict, and with ``cm.srgb_to_linear`` when seeding from the palette.
    """
    return tuple(prefs.finetune_bg_primary
                 if prefs.finetune_bg_primary_custom else prefs.finetune_bg_primary_def)


def _effective_bg_secondary(prefs):
    """Return Background 2 in LINEAR light: custom override or Background 1.

    While the override is off the seeded default already carries whatever
    Background 1 resolves to, so widget bodies stay in step with the panels
    they sit on.
    """
    return tuple(prefs.finetune_bg_secondary
                 if prefs.finetune_bg_secondary_custom else prefs.finetune_bg_secondary_def)


@_guard_updates
def _on_bg_primary_update(self, context):
    """Live-apply the Background 1 override; keep the swatch in sync."""
    global _suppress_bg_primary_update
    if _suppress_bg_primary_update:
        return
    try:
        prefs = context.preferences.addons[__package__].preferences
    except Exception:
        return

    # Show the derived colour in the swatch while the override is off.
    _suppress_bg_primary_update = True
    try:
        if not prefs.finetune_bg_primary_custom:
            prefs.finetune_bg_primary = tuple(prefs.finetune_bg_primary_def)
    except Exception:
        pass
    finally:
        _suppress_bg_primary_update = False

    _reapply_loaded_palette(context)


@_guard_updates
def _on_bg_secondary_update(self, context):
    """Live-apply the Background 2 override; keep the swatch in sync."""
    global _suppress_bg_secondary_update
    if _suppress_bg_secondary_update:
        return
    try:
        prefs = context.preferences.addons[__package__].preferences
    except Exception:
        return

    _suppress_bg_secondary_update = True
    try:
        if not prefs.finetune_bg_secondary_custom:
            prefs.finetune_bg_secondary = tuple(prefs.finetune_bg_secondary_def)
    except Exception:
        pass
    finally:
        _suppress_bg_secondary_update = False

    _reapply_loaded_palette(context)


def seed_bg_role_defaults(theme_bg_rgb, surface_rgb):
    """Store the derived Background 1 / Background 2 colours.

    Called by apply.py on every theme apply with **sRGB** palette values:
    Background 1 defaults to the palette's own background, Background 2 to the
    current surface colour (which already follows Background 1 when that is
    overridden). Swatches are refreshed unless the user has an override of
    their own. Stored as linear light (COLOR properties).
    """
    global _suppress_bg_primary_update, _suppress_bg_secondary_update
    try:
        prefs = bpy.context.preferences.addons[__package__].preferences
    except Exception:
        return
    if not theme_bg_rgb:
        theme_bg_rgb = surface_rgb
    primary = cm.srgb_to_linear(theme_bg_rgb[:3])
    secondary = cm.srgb_to_linear(surface_rgb[:3])
    _suppress_bg_primary_update = True
    _suppress_bg_secondary_update = True
    try:
        prefs.finetune_bg_primary_def = (*primary, 1.0)
        prefs.finetune_bg_secondary_def = (*secondary, 1.0)
        if not prefs.finetune_bg_primary_custom:
            prefs.finetune_bg_primary = (*primary, 1.0)
        if not prefs.finetune_bg_secondary_custom:
            prefs.finetune_bg_secondary = (*secondary, 1.0)
    except Exception:
        pass
    finally:
        _suppress_bg_primary_update = False
        _suppress_bg_secondary_update = False


# Guards programmatic writes to the global text override properties.
_suppress_global_text_update = False


def _effective_global_text(prefs):
    """Return the text colour to force, in LINEAR light: the pick, or the
    palette default. Convert with ``cm.linear_to_srgb`` before writing."""
    return tuple(prefs.finetune_text
                 if prefs.finetune_text_custom else prefs.finetune_text_def)


def _effective_global_text_sel(prefs):
    """Return the selected-text colour in LINEAR light: the pick, or the
    palette default. Convert with ``cm.linear_to_srgb`` before writing."""
    return tuple(prefs.finetune_text_sel
                 if prefs.finetune_text_sel_custom else prefs.finetune_text_sel_def)


# ----------------------------------------------------------------------
# Finetune: interface scale (Blender's own Preferences > Interface value)
# ----------------------------------------------------------------------
# 1.00-2.00 is the slider's window; Blender itself accepts 0.50-6.00 for
# `PreferencesView.ui_scale`. Seeding only ever READS Blender - a write happens
# when the user moves the slider, or when "Reset to Original" restores the
# value that was found on load.
_suppress_ui_scale_update = False


def _view_prefs():
    """Blender's PreferencesView, or None outside a real session."""
    try:
        return bpy.context.preferences.view
    except Exception:
        return None


def seed_ui_scale_defaults():
    """Show the Resolution Scale Blender already has, clamped to the slider range."""
    global _suppress_ui_scale_update
    view = _view_prefs()
    try:
        current = float(view.ui_scale) if view is not None else 1.0
    except Exception:
        current = 1.0
    value = min(2.0, max(1.0, current))
    try:
        prefs = bpy.context.preferences.addons[__package__].preferences
    except Exception:
        return
    _suppress_ui_scale_update = True
    try:
        prefs.finetune_ui_scale_def = current
        prefs.finetune_ui_scale = value
    except Exception:
        pass
    finally:
        _suppress_ui_scale_update = False


def restore_ui_scale_default():
    """Reset to Original: put the interface scale back to the seeded value."""
    global _suppress_ui_scale_update
    try:
        prefs = bpy.context.preferences.addons[__package__].preferences
    except Exception:
        return
    value = float(getattr(prefs, "finetune_ui_scale_def", 1.0))
    _suppress_ui_scale_update = True
    try:
        prefs.finetune_ui_scale = value
    except Exception:
        pass
    finally:
        _suppress_ui_scale_update = False
    view = _view_prefs()
    if view is not None:
        try:
            view.ui_scale = value
        except Exception:
            pass


@_guard_updates
def _on_ui_scale_update(self, context=None):
    """Live: write the slider straight to Blender's Resolution Scale."""
    global _suppress_ui_scale_update
    if _suppress_ui_scale_update:
        return
    view = None
    if context is not None:
        view = getattr(context.preferences, "view", None)
    if view is None:
        view = _view_prefs()
    if view is None:
        return
    try:
        view.ui_scale = float(self.finetune_ui_scale)
    except Exception:
        pass


def seed_global_text_defaults(text_rgb, selected_rgb):
    """Store the current palette's default text colours (sRGB in, linear stored).

    Called by apply.py on every theme apply. Only refreshes the snapshot while
    the matching Custom toggle is off, so turning an override off falls back to
    the palette's own colours.
    """
    global _suppress_global_text_update
    try:
        prefs = bpy.context.preferences.addons[__package__].preferences
    except Exception:
        return
    text_lin = cm.srgb_to_linear(text_rgb[:3])
    sel_lin = cm.srgb_to_linear(selected_rgb[:3])
    _suppress_global_text_update = True
    try:
        prefs.finetune_text_def = text_lin
        prefs.finetune_text_sel_def = sel_lin
        if not prefs.finetune_text_custom:
            prefs.finetune_text = text_lin
        if not prefs.finetune_text_sel_custom:
            prefs.finetune_text_sel = sel_lin
    except Exception:
        pass
    finally:
        _suppress_global_text_update = False


@_guard_updates
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
        # COLOR properties hold linear light; theme fields expect sRGB.
        override_theme_text(context.preferences.themes[0],
                            text=cm.linear_to_srgb(text),
                            selected=cm.linear_to_srgb(sel))
    except Exception:
        pass
    _redraw_after_apply()


# Guards programmatic writes to the text-style properties.
_suppress_text_style_update = False

# 1.1.1-beta: the Finetune colour properties above switched from raw sRGB to
# linear light (COLOR subtype semantics). Values saved by an earlier build are
# still sRGB, so convert them once — otherwise a saved custom override would
# suddenly apply lighter than the user picked.
_COLORSPACE_MIGRATION_RGB = (
    ("finetune_dope_text", "finetune_dope_text_def"),
    ("finetune_dope_text_sel", "finetune_dope_text_sel_def"),
    ("finetune_text", "finetune_text_def"),
    ("finetune_text_sel", "finetune_text_sel_def"),
)


def migrate_finetune_colors_to_linear(prefs):
    """One-shot sRGB -> linear conversion of saved Finetune colour properties.

    Guarded by the hidden ``finetune_colorspace_linear`` flag, so it runs at
    most once per user profile. Update callbacks are suppressed while writing:
    the conversion itself is the change, no live re-apply is needed.
    """
    global _suppress_dope_update, _suppress_grid_update, _suppress_global_text_update

    if prefs is None or getattr(prefs, "finetune_colorspace_linear", False):
        return
    _suppress_dope_update = True
    _suppress_grid_update = True
    _suppress_global_text_update = True
    try:
        for name, def_name in _COLORSPACE_MIGRATION_RGB:
            setattr(prefs, name, cm.srgb_to_linear(tuple(getattr(prefs, name))[:3]))
            setattr(prefs, def_name, cm.srgb_to_linear(tuple(getattr(prefs, def_name))[:3]))
        prefs.finetune_grid = _linear_from_srgb_rgba(tuple(prefs.finetune_grid))
        prefs.finetune_grid_def = _linear_from_srgb_rgba(tuple(prefs.finetune_grid_def))
        prefs.finetune_colorspace_linear = True
    except Exception:
        return
    finally:
        _suppress_dope_update = False
        _suppress_grid_update = False
        _suppress_global_text_update = False

# Text styles managed by Finetune > Text Style. These live on
# `preferences.ui_styles` (Themes > User Interface > Text Style draws them),
# NOT on the Theme, so they are only forced when the Custom toggle is on.
_TEXT_STYLE_KEYS = ("panel_title", "widget", "tooltip")
# Text shadow is applied to these only; panel title keeps its own value
# (Blender's stock panel-title shadow is 3 / blur, widget and tooltip are 1).
_TEXT_SHADOW_KEYS = ("widget", "tooltip")


_SORT_ITEMS = [
    ('FAVOURITES', "Favorites First", "Show marked favorite palettes at the top"),
    ('POPULAR', "Popular First", "Show well-known themes at the top"),
    ('AZ', "A → Z", "Sort alphabetically"),
    ('ZA', "Z → A", "Sort reverse alphabetically"),
]

_FILTER_ITEMS = [
    ('ALL', "All Palettes", "Show every palette"),
    ('DARK', "Dark", "Show only palettes with a dark background"),
    ('LIGHT', "Light", "Show only palettes with a light background"),
]


def get_favorite_paths():
    """Return the persisted set of favourite palette paths."""
    try:
        prefs = bpy.context.preferences.addons[__package__].preferences
        values = json.loads(prefs.favorite_theme_paths or "[]")
        return {str(path) for path in values if path}
    except Exception:
        return set()


@_guard_updates
def _on_sort_update(self, context):
    """Re-sort the visible theme list when the persisted sort mode changes."""
    try:
        from . import _on_theme_sort_update
    except Exception:
        return
    _on_theme_sort_update(self, context)


@_guard_updates
def _on_filter_update(self, context):
    """Re-filter the visible theme list when the dark/light filter changes."""
    try:
        from . import _on_theme_sort_update
    except Exception:
        return
    _on_theme_sort_update(self, context)


@_guard_updates
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


@_guard_updates
def _on_source_mode_update(self, context):
    """Swap the browser to the index of the newly selected mode.

    LOCAL rebuilds its index by scanning the chosen folder; REMOTE rebuilds
    its index from the already-cached source directories. Neither path
    downloads anything, so switching modes is instant and offline-safe, and
    the two indexes live in separate files so neither overwrites the other.
    """
    import os

    from . import repo, download_job

    try:
        mode = repo.INDEX_LOCAL if self.source_mode == 'LOCAL' else repo.INDEX_REMOTE
        # Prefer the existing snapshot; never scan a cache mid-publication.
        if not repo.has_index(mode) and not download_job.is_running():
            if self.source_mode == 'LOCAL':
                folder = bpy.path.abspath(self.local_folder)
                if folder and os.path.isdir(folder):
                    repo.index_local_folder(folder)
            else:
                repo.rebuild_remote_index()
        self.themes_loaded = repo.has_index(mode)
    except Exception:
        traceback.print_exc()

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
    """Snapshot each native text style independently while not overriding.

    Called after registration and by apply.py on every theme apply. A default is only recorded while
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

    styles = _ui_text_styles()
    try:
        snapshots = json.loads(prefs.finetune_text_style_defaults or '{}')
        if not isinstance(snapshots, dict):
            snapshots = {}
    except (TypeError, ValueError):
        snapshots = {}
    for index, (key, style) in enumerate(styles):
        saved = snapshots.setdefault(f'{index}:{key}', {})
        if not font_custom:
            saved['points'] = float(style.points)
        if not shadow_custom and key in _TEXT_SHADOW_KEYS:
            saved['shadow'] = int(style.shadow)
    prefs.finetune_text_style_defaults = json.dumps(snapshots)

    representative = dict(styles).get("widget")
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


def apply_text_style(prefs=None, custom_only=False):
    """Write the Finetune text-style values into preferences.ui_styles.

    Custom off -> the snapshot value is written back (so switching Custom off
    restores what the user had). Custom on -> the chosen value is enforced.
    Font size covers Panel Title + Widget + Tooltip; shadow only Widget and
    Tooltip. Palette application uses custom_only=True so disabled groups are
    untouched; toggle callbacks restore per-style snapshots.
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

    try:
        snapshots = json.loads(prefs.finetune_text_style_defaults or '{}')
        if not isinstance(snapshots, dict):
            snapshots = {}
    except (TypeError, ValueError):
        snapshots = {}
    for index, (key, font_style) in enumerate(styles):
        saved = snapshots.get(f'{index}:{key}', {})
        if not custom_only or prefs.finetune_font_custom:
            try:
                font_style.points = points if prefs.finetune_font_custom else saved.get('points', points)
            except Exception:
                pass
        if key in _TEXT_SHADOW_KEYS and (not custom_only or prefs.finetune_shadow_custom):
            try:
                font_style.shadow = shadow if prefs.finetune_shadow_custom else saved.get('shadow', shadow)
            except Exception:
                pass


@_guard_updates
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

    look_style: EnumProperty(
        name="Look Style",
        description="Surface treatment; preserves palette colors and custom overrides",
        # Keep Layered=8 and the other surviving IDs stable across upgrades.
        items=[('LAYERED', "Default", "Layered background, panel and control tones", 8),
               ('CARD', "Card", "Distinct panel surfaces, soft corners and flat controls", 3),
               ('OUTLINED', "Outlined", "Flat surfaces and crisp control borders", 5),
               ('INSET', "Inset", "Recessed panel surfaces with lighter controls", 6),
               ('ACCENT', "Accent", "Card surfaces with restrained accent-tinted headers", 7)],
        default='LAYERED', update=_on_look_style_update,
    )
    # Legacy restoration fields retained only for saved-preference compatibility.
    look_style_original_roundness: FloatProperty(
        default=-1, min=-1, max=1, options={'HIDDEN'})
    look_style_shading_defaults: StringProperty(default="", options={'HIDDEN'})

    # UI-only page selection. Existing section states remain for saved settings.
    ui_page: EnumProperty(
        name="Workspace",
        description="Choose a Palette Studio task",
        items=[
            ('BROWSE', "Browse", "Find and apply a palette", 'COLOR', 0),
            ('PALETTE', "Palette", "Edit palette slots and Quick Adjust", 'BRUSHES_ALL', 1),
            ('APPEARANCE', "Finetune", "Tune interface, viewport and animation", 'PREFERENCES', 2),
            ('CONFIGURE', "Settings", "Manage sources, cache and native presets", 'TOOL_SETTINGS', 3),
        ],
        default='BROWSE',
    )

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

    show_quick_adjust: BoolProperty(
        name="Quick Adjust", description="Adjust all checked ANSI colors together", default=True)
    show_hex: BoolProperty(
        name="Show Hex", description="Show editable hexadecimal color values beside swatches", default=False)
    show_cache: BoolProperty(name="Cache", default=False, options={'HIDDEN'})
    show_presets: BoolProperty(name="Blender Presets", default=False)
    show_sources: BoolProperty(name="Sources", default=True)
    show_noctalia: BoolProperty(name="Noctalia Sync", default=False)
    show_blender_theme: BoolProperty(name="Blender Theme", default=False)

    # Saved fold states are preserved; new profiles start with less detail.
    show_ft_ui: BoolProperty(
        name="User Interface",
        default=False,
    )
    show_ft_fonts: BoolProperty(name="Fonts & Text", default=False)
    show_ft_view3d: BoolProperty(
        name="3D Viewport",
        default=False,
    )
    show_ft_extras: BoolProperty(
        name="Extras",
        default=False,
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
        update=_on_source_mode_update,
        options={'HIDDEN'},
    )

    # UI / get_enabled_sources() order: NvChad, iTerm2, base24, kitty, alacritty.
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
    source_kitty: BoolProperty(
        name="kitty-themes",
        description="Show ~412 themes from the kovidgoyal/kitty-themes repository "
                    "(downloaded by Load Themes)",
        default=False,
        update=_on_source_update,
    )
    source_alacritty: BoolProperty(
        name="alacritty-theme",
        description="Show ~177 themes from the alacritty/alacritty-theme repository "
                    "(downloaded by Load Themes)",
        default=False,
        update=_on_source_update,
    )
    source_noctalia: BoolProperty(
        name="Noctalia",
        description="Show the Noctalia color schemes found on this machine plus the "
                    "community palettes (downloaded by Load Themes)",
        default=True,
        update=_on_source_update,
    )

    local_folder: StringProperty(
        name="Local Folder",
        description="Path to a folder containing theme files (.itermcolors, .yml, .yaml, .conf, .toml, .lua)",
        default="",
        subtype='DIR_PATH',
        options={'HIDDEN'},
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
    outline_color: EnumProperty(
        name="Outline 1",
        description="Palette slot used for widget outlines, borders and separators",
        items=_ACCENT_ITEMS,
        default='bg',
        update=_on_accent_update,
    )
    outline_color_2: EnumProperty(
        name="Outline 2",
        description="Palette slot used for panel and toolbar-item outlines",
        items=_ACCENT_ITEMS,
        default='bg',
        update=_on_accent_update,
    )
    outline_color_3: EnumProperty(
        name="Outline 3",
        description="Palette slot used for regular and option widget outlines",
        items=_ACCENT_ITEMS,
        default='bg',
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
    last_selected_theme_path: StringProperty(
        name="Last Selected Palette Path",
        description="Path of the last palette selected in the browser",
        default="",
        options={'HIDDEN'},
    )
    last_selected_theme_variant: StringProperty(
        name="Last Selected Palette Variant",
        description="Variant of the last selected palette, when applicable",
        default="",
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
        default=0.5, min=0.0, max=1.0,
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

    finetune_text_style_defaults: StringProperty(
        name="Original Text Styles",
        description="Per-style font and shadow snapshots for restoring native settings",
        default='{}', options={'HIDDEN'},
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

    # --- Finetune: camera passepartout color ---
    # A single persistent user pick, deliberately WITHOUT a Custom/default
    # pair: the theme's passepartout always follows this colour, so it never
    # changes when a palette is applied. Default literal #000000. Not part of
    # migrate_finetune_colors_to_linear — there are no pre-1.2.2 saved
    # values for this property, and converting would corrupt future picks.
    finetune_cam_passepartout: FloatVectorProperty(
        name="Passepartout",
        description=("Color outside the camera frame; follows this pick over "
                     "palette changes (Themes > 3D Viewport > Camera > Passepartout)"),
        subtype='COLOR', size=3, min=0.0, max=1.0,
        default=(0.0, 0.0, 0.0),
        update=_on_cam_passepartout_update,
    )

    # Set once the Finetune colour properties have been migrated from the old
    # raw-sRGB storage to linear light (see
    # migrate_finetune_colors_to_linear). Not drawn.
    finetune_colorspace_linear: BoolProperty(
        name="Finetune Colors Migrated",
        default=False,
        options={'HIDDEN'},
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

    finetune_background_type: EnumProperty(
        name="Background Type",
        items=[('SINGLE_COLOR', "Static", "Use Gradient A as a solid background"),
               ('LINEAR', "Gradient", "Blend Gradient A and B vertically"),
               ('RADIAL', "Vignette", "Blend Gradient A and B radially")],
        default='SINGLE_COLOR', update=_on_viewport_background_update,
    )
    finetune_gradient_a_custom: BoolProperty(
        name="Custom Gradient A", default=False, update=_on_viewport_background_update)
    finetune_gradient_a: FloatVectorProperty(
        name="Gradient A", subtype='COLOR', size=3, min=0.0, max=1.0,
        default=(0.0, 0.0, 0.0), update=_on_viewport_background_update)
    finetune_gradient_a_def: FloatVectorProperty(
        name="Default Gradient A", subtype='COLOR', size=3, min=0.0, max=1.0,
        default=(0.0, 0.0, 0.0), options={'HIDDEN'})
    finetune_gradient_b_custom: BoolProperty(
        name="Custom Gradient B", default=False, update=_on_viewport_background_update)
    finetune_gradient_b: FloatVectorProperty(
        name="Gradient B", subtype='COLOR', size=3, min=0.0, max=1.0,
        default=(0.0, 0.0, 0.0), update=_on_viewport_background_update)
    finetune_gradient_b_def: FloatVectorProperty(
        name="Default Gradient B", subtype='COLOR', size=3, min=0.0, max=1.0,
        default=(0.0, 0.0, 0.0), options={'HIDDEN'})

    # --- Finetune: User Interface surface colours --------------------------
    # Background 1 drives every former "background" property (panels, editor
    # backgrounds and headers); Background 2 drives the former
    # bright-black surfaces that are not outlines. Both are direct colour
    # overrides rather than slot picks: while a toggle is off the palette's own
    # background is used, so nothing changes until the user opts in. The
    # swatches hold LINEAR light, like every other Finetune colour property.
    # size=4 so Blender's native picker offers the A slider; alpha defaults to
    # 1.0 and multiplies the design alphas (row_alternate 0.5, frame_node 0.6).
    finetune_bg_primary_custom: BoolProperty(
        name="Custom Background 1",
        description="Override the colour used by panels, editor backgrounds and headers",
        default=False,
        update=_on_bg_primary_update,
    )
    finetune_bg_primary: FloatVectorProperty(
        name="Background 1",
        description="Surface colour for panels, editor backgrounds and headers",
        subtype='COLOR', size=4, min=0.0, max=1.0,
        default=(0.0, 0.0, 0.0, 1.0),
        update=_on_bg_primary_update,
    )
    finetune_bg_primary_def: FloatVectorProperty(
        name="Default Background 1",
        subtype='COLOR', size=4, min=0.0, max=1.0,
        default=(0.0, 0.0, 0.0, 1.0),
    )
    finetune_bg_secondary_custom: BoolProperty(
        name="Custom Background 2",
        description=("Override the colour used by widget bodies, buttons and the other "
                     "non-outline surfaces"),
        default=False,
        update=_on_bg_secondary_update,
    )
    finetune_bg_secondary: FloatVectorProperty(
        name="Background 2",
        description=("Surface colour for widget bodies, buttons, alternate rows and "
                     "other non-outline surfaces"),
        subtype='COLOR', size=4, min=0.0, max=1.0,
        default=(0.0, 0.0, 0.0, 1.0),
        update=_on_bg_secondary_update,
    )
    finetune_bg_secondary_def: FloatVectorProperty(
        name="Default Background 2",
        subtype='COLOR', size=4, min=0.0, max=1.0,
        default=(0.0, 0.0, 0.0, 1.0),
    )

    # --- Finetune: interface scale (Blender's Resolution Scale) ---
    finetune_ui_scale: FloatProperty(
        name="UI Scale",
        description=("Blender's interface Resolution Scale (Preferences > Interface > "
                     "Display). Seeded from the value Blender already has; this "
                     "slider covers 1.00-2.00"),
        default=1.0, min=1.0, max=2.0, precision=2,
        update=_on_ui_scale_update,
    )
    finetune_ui_scale_def: FloatProperty(
        name="Default UI Scale",
        default=1.0, min=0.5, max=6.0, precision=2,
        options={'HIDDEN'},
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
        if self.source_kitty:
            sources.append("kitty")
        if self.source_alacritty:
            sources.append("alacritty")
        if self.source_noctalia:
            # Covers the local Noctalia schemes and the community palettes:
            # both are indexed under this one tag.
            sources.append("noctalia")
        return sources

    # ------------------------------------------------------------------
    # Section header helper
    # ------------------------------------------------------------------
    def _draw_section_header(self, layout, prop_name, label, icon):
        """Draw a foldable card header. Returns the card body when open."""
        is_open = getattr(self, prop_name)
        layout.separator(factor=0.5)
        box = layout.box()
        row = box.row(align=True)
        row.alignment = 'LEFT'
        row.scale_y = 1.15
        row.label(text="", icon=icon)
        row.prop(
            self, prop_name,
            icon='TRIA_DOWN' if is_open else 'TRIA_RIGHT',
            text=label,
            emboss=False,
            icon_only=False,
        )
        return box if is_open else None

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------
    def draw(self, context):
        draw_sections(self.layout, self, context)


def _draw_group(layout, title, icon='NONE'):
    """Section heading plus an aligned property column."""
    layout.separator(factor=0.4)
    layout.label(text=title, icon=icon)
    col = layout.column(align=True)
    col.use_property_split = True
    col.use_property_decorate = False
    return col


def _draw_override(layout, prefs, toggle, value, label):
    """Fixed label/value columns keep overrides readable in a narrow sidebar."""
    split = layout.split(factor=0.48, align=True)
    split.prop(prefs, toggle, text=label)
    field = split.row(align=True)
    field.enabled = getattr(prefs, toggle)
    field.prop(prefs, value, text="")


def _selected_theme(wm):
    index = wm.palette_studio_theme_active
    return wm.palette_studio_themes[index] if 0 <= index < len(wm.palette_studio_themes) else None


def _draw_hero(layout, prefs, context):
    """Current-palette card with a slim, read-only ANSI color ribbon."""
    wm = context.window_manager
    hero = layout.box()
    title = hero.row(align=True)
    title.scale_y = 1.15
    if wm.palette_studio_palette_loaded:
        title.label(text=wm.palette_studio_palette_theme_name or "Untitled Palette", icon='COLOR')
        badge = title.row()
        badge.alignment = 'RIGHT'
        badge.enabled = False
        badge.label(text="LOADED", icon='CHECKMARK')
        ribbon = hero.row(align=True)
        ribbon.scale_y = 0.65
        for item in wm.palette_studio_palette:
            if item.slot_id.startswith("ansi_") and int(item.slot_id[5:]) < 8:
                ribbon.prop(item, "preview_color", text="")
    else:
        title.label(text="Palette Studio", icon='COLOR')
        badge = title.row()
        badge.alignment = 'RIGHT'
        badge.enabled = False
        badge.label(text="READY", icon='INFO')
        hero.label(text="1000+ palettes, ready to explore.")
        hero.label(text="Pick one, then make it yours.", icon='COLOR')


def _draw_nav(layout, prefs):
    """Four clear task buttons, two per row for narrow sidebars."""
    nav = layout.column(align=True)
    for pages in (('BROWSE', 'PALETTE'), ('APPEARANCE', 'CONFIGURE')):
        row = nav.row(align=True)
        row.scale_y = 1.3
        for page in pages:
            row.prop_enum(prefs, "ui_page", page)


def _draw_browse(layout, prefs, context):
    wm = context.window_manager
    library = layout.box()
    header = library.row()
    header.label(text="Palette Library", icon='COLOR')
    count = header.row()
    count.alignment = 'RIGHT'
    count.enabled = False
    count.label(text=str(len(wm.palette_studio_themes)))

    loaded = prefs.themes_loaded or bool(wm.palette_studio_themes)
    if not loaded:
        library.label(text="Your library is empty.", icon='INFO')
        library.label(text="Download palettes, then explore.")
        from . import download_job
        action = library.row()
        action.scale_y = 1.5
        action.enabled = not download_job.is_running()
        action.operator("palette_studio.refresh_repo",
                        text="Download Palettes",
                        icon='IMPORT')
        library.prop_enum(prefs, "ui_page", 'CONFIGURE',
                          text="Choose Sources", icon='TOOL_SETTINGS')
        return

    search = library.row(align=True)
    search.scale_y = 1.3
    search.prop(wm, "palette_studio_theme_search", text="", icon='VIEWZOOM')
    search.operator("palette_studio.surprise_me", text="", icon='RNDCURVE')

    filter_row = library.row(align=True)
    filter_row.prop(prefs, "theme_filter", expand=True)

    sort_row = library.row(align=True)
    sort_row.prop(prefs, "theme_sort", text="Sort")

    library.template_list("PALETTE_STUDIO_UL_theme_list", "", wm, "palette_studio_themes",
                          wm, "palette_studio_theme_active", rows=8)
    if not wm.palette_studio_themes:
        library.label(text="No palettes match.", icon='INFO')
        library.label(text="Try another search or filter.")
        return


def _draw_palette(layout, prefs, context):
    wm = context.window_manager
    if not wm.palette_studio_palette_loaded:
        box = layout.box()
        box.label(text="No palette open.", icon='COLOR')
        box.label(text="Choose one in Browse to start.")
        row = box.row()
        row.scale_y = 1.4
        row.prop_enum(prefs, "ui_page", 'BROWSE', text="Browse Palettes", icon='COLOR')
        row = box.row()
        row.enabled = _selected_theme(wm) is not None
        row.operator("palette_studio.load_palette", text="Load Selected Palette", icon='IMPORT')
        return

    groups = (("Base Colors", [item for item in wm.palette_studio_palette
                               if not item.slot_id.startswith("ansi_")], 'COLOR'),
              ("Standard / ANSI 0-7", [item for item in wm.palette_studio_palette
                                      if item.slot_id.startswith("ansi_") and int(item.slot_id[5:]) < 8],
               'COLOR'),
              ("Bright / ANSI 8-15", [item for item in wm.palette_studio_palette
                                      if item.slot_id.startswith("ansi_") and int(item.slot_id[5:]) >= 8],
               'LIGHT'))
    for title, items, icon in groups:
        box = layout.box()
        box.label(text=title, icon=icon)
        grid = box.grid_flow(row_major=True, columns=2, even_columns=True,
                             even_rows=True, align=True)
        for item in items:
            cell = grid.column(align=True)
            swatch = cell.row()
            swatch.scale_y = 1.8
            swatch.prop(item, "color", text="")
            name = cell.row(align=True)
            if item.slot_id.startswith("ansi_"):
                name.prop(item, "enabled", text="")
                # Keep the slot number visible; the group already says Bright.
                number = int(item.slot_id[5:])
                label = item.label.split(" — ")[-1].removeprefix("Bright ")
                name.label(text=f"{number:02d} {label}")
            else:
                name.label(text=item.label)
            if prefs.show_hex:
                cell.prop(item, "hex_value", text="")

    layout.prop(prefs, "show_hex")
    box = prefs._draw_section_header(layout, "show_quick_adjust", "Quick Adjust", 'MODIFIER')
    if box is not None:
        box.label(text="Applies to checked ANSI colors.")
        col = box.column(align=True)
        for prop, label in (("palette_quick_hue", "Hue"), ("palette_quick_sat", "Saturation"),
                            ("palette_quick_val", "Value"), ("palette_quick_alpha", "Alpha")):
            col.prop(wm, prop, text=label, slider=True)

    layout.separator()
    box = layout.column(align=True)
    box.operator("palette_studio.reset_palette", text="Reset to Original", icon='LOOP_BACK')
    row = box.row()
    row.enabled = _selected_theme(wm) is not None
    row.operator("palette_studio.load_palette", text="Reload Selected Palette", icon='FILE_REFRESH')
    layout.separator()
    save = layout.row()
    save.scale_y = 1.4
    save.operator("palette_studio.save_theme", text="Save Palette Preset", icon='FILE_TICK')


def _draw_appearance(layout, prefs, context):
    styles = layout.box()
    styles.label(text="Choose a Look", icon='SHADING_RENDERED')
    tiles = (('LAYERED', 'SHADING_SOLID'), ('CARD', 'MOD_BEVEL'),
             ('OUTLINED', 'MOD_WIREFRAME'), ('INSET', 'MOD_SUBSURF'))
    grid = styles.grid_flow(row_major=True, columns=2, even_columns=True, align=True)
    for style, icon in tiles:
        row = grid.row()
        row.scale_y = 1.25
        row.prop_enum(prefs, "look_style", style, icon=icon)
    row = styles.row()
    row.scale_y = 1.25
    row.prop_enum(prefs, "look_style", 'ACCENT', icon='COLOR')
    if not context.window_manager.palette_studio_palette_loaded:
        styles.label(text="Load a palette to try these looks live.", icon='INFO')

    box = prefs._draw_section_header(layout, "show_ft_ui", "Interface", 'USER')
    if box is not None:
        col = _draw_group(box, "Accents & Outlines", 'COLOR')
        for prop, label in (("accent_primary", "Primary"), ("accent_secondary", "Secondary"),
                            ("accent_tertiary", "Tertiary"), ("outline_color", "Outline 1"),
                            ("outline_color_2", "Outline 2"), ("outline_color_3", "Outline 3")):
            col.prop(prefs, prop, text=label)
        _draw_group(box, "Surfaces", 'SHADING_RENDERED')
        _draw_override(box, prefs, "finetune_bg_primary_custom", "finetune_bg_primary", "Background 1")
        _draw_override(box, prefs, "finetune_bg_secondary_custom", "finetune_bg_secondary", "Background 2")
        col = _draw_group(box, "Shape & Scale", 'PREFERENCES')
        col.prop(prefs, "finetune_roundness", text="Roundness", slider=True)
        col.prop(prefs, "finetune_ui_scale", text="UI Scale", slider=True)

    box = prefs._draw_section_header(layout, "show_ft_fonts", "Fonts & Text", 'FONT_DATA')
    if box is not None:
        _draw_group(box, "Typography", 'FONT_DATA')
        box.label(text="Interface Font")
        box.prop(context.preferences.view, "font_path_ui", text="")
        for toggle, value, label in (
                ("finetune_font_custom", "finetune_font_size", "Font Size"),
                ("finetune_shadow_custom", "finetune_text_shadow", "Shadow"),
                ("finetune_text_custom", "finetune_text", "Text Color"),
                ("finetune_text_sel_custom", "finetune_text_sel", "Selected Text")):
            _draw_override(box, prefs, toggle, value, label)

    box = prefs._draw_section_header(layout, "show_ft_view3d", "Viewport", 'VIEW3D')
    if box is not None:
        col = _draw_group(box, "Background", 'SHADING_RENDERED')
        col.prop(prefs, "finetune_background_type", text="Type")
        _draw_override(box, prefs, "finetune_gradient_a_custom", "finetune_gradient_a", "Gradient A")
        if prefs.finetune_background_type != 'SINGLE_COLOR':
            _draw_override(box, prefs, "finetune_gradient_b_custom", "finetune_gradient_b", "Gradient B")
            row = box.row()
            row.enabled = context.window_manager.palette_studio_palette_loaded
            row.operator("palette_studio.swap_gradient_colors", text="Swap A / B", icon='ARROW_LEFTRIGHT')
        col = _draw_group(box, "Axes & Selection", 'OBJECT_DATA')
        for prop, label in (("finetune_axis_x", "X Axis"), ("finetune_axis_y", "Y Axis"),
                            ("finetune_axis_z", "Z Axis"), ("finetune_object_selected", "Selected"),
                            ("finetune_active_object", "Active")):
            col.prop(prefs, prop, text=label)
        col = _draw_group(box, "Geometry Sizes", 'EDITMODE_HLT')
        for prop, label in (("finetune_edge_width", "Edges"), ("finetune_vertex_size", "Vertices"),
                            ("finetune_facedot_size", "Face Dots"), ("finetune_outline_width", "Outline")):
            col.prop(prefs, prop, text=label)
        box.separator()
        _draw_override(box, prefs, "finetune_grid_custom", "finetune_grid", "Grid Color")
        col = _draw_group(box, "Camera", 'CAMERA_DATA')
        col.prop(prefs, "finetune_cam_passepartout", text="Passepartout")

    box = prefs._draw_section_header(layout, "show_ft_extras", "Animation", 'ANIM')
    if box is not None:
        col = _draw_group(box, "Timeline Colors", 'TIME')
        col.prop(prefs, "finetune_playhead", text="Playhead")
        col.prop(prefs, "finetune_keyframe_selected", text="Selected Keys")


def _draw_configure(layout, prefs, context):
    box = prefs._draw_section_header(layout, "show_sources", "Sources", 'IMPORT')
    if box is not None:
        box.use_property_split = False
        box.label(text="Pick the collections you want to explore.")
        grid = box.grid_flow(row_major=True, columns=2, even_columns=True, align=True)
        for prop, label in (("source_nvchad", "NvChad"), ("source_iterm", "iTerm2"),
                            ("source_base24", "Base24"), ("source_kitty", "Kitty"),
                            ("source_alacritty", "Alacritty"), ("source_noctalia", "Noctalia")):
            grid.prop(prefs, prop, text=label)

    layout.separator()
    library = layout.column()
    from . import download_job
    running = download_job.is_running()
    row = library.row()
    row.scale_y = 1.4
    row.enabled = not running
    row.operator("palette_studio.refresh_repo", text="Download Palettes", icon='IMPORT')
    row = library.row()
    row.enabled = not running and (prefs.themes_loaded
                                  or bool(context.window_manager.palette_studio_themes))
    row.operator("palette_studio.unload_themes", text="Unload Palettes", icon='TRASH')
    if running:
        row = library.row()
        row.scale_y = 1.2
        row.operator("palette_studio.cancel_download", text="Cancel Download", icon='CANCEL')
    status = download_job.status_message()
    if status:
        library.label(text=status, icon='INFO')

    if prefs.source_noctalia:
        layout.operator("palette_studio.sync_noctalia", text="noctalia sync (optional)", icon='FILE_REFRESH')

    box = prefs._draw_section_header(layout, "show_blender_theme", "Blender Theme", 'PRESET')
    if box is not None:
        box.label(text="Return Blender to its own default colors.")
        box.operator("palette_studio.restore_theme", text="Restore Blender Theme", icon='LOOP_BACK')


def _draw_presets(layout, prefs, context):
    """Native presets remain available even when the palette library is empty."""
    theme = context.preferences.themes[0]
    box = prefs._draw_section_header(layout, "show_presets", "Blender Presets", 'PRESET')
    if box is not None:
        box.menu("USERPREF_MT_interface_theme_presets",
                 text=bpy.path.display_name(theme.filepath) if theme.filepath else "Choose Preset")
        row = box.row(align=True)
        row.operator("wm.interface_theme_preset_add", text="Add", icon='ADD')
        row.operator("wm.interface_theme_preset_remove", text="Remove", icon='REMOVE')
        row.operator("wm.interface_theme_preset_save", text="Save", icon='FILE_TICK')


def draw_sections(layout, prefs, context):
    """Complete task-based workspace shared by Preferences and the N-panel."""
    from . import _ensure_theme_list
    _ensure_theme_list(context)
    layout.use_property_decorate = False

    _draw_hero(layout, prefs, context)
    _draw_nav(layout, prefs)
    layout.separator()

    drawers = {'BROWSE': _draw_browse, 'PALETTE': _draw_palette,
               'APPEARANCE': _draw_appearance, 'CONFIGURE': _draw_configure}
    drawers[prefs.ui_page](layout, prefs, context)
    if prefs.ui_page == 'BROWSE':
        _draw_presets(layout, prefs, context)

    layout.separator()
    footer = layout.row()
    footer.scale_y = 1.3
    footer.operator("wm.save_userpref", text="Save Preferences", icon='FILE_TICK')
    note = layout.column(align=True)
    note.enabled = False
    note.label(text="1.2.0")


def register():
    from . import _register_class
    _register_class(PaletteStudioPrefs)


def initialize_settings():
    """Initialize only after legacy settings and WindowManager RNA are ready."""
    with suspend_updates():
        prefs = bpy.context.preferences.addons[__package__].preferences
        # Retire the local-folder UI without touching its files or saved theme.
        prefs.source_mode = 'REMOTE'
        # Removed styles fall back safely; startup must not repaint the saved theme.
        if not prefs.look_style:
            prefs.look_style = 'LAYERED'
            prefs.finetune_roundness = 0.5
        prefs.look_style_original_roundness = -1
        prefs.look_style_shading_defaults = ''
        seed_ui_scale_defaults()
        migrate_finetune_colors_to_linear(
            bpy.context.preferences.addons[__package__].preferences)
        seed_text_style_defaults()


def unregister():
    try:
        bpy.utils.unregister_class(PaletteStudioPrefs)
    except Exception:
        pass

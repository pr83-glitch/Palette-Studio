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
Palette for Blender
================================

Import terminal color schemes (.itermcolors, Gogh/base16 YAML, kitty .conf)
and apply them as Blender themes. Each Blender theme colour is an exact colour
from the source palette (the 16 ANSI slots plus bg/fg/cursor/selection); the
role -> slot mapping lives in ``color_roles.ROLE_MAP``.

Author: NXSTYNATE
License: GPL-3.0
"""

_needs_reload = "bpy" in locals()

import bpy
import colorsys
import json
import os
import traceback
from bpy.props import (
    StringProperty,
    IntProperty,
    BoolProperty,
    CollectionProperty,
    FloatProperty,
    FloatVectorProperty,
)
from bpy.types import (
    Operator,
    Panel,
    PropertyGroup,
    UIList,
)

from . import (
    color_math,
    color_roles,
    iterm_parser,
    blender_theme_map,
    apply,
    repo,
    popular,
    prefs,
    palette_slots,
)

if _needs_reload:
    import importlib
    color_math = importlib.reload(color_math)
    color_roles = importlib.reload(color_roles)
    iterm_parser = importlib.reload(iterm_parser)
    blender_theme_map = importlib.reload(blender_theme_map)
    apply = importlib.reload(apply)
    repo = importlib.reload(repo)
    popular = importlib.reload(popular)
    prefs = importlib.reload(prefs)
    palette_slots = importlib.reload(palette_slots)


# =========================================================================
# Color slot labels — maps index to human-readable role
# =========================================================================

# Defined in palette_slots.py so prefs.py can import them without a cycle.
PALETTE_SLOTS = palette_slots.PALETTE_SLOTS

# Friendly display names for the source key stored on each indexed theme.
_SOURCE_LABELS = {
    "nvchad": "NvChad",
    "iterm": "iTerm2",
    "base24": "base24",
    "kitty": "kitty",
    "alacritty": "Alacritty",
    "noctalia": "Noctalia",
    "base16": "base16",
    "local": "Local",
}


def _hex_from_rgb(r, g, b):
    # round() rather than truncation: a truncation turns 1.0 into 0xFE, so
    # pure white/black in a theme showed up as #FEFEFE / #010101.
    return "#{:02X}{:02X}{:02X}".format(
        max(0, min(255, int(round(r * 255)))),
        max(0, min(255, int(round(g * 255)))),
        max(0, min(255, int(round(b * 255)))),
    )


def _rgb_from_hex(hexstr):
    """Parse hex like '#FF00AA' or 'FF00AA' into (r,g,b) floats."""
    h = hexstr.strip().lstrip('#')
    if len(h) != 6:
        return None
    try:
        r = int(h[0:2], 16) / 255.0
        g = int(h[2:4], 16) / 255.0
        b = int(h[4:6], 16) / 255.0
        return (r, g, b)
    except ValueError:
        return None


# =========================================================================
# Property groups
# =========================================================================

class PALETTE_STUDIO_ThemeItem(PropertyGroup):
    name: StringProperty(name="Theme Name")
    path: StringProperty(name="File Path")
    source: StringProperty(name="Source")
    favorite: BoolProperty(name="Favourite", default=False)
    dark: BoolProperty(name="Dark Theme", default=True)
    # Noctalia packs a dark and a light palette into one file, so the entry
    # remembers which one it stands for (empty for every other format).
    variant: StringProperty(name="Variant")


# Live apply debounce: a colour-wheel drag fires an update per mouse move, so
# the re-apply is coalesced through a one-shot timer instead of rewriting the
# whole theme on every tick.
_live_apply_timer = None


def _schedule_live_apply():
    """Queue one live re-apply of the loaded palette."""
    global _live_apply_timer
    if _live_apply_timer is None:
        try:
            _live_apply_timer = bpy.app.timers.register(
                _run_live_apply, first_interval=0.05)
        except Exception:
            _live_apply_timer = None


def _run_live_apply():
    """One-shot timer body: apply once, then let the next edit schedule again."""
    global _live_apply_timer
    _live_apply_timer = None
    try:
        from . import prefs
        prefs._reapply_loaded_palette(bpy.context)
    except Exception:
        pass
    return None


def cancel_live_apply():
    """Drop a pending live apply (called from unregister)."""
    global _live_apply_timer
    if _live_apply_timer is not None:
        try:
            bpy.app.timers.unregister(_live_apply_timer)
        except Exception:
            pass
        _live_apply_timer = None


def _maybe_live_apply(context):
    """Schedule a live re-apply when a palette is loaded in the editor.

    Palette Editor edits always apply live, like Finetune; the Settings
    "Preview" toggle only governs theme-list browsing. During
    ``_populate_palette_from_theme`` the loaded flag is still False, so the
    programmatic writes there never queue an apply.
    """
    try:
        wm = context.window_manager
        if not wm.palette_studio_palette_loaded or not len(wm.palette_studio_palette):
            return
    except Exception:
        return
    _schedule_live_apply()


def _on_palette_hex_update(self, context):
    """When hex field is edited, update the color swatch.

    ``hex_value`` is sRGB text, while ``color`` is a ``subtype='COLOR'``
    property, which Blender stores in linear light. Convert on the way in,
    otherwise the swatch drifts lighter than the hex it is supposed to show.
    """
    rgb = _rgb_from_hex(self.hex_value)
    if rgb:
        linear = color_math.srgb_to_linear(rgb)
        # Prevent recursive update
        if (abs(self.color[0] - linear[0]) > 0.002
                or abs(self.color[1] - linear[1]) > 0.002
                or abs(self.color[2] - linear[2]) > 0.002):
            self.color = linear
    _maybe_live_apply(context)


def _on_palette_color_update(self, context):
    """When color swatch is edited, update the hex field and apply live."""
    new_hex = _hex_from_rgb(*color_math.linear_to_srgb(self.color))
    if self.hex_value != new_hex:
        self.hex_value = new_hex
    _maybe_live_apply(context)


def _on_palette_slot_enabled_update(self, context):
    """Quick Adjust checkbox: live-apply (the base colour is untouched)."""
    _maybe_live_apply(context)


def _on_quick_adjust_update(self, context):
    """Quick Adjust sliders: live-apply (debounced)."""
    _maybe_live_apply(context)


class PALETTE_STUDIO_PaletteColor(PropertyGroup):
    """A single editable color in the palette."""
    slot_id: StringProperty(name="Slot ID")
    label: StringProperty(name="Label")
    color: FloatVectorProperty(
        name="Color",
        subtype='COLOR',
        size=3,
        min=0.0, max=1.0,
        default=(0.5, 0.5, 0.5),
        update=_on_palette_color_update,
    )
    hex_value: StringProperty(
        name="Hex",
        default="#808080",
        maxlen=7,
        update=_on_palette_hex_update,
    )
    # Quick Adjust skips unchecked ANSI slots; their swatch stays editable.
    enabled: BoolProperty(
        name="Enabled",
        description="Include this ANSI slot in the Quick Adjust sliders",
        default=True,
        update=_on_palette_slot_enabled_update,
    )
    # Store original color for reset
    orig_r: bpy.props.FloatProperty(default=0.5)
    orig_g: bpy.props.FloatProperty(default=0.5)
    orig_b: bpy.props.FloatProperty(default=0.5)


# =========================================================================
# Helpers
# =========================================================================

def _populate_palette_from_theme(wm, palette_theme):
    """Fill the editable palette collection from a parsed iTerm theme."""
    # Cleared first: the live-apply callbacks stay inert while the collection
    # is being rebuilt (see _maybe_live_apply).
    wm.palette_studio_palette_loaded = False
    wm.palette_studio_palette.clear()

    ansi = palette_theme.get("ansi", [])

    for slot_id, label in PALETTE_SLOTS:
        item = wm.palette_studio_palette.add()
        item.slot_id = slot_id
        item.label = label

        # Determine the color for this slot
        if slot_id.startswith("ansi_"):
            idx = int(slot_id.split("_")[1])
            if idx < len(ansi) and ansi[idx]:
                c = ansi[idx]
            else:
                c = (0.5, 0.5, 0.5)
        else:
            c = palette_theme.get(slot_id)
            if c is None:
                # Use sensible defaults for missing extras
                if slot_id == "bg":
                    c = ansi[0] if ansi[0] else (0.1, 0.1, 0.1)
                elif slot_id == "fg":
                    c = ansi[7] if ansi[7] else (0.9, 0.9, 0.9)
                elif slot_id == "cursor":
                    c = ansi[4] if ansi[4] else (0.5, 0.5, 1.0)
                elif slot_id == "selection":
                    c = (0.3, 0.3, 0.5)
                else:
                    c = (0.5, 0.5, 0.5)

        # ``color`` is a subtype='COLOR' property, so Blender holds it in
        # linear light; the parsed theme and ``hex_value`` are sRGB. Convert on
        # the way in or the swatch renders lighter than the hex code.
        linear = color_math.srgb_to_linear(c[:3])
        item.color = linear
        item.hex_value = _hex_from_rgb(*c[:3])
        item.orig_r = linear[0]
        item.orig_g = linear[1]
        item.orig_b = linear[2]
        item.enabled = True

    # Quick Adjust starts neutral for every newly loaded palette.
    wm.palette_quick_hue = 0.5
    wm.palette_quick_sat = 1.0
    wm.palette_quick_val = 1.0
    wm.palette_quick_alpha = 1.0

    wm.palette_studio_palette_loaded = True
    wm.palette_studio_palette_theme_name = palette_theme.get("name", "Unknown")


# Finetune palette colours: (theme key consumed by build_palette, preference).
_FINETUNE_COLOR_PROPS = (
    ("playhead_color", "finetune_playhead"),
    ("keyframe_selected_color", "finetune_keyframe_selected"),
    ("axis_x_color", "finetune_axis_x"),
    ("axis_y_color", "finetune_axis_y"),
    ("axis_z_color", "finetune_axis_z"),
    ("object_selected_color", "finetune_object_selected"),
    ("object_active_color", "finetune_active_object"),
)


def _slot_color(theme, slot_id):
    """Resolve a palette slot id ("ansi_3", "selection", …) to RGB in a
    normalized theme dict. Returns None when the slot is missing/empty.

    A slot carrying Quick Adjust alpha comes back as RGBA, so an accent or
    Finetune pick pointing at it inherits that alpha.
    """
    if not slot_id:
        return None
    if slot_id.startswith("ansi_"):
        try:
            idx = int(slot_id.split("_", 1)[1])
        except (ValueError, IndexError):
            return None
        ansi = theme.get("ansi") or []
        if 0 <= idx < len(ansi) and ansi[idx]:
            color = ansi[idx]
            return tuple(color[:4]) if len(color) > 3 else tuple(color[:3])
        return None
    color = theme.get(slot_id)
    if color:
        return tuple(color[:4]) if len(color) > 3 else tuple(color[:3])
    return None


def _palette_slot_enabled(wm, slot_id):
    """Quick Adjust checkbox state for one slot (missing slot = excluded)."""
    try:
        for item in wm.palette_studio_palette:
            if item.slot_id == slot_id:
                return bool(item.enabled)
    except Exception:
        pass
    return False


def _apply_quick_adjust(theme, wm):
    """Apply the Palette Editor's Quick Adjust sliders to ANSI 0-15.

    Hue is a position on the hue circle, exactly like Blender's own hue slider:
    0.5 is neutral and 0/1 wrap around. Saturation and value are multipliers
    where 1.0 is neutral. Alpha is written as the slot's alpha. Only checked
    slots are touched, and every value is recomputed from the slot's untouched
    base colour, so the sliders are non-destructive: at their defaults this
    returns the theme unchanged and the palette is byte-identical to a plain
    apply. bg/fg/cursor/selection are never touched.

    Alpha is only added to a tuple when it is actually below 1, so the default
    path keeps the plain RGB values the rest of the pipeline expects.
    """
    try:
        hue = float(wm.palette_quick_hue)
        sat = float(wm.palette_quick_sat)
        val = float(wm.palette_quick_val)
        alpha = float(wm.palette_quick_alpha)
    except (AttributeError, TypeError):
        return theme

    hue_shift = hue - 0.5
    neutral = (abs(hue_shift) < 1e-9
               and abs(sat - 1.0) < 1e-9
               and abs(val - 1.0) < 1e-9)
    alpha_on = abs(alpha - 1.0) > 1e-6
    if neutral and not alpha_on:
        return theme

    ansi = list(theme.get("ansi") or ())
    for i in range(min(16, len(ansi))):
        color = ansi[i]
        if not color:
            continue
        if not _palette_slot_enabled(wm, "ansi_%d" % i):
            continue

        r, g, b = color[:3]
        if not neutral:
            h, s, v = colorsys.rgb_to_hsv(r, g, b)
            h = (h + hue_shift) % 1.0
            s = min(1.0, max(0.0, s * sat))
            v = min(1.0, max(0.0, v * val))
            r, g, b = colorsys.hsv_to_rgb(h, s, v)

        ansi[i] = (r, g, b, alpha) if alpha_on else (r, g, b)

    theme["ansi"] = ansi
    return theme


def _apply_accent_overrides(theme, addon_prefs, reset_axes=True):
    """Copy the user's colour choices into a normalized theme dict.

    Covers the three accent roles, the three Outline roles, the Background 1/2
    surface overrides and the Finetune palette colours (Playhead, Axis X/Y/Z).
    The dropdown roles pick *which palette slot* supplies the colour, so they
    are resolved against whatever theme is being applied; the two background
    roles carry a literal colour instead. Missing slots are left for
    build_palette() to fall back on.

    When ``reset_axes`` is set (any palette/theme apply), the axis dropdowns are
    written back to their ANSI defaults first — an axis pick is a per-palette
    tweak. Doing it here, before build_palette() runs, keeps the dropdown and the
    applied theme in sync. Live Finetune tweaks pass reset_axes=False.
    """
    if addon_prefs is None:
        return theme
    if reset_axes:
        try:
            from . import prefs as _prefs_mod
            _prefs_mod.reset_axis_colors(addon_prefs)
        except Exception:
            pass
    for role in ("accent_primary", "accent_secondary", "accent_tertiary",
                 "outline_color", "outline_color_2", "outline_color_3"):
        color = _slot_color(theme, getattr(addon_prefs, role, None))
        if color:
            theme[role] = color
    # Background 1 / 2 are direct colour overrides (Finetune toggle + swatch)
    # rather than slot picks. Their properties hold LINEAR light while the theme
    # dict and apply.py work in sRGB. Nothing is written while a toggle is off,
    # so color_roles.SLOT_CHAINS supplies the palette background instead
    # (Background 2 falls back to Background 1, then to the background).
    try:
        from . import prefs as _prefs_mod
        for role in ("bg_primary", "bg_secondary"):
            if not getattr(addon_prefs, "finetune_%s_custom" % role, False):
                continue
            rgba = getattr(_prefs_mod, "_effective_%s" % role)(addon_prefs)
            theme[role] = (*color_math.linear_to_srgb(rgba[:3]), rgba[3])
    except Exception:
        pass
    # Finetune colours may point at an accent role, so this runs after the
    # accent loop above has filled them in.
    for key, prop in _FINETUNE_COLOR_PROPS:
        color = _slot_color(theme, getattr(addon_prefs, prop, None))
        if color:
            theme[key] = color
    return theme


def _build_theme_from_palette(wm, addon_prefs=None, reset_axes=True):
    """Reconstruct an iTerm theme dict from the editable palette."""
    theme = {
        "name": wm.palette_studio_palette_theme_name,
        "ansi": [],
    }

    # Build a lookup. ``item.color`` is linear light (COLOR subtype), the
    # theme dict expects sRGB.
    palette_map = {}
    for item in wm.palette_studio_palette:
        palette_map[item.slot_id] = color_math.linear_to_srgb(item.color)

    # ANSI 0-15
    for i in range(16):
        key = f"ansi_{i}"
        theme["ansi"].append(palette_map.get(key, (0.5, 0.5, 0.5)))

    # Named
    theme["bg"] = palette_map.get("bg", theme["ansi"][0])
    theme["fg"] = palette_map.get("fg", theme["ansi"][7])
    theme["cursor"] = palette_map.get("cursor")
    theme["selection"] = palette_map.get("selection")

    # Set extras to None that we don't expose
    theme["cursor_text"] = None
    theme["selected_text"] = None
    theme["bold"] = None

    # Quick Adjust rewrites the ANSI colours; the accent roles and Finetune
    # picks resolve afterwards so they follow the adjusted values.
    theme = _apply_quick_adjust(theme, wm)

    return _apply_accent_overrides(theme, addon_prefs, reset_axes)


# =========================================================================
# Operators
# =========================================================================

class PALETTE_STUDIO_OT_refresh_repo(Operator):
    """Refresh the theme list from local folder or remote repositories"""
    bl_idname = "palette_studio.refresh_repo"
    bl_label = "Refresh Theme List"
    bl_options = {'REGISTER'}

    def execute(self, context):
        from . import repo

        addon_prefs = context.preferences.addons[__package__].preferences
        wm = context.window_manager

        try:
            if addon_prefs.source_mode == 'LOCAL':
                folder = bpy.path.abspath(addon_prefs.local_folder)
                if not folder or not os.path.isdir(folder):
                    self.report({'ERROR'}, f"Invalid folder: {folder}")
                    return {'CANCELLED'}
                index = repo.index_local_folder(folder)
            else:
                # Respect Blender's online access setting (required for extensions platform)
                if not bpy.app.online_access:
                    self.report({'ERROR'},
                        "Online access is disabled. Enable in Preferences > System > Network.")
                    return {'CANCELLED'}

                enabled = addon_prefs.get_enabled_sources()
                if not enabled:
                    self.report({'ERROR'}, "No sources enabled. Check add-on preferences.")
                    return {'CANCELLED'}
                index = repo.download_sources(
                    enabled_sources=enabled,
                    progress_callback=lambda msg: self.report({'INFO'}, msg)
                )

            addon_prefs.themes_loaded = True
            count = _populate_theme_list(wm, index.get("themes", []))
            self.report({'INFO'}, f"Found {count} themes")

        except Exception as e:
            self.report({'ERROR'}, f"Failed to refresh: {e}")
            traceback.print_exc()
            return {'CANCELLED'}

        return {'FINISHED'}


class PALETTE_STUDIO_OT_unload_themes(Operator):
    """Unload the theme list and delete downloaded theme files"""
    bl_idname = "palette_studio.unload_themes"
    bl_label = "Unload"
    bl_options = {'REGISTER'}

    def execute(self, context):
        addon_prefs = context.preferences.addons[__package__].preferences
        wm = context.window_manager

        # Flag first so the search/sort callbacks don't repopulate the list
        # from an index we are about to delete.
        addon_prefs.themes_loaded = False

        removed = 0
        if addon_prefs.source_mode == 'REMOTE':
            removed = repo.clear_cache()

        wm.palette_studio_theme_search = ""
        wm.palette_studio_themes.clear()
        wm.palette_studio_theme_active = 0
        wm.palette_studio_theme_count = 0

        if removed:
            self.report({'INFO'}, "Themes unloaded and downloads deleted")
        else:
            self.report({'INFO'}, "Themes unloaded")
        return {'FINISHED'}


class PALETTE_STUDIO_OT_load_palette(Operator):
    """Load the selected theme into the palette editor for customization"""
    bl_idname = "palette_studio.load_palette"
    bl_label = "Load into Editor"
    bl_options = {'REGISTER'}

    def execute(self, context):
        from . import iterm_parser

        wm = context.window_manager
        idx = wm.palette_studio_theme_active
        if idx < 0 or idx >= len(wm.palette_studio_themes):
            self.report({'ERROR'}, "No theme selected")
            return {'CANCELLED'}

        theme_item = wm.palette_studio_themes[idx]

        try:
            palette_theme = iterm_parser.parse_theme_file(
                theme_item.path, theme_item.variant)
            _populate_palette_from_theme(wm, palette_theme)
            self.report({'INFO'}, f"Loaded palette: {theme_item.name}")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to load: {e}")
            traceback.print_exc()
            return {'CANCELLED'}

        return {'FINISHED'}


def _theme_preset_path(name):
    """Path of an existing saved theme preset with this name, else None.

    Blender stores interface-theme presets as .xml under presets/interface_theme;
    match by display name so names containing spaces resolve correctly.
    """
    name = (name or "").strip()
    if not name:
        return None
    try:
        return bpy.utils.preset_find(
            name, "interface_theme", display_name=True, ext=".xml") or None
    except Exception:
        return None


class PALETTE_STUDIO_OT_save_theme(Operator):
    """Save the customized palette as a new user theme"""
    bl_idname = "palette_studio.save_theme"
    bl_label = "Save as New Theme"
    bl_options = {'REGISTER'}

    theme_name: StringProperty(
        name="Theme Name",
        description="Name for the new custom theme",
        default="",
    )
    # Set by the follow-up invocation that shows the overwrite confirmation.
    confirm_flow: BoolProperty(default=False, options={'SKIP_SAVE'})

    def draw(self, context):
        layout = self.layout
        layout.label(text="Save Palette Preset", icon='FILE_TICK')
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.prop(self, "theme_name", text="Name")
        if not self.confirm_flow and _theme_preset_path(self.theme_name):
            box = layout.box()
            box.label(text="This preset name already exists.", icon='ERROR')
            box.label(text="Continue to confirm overwrite.")

    def invoke(self, context, event):
        if self.confirm_flow:
            name = self.theme_name.strip()
            return context.window_manager.invoke_confirm(
                self, event,
                title="Overwrite Theme?",
                message=f'A theme named "{name}" already exists. Overwrite it?',
                confirm_text="Overwrite",
                icon='ERROR',
            )

        wm = context.window_manager
        if wm.palette_studio_palette_loaded and wm.palette_studio_palette_theme_name:
            self.theme_name = wm.palette_studio_palette_theme_name
        else:
            self.theme_name = "Custom Theme"

        existing = _theme_preset_path(self.theme_name)
        return context.window_manager.invoke_props_dialog(
            self, confirm_text="Overwrite" if existing else "Save")

    def execute(self, context):
        from . import blender_theme_map, apply

        wm = context.window_manager

        if not wm.palette_studio_palette_loaded or len(wm.palette_studio_palette) == 0:
            self.report({'ERROR'}, "No palette loaded. Load a theme first.")
            return {'CANCELLED'}

        name = self.theme_name.strip()
        if not name:
            self.report({'ERROR'}, "Enter a theme name")
            return {'CANCELLED'}

        existing_path = _theme_preset_path(name)

        # First pass with a name clash: ask before touching the saved theme.
        if existing_path and not self.confirm_flow:
            bpy.ops.palette_studio.save_theme(
                'INVOKE_DEFAULT', confirm_flow=True, theme_name=name)
            return {'FINISHED'}

        try:
            palette_theme = _build_theme_from_palette(
                wm, context.preferences.addons[__package__].preferences)
            palette = blender_theme_map.build_palette(palette_theme)
            apply.apply_theme_to_blender(palette)

            if existing_path:
                # preset_add appends .001 instead of replacing, so clear the
                # old file first. A built-in/read-only preset can't be removed
                # and will simply be shadowed by the new user preset.
                try:
                    os.remove(existing_path)
                except OSError:
                    pass

            ret = bpy.ops.wm.interface_theme_preset_add(name=name)
            if ret == {'CANCELLED'}:
                self.report({'ERROR'}, f"Could not save theme \"{name}\"")
                return {'CANCELLED'}

            if existing_path:
                self.report({'INFO'}, f"Overwrote custom theme: {name}")
            else:
                self.report({'INFO'}, f"Saved custom theme: {name}")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to save theme: {e}")
            traceback.print_exc()
            return {'CANCELLED'}

        return {'FINISHED'}


class PALETTE_STUDIO_OT_reset_palette(Operator):
    """Reset all palette colors to the original theme values"""
    bl_idname = "palette_studio.reset_palette"
    bl_label = "Reset to Original"
    bl_options = {'REGISTER'}

    def execute(self, context):
        wm = context.window_manager
        for item in wm.palette_studio_palette:
            item.color = (item.orig_r, item.orig_g, item.orig_b)
            item.hex_value = _hex_from_rgb(
                *color_math.linear_to_srgb((item.orig_r, item.orig_g, item.orig_b))
            )
            item.enabled = True

        # Quick Adjust back to neutral. These writes queue one debounced live
        # re-apply (see _maybe_live_apply), which is what makes the reset
        # visible now that there is no Apply button.
        wm.palette_quick_hue = 0.5
        wm.palette_quick_sat = 1.0
        wm.palette_quick_val = 1.0
        wm.palette_quick_alpha = 1.0

        # The interface scale goes back to the value Blender had on load.
        prefs.restore_ui_scale_default()

        self.report({'INFO'}, "Palette reset to original")
        return {'FINISHED'}


class PALETTE_STUDIO_OT_search_themes(Operator):
    """Filter the theme list by search term"""
    bl_idname = "palette_studio.search"
    bl_label = "Search Themes"
    bl_options = {'REGISTER'}

    def execute(self, context):
        from . import repo, prefs

        wm = context.window_manager
        query = wm.palette_studio_theme_search

        all_themes = repo.get_theme_list()
        filtered = repo.search_themes(query, all_themes)
        filtered = _sort_themes(
            filtered, _sort_mode_for(context),
            prefs.get_favorite_paths(),
        )

        _populate_theme_list(wm, filtered, _sort_mode_for(context))
        return {'FINISHED'}


class PALETTE_STUDIO_OT_preview_swatches(Operator):
    """Show color swatches for the selected theme"""
    bl_idname = "palette_studio.preview"
    bl_label = "Preview Theme Colors"
    bl_options = {'REGISTER'}

    def execute(self, context):
        from . import iterm_parser, blender_theme_map

        wm = context.window_manager
        idx = wm.palette_studio_theme_active
        if idx < 0 or idx >= len(wm.palette_studio_themes):
            self.report({'ERROR'}, "No theme selected")
            return {'CANCELLED'}

        theme_item = wm.palette_studio_themes[idx]

        try:
            palette_theme = iterm_parser.parse_theme_file(
                theme_item.path, theme_item.variant)
            _apply_accent_overrides(palette_theme, context.preferences.addons[__package__].preferences)
            palette = blender_theme_map.build_palette(palette_theme)
            summary = blender_theme_map.palette_summary(palette)
            print(f"\n=== Theme: {theme_item.name} ===")
            print(f"  Dark theme: {palette['dark']}")
            print("  ANSI Colors:")
            for i, c in enumerate(palette['ansi']):
                hexc = "#{:02x}{:02x}{:02x}".format(
                    int(c[0]*255), int(c[1]*255), int(c[2]*255)
                )
                print(f"    [{i:2d}] {hexc}")
            print("  Derived palette:")
            print(summary)
            self.report({'INFO'}, f"Preview printed to console for: {theme_item.name}")
        except Exception as e:
            self.report({'ERROR'}, f"Preview failed: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}


# =========================================================================

class PALETTE_STUDIO_OT_sync_noctalia(Operator):
    """Load the color scheme Noctalia is using right now"""

    bl_idname = "palette_studio.sync_noctalia"
    bl_label = "Sync Current Theme"
    bl_options = {'REGISTER'}

    def execute(self, context):
        from . import repo, iterm_parser, blender_theme_map, apply

        found = repo.noctalia_sync_source()
        if not found:
            self.report(
                {'WARNING'},
                "No Noctalia theme found (is Noctalia installed?)")
            return {'CANCELLED'}

        kind, payload = found
        try:
            if kind == "kitty":
                # The terminal theme Noctalia rewrites on every palette change.
                # Plain kitty syntax, and the only source that also reflects
                # wallpaper-generated palettes.
                palette_theme = iterm_parser.parse_theme_file(payload)
                palette_theme["name"] = "Noctalia"
            else:
                name, variant, path = payload
                palette_theme = iterm_parser.parse_theme_file(path, variant)
                palette_theme["name"] = "%s (%s)" % (name, variant.capitalize())
            addon_prefs = context.preferences.addons[__package__].preferences
            _apply_accent_overrides(palette_theme, addon_prefs)
            palette = blender_theme_map.build_palette(palette_theme)
            apply.apply_theme_to_blender(palette)
            # Same order as picking a theme in the browser: apply first, then
            # refill the Palette Editor so both show the same colours.
            _populate_palette_from_theme(context.window_manager, palette_theme)
        except Exception as e:  # noqa: BLE001 - report anything, never crash
            self.report({'ERROR'}, f"Sync failed: {e}")
            return {'CANCELLED'}

        self.report({'INFO'}, f"Synced Noctalia theme ({kind})")
        return {'FINISHED'}


class PALETTE_STUDIO_OT_toggle_favourite(Operator):
    """Toggle the selected palette's persistent favourite state."""
    bl_idname = "palette_studio.toggle_favourite"
    bl_label = "Toggle Favourite"
    bl_options = {'REGISTER'}

    def execute(self, context):
        wm = context.window_manager
        index = wm.palette_studio_theme_active
        if index < 0 or index >= len(wm.palette_studio_themes):
            self.report({'WARNING'}, "No theme selected")
            return {'CANCELLED'}

        selected_path = wm.palette_studio_themes[index].path
        from . import prefs as prefs_module
        prefs = context.preferences.addons[__package__].preferences
        favorite_paths = prefs_module.get_favorite_paths()
        if selected_path in favorite_paths:
            favorite_paths.remove(selected_path)
            message = "Removed from favourites"
        else:
            favorite_paths.add(selected_path)
            message = "Added to favourites"
        prefs.favorite_theme_paths = json.dumps(sorted(favorite_paths))

        # Rebuild the current filtered/sorted list, then keep the same theme
        # selected even if its position moved in Favourites First mode.
        _on_theme_search_update(self, context)
        for i, item in enumerate(wm.palette_studio_themes):
            if item.path == selected_path:
                wm.palette_studio_theme_active = i
                break

        self.report({'INFO'}, f"{message}: {wm.palette_studio_themes[wm.palette_studio_theme_active].name}")
        return {'FINISHED'}


class PALETTE_STUDIO_UL_theme_list(UIList):
    bl_idname = "PALETTE_STUDIO_UL_theme_list"

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        if self.layout_type == 'GRID':
            layout.label(text="", icon='COLOR')
            return
        # Keep names readable at sidebar widths. Full source metadata lives
        # in the selected-palette card rather than competing with every name.
        split = layout.split(factor=0.80)
        split.label(text=item.name, icon='SOLO_ON' if item.favorite else 'COLOR')
        tag = split.row()
        tag.alignment = 'RIGHT'
        tag.enabled = False
        tag.label(text="Dark" if item.dark else "Light")


# =========================================================================
# Panels
# =========================================================================

class PALETTE_STUDIO_PT_sidebar(Panel):
    bl_idname = "PALETTE_STUDIO_PT_sidebar"
    bl_label = "Palette Studio"
    bl_category = "Palette Studio"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    def draw(self, context):
        layout = self.layout
        addon_prefs = context.preferences.addons[__package__].preferences

        # Both surfaces expose the same task pages and all native preset actions.
        prefs.draw_sections(layout, addon_prefs, context)






# =========================================================================
# Registration
# =========================================================================

classes = (
    PALETTE_STUDIO_ThemeItem,
    PALETTE_STUDIO_PaletteColor,
    PALETTE_STUDIO_OT_refresh_repo,
    PALETTE_STUDIO_OT_unload_themes,
    PALETTE_STUDIO_OT_load_palette,
    PALETTE_STUDIO_OT_save_theme,
    PALETTE_STUDIO_OT_reset_palette,
    PALETTE_STUDIO_OT_search_themes,
    PALETTE_STUDIO_OT_preview_swatches,
    PALETTE_STUDIO_OT_sync_noctalia,
    PALETTE_STUDIO_OT_toggle_favourite,
    PALETTE_STUDIO_UL_theme_list,
    PALETTE_STUDIO_PT_sidebar,
)


def _current_addon_prefs():
    """The live preferences instance for this add-on, if Blender has one."""
    try:
        addon = bpy.context.preferences.addons.get(__package__)
    except Exception:
        return None
    return getattr(addon, "preferences", None) if addon is not None else None


def _registered_class_matches(existing, cls):
    """True when an already-registered class exposes every property ours does."""
    annotations = getattr(cls, "__annotations__", None)
    if not annotations:
        return False
    try:
        props = existing.bl_rna.properties
    except Exception:
        return False
    for name in annotations:
        try:
            if name not in props:
                return False
        except Exception:
            return False
    return True


def _snapshot_settings(cls):
    """Copy the current values of cls' properties off the live instance."""
    instance = _current_addon_prefs()
    if instance is None:
        return {}
    saved = {}
    for name in getattr(cls, "__annotations__", None) or {}:
        try:
            saved[name] = getattr(instance, name)
        except Exception:
            pass
    return saved


def _restore_settings(saved):
    """Write a snapshot back onto the live preferences instance."""
    if not saved:
        return
    instance = _current_addon_prefs()
    if instance is None:
        return
    for name, value in saved.items():
        try:
            setattr(instance, name, value)
        except Exception:
            pass


def _register_class(cls):
    """Register a bpy class, coping with one that is already registered.

    Blender may already have a class of this name registered - its own
    extension-preference registration, or an in-place module reload. If that
    class already defines every property ours does it is left untouched: it
    holds the user's saved settings, and re-registering (what 0.5.1 did) throws
    them away. Only an older/short definition is replaced, and its values are
    snapshotted and written back afterwards. Re-registering the
    AddonPreferences class is what made every Finetune setting reset.
    """
    stale = getattr(bpy.types, cls.__name__, None)

    if stale is not None and _registered_class_matches(stale, cls):
        return

    saved = _snapshot_settings(cls) if stale is not None else {}

    if stale is not None:
        _unregister_class(stale)

    try:
        bpy.utils.register_class(cls)
    except ValueError:
        # Identifier held by a class we cannot see on bpy.types.
        _unregister_class(cls)
        for sub in list(bpy.types.AddonPreferences.__subclasses__()):
            if sub.__name__ == cls.__name__:
                _unregister_class(sub)
        bpy.utils.register_class(cls)

    _restore_settings(saved)


def _unregister_class(cls):
    """Unregister a class, tolerating one that is no longer registered."""
    try:
        bpy.utils.unregister_class(cls)
    except Exception:
        pass


def _on_theme_active_update(self, context):
    """Apply the theme as soon as the list selection changes.

    Selecting a theme in the Palette Browser is the apply action: the browser
    has no Apply button, only Reset. The Palette Editor is refilled from the
    same parsed theme so the slots always match what was just applied.
    Nothing is written to disk here - the live theme
    (`preferences.themes[0]`) is mutated in memory until the user saves
    preferences or stores a preset.
    """
    try:
        addon_prefs = context.preferences.addons[__package__].preferences
    except (KeyError, AttributeError):
        return

    wm = context.window_manager

    idx = wm.palette_studio_theme_active
    if idx < 0 or idx >= len(wm.palette_studio_themes):
        return

    theme_item = wm.palette_studio_themes[idx]

    try:
        from . import iterm_parser, blender_theme_map, apply

        palette_theme = iterm_parser.parse_theme_file(
            theme_item.path, theme_item.variant)
        _apply_accent_overrides(palette_theme, addon_prefs)
        palette = blender_theme_map.build_palette(palette_theme)
        apply.apply_theme_to_blender(palette)
        # Keep the Palette Editor in step with what was just applied. Safe to
        # call from here: the populate clears the loaded flag first, so the
        # per-slot update callbacks it fires cannot queue another apply.
        _populate_palette_from_theme(wm, palette_theme)
        # Persist the stable identity, not the list index: sorting and source
        # filters can move a palette between sessions.
        addon_prefs.last_selected_theme_path = theme_item.path
        addon_prefs.last_selected_theme_variant = theme_item.variant
        # No XML export, no save - the selection itself is the apply.
    except Exception:
        pass  # Silently skip broken themes during browsing


def _on_theme_search_update(self, context):
    """Live-filter the theme list as the user types."""
    from . import repo

    wm = context.window_manager

    try:
        addon_prefs = context.preferences.addons[__package__].preferences
        loaded = addon_prefs.themes_loaded
    except (KeyError, AttributeError):
        loaded = True

    if not loaded:
        # Unloaded: keep the list empty instead of reloading from disk.
        wm.palette_studio_themes.clear()
        wm.palette_studio_theme_count = 0
        return

    query = wm.palette_studio_theme_search

    all_themes = repo.get_theme_list()
    filtered = repo.search_themes(query, all_themes)
    _populate_theme_list(wm, filtered)


def _on_theme_sort_update(self, context):
    """Re-sort the current list when sort mode changes."""
    _on_theme_search_update(self, context)


def _sort_themes(themes, sort_mode, favorite_paths=None):
    """Sort theme list based on the selected mode."""
    favorite_paths = favorite_paths or set()
    if sort_mode == 'FAVOURITES':
        return sorted(
            themes,
            key=lambda t: (t.get("path", "") not in favorite_paths, t["name"].lower()),
        )
    if sort_mode == 'POPULAR':
        from .popular import POPULAR_THEMES
        def _pop_rank(name):
            name_lower = name.lower()
            for i, pop in enumerate(POPULAR_THEMES):
                if pop in name_lower:
                    return i
            return len(POPULAR_THEMES)  # non-popular goes after all popular
        # Popular themes ranked by their position in the curated list,
        # non-popular themes alphabetically after
        return sorted(themes, key=lambda t: (_pop_rank(t["name"]), t["name"].lower()))
    elif sort_mode == 'AZ':
        return sorted(themes, key=lambda t: t["name"].lower())
    elif sort_mode == 'ZA':
        return sorted(themes, key=lambda t: t["name"].lower(), reverse=True)
    return themes


def _sort_mode_for(context=None):
    """Current sort mode from the persisted add-on preferences."""
    try:
        src = context if context is not None else bpy.context
        return src.preferences.addons[__package__].preferences.theme_sort
    except Exception:
        return 'POPULAR'


def _filter_mode_for(context=None):
    """Current dark/light filter from the persisted add-on preferences."""
    try:
        src = context if context is not None else bpy.context
        return src.preferences.addons[__package__].preferences.theme_filter
    except Exception:
        return 'ALL'


def _source_filter_for(context=None):
    """Enabled remote source keys, or None when source filtering is off.

    Returns None in LOCAL mode (a single 'local' source) or when the
    preferences are unavailable, so the caller can skip filtering.
    """
    try:
        src = context if context is not None else bpy.context
        prefs = src.preferences.addons[__package__].preferences
    except Exception:
        return None
    if prefs.source_mode != 'REMOTE':
        return None
    return set(prefs.get_enabled_sources())


def _filter_by_sources(themes, context=None):
    """Hide themes whose remote source is currently disabled in preferences.

    Purely a visibility filter: disabling a source never rewrites the index,
    so re-enabling it shows the already-cached themes again instantly.
    """
    enabled = _source_filter_for(context)
    if enabled is None:
        return themes
    return [t for t in themes if t.get("source") in enabled]


def _filter_themes(themes, filter_mode):
    """Keep only themes matching the dark/light filter."""
    if filter_mode == 'DARK':
        return [t for t in themes if t.get("dark", True)]
    if filter_mode == 'LIGHT':
        return [t for t in themes if not t.get("dark", True)]
    return themes


def _populate_theme_list(wm, themes_list, sort_mode=None, filter_mode=None):
    """Replace the visible theme list with themes_list (filtered, sorted)."""
    if sort_mode is None:
        sort_mode = _sort_mode_for()
    if filter_mode is None:
        filter_mode = _filter_mode_for()

    last_path = ""
    last_variant = ""
    try:
        from . import prefs as _prefs
        favorite_paths = _prefs.get_favorite_paths()
        addon_prefs = bpy.context.preferences.addons[__package__].preferences
        last_path = addon_prefs.last_selected_theme_path
        last_variant = addon_prefs.last_selected_theme_variant
    except Exception:
        favorite_paths = set()

    themes_list = _filter_by_sources(themes_list)
    themes_list = _filter_themes(themes_list, filter_mode)
    themes_list = _sort_themes(themes_list, sort_mode, favorite_paths)

    wm.palette_studio_themes.clear()
    for t in themes_list:
        item = wm.palette_studio_themes.add()
        item.name = t["name"]
        item.path = t["path"]
        item.source = t.get("source", "")
        item.favorite = t.get("path", "") in favorite_paths
        item.dark = bool(t.get("dark", True))
        item.variant = t.get("variant", "")

    wm.palette_studio_theme_count = len(wm.palette_studio_themes)

    # Restore by path/variant rather than index. Force a -1 -> index transition
    # so the update callback reapplies the remembered palette after a restart,
    # even when it happens to sort into position zero.
    if last_path:
        restored_index = next(
            (i for i, item in enumerate(wm.palette_studio_themes)
             if item.path == last_path and item.variant == last_variant),
            -1,
        )
        if restored_index >= 0:
            wm.palette_studio_theme_active = -1
            wm.palette_studio_theme_active = restored_index

    return wm.palette_studio_theme_count


_ensuring_theme_list = False


def _ensure_theme_list(context):
    """Restore a previously loaded theme list from the saved index.

    Runs lazily on the first panel draw of each window, so a restart no
    longer needs a manual "Load Themes". Cheap when the list is already
    populated. Never touches the network.
    """
    global _ensuring_theme_list

    wm = getattr(context, "window_manager", None)
    if wm is None or len(wm.palette_studio_themes) > 0 or _ensuring_theme_list:
        return

    try:
        addon_prefs = context.preferences.addons[__package__].preferences
    except (KeyError, AttributeError):
        return

    if not addon_prefs.themes_loaded:
        # Fall back to an existing cache when preferences were not saved
        # on quit. Unload removes the index, so this stays consistent.
        if addon_prefs.source_mode != 'REMOTE' or not repo.has_index():
            return

    _ensuring_theme_list = True
    try:
        repo.ensure_index_flags()
        themes = repo.get_theme_list()
        if not themes:
            addon_prefs.themes_loaded = False
            return

        # Restored from cache: mark as loaded so the browser switches out of
        # its first-run state even when preferences were not saved on quit.
        addon_prefs.themes_loaded = True

        query = wm.palette_studio_theme_search
        if query:
            themes = repo.search_themes(query, themes)

        _populate_theme_list(wm, themes)
    except Exception:
        pass  # Never break drawing because of a bad cache
    finally:
        _ensuring_theme_list = False


def _migrate_legacy_preferences():
    """Copy settings from the pre-rename "Palette Custom" add-on, once.

    Carries favourites, Finetune overrides and sort/source settings across
    the palette_custom -> palette_studio rename. Runs on a fresh install
    only, guarded by the ``migrated_from_legacy`` marker so later edits are
    never overwritten.
    """
    try:
        addons = bpy.context.preferences.addons
    except Exception:
        return

    new_addon = addons.get(__package__)
    if new_addon is None:
        return
    new_prefs = getattr(new_addon, "preferences", None)
    if new_prefs is None:
        return
    if getattr(new_prefs, "migrated_from_legacy", False):
        return

    from .repo import LEGACY_PACKAGES

    for legacy in LEGACY_PACKAGES:
        old_addon = addons.get(legacy)
        if old_addon is None:
            continue
        old_prefs = getattr(old_addon, "preferences", None)
        if old_prefs is None:
            continue

        try:
            new_names = {
                p.identifier for p in new_prefs.bl_rna.properties
                if not p.is_readonly
            }
            old_names = {p.identifier for p in old_prefs.bl_rna.properties}
        except Exception:
            continue

        for name in new_names & old_names:
            if name in {"rna_type", "name"}:
                continue
            try:
                setattr(new_prefs, name, getattr(old_prefs, name))
            except Exception:
                pass

        new_prefs.migrated_from_legacy = True
        break


def register():
    from . import prefs

    for cls in classes:
        _register_class(cls)

    prefs.register()

    _migrate_legacy_preferences()
    try:
        from . import repo
        repo.migrate_legacy_cache()
    except Exception:
        pass

    # Theme list
    bpy.types.WindowManager.palette_studio_themes = CollectionProperty(type=PALETTE_STUDIO_ThemeItem)
    bpy.types.WindowManager.palette_studio_theme_active = IntProperty(
        default=0,
        update=_on_theme_active_update,
    )
    bpy.types.WindowManager.palette_studio_theme_search = StringProperty(
        name="Search", default="",
        description="Filter themes by name (fuzzy match)",
        update=_on_theme_search_update,
    )
    bpy.types.WindowManager.palette_studio_theme_count = IntProperty(default=0)

    # Palette editor
    bpy.types.WindowManager.palette_studio_palette = CollectionProperty(type=PALETTE_STUDIO_PaletteColor)
    bpy.types.WindowManager.palette_studio_palette_loaded = BoolProperty(default=False)
    bpy.types.WindowManager.palette_studio_palette_theme_name = StringProperty(default="")
    # Palette Editor > Quick Adjust: relative offsets applied to the checked
    # ANSI 0-15 slots on top of their (never overwritten) base colours.
    bpy.types.WindowManager.palette_quick_hue = FloatProperty(
        name="Hue",
        description="Hue position for the checked ANSI colours (like Blender's own "
                    "hue slider: 0.5 leaves them unchanged, 0/1 wrap around)",
        default=0.5, min=0.0, max=1.0,
        update=_on_quick_adjust_update,
    )
    bpy.types.WindowManager.palette_quick_sat = FloatProperty(
        name="Saturation",
        description="Saturation multiplier for the checked ANSI colours "
                    "(1.0 leaves them unchanged)",
        default=1.0, min=0.0, max=2.0,
        update=_on_quick_adjust_update,
    )
    bpy.types.WindowManager.palette_quick_val = FloatProperty(
        name="Value",
        description="Brightness multiplier for the checked ANSI colours "
                    "(1.0 leaves them unchanged)",
        default=1.0, min=0.0, max=2.0,
        update=_on_quick_adjust_update,
    )
    bpy.types.WindowManager.palette_quick_alpha = FloatProperty(
        name="Alpha",
        description="Alpha written to every checked ANSI colour",
        default=1.0, min=0.0, max=1.0,
        update=_on_quick_adjust_update,
    )


def unregister():
    from . import prefs

    # A pending debounced live-apply must not fire into a half-removed add-on.
    cancel_live_apply()

    # Tolerant removal: a previous register() may have stopped partway, so a
    # property can legitimately be missing here.
    for prop_name in (
        "palette_quick_alpha",
        "palette_quick_val",
        "palette_quick_sat",
        "palette_quick_hue",
        "palette_studio_palette_theme_name",
        "palette_studio_palette_loaded",
        "palette_studio_palette",
        "palette_studio_theme_count",
        "palette_studio_theme_search",
        "palette_studio_theme_active",
        "palette_studio_themes",
    ):
        if hasattr(bpy.types.WindowManager, prop_name):
            try:
                delattr(bpy.types.WindowManager, prop_name)
            except Exception:
                pass

    prefs.unregister()

    for cls in reversed(classes):
        _unregister_class(cls)


if __name__ == "__main__":
    register()

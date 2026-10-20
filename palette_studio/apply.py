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
Apply a generated theme palette to the live Blender session.

Comprehensive mapping covering:
- 3D Viewport gradient background
- Panel colors (back, header, sub, outline, text)
- All widget types
- Node editor node-type colors
- NLA strip colors
- Collection colors
- Bone color sets
- Topbar / Statusbar
- All editor spaces
"""

from . import color_math as cm


def _srgb_from_linear_rgba(rgba):
    """Stored linear-light RGBA (Finetune COLOR property) -> sRGB, alpha kept."""
    return (*cm.linear_to_srgb(rgba), *tuple(rgba[3:]))


def _set_color(obj, attr, color):
    """
    Safely set a color property on a Blender theme object.
    Handles RGB(3) vs RGBA(4) mismatches via try/except cascade.
    """
    if not hasattr(obj, attr):
        return

    color = tuple(float(c) for c in color)

    # Strategy 1: try as-is
    try:
        setattr(obj, attr, color)
        return
    except (TypeError, ValueError):
        pass

    # Strategy 2: if we sent 4, try 3
    if len(color) >= 4:
        try:
            setattr(obj, attr, color[:3])
            return
        except (TypeError, ValueError):
            pass

    # Strategy 3: if we sent 3, try 4
    if len(color) == 3:
        try:
            setattr(obj, attr, (*color, 1.0))
            return
        except (TypeError, ValueError):
            pass

    # Strategy 4: introspect
    try:
        current = getattr(obj, attr)
        n = len(current)
        if n == 3:
            setattr(obj, attr, color[:3])
        elif n == 4:
            setattr(obj, attr, (*color[:3], color[3] if len(color) > 3 else 1.0))
        else:
            setattr(obj, attr, color[:n])
    except Exception:
        pass


def _try_set(obj, attr, value):
    """Try to set a non-color attribute, silently skip on failure."""
    try:
        setattr(obj, attr, value)
    except (AttributeError, TypeError, ValueError):
        pass


def _rgba(color, alpha=None):
    """Palette colour -> RGBA for a theme colour field.

    Palette values are RGB, but the Palette Editor's Quick Adjust alpha
    slider makes ANSI-derived roles carry an alpha component. That value is
    honoured here; ``alpha`` is a role's own design alpha (``face_select``
    at 0.35, fully transparent panels at 0.0) and multiplies with it, so the
    intentional translucency survives instead of being overwritten. Plain
    RGB values stay fully opaque.
    """
    color = tuple(float(c) for c in color)
    base = color[3] if len(color) > 3 else 1.0
    if alpha is not None:
        base *= float(alpha)
    return (color[0], color[1], color[2], base)


def _iter_theme_structs(struct, depth=0):
    """Yield a theme struct plus every pointer-reachable child.

    Depth-limited walk so the sweep below covers UI widgets, region structs
    and every editor space on any Blender version without hard-coding names.
    """
    if depth > 3:
        return
    yield struct
    try:
        props = struct.bl_rna.properties
    except Exception:
        return
    for prop in props:
        if prop.type != 'POINTER' or prop.identifier == 'rna_type':
            continue
        try:
            child = getattr(struct, prop.identifier)
        except Exception:
            continue
        if child is None:
            continue
        try:
            child.bl_rna
        except Exception:
            continue
        for item in _iter_theme_structs(child, depth + 1):
            yield item


def override_theme_text(theme, text=None, selected=None):
    """Force every plain text (or text-selected) colour in the theme.

    ``text`` overrides fields literally named ``text`` (every editor space,
    the Channels/Scrubbing regions and all UI widget colour sets).
    ``selected`` overrides ``text_sel`` / ``text_selected``. A None argument
    leaves that group untouched. Fields such as ``text_hi``,
    ``header_text`` and ``button_text`` are deliberately not touched.
    """
    if text is None and selected is None:
        return
    for struct in _iter_theme_structs(theme):
        if text is not None:
            _set_color(struct, 'text', text)
        if selected is not None:
            _set_color(struct, 'text_sel', selected)
            _set_color(struct, 'text_selected', selected)


# Default roundness used when the add-on preferences are unavailable.
# Matches the Layered (Default) style.
ROUNDNESS_FALLBACK = 0.5


def apply_roundness(theme, value):
    """Write one roundness value to every roundness-capable theme setting.

    Covers User Interface > Styles > Panel Roundness plus the "roundness"
    field of every widget color set (wcol_*), which each expose their own
    value. Names are discovered dynamically so new widget sets in future
    Blender versions are picked up automatically.
    """
    ui = getattr(theme, 'user_interface', None)
    if ui is None:
        return
    try:
        value = max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return

    _try_set(ui, 'panel_roundness', value)

    try:
        names = [n for n in dir(ui) if n.startswith('wcol_')]
    except Exception:
        return
    for name in names:
        try:
            wcol = getattr(ui, name)
            if wcol is not None and hasattr(wcol, 'roundness'):
                _try_set(wcol, 'roundness', value)
        except Exception:
            continue


def apply_channel_text(theme, text, selected):
    """Shared live/apply channel text writer for unified 5.x and per-editor 4.5."""
    regions = getattr(theme, 'regions', None)
    channels = getattr(regions, 'channels', None)
    if channels is not None:
        _set_color(channels, 'text', text)
        _set_color(channels, 'text_selected', selected)
    else:
        for editor in ('dopesheet_editor', 'graph_editor', 'nla_editor'):
            space = getattr(getattr(theme, editor, None), 'space_list', None)
            if space is not None:
                _set_color(space, 'list_text', text)
                _set_color(space, 'list_text_hi', selected)


def _apply_widget_shading(ui):
    """Every supported style uses flat controls."""
    for name in (name for name in dir(ui) if name.startswith('wcol_')):
        widget = getattr(ui, name)
        _try_set(widget, 'show_shaded', False)
        _try_set(widget, 'shadetop', 0)
        _try_set(widget, 'shadedown', 0)


def apply_theme_to_blender(palette):
    """
    Apply the palette to Blender's active theme via the Python API.
    Returns True on success, error string on failure.

    Supports both Blender 4.x (per-editor theme settings) and 5.0+
    (unified theme settings). The version is detected at runtime.
    """
    try:
        import bpy
    except ImportError:
        return "bpy not available - not running inside Blender"

    _is_5 = bpy.app.version >= (5, 0, 0)

    theme = bpy.context.preferences.themes[0]
    p = palette

    # Finetune: 3D viewport geometry sizes (Themes > 3D Viewport > Geometry).
    _prefs = None
    try:
        _prefs = bpy.context.preferences.addons[__package__].preferences
        _sizes = {
            "edge_width": _prefs.finetune_edge_width,
            "vertex_size": _prefs.finetune_vertex_size,
            "facedot_size": _prefs.finetune_facedot_size,
            "outline_width": _prefs.finetune_outline_width,
        }
    except Exception:
        _sizes = {"edge_width": 1, "vertex_size": 3, "facedot_size": 3, "outline_width": 1}

    from .look_styles import surface_palette
    style = getattr(_prefs, 'look_style', 'LAYERED') or 'LAYERED'
    p = surface_palette(palette, style,
                        getattr(_prefs, 'finetune_bg_primary_custom', False),
                        getattr(_prefs, 'finetune_bg_secondary_custom', False))
    panel_alpha = 1.0
    sub_alpha = panel_alpha
    tabs_alpha = 0.0 if style == 'LAYERED' else 1.0
    source_bg = palette.get("theme_bg") or palette["ui_bg"]

    # Finetune > Dopesheet Texts: seed this palette's default channel text
    # colors (theme foreground + white), then use the effective values (custom
    # overrides win when enabled). The properties are COLOR subtypes, so they
    # hold linear light; theme fields take sRGB.
    if _prefs is not None:
        try:
            from . import prefs as _prefs_mod
            _prefs_mod.seed_dope_defaults(p["ui_text"], p["white"])
        except Exception:
            pass
    if _prefs is not None:
        dope_text = cm.linear_to_srgb(tuple(_prefs.finetune_dope_text))
        dope_text_sel = cm.linear_to_srgb(tuple(_prefs.finetune_dope_text_sel))
    else:
        dope_text = p["ui_text"]
        dope_text_sel = p["white"]

    # Finetune > Grid Color: seed the palette's default grid color, then
    # use the effective value (custom override wins when enabled).
    if _prefs is not None:
        try:
            from . import prefs as _prefs_mod
            _prefs_mod.seed_grid_defaults(_rgba(p["grid_line"]))
        except Exception:
            pass
    if _prefs is not None:
        grid_color = _srgb_from_linear_rgba(tuple(_prefs.finetune_grid))
    else:
        grid_color = _rgba(p["grid_line"])

    # Finetune > Text Style (Themes > User Interface > Text Style): the values
    # live in user preferences (preferences.ui_styles), not in the Theme, so
    # they are only forced when the matching Custom toggle is enabled.
    if _prefs is not None:
        try:
            from . import prefs as _prefs_mod
            _prefs_mod.seed_text_style_defaults()
            if (getattr(_prefs, "finetune_font_custom", False)
                    or getattr(_prefs, "finetune_shadow_custom", False)):
                _prefs_mod.apply_text_style(_prefs, custom_only=True)
        except Exception:
            pass

    # Finetune > Roundness: a single user value drives every roundness setting.
    roundness = getattr(_prefs, 'finetune_roundness', ROUNDNESS_FALLBACK)

    # Channel group / summary strength: stronger in dark themes so labels stay readable.
    chan_a = 0.7 if p.get("dark", True) else 0.3

    # =====================================================================
    # USER INTERFACE (global widget colors + panel colors)
    # =====================================================================
    ui = theme.user_interface
    _apply_widget_shading(ui)

    def set_wcol(wcol, outline, inner, inner_sel, item, text, text_sel):
        # outline, inner, inner_sel, item are RGBA float[4] in Blender
        _set_color(wcol, 'outline', _rgba(outline))
        _set_color(wcol, 'inner', _rgba(inner))
        _set_color(wcol, 'inner_sel', _rgba(inner_sel))
        _set_color(wcol, 'item', _rgba(item))
        _set_color(wcol, 'text', _rgba(text))
        _set_color(wcol, 'text_sel', _rgba(text_sel))

    # Regular: Inner Selected uses the Secondary palette color.
    set_wcol(ui.wcol_regular,
             _rgba(p["outline_color_3"], 0.3), p["widget_bg"], p["accent_secondary"],
             p["ui_accent_func"], p["widget_text"], p["ui_accent_func_text"])

    set_wcol(ui.wcol_tool,
             _rgba(p["outline_color_3"], 0.3), p["button_bg"], _rgba(p["accent_primary"], 0.5),
             p["ui_accent_func"], p["button_text"], p["ui_accent_func_text"])

    # Toolbar item: active state only — Inner Selected = Secondary accent;
    # Outline uses Outline 2 at 0.3 alpha.
    set_wcol(ui.wcol_toolbar_item,
             _rgba(p["outline_color_2"], 0.3), p["toolbar_bg"], p["accent_secondary"],
             p["option_check"], p["toolbar_text"], p["ui_accent_func_text"])

    # Radio buttons: active state only — Inner Selected = Tertiary accent.
    set_wcol(ui.wcol_radio,
             _rgba(p["outline_color_2"], 0.3), p["widget_bg"], p["accent_tertiary"],
             p["option_check"], p["widget_text"], p["ui_bg"])

    # Shared readable text-field selection across all look styles.
    set_wcol(ui.wcol_text,
              p["input_border"], p["input_bg"], source_bg,
              _rgba(p["accent_secondary"], 0.3), p["input_text"], p["ui_text"])

    # Checkbox / Option: active state only — Inner Selected = Primary accent;
    # Outline uses Outline 3 at 0.3 alpha.
    # Item = a glyph that stays readable on it. Outline, Inner, Text and
    # Text Selected keep the theme's own values.
    set_wcol(ui.wcol_option,
             _rgba(p["outline_color_3"], 0.3), p["widget_bg"], p["accent_primary"],
             p["accent_secondary_text"], p["widget_text"], p["ui_accent_func_text"])

    # Toggle: active state only — Inner Selected = Tertiary accent.
    # Text Selected deliberately mirrors Tab Colors > Text Selected: both take
    # the Background 1 surface role (p["ui_bg"]), so selected text reads
    # against the accent fill instead of using fg.
    set_wcol(ui.wcol_toggle,
             _rgba(p["outline_color_3"], 0.3), p["widget_bg"], p["accent_tertiary"],
             p["ui_accent_text"], p["widget_text"], p["ui_bg"])

    set_wcol(ui.wcol_num,
             p["input_border"], p["input_bg"], p["ui_selection"],
             p["ui_accent_func"], p["input_text"], p["ui_selection_text"])

    # Value Slider: Outline 3 and Secondary item color.
    set_wcol(ui.wcol_numslider,
             p["outline_color_3"], p["input_bg"], p["ui_selection"],
             p["accent_secondary"], p["input_text"], p["ui_selection_text"])

    set_wcol(ui.wcol_box,
             _rgba(p["outline_color_3"], 0.3), p["ui_card"], p["ui_selection"],
             p["ui_accent_func"], p["widget_text"], p["ui_selection_text"])

    set_wcol(ui.wcol_menu,
             _rgba(p["outline_color_3"], 0.3), p["ui_popup"], p["menu_inner_sel"],
             p["menu_accent"], p["widget_text"], p["menu_text_sel"])

    set_wcol(ui.wcol_pulldown,
             p["ui_border"], p["ui_popup"], p["menu_inner_sel"],
             p["menu_accent"], p["widget_text"], p["menu_text_sel"])

    set_wcol(ui.wcol_menu_back,
             p["ui_border"], p["ui_popup"], p["menu_inner_sel"],
             p["menu_accent"], p["widget_text"], p["menu_text_sel"])

    set_wcol(ui.wcol_menu_item,
             p["ui_border"], p["ui_popup"], p["menu_inner_sel"],
             p["menu_accent"], p["widget_text"], p["menu_text_sel"])

    set_wcol(ui.wcol_tooltip,
             p["ui_border"], p["ui_card"], p["ui_selection"],
             p["ui_accent_func"], p["widget_text"], p["ui_selection_text"])

    set_wcol(ui.wcol_scroll,
             _rgba(p["outline_color_2"], 0.3), p["scroll_bg"], p["scroll_handle_hover"],
             p["scroll_handle"], p["widget_text"], p["widget_text"])

    set_wcol(ui.wcol_progress,
             p["ui_border"], p["widget_bg"], p["ui_accent_func"],
             p["ui_accent_func"], p["widget_text"], p["ui_accent_func_text"])

    # List Item: Inner Selected uses the Tertiary palette color.
    set_wcol(ui.wcol_list_item,
             _rgba(p["outline_color_3"], 0.3), p["ui_bg"], p["accent_tertiary"],
             p["ui_accent_func"], p["widget_text"], p["ui_bg"])

    # Tab: active state only — Inner Selected = Primary accent.
    set_wcol(ui.wcol_tab,
             p["tab_outline"], p["tab_inactive_bg"], p["accent_primary"],
             p["ui_accent_func"], p["ui_text_muted"], p["ui_bg"])

    # wcol_pie_menu if available
    try:
        set_wcol(ui.wcol_pie_menu,
                 p["ui_border"], p["ui_popup"], p["pie_highlight"],
                 p["pie_item"], p["widget_text"], p["pie_highlight_text"])
    except AttributeError:
        pass

    # --- Panel colors (global) ---
    _set_color(ui, 'panel_back', _rgba(p["ui_panel"], panel_alpha))
    _set_color(ui, 'panel_header', _rgba(p["ui_panel_header"]))
    _set_color(ui, 'panel_sub_back', _rgba(p["ui_panel_sub"], sub_alpha))
    _set_color(ui, 'panel_outline', _rgba(p["ui_panel_outline"]))
    _set_color(ui, 'panel_text', p["panel_text"])
    _set_color(ui, 'panel_title', p["panel_title"])
    apply_roundness(theme, roundness)
    # Primary accent is subtle enough not to compete with widget outlines.
    _set_color(ui, 'editor_outline', _rgba(p["accent_primary"], 0.1))
    _set_color(ui, 'editor_border', p["editor_border"])

    # --- Axis & gizmo ---
    _set_color(ui, 'axis_x', p["gizmo_x"])
    _set_color(ui, 'axis_y', p["gizmo_y"])
    _set_color(ui, 'axis_z', p["gizmo_z"])
    _set_color(ui, 'gizmo_primary', p["ui_accent"])
    _set_color(ui, 'gizmo_secondary', p["accent_tertiary"])
    _set_color(ui, 'gizmo_a', p["ui_accent"])
    _set_color(ui, 'gizmo_b', p["accent_tertiary"])

    # --- Widget emboss ---
    # All supported looks use flat controls without emboss.
    _set_color(ui, 'widget_emboss', _rgba(p["black"], 0.0))
    _set_color(ui, 'widget_text_cursor', p["ui_cursor"])

    # --- Transparent checker ---
    _set_color(ui, 'transparent_checker_primary', p["ui_card"])
    _set_color(ui, 'transparent_checker_secondary', p["ui_panel"])
    _try_set(ui, 'transparent_checker_size', 10)

    # --- Icon alpha/saturation ---
    _try_set(ui, 'icon_alpha', 1.0)
    _try_set(ui, 'icon_saturation', 1.0)
    _try_set(ui, 'icon_border_intensity', 0.0)
    # NOTE: menu_shadow_fac / menu_shadow_width are deliberately NOT written —
    # Palette Studio does not influence panel/menu shadow strength or width.

    # --- Icon colors ---
    _set_color(ui, 'icon_scene', _rgba(p["icon_scene"]))
    _set_color(ui, 'icon_collection', _rgba(p["icon_collection"]))
    _set_color(ui, 'icon_object', _rgba(p["icon_object"]))
    _set_color(ui, 'icon_object_data', _rgba(p["icon_object_data"]))
    _set_color(ui, 'icon_modifier', _rgba(p["icon_modifier"]))
    _set_color(ui, 'icon_shading', _rgba(p["icon_shading"]))
    _set_color(ui, 'icon_folder', _rgba(p["icon_folder"]))
    _set_color(ui, 'icon_autokey', _rgba(p["icon_autokey"]))

    # =====================================================================
    # COLLECTION COLORS
    # =====================================================================
    try:
        ccolors = p.get("collection_colors", [])
        for i, cc in enumerate(ccolors):
            if i < len(theme.collection_color):
                _set_color(theme.collection_color[i], 'color', cc)
    except (AttributeError, IndexError):
        pass

    # =====================================================================
    # BONE COLOR SETS
    # =====================================================================
    try:
        bone_sets = [
            (p["danger"], p["danger_bright"], p["ui_accent"]),      # set 1
            (p["success"], p["success_bright"], p["ui_accent"]),     # set 2
            (p["accent_primary"], p["bright_cyan"], p["ui_accent"]), # set 3
            (p["magenta"], p["bright_magenta"], p["ui_accent"]),     # set 4
            (p["warning"], p["bright_yellow"], p["ui_accent"]),      # set 5
        ]
        for i, (normal, select, active) in enumerate(bone_sets):
            if i < len(theme.bone_color_sets):
                bcs = theme.bone_color_sets[i]
                _set_color(bcs, 'normal', normal)
                _set_color(bcs, 'select', select)
                _set_color(bcs, 'active', active)
                _try_set(bcs, 'show_colored_constraints', True)
    except (AttributeError, IndexError):
        pass

    # =====================================================================
    # SPACE THEME HELPERS
    # =====================================================================

    def set_space_generic(space):
        """Apply common space properties (ThemeSpaceGeneric)."""
        _set_color(space, 'back', p["ui_bg"])
        _set_color(space, 'title', p["ui_text_highlight"])
        _set_color(space, 'text', p["ui_text"])
        _set_color(space, 'text_hi', p["ui_text_highlight"])
        _set_color(space, 'header', _rgba(p["header_bg"]))
        _set_color(space, 'header_text', p["header_text"])
        _set_color(space, 'header_text_hi', p["ui_text_highlight"])
        # Toolbar/sidebar backgrounds are transparent in every look style.
        _set_color(space, 'button', _rgba(p["button_bg"], 0.0))
        _set_color(space, 'button_title', p["button_text"])
        _set_color(space, 'button_text', p["button_text"])
        _set_color(space, 'button_text_hi', p["button_text_hi"])
        _set_color(space, 'execution_buts', _rgba(p["button_bg"]))

        if not _is_5:
            # 4.x per-editor properties — removed/unified in 5.0
            _set_color(space, 'navigation_bar', _rgba(p["ui_panel"]))
            _set_color(space, 'tab_active', _rgba(p["tab_active_bg"], 0.6))
            _set_color(space, 'tab_inactive', p["tab_inactive_bg"])
            _set_color(space, 'tab_back', _rgba(p["ui_bg"], tabs_alpha))
            _set_color(space, 'tab_outline', p["tab_outline"])
            # Panel colors per-space
            try:
                pc = space.panelcolors
                _set_color(pc, 'header', _rgba(p["ui_panel_header"]))
                _set_color(pc, 'back', _rgba(p["ui_panel"], panel_alpha))
                _set_color(pc, 'sub_back', _rgba(p["ui_panel_sub"], sub_alpha))
            except AttributeError:
                pass

    def set_space_gradient(space):
        """Apply common space properties for ThemeSpaceGradient (3D viewport)."""
        _set_color(space, 'title', p["ui_text_highlight"])
        _set_color(space, 'text', p["ui_text"])
        _set_color(space, 'text_hi', p["ui_text_highlight"])
        _set_color(space, 'header', _rgba(p["header_bg"]))
        _set_color(space, 'header_text', p["header_text"])
        _set_color(space, 'header_text_hi', p["ui_text_highlight"])
        _set_color(space, 'button', _rgba(p["button_bg"], 0.0))
        _set_color(space, 'button_title', p["button_text"])
        _set_color(space, 'button_text', p["button_text"])
        _set_color(space, 'button_text_hi', p["button_text_hi"])
        _set_color(space, 'execution_buts', _rgba(p["button_bg"]))

        if not _is_5:
            # 4.x per-editor properties — removed/unified in 5.0
            _set_color(space, 'navigation_bar', _rgba(p["ui_panel"]))
            _set_color(space, 'tab_active', _rgba(p["tab_active_bg"], 0.6))
            _set_color(space, 'tab_inactive', p["tab_inactive_bg"])
            _set_color(space, 'tab_back', _rgba(p["ui_bg"], tabs_alpha))
            _set_color(space, 'tab_outline', p["tab_outline"])
            _set_color(space, 'button', _rgba(p["ui_bg"], 0.0))

        # Gradients — this controls the 3D viewport canvas background
        try:
            grad = space.gradients
            a, b = p["viewport_gradient_high"], p["viewport_gradient_low"]
            if _prefs is not None:
                from . import prefs as _prefs_mod
                _prefs_mod.seed_viewport_background_defaults(a, b)
                a = cm.linear_to_srgb(tuple(_prefs.finetune_gradient_a))
                b = cm.linear_to_srgb(tuple(_prefs.finetune_gradient_b))
            # Blender's High/Off color is the solid background in Static mode.
            _set_color(grad, 'high_gradient', a)
            _set_color(grad, 'gradient', b)
            _try_set(grad, 'background_type', getattr(_prefs, 'finetune_background_type', 'SINGLE_COLOR'))
        except AttributeError:
            pass

        if not _is_5:
            # Panel colors per-space (removed in 5.0)
            try:
                pc = space.panelcolors
                _set_color(pc, 'header', _rgba(p["ui_panel_header"]))
                _set_color(pc, 'back', _rgba(p["ui_panel"], panel_alpha))
                _set_color(pc, 'sub_back', _rgba(p["ui_panel_sub"], sub_alpha))
            except AttributeError:
                pass

    # =====================================================================
    # 3D VIEWPORT
    # =====================================================================
    v3d = theme.view_3d
    set_space_gradient(v3d.space)

    # Asset shelf (per-editor in 4.x, unified in regions in 5.0)
    if not _is_5:
        try:
            ash = v3d.asset_shelf
            _set_color(ash, 'header_back', p["header_bg"])
            _set_color(ash, 'back', p["ui_bg"])
        except AttributeError:
            pass

    _set_color(v3d, 'grid', grid_color)
    _set_color(v3d, 'wire', p["wire_color"])
    _set_color(v3d, 'wire_edit', p["edit_wire"])
    _set_color(v3d, 'object_selected', p["object_selected_color"])
    _set_color(v3d, 'object_active', p["object_active_color"])
    _set_color(v3d, 'vertex', p["edit_vertex"])
    _set_color(v3d, 'vertex_select', p["edge_select"])
    _set_color(v3d, 'vertex_unreferenced', p["danger"])
    _set_color(v3d, 'edge_select', p["edge_select"])

    if _is_5:
        # 5.0 renamed/combined these properties
        _set_color(v3d, 'seam', p["danger"])
        _set_color(v3d, 'sharp', p["bright_cyan"])
        _set_color(v3d, 'crease', p["bright_magenta"])
        _set_color(v3d, 'bevel', p["bright_cyan"])
        _set_color(v3d, 'freestyle', p["success"])
    else:
        # 4.x names
        _set_color(v3d, 'edge_seam', p["danger"])
        _set_color(v3d, 'edge_sharp', p["bright_cyan"])
        _set_color(v3d, 'edge_crease', p["bright_magenta"])
        _set_color(v3d, 'edge_bevel', p["bright_cyan"])
        _set_color(v3d, 'freestyle_edge_mark', p["success"])
        _set_color(v3d, 'freestyle_face_mark', _rgba(p["accent_tertiary"], 0.4))

    _set_color(v3d, 'edge_facesel', p["ui_accent"])
    _set_color(v3d, 'face_select', _rgba(p["ui_accent"], 0.25))
    _set_color(v3d, 'face_dot', p["ui_accent"])
    _set_color(v3d, 'empty', p["ui_text_muted"])
    _set_color(v3d, 'camera', p["ui_text_muted"])
    # Passepartout (dimmed area around camera frame): a persistent Finetune
    # pick (Appearance > Viewport), deliberately independent of the applied
    # palette. COLOR property holds linear light; the theme field takes sRGB
    # RGB (RNA is a 3-float property without alpha on 4.5/5.2). Without
    # preferences the default literal #000000 is used instead.
    if _prefs is not None:
        try:
            cam_passepartout = cm.linear_to_srgb(tuple(_prefs.finetune_cam_passepartout))
        except Exception:
            cam_passepartout = (0.0, 0.0, 0.0)
    else:
        cam_passepartout = (0.0, 0.0, 0.0)
    try:
        _set_color(v3d, 'camera_passepartout', cam_passepartout)
    except Exception:
        pass
    _set_color(v3d, 'lamp', p["warning"])
    _set_color(v3d, 'light', p["warning"])
    _set_color(v3d, 'speaker', p["ui_text_muted"])
    _set_color(v3d, 'text_grease_pencil', p["success"])
    _set_color(v3d, 'gp_vertex', p["success"])
    _set_color(v3d, 'gp_vertex_select', p["success_bright"])
    _try_set(v3d, 'gp_vertex_size', 3)
    _set_color(v3d, 'bone_solid', p["bone_color"])
    _set_color(v3d, 'bone_pose', p["bone_color"])
    _set_color(v3d, 'bone_pose_active', p["bone_color"])
    _set_color(v3d, 'bone_locked_weight', _rgba(p["danger"], 0.4))
    _set_color(v3d, 'transform', p["ui_accent"])
    _set_color(v3d, 'lastsel_point', p["ui_text_highlight"])
    _set_color(v3d, 'normal', p["accent_tertiary"])
    _set_color(v3d, 'vertex_normal', p["ui_accent"])
    _set_color(v3d, 'loop_normal', p["magenta"])
    _set_color(v3d, 'split_normal', p["danger"])
    _set_color(v3d, 'face_back', _rgba(p["ui_accent"], 0.1))
    _set_color(v3d, 'face_front', _rgba(p["ui_accent"], 0.2))
    _set_color(v3d, 'editmesh_active', _rgba(p["ui_accent"], 0.5))

    if not _is_5:
        # 4.x per-editor: frame_current, handles, act_spline moved to common in 5.0
        _set_color(v3d, 'frame_current', p["playhead_color"])
        _set_color(v3d, 'before_current_frame', p["before_frame"])
        _set_color(v3d, 'after_current_frame', p["after_frame"])
        _set_color(v3d, 'handle_free', p["danger"])
        _set_color(v3d, 'handle_auto', p["success"])
        _set_color(v3d, 'handle_vect', p["accent_tertiary"])
        _set_color(v3d, 'handle_align', p["magenta"])
        _set_color(v3d, 'handle_sel_free', p["danger"])
        _set_color(v3d, 'handle_sel_auto', p["success"])
        _set_color(v3d, 'handle_sel_vect', p["accent_tertiary"])
        _set_color(v3d, 'handle_sel_align', p["bright_magenta"])
        _set_color(v3d, 'act_spline', p["ui_accent"])

    _set_color(v3d, 'nurb_uline', p["accent_tertiary"])
    _set_color(v3d, 'nurb_vline', p["magenta"])
    _set_color(v3d, 'nurb_sel_uline', p["obj_selected"])
    _set_color(v3d, 'nurb_sel_vline', p["bright_magenta"])
    _set_color(v3d, 'clipping_border_3d', _rgba(p["warning"], 0.5))
    _set_color(v3d, 'view_overlay', p["ui_text"])
    _set_color(v3d, 'paint_curve_pivot', p["danger"])
    _set_color(v3d, 'paint_curve_handle', p["success"])
    _set_color(v3d, 'skin_root', p["danger"])
    _set_color(v3d, 'extra_edge_len', p["success"])
    _set_color(v3d, 'extra_edge_angle', p["accent_tertiary"])
    _set_color(v3d, 'extra_face_angle', p["ui_accent"])
    _set_color(v3d, 'extra_face_area', p["magenta"])
    _set_color(v3d, 'bundle_solid', p["ui_card"])
    _try_set(v3d, 'outline_width', _sizes["outline_width"])
    _try_set(v3d, 'vertex_size', _sizes["vertex_size"])
    _try_set(v3d, 'edge_width', _sizes["edge_width"])
    _try_set(v3d, 'facedot_size', _sizes["facedot_size"])

    # =====================================================================
    # PROPERTIES EDITOR
    # =====================================================================
    set_space_generic(theme.properties.space)

    # =====================================================================
    # OUTLINER
    # =====================================================================
    set_space_generic(theme.outliner.space)
    o = theme.outliner
    _set_color(o, 'match', p["ui_accent"])
    _set_color(o, 'selected_highlight', p["list_highlight"])  # palette selection
    _set_color(o, 'active', p["list_highlight"])  # Themes > Outliner > Active Highlight
    _set_color(o, 'selected_object', p["ui_text"] if style == 'LAYERED' else _rgba(p["obj_selected"], 0.3))
    _set_color(o, 'active_object', source_bg if style == 'LAYERED' else _rgba(p["black"], 0.5))
    _set_color(o.space, 'text_highlight', _rgba(p["black"], 0.5))
    _set_color(o, 'edited_object', _rgba(p["success"], 0.3))
    _set_color(o, 'row_alternate', _rgba(p["row_alternate"], 0.5))

    # =====================================================================
    # TEXT EDITOR
    # =====================================================================
    set_space_generic(theme.text_editor.space)
    te = theme.text_editor
    _set_color(te, 'line_numbers', p["text_line_numbers"])
    _set_color(te, 'line_numbers_background', p["ui_panel"])
    _set_color(te, 'selected_text', p["text_selection"])
    _set_color(te, 'cursor', p["text_cursor"])
    _set_color(te, 'syntax_builtin', p["accent_tertiary"])
    _set_color(te, 'syntax_symbols', p["ui_text_muted"])
    _set_color(te, 'syntax_special', p["magenta"])
    _set_color(te, 'syntax_comment', p["ui_text_disabled"])
    _set_color(te, 'syntax_preprocessor', p["accent_primary"])
    _set_color(te, 'syntax_reserved', p["danger"])
    _set_color(te, 'syntax_string', p["success"])
    _set_color(te, 'syntax_numbers', p["warning"])

    # =====================================================================
    # GRAPH EDITOR
    # =====================================================================
    set_space_generic(theme.graph_editor.space)
    ge = theme.graph_editor
    _set_color(ge, 'grid', p["grid_line"])

    if not _is_5:
        # 4.x per-editor: frame_current, channels, handles moved to common in 5.0
        _set_color(ge, 'frame_current', p["playhead_color"])
        _set_color(ge, 'handle_free', p["danger"])
        _set_color(ge, 'handle_auto', p["success"])
        _set_color(ge, 'handle_vect', p["accent_tertiary"])
        _set_color(ge, 'handle_align', p["magenta"])
        _set_color(ge, 'handle_sel_free', p["danger"])
        _set_color(ge, 'handle_sel_auto', p["success"])
        _set_color(ge, 'handle_sel_vect', p["accent_tertiary"])
        _set_color(ge, 'handle_sel_align', p["bright_magenta"])
        _set_color(ge, 'handle_auto_clamped', p["warning"])
        _set_color(ge, 'handle_sel_auto_clamped', p["warning"])
        _set_color(ge, 'channel_group', p["anim_channel_group"])
        _set_color(ge, 'active_channels_group', p["anim_channel_group_active"])
        _set_color(ge, 'dopesheet_channel', _rgba(p["ui_panel"], 0.5))
        _set_color(ge, 'dopesheet_subchannel', _rgba(p["ui_card"], 0.5))
        _set_color(ge, 'channels_region', p["ui_panel"])

    _set_color(ge, 'lastsel_point', p["ui_text_highlight"])
    _set_color(ge, 'handle_vertex', p["vertex_color"])
    _set_color(ge, 'handle_vertex_select', p["edge_select"])
    _try_set(ge, 'handle_vertex_size', 4)
    _set_color(ge, 'window_sliders', p["ui_accent"])

    # =====================================================================
    # DOPESHEET EDITOR
    # =====================================================================
    set_space_generic(theme.dopesheet_editor.space)
    de = theme.dopesheet_editor
    # Current-frame ruler text in the header uses the palette background.
    _set_color(de.space, 'header_text_hi', p["theme_bg"])
    _set_color(de, 'grid', p["grid_line"])
    # Summary row/track uses the palette accent (all Blender versions)
    _set_color(de, 'summary', _rgba(p["ui_accent"], chan_a))
    # Dopesheet panel "Region Background" = palette background
    _set_color(de.space, 'button', _rgba(p["ui_bg"], 0.0))
    # These borders remain per-editor even in Blender 5.x.
    _set_color(de, 'keyframe_border', _rgba(p["ui_border"], 0.0))
    _set_color(de, 'keyframe_border_selected', p["ui_text"])

    if not _is_5:
        # Source list (channels region); Timeline uses the Dope Sheet theme.
        _set_color(de.space_list, 'list', p["ui_bg"])
        # 4.x per-editor: frame_current, keyframes, channels moved to common in 5.0
        _set_color(de, 'frame_current', p["playhead_color"])
        _set_color(de, 'value_sliders', _rgba(p["ui_accent"], 0.3))
        _set_color(de, 'view_sliders', _rgba(p["accent_tertiary"], 0.3))
        _set_color(de, 'dopesheet_channel', _rgba(p["ui_panel"], 0.5))
        _set_color(de, 'dopesheet_subchannel', _rgba(p["ui_card"], 0.5))
        _set_color(de, 'channel_group', p["anim_channel_group"])
        _set_color(de, 'active_channels_group', p["anim_channel_group_active"])
        _set_color(de, 'long_key', _rgba(p["magenta"], 0.3))
        _set_color(de, 'long_key_selected', _rgba(p["bright_magenta"], 0.3))
        _set_color(de, 'keyframe', p["ui_text"])
        _set_color(de, 'keyframe_selected', p["keyframe_selected_color"])
        _set_color(de, 'keyframe_extreme', p["danger"])
        _set_color(de, 'keyframe_extreme_selected', p["danger"])
        _set_color(de, 'keyframe_breakdown', p["accent_tertiary"])
        _set_color(de, 'keyframe_breakdown_selected', p["accent_tertiary"])
        _set_color(de, 'keyframe_jitter', p["success"])
        _set_color(de, 'keyframe_jitter_selected', p["success"])
        _set_color(de, 'keyframe_movehold', p["magenta"])
        _set_color(de, 'keyframe_movehold_selected', p["bright_magenta"])
        _set_color(de, 'channels_region', p["ui_panel"])
        _set_color(de, 'window_sliders', p["ui_accent"])
        _set_color(de, 'time_scrub_background', _rgba(p["ui_panel"], 0.75))
        _set_color(de, 'time_marker_line', _rgba(p["warning"], 0.5))
        _set_color(de, 'time_marker_line_selected', _rgba(p["ui_accent"], 0.8))

    # =====================================================================
    # NODE EDITOR
    # =====================================================================
    set_space_generic(theme.node_editor.space)
    ne = theme.node_editor
    _set_color(ne, 'grid', p["grid_line"])
    _set_color(ne, 'node_selected', p["node_selected"])
    _set_color(ne, 'node_active', p["ui_accent"])
    _set_color(ne, 'wire', p["wire_color"])
    _set_color(ne, 'wire_inner', p["ui_text_muted"])
    _set_color(ne, 'wire_select', p["obj_selected"])
    _set_color(ne, 'selected_text', p["ui_selection"])
    _set_color(ne, 'node_backdrop', _rgba(p["ui_bg"], 0.6))
    _try_set(ne, 'noodle_curving', 5)

    # Node type colors
    _set_color(ne, 'converter_node', p["node_converter"])
    _set_color(ne, 'color_node', p["node_color"])
    _set_color(ne, 'group_node', p["node_group"])
    _set_color(ne, 'interface_node', p["node_interface"])
    _set_color(ne, 'input_node', p["node_input"])
    _set_color(ne, 'output_node', p["node_output"])
    _set_color(ne, 'matte_node', p["node_matte"])
    _set_color(ne, 'distor_node', p["node_distort"])
    _set_color(ne, 'filter_node', p["node_filter"])
    _set_color(ne, 'pattern_node', p["node_pattern"])
    _set_color(ne, 'script_node', p["node_script"])
    _set_color(ne, 'shader_node', p["node_shader"])
    _set_color(ne, 'texture_node', p["node_texture"])
    _set_color(ne, 'vector_node', p["node_vector"])
    _set_color(ne, 'layout_node', p["node_layout"])
    _set_color(ne, 'frame_node', _rgba(p["node_frame"], 0.6))
    _set_color(ne, 'group_socket_node', p["node_group"])

    # =====================================================================
    # NLA EDITOR
    # =====================================================================
    set_space_generic(theme.nla_editor.space)
    nla = theme.nla_editor
    _set_color(nla, 'grid', p["grid_line"])
    _set_color(nla, 'strips', p["nla_strip"])
    _set_color(nla, 'strips_selected', p["nla_strip_selected"])
    _set_color(nla, 'transition_strips', p["nla_transition"])
    _set_color(nla, 'transition_strips_selected', p["nla_strip_selected"])
    _set_color(nla, 'meta_strips', p["nla_meta"])
    _set_color(nla, 'meta_strips_selected', p["nla_strip_selected"])
    _set_color(nla, 'sound_strips', p["nla_sound"])
    _set_color(nla, 'sound_strips_selected', p["nla_strip_selected"])
    _set_color(nla, 'tweak', p["nla_tweak"])
    _set_color(nla, 'tweak_duplicate', p["nla_tweak_dup"])

    if not _is_5:
        # 4.x per-editor: frame_current, keyframes, channels, scrubbing moved to common in 5.0
        _set_color(nla, 'frame_current', p["playhead_color"])
        _set_color(nla, 'keyframe_border', p["ui_border"])
        _set_color(nla, 'keyframe_border_selected', p["ui_text"])
        _set_color(nla, 'view_sliders', p["ui_accent"])
        _set_color(nla, 'dopesheet_channel', _rgba(p["ui_panel"], 0.5))
        _set_color(nla, 'dopesheet_subchannel', _rgba(p["ui_card"], 0.5))
        _set_color(nla, 'time_scrub_background', _rgba(p["ui_panel"], 0.75))
        _set_color(nla, 'time_marker_line', _rgba(p["warning"], 0.5))
        _set_color(nla, 'time_marker_line_selected', _rgba(p["ui_accent"], 0.8))

    # =====================================================================
    # TIMELINE
    # =====================================================================
    try:
        set_space_generic(theme.timeline.space)
        tl = theme.timeline
        # Current-frame ruler text in the header uses the palette background.
        _set_color(theme.timeline.space, 'header_text_hi', p["theme_bg"])
        _set_color(tl, 'grid', p["grid_line"])
        # Summary row uses the palette accent
        _set_color(tl, 'summary', _rgba(p["ui_accent"], chan_a))
        if not _is_5:
            _set_color(tl, 'frame_current', p["playhead_color"])
            _set_color(tl, 'time_scrub_background', _rgba(p["ui_panel"], 0.75))
            _set_color(tl, 'time_marker_line', _rgba(p["warning"], 0.5))
            _set_color(tl, 'time_marker_line_selected', _rgba(p["ui_accent"], 0.8))
    except AttributeError:
        pass

    # =====================================================================
    # CONSOLE
    # =====================================================================
    set_space_generic(theme.console.space)
    c = theme.console
    _set_color(c, 'line_output', p["ui_text"])
    _set_color(c, 'line_input', p["success"])
    _set_color(c, 'line_info', p["info_color"])
    _set_color(c, 'line_error', p["danger"])
    _set_color(c, 'cursor', p["ui_cursor"])
    _set_color(c, 'select', p["ui_selection"])

    # =====================================================================
    # INFO
    # =====================================================================
    set_space_generic(theme.info.space)
    inf = theme.info
    _set_color(inf, 'info_selected', p["ui_selection"])
    _set_color(inf, 'info_selected_text', p["ui_selection_text"])
    _set_color(inf, 'info_error', _rgba(p["danger"], 0.3))
    _set_color(inf, 'info_error_text', p["danger"])
    _set_color(inf, 'info_warning', _rgba(p["warning"], 0.3))
    _set_color(inf, 'info_warning_text', p["warning"])
    _set_color(inf, 'info_info', _rgba(p["info_color"], 0.3))
    _set_color(inf, 'info_info_text', p["info_color"])
    _set_color(inf, 'info_debug', _rgba(p["accent_tertiary"], 0.3))
    _set_color(inf, 'info_debug_text', p["accent_tertiary"])
    _set_color(inf, 'info_property', _rgba(p["ui_accent"], 0.3))
    _set_color(inf, 'info_property_text', p["ui_accent"])
    _set_color(inf, 'info_operator', _rgba(p["success"], 0.3))
    _set_color(inf, 'info_operator_text', p["success"])

    # =====================================================================
    # PREFERENCES
    # =====================================================================
    set_space_generic(theme.preferences.space)

    # =====================================================================
    # FILE BROWSER
    # =====================================================================
    set_space_generic(theme.file_browser.space)
    _set_color(theme.file_browser, 'selected_file', p["ui_selection"])
    _set_color(theme.file_browser, 'row_alternate', _rgba(p["row_alternate"], 0.5))

    # =====================================================================
    # TOPBAR
    # =====================================================================
    try:
        set_space_generic(theme.topbar.space)
    except AttributeError:
        pass

    # =====================================================================
    # STATUSBAR
    # =====================================================================
    set_space_generic(theme.statusbar.space)

    # =====================================================================
    # SPREADSHEET
    # =====================================================================
    try:
        set_space_generic(theme.spreadsheet.space)
        _set_color(theme.spreadsheet, 'row_alternate', _rgba(p["row_alternate"], 0.5))
    except AttributeError:
        pass

    # =====================================================================
    # IMAGE EDITOR
    # =====================================================================
    set_space_generic(theme.image_editor.space)
    ie = theme.image_editor
    _set_color(ie, 'grid', p["grid_line"])
    _set_color(ie, 'vertex', p["vertex_color"])
    _set_color(ie, 'vertex_select', p["edge_select"])
    _set_color(ie, 'vertex_unreferenced', p["danger"])
    _try_set(ie, 'vertex_size', 3)
    _set_color(ie, 'face_select', _rgba(p["ui_accent"], 0.25))
    _set_color(ie, 'face_dot', p["ui_accent"])
    _set_color(ie, 'editmesh_active', _rgba(p["ui_accent"], 0.5))
    _set_color(ie, 'wire_edit', p["wire_edit"])

    if not _is_5:
        # 4.x per-editor: frame_current, handles moved to common in 5.0
        _set_color(ie, 'frame_current', p["playhead_color"])
        _set_color(ie, 'handle_free', p["danger"])
        _set_color(ie, 'handle_auto', p["success"])
        _set_color(ie, 'handle_align', p["magenta"])
        _set_color(ie, 'handle_sel_free', p["danger"])
        _set_color(ie, 'handle_sel_auto', p["success"])
        _set_color(ie, 'handle_sel_align', p["bright_magenta"])

    _set_color(ie, 'paint_curve_pivot', p["danger"])
    _set_color(ie, 'paint_curve_handle', p["success"])
    _set_color(ie, 'uv_shadow', _rgba(p["ui_text_disabled"], 0.3))
    _set_color(ie, 'stitch_indicator_active', p["success"])
    _set_color(ie, 'stitch_indicator_disconnected', p["danger"])

    # =====================================================================
    # SEQUENCE EDITOR
    # =====================================================================
    set_space_generic(theme.sequence_editor.space)
    se = theme.sequence_editor
    _set_color(se, 'grid', p["grid_line"])
    _set_color(se, 'draw_action', _rgba(p["ui_accent"], 0.5))
    _set_color(se, 'movie_strip', _rgba(p["accent_tertiary"], 0.5))
    _set_color(se, 'movieclip_strip', _rgba(p["magenta"], 0.5))
    _set_color(se, 'image_strip', _rgba(p["accent_primary"], 0.5))
    _set_color(se, 'scene_strip', _rgba(p["success"], 0.5))
    _set_color(se, 'audio_strip', _rgba(p["accent_tertiary"], 0.5))
    _set_color(se, 'effect_strip', _rgba(p["magenta"], 0.5))
    _set_color(se, 'transition_strip', _rgba(p["bright_magenta"], 0.5))
    _set_color(se, 'color_strip', _rgba(p["warning"], 0.5))
    _set_color(se, 'meta_strip', _rgba(p["ui_card"], 0.5))
    _set_color(se, 'text_strip', _rgba(p["ui_text"], 0.5))
    _set_color(se, 'active_strip', _rgba(p["obj_active"], 0.5))
    _set_color(se, 'selected_strip', _rgba(p["obj_selected"], 0.5))
    _set_color(se, 'row_alternate', _rgba(p["row_alternate"], 0.5))
    _set_color(se, 'window_sliders', p["ui_accent"])

    if not _is_5:
        # 4.x per-editor: frame_current, keyframe, scrubbing moved to common in 5.0
        _set_color(se, 'frame_current', p["playhead_color"])
        _set_color(se, 'keyframe', p["ui_text"])
        _set_color(se, 'time_scrub_background', _rgba(p["ui_panel"], 0.75))

    # =====================================================================
    # CLIP EDITOR
    # =====================================================================
    set_space_generic(theme.clip_editor.space)
    ce = theme.clip_editor
    _set_color(ce, 'grid', p["grid_line"])
    _set_color(ce, 'marker_outline', p["ui_border"])
    _set_color(ce, 'marker', p["ui_accent"])
    _set_color(ce, 'active_marker', p["obj_active"])
    _set_color(ce, 'selected_marker', p["obj_selected"])
    _set_color(ce, 'dis_marker', p["ui_text_disabled"])
    _set_color(ce, 'locked_marker', p["danger"])
    _set_color(ce, 'handle_vertex', p["vertex_color"])
    _set_color(ce, 'handle_vertex_select', p["edge_select"])
    _try_set(ce, 'handle_vertex_size', 5)
    _set_color(ce, 'path_before', p["danger"])
    _set_color(ce, 'path_after', p["accent_tertiary"])
    _set_color(ce, 'path_keyframe_before', p["danger"])
    _set_color(ce, 'path_keyframe_after', p["accent_tertiary"])
    _set_color(ce, 'strips', p["ui_accent"])
    _set_color(ce, 'strips_selected', p["obj_selected"])

    if not _is_5:
        # 4.x per-editor: frame_current, scrubbing moved to common in 5.0
        _set_color(ce, 'frame_current', p["playhead_color"])
        _set_color(ce, 'time_scrub_background', _rgba(p["ui_panel"], 0.75))

    # =====================================================================
    # BLENDER 5.0+ UNIFIED THEME SETTINGS
    # =====================================================================
    if _is_5:
        # --- Regions: Sidebars ---
        sb = theme.regions.sidebars
        _set_color(sb, 'back', _rgba(p["ui_bg"], 0.0))
        _set_color(sb, 'tab_back', _rgba(p["ui_bg"], tabs_alpha))

        # --- Regions: Channels ---
        ch = theme.regions.channels
        _set_color(ch, 'back', p["ui_bg"])


        # --- Regions: Scrubbing / Markers ---
        scr = theme.regions.scrubbing
        _set_color(scr, 'back', _rgba(p["ui_panel"], 0.75))
        _set_color(scr, 'text', p["ui_text_muted"])
        _set_color(scr, 'time_marker', _rgba(p["warning"], 0.5))
        _set_color(scr, 'time_marker_selected', _rgba(p["ui_accent"], 0.8))

        # --- Regions: Asset Shelf ---
        ash = theme.regions.asset_shelf
        _set_color(ash, 'header_back', p["header_bg"])
        _set_color(ash, 'back', p["ui_bg"])

        # --- Common: Animation ---
        anim = theme.common.anim
        _set_color(anim, 'playhead', p["playhead_color"])
        _set_color(anim, 'summary', _rgba(p["ui_accent"], chan_a))
        _set_color(anim, 'preview_range', _rgba(p["ui_accent"], 0.3))
        # Common > Animation: exact palette colours, no synthesized alpha.
        _set_color(anim, 'channels', p["anim_channels"])
        _set_color(anim, 'channels_sub', p["anim_channels_sub"])
        _set_color(anim, 'channel_group', p["anim_channel_group"])
        _set_color(anim, 'channel_group_active', p["anim_channel_group_active"])
        _set_color(anim, 'channel', p["ui_panel"])
        _set_color(anim, 'channel_selected', p["list_highlight"])
        _set_color(anim, 'keyframe', p["ui_text"])
        _set_color(anim, 'keyframe_selected', p["keyframe_selected_color"])
        _set_color(anim, 'keyframe_breakdown', p["accent_tertiary"])
        _set_color(anim, 'keyframe_breakdown_selected', p["accent_tertiary"])
        _set_color(anim, 'keyframe_extreme', p["danger"])
        _set_color(anim, 'keyframe_extreme_selected', p["danger"])
        _set_color(anim, 'keyframe_jitter', p["success"])
        _set_color(anim, 'keyframe_jitter_selected', p["success"])
        _set_color(anim, 'keyframe_moving_hold', p["magenta"])
        _set_color(anim, 'keyframe_moving_hold_selected', p["bright_magenta"])
        _set_color(anim, 'keyframe_generated', p["ui_text_muted"])
        _set_color(anim, 'keyframe_generated_selected', p["ui_text_highlight"])
        _set_color(anim, 'long_key', _rgba(p["magenta"], 0.3))
        _set_color(anim, 'long_key_selected', _rgba(p["bright_magenta"], 0.3))

        # --- Common: Curves (handles) ---
        crv = theme.common.curves
        _set_color(crv, 'handle_free', p["danger"])
        _set_color(crv, 'handle_sel_free', p["danger"])
        _set_color(crv, 'handle_auto', p["success"])
        _set_color(crv, 'handle_sel_auto', p["success"])
        _set_color(crv, 'handle_vect', p["accent_tertiary"])
        _set_color(crv, 'handle_sel_vect', p["accent_tertiary"])
        _set_color(crv, 'handle_align', p["magenta"])
        _set_color(crv, 'handle_sel_align', p["bright_magenta"])
        _set_color(crv, 'handle_auto_clamped', p["warning"])
        _set_color(crv, 'handle_sel_auto_clamped', p["warning"])
        _set_color(crv, 'handle_vertex', p["vertex_color"])
        _set_color(crv, 'handle_vertex_select', p["edge_select"])
        _try_set(crv, 'handle_vertex_size', 4)

        # --- User Interface: 5.0 panel properties ---
        # (panel_back, panel_header, panel_sub_back already set above
        #  in the shared UI section — these are the NEW 5.0 properties)
        _set_color(ui, 'panel_active', _rgba(p["ui_accent"], 0.15))
        _set_color(ui, 'editor_outline_active', p["ui_accent"])

    # =====================================================================
    # Finetune > Text / Text Selected: global overrides. Applied last so they
    # win over every palette-derived text colour. The seed call keeps the
    # "off" state pointing at the palette's own colours.
    # =====================================================================
    apply_channel_text(theme, dope_text, dope_text_sel)
    if _prefs is not None:
        try:
            from . import prefs as _prefs_mod
            _prefs_mod.seed_global_text_defaults(p["ui_text"], p["white"])
            _prefs_mod.seed_bg_role_defaults(palette.get("theme_bg"), palette["ui_bg"])
        except Exception:
            pass
        text_override = (cm.linear_to_srgb(tuple(_prefs.finetune_text))
                         if getattr(_prefs, "finetune_text_custom", False) else None)
        sel_override = (cm.linear_to_srgb(tuple(_prefs.finetune_text_sel))
                        if getattr(_prefs, "finetune_text_sel_custom", False) else None)
        if text_override is not None or sel_override is not None:
            try:
                override_theme_text(theme, text=text_override, selected=sel_override)
            except Exception:
                pass

    # =====================================================================
    # FORCE UI REDRAW
    # =====================================================================
    wm = getattr(bpy.context, 'window_manager', None)
    for window in getattr(wm, 'windows', ()):
        screen = getattr(window, 'screen', None)
        for area in getattr(screen, 'areas', ()):
            area.tag_redraw()

    return True

# SPDX-License-Identifier: GPL-3.0-or-later
"""UI-only surface shades; source palettes and semantic colors stay untouched."""
import colorsys

from . import color_math as cm


ROUNDNESS = {'LAYERED': 0.5, 'CARD': 0.8, 'OUTLINED': 0.2, 'INSET': 0.35, 'ACCENT': 0.65}
# Panel dark/light, then control dark/light: keep Card's original treatment.
SURFACE_SHIFTS = {
    'CARD': (0.065, 0.04, 0.025, -0.025),
    'OUTLINED': (0.0, 0.0, 0.0, 0.0),
    'INSET': (-0.035, -0.055, 0.035, 0.015),
    'ACCENT': (0.065, 0.04, 0.025, -0.025),
    'LAYERED': (0.035, -0.035, 0.075, 0.03),
}


def _readable(color, rgb, text):
    text_lum = cm.luminance(*text[:3])

    def contrast(rgb):
        lum = cm.luminance(*rgb[:3])
        return (max(lum, text_lum) + 0.05) / (min(lum, text_lum) + 0.05)

    minimum = min(4.5, contrast(color))
    # Reduce the effect rather than recolor text or worsen a low-contrast source.
    for _ in range(8):
        if contrast(rgb) >= minimum:
            return (*rgb, *color[3:])
        rgb = tuple((a + b) * 0.5 for a, b in zip(color[:3], rgb))
    return tuple(color)


def _shade(color, amount, text):
    hue, lightness, saturation = colorsys.rgb_to_hls(*color[:3])
    rgb = colorsys.hls_to_rgb(hue, cm.clamp(lightness + amount), saturation)
    return _readable(color, rgb, text)


def _tint(color, accent, amount, text):
    rgb = tuple(a + (b - a) * amount for a, b in zip(color[:3], accent[:3]))
    return _readable(color, rgb, text)


def surface_palette(palette, style, primary_custom=False, secondary_custom=False):
    """Return a styled copy, leaving explicit surface picks exact."""
    if style not in ROUNDNESS:
        return palette
    p = dict(palette)
    dark = palette['dark']
    shifts = SURFACE_SHIFTS[style]
    panel, control = shifts[0 if dark else 1], shifts[2 if dark else 3]
    if not primary_custom:
        for key in ('ui_panel', 'ui_panel_header', 'ui_panel_sub', 'header_bg'):
            p[key] = _shade(palette[key], panel, palette['ui_text'])
            if style == 'ACCENT' and key in ('ui_panel_header', 'header_bg'):
                p[key] = _tint(p[key], palette['ui_accent'], 0.18, palette['ui_text'])
    if not secondary_custom:
        for key in ('ui_card', 'ui_popup', 'widget_bg', 'widget_hover', 'widget_active',
                    'button_bg', 'button_hover', 'toolbar_bg', 'tab_inactive_bg'):
            p[key] = _shade(palette[key], control, palette['ui_text'])
    return p

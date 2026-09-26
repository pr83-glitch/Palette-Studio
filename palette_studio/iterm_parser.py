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
Parse color scheme files from multiple sources and normalize to a common format.

Supported formats:
  - .itermcolors (Apple plist) — iTerm2-Color-Schemes repo
  - .yml (Gogh YAML)          — Gogh terminal themes
  - .yaml (base16 YAML)       — base16 schemes
  - .conf (kitty config)      — kovidgoyal/kitty-themes
  - .yaml (base24, system: base24) — tinted-theming/schemes
  - .lua (NvChad base46)      — NvChad/base46

All parsers output the same normalized dict:
    name: str
    path: str
    source: str ("iterm", "gogh", "base16", "base24", "nvchad")
    ansi: list of 16 RGB tuples (float 0-1)
    bg: RGB tuple
    fg: RGB tuple
    cursor: RGB tuple or None
    cursor_text: RGB tuple or None
    selection: RGB tuple or None
    selected_text: RGB tuple or None
    bold: RGB tuple or None
"""

import plistlib
import os
import re
from pathlib import Path


# =========================================================================
# Hex helpers
# =========================================================================

def _hex_to_rgb(hexstr):
    """Convert '#RRGGBB', 'RRGGBB' (or short '#RGB') to (r, g, b) floats 0-1.

    Tolerant of surrounding whitespace, a leading '#' anywhere, and trailing
    inline comments. Short 3/4-digit hex forms (used by some terminal themes)
    are expanded before parsing. Returns None when the value is unusable.
    """
    if not hexstr:
        return None

    h = str(hexstr).strip()
    hash_pos = h.find('#')
    h = h[hash_pos + 1:] if hash_pos != -1 else h

    # Cut anything after the first whitespace/comment marker so values such
    # as '#RRGGBB # note' still parse.
    for sep in (' ', '\t', ';', '#'):
        idx = h.find(sep)
        if idx != -1:
            h = h[:idx]
    h = h.strip()

    if len(h) in (3, 4):
        h = ''.join(ch * 2 for ch in h[:3])

    if len(h) != 6:
        return None
    try:
        return (
            int(h[0:2], 16) / 255.0,
            int(h[2:4], 16) / 255.0,
            int(h[4:6], 16) / 255.0,
        )
    except ValueError:
        return None


# =========================================================================
# iTerm (.itermcolors) parser
# =========================================================================

ANSI_KEYS = [f"Ansi {i} Color" for i in range(16)]


def _extract_rgb(color_dict):
    """Extract RGB floats from an iTerm color dict."""
    r = float(color_dict.get("Red Component", 0.0))
    g = float(color_dict.get("Green Component", 0.0))
    b = float(color_dict.get("Blue Component", 0.0))
    return (
        max(0.0, min(1.0, r)),
        max(0.0, min(1.0, g)),
        max(0.0, min(1.0, b)),
    )


def parse_itermcolors(filepath):
    """Parse an .itermcolors (plist) file."""
    filepath = Path(filepath)
    with open(filepath, "rb") as f:
        plist = plistlib.load(f)

    theme = {
        "name": filepath.stem,
        "path": str(filepath),
        "source": "iterm",
        "ansi": [],
    }

    for key in ANSI_KEYS:
        if key in plist:
            theme["ansi"].append(_extract_rgb(plist[key]))
        else:
            theme["ansi"].append(None)

    _fill_missing_ansi(theme)

    theme["bg"] = _extract_rgb(plist["Background Color"]) if "Background Color" in plist else theme["ansi"][0]
    theme["fg"] = _extract_rgb(plist["Foreground Color"]) if "Foreground Color" in plist else theme["ansi"][7]

    for extra, key in [
        ("cursor", "Cursor Color"),
        ("cursor_text", "Cursor Text Color"),
        ("selection", "Selection Color"),
        ("selected_text", "Selected Text Color"),
        ("bold", "Bold Color"),
    ]:
        theme[extra] = _extract_rgb(plist[key]) if key in plist else None

    return theme


# =========================================================================
# Gogh YAML parser
# =========================================================================

def _parse_yaml_simple(text):
    """
    Minimal YAML parser for flat or single-nested key-value files.
    Handles: key: 'value', key: "value", key: value, and # comments.
    For nested keys like 'palette:', flattens one level deep.
    Returns dict of string key -> string value.
    """
    result = {}
    in_section = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#') or stripped == '---':
            continue
        if ':' not in stripped:
            continue

        # Check indentation — if indented, treat as nested under current section
        indent = len(line) - len(line.lstrip())

        key, _, val = stripped.partition(':')
        key = key.strip()
        val = val.strip()

        # Strip quotes
        if val and val[0] in ("'", '"'):
            quote = val[0]
            end = val.find(quote, 1)
            if end > 0:
                val = val[1:end]
        else:
            comment_pos = val.find('#')
            if comment_pos > 0:
                val = val[:comment_pos].strip()

        if indent == 0 or (indent <= 2 and not in_section):
            if val == '' or val == '':
                # This is a section header like "palette:"
                in_section = key
            else:
                in_section = None
                result[key] = val
        else:
            # Nested key — store directly (flattened)
            result[key] = val

    return result


def parse_gogh_yaml(filepath):
    """
    Parse a Gogh YAML theme file.

    Gogh format:
        color_01 - color_08: ANSI 0-7 (normal)
        color_09 - color_16: ANSI 8-15 (bright)
        background: bg hex
        foreground: fg hex
        cursor: cursor hex (optional)
    """
    filepath = Path(filepath)
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        data = _parse_yaml_simple(f.read())

    theme_name = data.get("name", filepath.stem)

    theme = {
        "name": theme_name,
        "path": str(filepath),
        "source": "gogh",
        "ansi": [],
    }

    for i in range(16):
        key = f"color_{i+1:02d}"
        hexval = data.get(key, "")
        rgb = _hex_to_rgb(hexval)
        theme["ansi"].append(rgb)

    _fill_missing_ansi(theme)

    bg_hex = data.get("background", "")
    fg_hex = data.get("foreground", "")
    cursor_hex = data.get("cursor", "")

    theme["bg"] = _hex_to_rgb(bg_hex) or theme["ansi"][0]
    theme["fg"] = _hex_to_rgb(fg_hex) or theme["ansi"][7]
    theme["cursor"] = _hex_to_rgb(cursor_hex) if cursor_hex else None
    theme["cursor_text"] = None
    theme["selection"] = None
    theme["selected_text"] = None
    theme["bold"] = None

    return theme


# =========================================================================
# base16 YAML parser
# =========================================================================

def parse_base16_yaml(filepath):
    """
    Parse a base16 YAML scheme file.

    base16 mapping to ANSI:
        base00 = bg / ANSI 0       base08 = red / ANSI 1, 9
        base01 = lighter bg        base09 = orange / ANSI 3
        base02 = selection / ANSI 8 base0A = yellow / ANSI 11
        base03 = comments          base0B = green / ANSI 2, 10
        base04 = dark fg           base0C = cyan / ANSI 6, 14
        base05 = fg / ANSI 7       base0D = blue / ANSI 4, 12
        base06 = light fg          base0E = magenta / ANSI 5, 13
        base07 = ANSI 15           base0F = brown
    """
    filepath = Path(filepath)
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        data = _parse_yaml_simple(f.read())

    theme_name = data.get("scheme", data.get("name", filepath.stem))

    bases = {}
    for i in range(16):
        key = f"base{i:02X}"
        hexval = data.get(key, "")
        if hexval and not hexval.startswith('#'):
            hexval = '#' + hexval
        bases[key] = _hex_to_rgb(hexval)

    ansi = [
        bases.get("base00"),  #  0 Black
        bases.get("base08"),  #  1 Red
        bases.get("base0B"),  #  2 Green
        bases.get("base09"),  #  3 Yellow
        bases.get("base0D"),  #  4 Blue
        bases.get("base0E"),  #  5 Magenta
        bases.get("base0C"),  #  6 Cyan
        bases.get("base05"),  #  7 White
        bases.get("base02"),  #  8 Bright Black
        bases.get("base08"),  #  9 Bright Red
        bases.get("base0B"),  # 10 Bright Green
        bases.get("base0A"),  # 11 Bright Yellow
        bases.get("base0D"),  # 12 Bright Blue
        bases.get("base0E"),  # 13 Bright Magenta
        bases.get("base0C"),  # 14 Bright Cyan
        bases.get("base07"),  # 15 Bright White
    ]

    theme = {
        "name": theme_name,
        "path": str(filepath),
        "source": "base16",
        "ansi": ansi,
    }
    _fill_missing_ansi(theme)

    theme["bg"] = bases.get("base00") or theme["ansi"][0]
    theme["fg"] = bases.get("base05") or theme["ansi"][7]
    theme["cursor"] = bases.get("base06")
    theme["cursor_text"] = bases.get("base00")
    theme["selection"] = bases.get("base02")
    theme["selected_text"] = bases.get("base06")
    theme["bold"] = None

    return theme


# =========================================================================
# base24 YAML parser (tinted-theming/schemes)
# =========================================================================

# base24 ANSI order per the tinted-theming base24 spec. Unlike base16,
# ANSI 8 is base03 and the bright colours come from base12..base17.
_BASE24_ANSI_ORDER = [
    "base00", "base08", "base0B", "base0A",
    "base0D", "base0E", "base0C", "base05",
    "base03", "base12", "base14", "base13",
    "base16", "base17", "base15", "base07",
]


def _prettify_stem(stem, strip_prefixes=()):
    """
    Turn a filename stem into a readable theme name.

    Strips an optional leading prefix (case-insensitive), then replaces
    hyphens/underscores with spaces and title-cases each word.
    """
    name = str(stem or "")
    low = name.lower()
    for prefix in strip_prefixes:
        if low.startswith(prefix):
            name = name[len(prefix):]
            break
    name = name.replace("_", " ").replace("-", " ").strip()
    pretty = " ".join(w.capitalize() for w in name.split())
    return pretty or str(stem or "")


def _base16_dict_to_ansi(bases):
    """
    Map a resolved base00..base0F dict to 16 ANSI RGB tuples.
    """
    return [
        bases.get("base00"),  #  0 Black
        bases.get("base08"),  #  1 Red
        bases.get("base0B"),  #  2 Green
        bases.get("base09"),  #  3 Yellow
        bases.get("base0D"),  #  4 Blue
        bases.get("base0E"),  #  5 Magenta
        bases.get("base0C"),  #  6 Cyan
        bases.get("base05"),  #  7 White
        bases.get("base02"),  #  8 Bright Black
        bases.get("base08"),  #  9 Bright Red
        bases.get("base0B"),  # 10 Bright Green
        bases.get("base0A"),  # 11 Bright Yellow
        bases.get("base0D"),  # 12 Bright Blue
        bases.get("base0E"),  # 13 Bright Magenta
        bases.get("base0C"),  # 14 Bright Cyan
        bases.get("base07"),  # 15 Bright White
    ]


def _set_base_theme_fields(theme, bases):
    """
    Assign the shared bg/fg/cursor/selection fields from a base dict.
    """
    theme["bg"] = bases.get("base00") or theme["ansi"][0]
    theme["fg"] = bases.get("base05") or theme["ansi"][7]
    theme["cursor"] = bases.get("base06")
    theme["cursor_text"] = bases.get("base00")
    theme["selection"] = bases.get("base02")
    theme["selected_text"] = bases.get("base06")
    theme["bold"] = None


def parse_base24_yaml(filepath):
    """
    Parse a tinted-theming base24 YAML scheme.

    base24 extends base16 with a full ANSI palette (base10..base17 hold
    the darker blacks and the bright variants).
    """
    filepath = Path(filepath)
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        data = _parse_yaml_simple(f.read())

    theme_name = data.get("name", data.get("scheme", filepath.stem))

    bases = {}
    for i in range(24):
        key = "base{:02X}".format(i)
        hexval = data.get(key, "")
        if hexval and not hexval.startswith("#"):
            hexval = "#" + hexval
        bases[key] = _hex_to_rgb(hexval)

    if not bases.get("base00") and not any(bases.values()):
        raise ValueError("Not a base24 palette: {}".format(filepath))

    theme = {
        "name": theme_name,
        "path": str(filepath),
        "source": "base24",
        "ansi": [bases.get(k) for k in _BASE24_ANSI_ORDER],
    }
    _fill_missing_ansi(theme)
    _set_base_theme_fields(theme, bases)
    return theme


# =========================================================================
# NvChad base46 (.lua) parser
# =========================================================================

def _lua_table_body(text, name):
    """
    Return the body of a Lua table assignment name = { ... } or None.
    """
    idx = text.find(name + " =")
    if idx == -1:
        idx = text.find(name + "=")
    if idx == -1:
        return None
    brace = text.find("{", idx)
    if brace == -1:
        return None
    depth = 0
    for pos in range(brace, len(text)):
        ch = text[pos]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[brace + 1:pos]
    return None


_HEX_INLINE = re.compile(r"([A-Za-z0-9_]+)\s*=\s*[\x27\x22]?(#[0-9A-Fa-f]{3,8})")
_BASE16_HEX = re.compile(r"(base[0-9A-Fa-f]{2})\s*=\s*[\x27\x22]?(#[0-9A-Fa-f]{3,8})")
_BASE16_REF = re.compile(r"(base[0-9A-Fa-f]{2})\s*=\s*M\.base_30\.([A-Za-z0-9_]+)")


def parse_base46_lua(filepath):
    """
    Parse an NvChad base46 Lua theme.

    Only the base_16 palette is used (base00..base0F, mapped like base16).
    Entries pointing at M.base_30.<name> are resolved from the base_30
    table in the same file.
    """
    filepath = Path(filepath)
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    body16 = _lua_table_body(text, "base_16")
    if body16 is None:
        raise ValueError("No base_16 table in base46 theme: {}".format(filepath))

    base30 = {}
    for m in _HEX_INLINE.finditer(_lua_table_body(text, "base_30") or ""):
        base30[m.group(1)] = m.group(2)

    bases = {}
    for m in _BASE16_HEX.finditer(body16):
        key = "base" + m.group(1)[4:].upper()
        bases[key] = _hex_to_rgb(m.group(2))
    for m in _BASE16_REF.finditer(body16):
        key = "base" + m.group(1)[4:].upper()
        bases.setdefault(key, _hex_to_rgb(base30.get(m.group(2), "")))

    if not bases.get("base00"):
        raise ValueError("Not a base46 palette: {}".format(filepath))

    theme = {
        "name": _prettify_stem(filepath.stem),
        "path": str(filepath),
        "source": "nvchad",
        "ansi": _base16_dict_to_ansi(bases),
    }
    _fill_missing_ansi(theme)
    _set_base_theme_fields(theme, bases)
    return theme


# =========================================================================
# kitty (.conf) parser
# =========================================================================

# kitty keyword values that alias another colour key in the same file.
_KITTY_KEYWORD_ALIASES = {
    "background": "background",
    "foreground": "foreground",
}


def parse_kitty_conf(filepath):
    """Parse a kitty theme file (.conf) from kovidgoyal/kitty-themes.

    kitty format (line based, '#' starts a full-line comment):
        ## name: Dracula
        foreground            #f8f8f2
        background            #282a36
        selection_background  #44475a
        selection_foreground  #ffffff
        cursor                #f8f8f2
        cursor_text_color     background
        color0 .. color15     #rrggbb
    """
    filepath = Path(filepath)
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    raw = {}
    theme_name = filepath.stem

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Metadata comment: "## name: Dracula".
        if stripped.startswith("##"):
            body = stripped[2:].strip()
            if ":" in body:
                meta_key, _, meta_val = body.partition(":")
                if meta_key.strip().lower() == "name" and meta_val.strip():
                    theme_name = meta_val.strip()
            continue
        # Full-line comment.
        if stripped.startswith("#"):
            continue

        parts = stripped.split(None, 1)
        if len(parts) != 2:
            continue

        key = parts[0].strip().lower()
        val = parts[1].strip()
        if val.startswith("#"):
            # Hex colour; keep the first token, dropping any trailing note.
            val = val.split()[0]
        elif "#" in val:
            val = val.split("#", 1)[0].strip()

        if key and val:
            raw[key] = val

    theme = {
        "name": theme_name,
        "path": str(filepath),
        "source": "kitty",
        "ansi": [],
    }

    for i in range(16):
        theme["ansi"].append(_hex_to_rgb(raw.get(f"color{i}", "")))

    _fill_missing_ansi(theme)

    theme["bg"] = _hex_to_rgb(raw.get("background", "")) or theme["ansi"][0]
    theme["fg"] = _hex_to_rgb(raw.get("foreground", "")) or theme["ansi"][7]

    def _resolve(value):
        """Resolve a hex value or a kitty keyword such as 'background'."""
        if not value:
            return None
        alias = _KITTY_KEYWORD_ALIASES.get(value.lower().strip())
        if alias == "background":
            return _hex_to_rgb(raw.get("background", "")) or theme["bg"]
        if alias == "foreground":
            return _hex_to_rgb(raw.get("foreground", "")) or theme["fg"]
        return _hex_to_rgb(value)

    theme["cursor"] = _resolve(raw.get("cursor"))
    theme["cursor_text"] = _resolve(raw.get("cursor_text_color"))
    theme["selection"] = _hex_to_rgb(raw.get("selection_background", "")) or None
    theme["selected_text"] = _hex_to_rgb(raw.get("selection_foreground", "")) or None
    theme["bold"] = None

    return theme


# =========================================================================
# Unified parser — dispatch by file extension
# =========================================================================

def parse_theme_file(filepath):
    """Auto-detect format and parse any supported theme file."""
    filepath = Path(filepath)
    ext = filepath.suffix.lower()

    if ext == ".itermcolors":
        return parse_itermcolors(filepath)
    elif ext == ".conf":
        return parse_kitty_conf(filepath)
    elif ext == ".lua":
        return parse_base46_lua(filepath)
    elif ext in (".yml", ".yaml"):
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(2000)
        if "color_01:" in content or "color_02:" in content:
            return parse_gogh_yaml(filepath)
        elif "base24" in content:
            return parse_base24_yaml(filepath)
        elif "base00:" in content or "base00 :" in content:
            return parse_base16_yaml(filepath)
        elif "palette:" in content and ("base0" in content or "base1" in content):
            return parse_base16_yaml(filepath)
        else:
            try:
                return parse_gogh_yaml(filepath)
            except Exception:
                return parse_base16_yaml(filepath)
    else:
        raise ValueError(f"Unsupported file format: {ext}")


# =========================================================================
# Defaults and scanning
# =========================================================================

def _fill_missing_ansi(theme):
    """Fill missing ANSI colors with reasonable defaults."""
    defaults = [
        (0.0, 0.0, 0.0),       # 0  black
        (0.8, 0.0, 0.0),       # 1  red
        (0.0, 0.8, 0.0),       # 2  green
        (0.8, 0.8, 0.0),       # 3  yellow
        (0.0, 0.0, 0.8),       # 4  blue
        (0.8, 0.0, 0.8),       # 5  magenta
        (0.0, 0.8, 0.8),       # 6  cyan
        (0.75, 0.75, 0.75),    # 7  white
        (0.5, 0.5, 0.5),       # 8  bright black
        (1.0, 0.0, 0.0),       # 9  bright red
        (0.0, 1.0, 0.0),       # 10 bright green
        (1.0, 1.0, 0.0),       # 11 bright yellow
        (0.0, 0.0, 1.0),       # 12 bright blue
        (1.0, 0.0, 1.0),       # 13 bright magenta
        (0.0, 1.0, 1.0),       # 14 bright cyan
        (1.0, 1.0, 1.0),       # 15 bright white
    ]
    for i in range(16):
        if theme["ansi"][i] is None:
            theme["ansi"][i] = defaults[i]


SUPPORTED_EXTENSIONS = {".itermcolors", ".yml", ".yaml", ".conf", ".lua"}


def is_dark_file(filepath, default=True):
    """Classify a theme file as dark or light from its background colour.

    Best-effort: returns *default* when the file cannot be parsed.
    """
    try:
        from . import color_math as cm
        bg = parse_theme_file(filepath).get("bg")
        if not bg:
            return default
        return cm.is_dark(bg)
    except Exception:
        return default


def scan_folder_detailed(folder_path):
    """
    Scan a folder for supported theme files.

    Returns a list of dicts with name, path, source and dark, using each
    file parsed display name. Files that do not yield a usable palette
    are skipped. Deduplicates by lowercase name within the folder.
    """
    folder = Path(folder_path)
    themes = []
    if not folder.is_dir():
        return themes

    from . import color_math as cm

    seen_names = set()

    def _scan_dir(d, depth=0):
        if depth > 2:
            return
        try:
            entries = sorted(d.iterdir(), key=lambda x: x.name.lower())
        except PermissionError:
            return
        for f in entries:
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
                try:
                    parsed = parse_theme_file(str(f))
                except Exception:
                    continue
                if not parsed or not parsed.get("bg"):
                    continue
                name = parsed.get("name") or f.stem
                key = name.lower()
                if key in seen_names:
                    continue
                seen_names.add(key)
                try:
                    dark = bool(cm.is_dark(parsed.get("bg")))
                except Exception:
                    dark = True
                themes.append({
                    "name": name,
                    "path": str(f),
                    "source": parsed.get("source", ""),
                    "dark": dark,
                })
            elif f.is_dir() and depth < 2:
                _scan_dir(f, depth + 1)

    _scan_dir(folder)
    themes.sort(key=lambda t: t["name"].lower())
    return themes


def scan_folder(folder_path):
    """
    Scan a folder for supported theme files and return (name, path) tuples.
    """
    return [(t["name"], t["path"]) for t in scan_folder_detailed(folder_path)]

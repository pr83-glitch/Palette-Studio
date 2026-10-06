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
Repository management for downloading and caching color scheme repos.

Supports five remote sources and one local source:
  - NvChad base46                   ~105 .lua   (on by default)
  - iTerm2-Color-Schemes            ~250 .itermcolors
  - tinted-theming base24           ~230 .yaml
  - kovidgoyal kitty-themes         ~412 .conf
  - alacritty/alacritty-theme       ~177 .toml
  - Noctalia schemes                ~11 local .json (dark + light each) plus
    noctalia-dev/community-palettes, downloaded like the other sources

All sources are downloaded as zip archives and extracted to separate
subdirectories. The index is always built from every cached source (a
superset), so the per-source toggles in preferences only hide/show
themes without forcing a re-download.

The same-named themes from different sources are all indexed; the
browser distinguishes them with a per-row source tag. iTerm2 .itermcolors,
Gogh .yml, kitty .conf, Alacritty .toml, base16/base24 .yaml, base46 .lua and
Noctalia .json files can also be loaded from a local folder.

Sources are pinned to reviewed upstream commits (see SOURCES) so a
download always fetches a known, reproducible snapshot. To update a
source: review the upstream repository, pick the new commit, and replace
that source's ``revision`` here after confirming the archive layout and
theme count still match.
"""

import os
import json
import time
import shutil
import zipfile
import io
from pathlib import Path


# =========================================================================
# Source definitions
# =========================================================================

# Sources are pinned to reviewed commits, not moving branches. The
# iTerm2 snapshot alone is ~31 MB compressed / ~23k entries, so the
# limits below leave generous headroom while still rejecting oversized
# or malformed archives.
_GITHUB_ARCHIVE = "https://github.com/{repo}/archive/{revision}.zip"

_MAX_DOWNLOAD_BYTES = 128 * 1024 * 1024
_MAX_ARCHIVE_ENTRIES = 100000
_MAX_TOTAL_UNCOMPRESSED_BYTES = 256 * 1024 * 1024
_MAX_THEME_FILE_BYTES = 8 * 1024 * 1024
_DOWNLOAD_CHUNK = 256 * 1024
_USER_AGENT = "PaletteStudio/1.1.0 (Blender add-on)"

# Local Noctalia schemes and the community-palettes download are ONE source in
# the UI ("Noctalia"), so both are indexed under this tag and a single Settings
# toggle governs them.
NOCTALIA_TAG = "noctalia"

SOURCES = {
    "nvchad": {
        "name": "NvChad base46",
        "repo": "NvChad/base46",
        "revision": "7df2bd89295db00b649cbc49bdf6fe5a1cc5df3b",
        "subdir": "themes",
        "extensions": {".lua"},
    },
    "iterm": {
        "name": "iTerm2-Color-Schemes",
        "repo": "mbadolato/iTerm2-Color-Schemes",
        "revision": "e49327f3d0fc3d5a4efc7e822b8d1489ef2eb66f",
        "subdir": "schemes",
        "extensions": {".itermcolors"},
    },
    "base24": {
        "name": "tinted-theming base24",
        "repo": "tinted-theming/schemes",
        "revision": "50f6e3b93a8f62db9d839f8b79a709c1bbdaac53",
        "subdir": "base24",
        "extensions": {".yaml"},
    },
    "kitty": {
        "name": "kitty-themes",
        "repo": "kovidgoyal/kitty-themes",
        "revision": "b95a97da1fad87263452590d74212499bd120de7",
        "subdir": "themes",
        "extensions": {".conf"},
    },
    "alacritty": {
        "name": "alacritty-theme",
        "repo": "alacritty/alacritty-theme",
        "revision": "ab88d5a80d676b5dc6157e91aba8067f2078dc94",
        "subdir": "themes",
        "extensions": {".toml"},
    },
    "community_palettes": {
        "name": "Noctalia community palettes",
        "repo": "noctalia-dev/community-palettes",
        "revision": "31b46f7e5af97f70bb6e46fab73ebf219a4d55ef",
        "subdir": "",
        "extensions": {".json"},
        "tag": NOCTALIA_TAG,
    },
}


def _source_url(src):
    """Build the pinned archive URL for a source definition."""
    return _GITHUB_ARCHIVE.format(repo=src["repo"], revision=src["revision"])


def get_cache_dir():
    """Get the cache directory path. Creates it if needed.

    Uses Blender's extension_path_user which is the only approved
    storage location for extensions platform add-ons.
    """
    import bpy
    try:
        cache = bpy.utils.extension_path_user(__package__, path="cache", create=True)
    except Exception as ex:
        raise RuntimeError(
            f"[Palette] Could not create extension cache directory: {ex}"
        ) from ex
    return cache


# Add-on package names the extension used before it was renamed to
# Palette Studio. Used only for one-time preference/cache migration.
LEGACY_PACKAGES = (
    "palette_custom",
    "bl_ext.user_default.palette_custom",
    "bl_ext.blender_org.palette_custom",
)


def migrate_legacy_cache():
    """Copy the pre-rename cache into the new extension's cache dir, once.

    Best-effort: skips silently when there is no legacy cache or the new
    cache already holds data, so it never blocks registration.
    """
    import bpy

    try:
        new_dir = get_cache_dir()
    except Exception:
        return False

    try:
        if os.path.isdir(new_dir) and os.listdir(new_dir):
            return False
    except OSError:
        return False

    for legacy in LEGACY_PACKAGES:
        try:
            old_dir = bpy.utils.extension_path_user(legacy, path="cache", create=False)
        except Exception:
            continue
        if not old_dir or not os.path.isdir(old_dir):
            continue
        if os.path.abspath(old_dir) == os.path.abspath(new_dir):
            continue
        try:
            shutil.copytree(old_dir, new_dir, dirs_exist_ok=True)
            return True
        except Exception:
            continue
    return False


def get_index_path():
    """Get the index JSON file path."""
    return os.path.join(get_cache_dir(), "theme_index.json")


def load_index():
    """Load the theme index from disk."""
    index_path = get_index_path()
    if os.path.exists(index_path):
        with open(index_path, "r") as f:
            return json.load(f)
    return {"themes": [], "last_updated": 0, "sources": []}


def save_index(index_data):
    """Save the theme index to disk."""
    index_path = get_index_path()
    with open(index_path, "w") as f:
        json.dump(index_data, f, indent=2)


def has_index():
    """True when a saved index exists and still points at real theme files."""
    try:
        themes = load_index().get("themes", [])
    except Exception:
        return False
    if not themes:
        return False
    return any(os.path.exists(t.get("path", "")) for t in themes)


def clear_cache():
    """Delete all cached theme files and the saved index.

    Returns the number of top-level entries removed. Missing or locked
    entries are skipped rather than raising, so Unload can never fail
    because of a single stubborn file.
    """
    try:
        cache_dir = get_cache_dir()
    except Exception:
        return 0
    if not os.path.isdir(cache_dir):
        return 0

    removed = 0
    for entry in os.listdir(cache_dir):
        target = os.path.join(cache_dir, entry)
        try:
            if os.path.isdir(target):
                shutil.rmtree(target)
            else:
                os.remove(target)
            removed += 1
        except OSError:
            continue
    return removed


# ----------------------------------------------------------------------
# Noctalia: local schemes and the one Noctalia is currently using
# ----------------------------------------------------------------------

def _config_home():
    """$XDG_CONFIG_HOME, or ~/.config."""
    return os.environ.get("XDG_CONFIG_HOME") or os.path.join(
        os.path.expanduser("~"), ".config")


def get_noctalia_dir():
    """Path of Noctalia's config directory."""
    return os.path.join(_config_home(), "noctalia")


def get_kitty_noctalia_path():
    """The kitty theme Noctalia rewrites with the colours it is showing.

    Noctalia regenerates this file on every palette change, INCLUDING
    wallpaper-generated palettes - those never appear in `settings.json`, so
    `noctalia_current_scheme()` cannot see them. That makes this file the
    truthful source for "the Noctalia colours right now". It is plain kitty
    syntax, so the existing kitty parser reads it unchanged.
    """
    return os.path.join(_config_home(), "kitty", "themes", "noctalia.conf")


def _noctalia_scheme_paths():
    """Paths of every local Noctalia scheme, sorted by folder name."""
    root = os.path.join(get_noctalia_dir(), "colorschemes")
    paths = []
    try:
        names = sorted(os.listdir(root), key=str.lower)
    except OSError:
        return paths
    for name in names:
        path = os.path.join(root, name, name + ".json")
        if os.path.isfile(path):
            paths.append(path)
    return paths


def noctalia_local_themes():
    """Index entries for every local Noctalia scheme (dark and light).

    No network and no cache: these are real files in the user's config, so
    they are simply indexed alongside whatever was downloaded.
    """
    from .iterm_parser import noctalia_variants

    entries = []
    for path in _noctalia_scheme_paths():
        name = os.path.basename(os.path.dirname(path))
        for variant in noctalia_variants(path):
            entries.append({
                "name": "%s (%s)" % (name, variant.capitalize()),
                "path": path,
                "source": NOCTALIA_TAG,
                "dark": variant == "dark",
                "variant": variant,
            })
    return entries


# ``settings.json`` is read on every Settings draw, so the answer is cached on
# the file's mtime instead of being re-parsed.
_noctalia_probe = {"stamp": None, "value": None}


def _read_noctalia_current(settings):
    """Resolve (name, variant, path) from a Noctalia settings.json."""
    from .iterm_parser import noctalia_variants

    try:
        with open(settings, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
    except Exception:
        return None
    schemes = data.get("colorSchemes") if isinstance(data, dict) else None
    if not isinstance(schemes, dict):
        return None
    name = str(schemes.get("predefinedScheme") or "").strip()
    if not name:
        return None
    variant = "dark" if schemes.get("darkMode", True) else "light"
    path = os.path.join(get_noctalia_dir(), "colorschemes", name, name + ".json")
    if not os.path.isfile(path):
        return None
    present = noctalia_variants(path)
    if not present:
        return None
    if variant not in present:
        variant = present[0]
    return (name, variant, path)


def noctalia_current_scheme():
    """(name, variant, path) of the scheme Noctalia uses now, else None.

    Noctalia records the active scheme in ``settings.json``:
    ``colorSchemes.predefinedScheme`` names it, ``colorSchemes.darkMode``
    picks the variant.
    """
    settings = os.path.join(get_noctalia_dir(), "settings.json")
    try:
        stamp = os.path.getmtime(settings)
    except OSError:
        return None
    if _noctalia_probe.get("stamp") != stamp:
        _noctalia_probe["stamp"] = stamp
        _noctalia_probe["value"] = _read_noctalia_current(settings)
    return _noctalia_probe["value"]


def noctalia_sync_source():
    """What the Sync Current Theme button should pull, or None.

    Returns ``("kitty", path)`` for the terminal theme Noctalia keeps up to
    date (preferred - it reflects wallpaper-generated palettes too), else
    ``("scheme", (name, variant, path))`` for the scheme recorded in
    ``settings.json``, else None.
    """
    kitty = get_kitty_noctalia_path()
    if os.path.isfile(kitty):
        return ("kitty", kitty)
    scheme = noctalia_current_scheme()
    if scheme:
        return ("scheme", scheme)
    return None


def index_local_folder(folder_path):
    """Scan a local folder for supported theme files and build an index."""
    from .iterm_parser import scan_folder_detailed

    themes = scan_folder_detailed(folder_path)
    entries = [
        {"name": t["name"], "path": t["path"], "source": "local",
         "dark": t["dark"], "variant": t.get("variant", "")}
        for t in themes
    ]
    # The local Noctalia schemes live outside the chosen folder but are local
    # files all the same, so they stay listed in LOCAL mode too.
    entries.extend(noctalia_local_themes())
    index = {
        "themes": entries,
        "last_updated": time.time(),
        "sources": ["local", NOCTALIA_TAG],
    }
    save_index(index)
    return index


def _download_bytes(url, progress_callback=None):
    """Stream a URL into memory, refusing anything over the size cap.

    TLS certificate verification is always enforced; a failed handshake
    raises instead of silently retrying without verification.
    """
    import urllib.request
    import urllib.error
    import ssl

    context = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})

    chunks = []
    total = 0
    with urllib.request.urlopen(req, context=context, timeout=120) as response:
        declared = response.headers.get("Content-Length")
        if declared:
            try:
                declared_bytes = int(declared)
            except ValueError:
                declared_bytes = 0
            if declared_bytes > _MAX_DOWNLOAD_BYTES:
                raise ValueError(
                    f"Download is larger than "
                    f"{_MAX_DOWNLOAD_BYTES // (1024 * 1024)} MB"
                )
        while True:
            chunk = response.read(_DOWNLOAD_CHUNK)
            if not chunk:
                break
            total += len(chunk)
            if total > _MAX_DOWNLOAD_BYTES:
                raise ValueError(
                    f"Download exceeded "
                    f"{_MAX_DOWNLOAD_BYTES // (1024 * 1024)} MB"
                )
            chunks.append(chunk)

    return b"".join(chunks)


def _extract_theme_files(zip_bytes, cache_subdir, extensions, repo_subdir=None):
    """Extract matching theme files from an in-memory zip archive.

    Only flat basenames inside ``cache_subdir`` are written, so archive
    paths can never escape the cache directory. Archive entry count and
    total uncompressed size are capped to reject zip bombs.
    """
    count = 0
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        infos = [info for info in zf.infolist() if not info.is_dir()]
        if len(infos) > _MAX_ARCHIVE_ENTRIES:
            raise ValueError(f"Archive has too many entries ({len(infos)})")

        total_uncompressed = 0
        for info in infos:
            total_uncompressed += info.file_size
            if total_uncompressed > _MAX_TOTAL_UNCOMPRESSED_BYTES:
                raise ValueError("Archive is too large when uncompressed")

            filename = info.filename.replace("\\", "/")
            basename = os.path.basename(filename)
            if not basename or basename in (".", ".."):
                continue

            _, ext = os.path.splitext(basename)
            if ext.lower() not in extensions:
                continue

            # Filter by subdir if specified (e.g. only files under "schemes/")
            if repo_subdir and repo_subdir not in filename.split("/"):
                continue

            # Skip config/template files
            if basename.lower() in ('config.yaml', 'config.yml', '.yaml', '.yml'):
                continue

            if info.file_size > _MAX_THEME_FILE_BYTES:
                continue

            target = os.path.join(cache_subdir, basename)
            with zf.open(info) as src, open(target, 'wb') as dst:
                shutil.copyfileobj(src, dst, _DOWNLOAD_CHUNK)
            count += 1

    return count


def _download_and_extract(url, cache_subdir, extensions, repo_subdir=None, progress_callback=None):
    """
    Download a zip from url, extract files matching extensions
    into cache_subdir. If repo_subdir is set, only extract files
    from paths containing that directory name.
    Returns count of extracted files.
    """
    os.makedirs(cache_subdir, exist_ok=True)

    if progress_callback:
        progress_callback(f"Downloading from {url[:60]}...")

    data = _download_bytes(url, progress_callback=progress_callback)

    if progress_callback:
        progress_callback("Extracting themes...")

    try:
        return _extract_theme_files(data, cache_subdir, extensions, repo_subdir)
    except zipfile.BadZipFile as ex:
        raise ValueError(f"Downloaded file is not a valid zip: {ex}") from ex


def download_repo(repo_url=None, progress_callback=None):
    """
    Legacy single-source download. Downloads iTerm2-Color-Schemes.
    Returns the index data dict.
    """
    if repo_url is None:
        repo_url = _source_url(SOURCES["iterm"])

    cache_dir = get_cache_dir()
    schemes_dir = os.path.join(cache_dir, "schemes")

    count = _download_and_extract(
        repo_url, schemes_dir, {".itermcolors"},
        repo_subdir="schemes",
        progress_callback=progress_callback,
    )

    if progress_callback:
        progress_callback(f"Extracted {count} themes.")

    return index_local_folder(schemes_dir)


def _scan_sources(cache_dir, source_keys):
    """Scan cached source directories and build a unified index dict.

    Duplicate names are only removed within a single source (by
    ``scan_folder``); the same name from different sources is kept and
    later distinguished by its source tag.

    No network access: only looks at what is already on disk. Shared by
    the download path and the cache-only refresh path.
    """
    from .iterm_parser import scan_folder_detailed

    all_themes = []
    sources_done = []

    for source_key in source_keys:
        src = SOURCES.get(source_key)
        if not src:
            continue

        source_dir = os.path.join(cache_dir, source_key)
        if not os.path.isdir(source_dir):
            # Try legacy "schemes" dir for iterm
            if source_key == "iterm":
                source_dir = os.path.join(cache_dir, "schemes")
                if not os.path.isdir(source_dir):
                    continue
            else:
                continue

        tag = src.get("tag", source_key)
        for entry in scan_folder_detailed(source_dir):
            # Same-named themes from different sources are all kept; the
            # source tag in the browser distinguishes them.
            all_themes.append({
                "name": entry["name"],
                "path": entry["path"],
                "source": tag,
                "dark": entry["dark"],
                "variant": entry.get("variant", ""),
            })

        sources_done.append(source_key)

    # Local Noctalia schemes need no download - they are on disk whenever
    # Noctalia is installed. When a scheme exists both locally and in the
    # downloaded community collection it is listed ONCE, from the local file:
    # that is the copy Noctalia is using, and the one Sync reads.
    local_noctalia = noctalia_local_themes()
    if local_noctalia:
        local_names = {e["name"].lower() for e in local_noctalia}
        all_themes = [t for t in all_themes
                      if t.get("source") != NOCTALIA_TAG
                      or t["name"].lower() not in local_names]
        all_themes.extend(local_noctalia)
        if NOCTALIA_TAG not in sources_done:
            sources_done.append(NOCTALIA_TAG)

    all_themes.sort(key=lambda t: t["name"].lower())

    return {
        "themes": all_themes,
        "last_updated": time.time(),
        "sources": sources_done,
    }


def _cached_source_keys(cache_dir):
    """Every source key whose download directory exists on disk.

    The index is built from this union rather than only the sources the
    user currently has enabled, so toggling a source in preferences can
    show/hide already-cached themes without another download.
    """
    keys = []
    for key in SOURCES:
        if os.path.isdir(os.path.join(cache_dir, key)):
            keys.append(key)
        elif key == "iterm" and os.path.isdir(os.path.join(cache_dir, "schemes")):
            # Legacy download location used before the per-source layout.
            keys.append(key)
    return keys


def download_sources(enabled_sources, progress_callback=None):
    """
    Download multiple sources and build a unified, deduplicated index.

    Args:
        enabled_sources: list of source keys, e.g. ["nvchad", "iterm", "base24"]
        progress_callback: optional function(msg: str)

    Returns the combined index data dict.
    """
    cache_dir = get_cache_dir()
    sources_done = []

    for source_key in enabled_sources:
        src = SOURCES.get(source_key)
        if not src:
            continue

        source_dir = os.path.join(cache_dir, source_key)

        try:
            if progress_callback:
                progress_callback(f"Downloading {src['name']}...")

            count = _download_and_extract(
                _source_url(src), source_dir, src["extensions"],
                repo_subdir=src.get("subdir"),
                progress_callback=progress_callback,
            )

            if progress_callback:
                progress_callback(f"{src['name']}: {count} themes extracted.")

            sources_done.append(source_key)

        except Exception as e:
            if progress_callback:
                progress_callback(f"Warning: {src['name']} failed: {e}")
            # Continue with other sources
            continue

    # Index every cached source (a superset of the enabled/downloaded set)
    # so the preference toggles are pure visibility filters.
    cached = _cached_source_keys(cache_dir)
    index = _scan_sources(cache_dir, cached)
    index["sources"] = cached
    save_index(index)

    if progress_callback:
        visible = sum(1 for t in index["themes"] if t.get("source") in sources_done)
        progress_callback(
            f"Total: {visible} themes available from {len(sources_done)} enabled source(s); "
            f"{len(index['themes'])} cached."
        )

    return index


def get_theme_list():
    """Get the current list of themes from the index."""
    index = load_index()
    return index.get("themes", [])


def ensure_index_flags():
    """Backfill per-theme metadata (dark flag) on indexes written by older
    versions, then persist. No-op once every entry carries the flag."""
    try:
        index = load_index()
    except Exception:
        return

    themes = index.get("themes", [])
    if not themes or all("dark" in t for t in themes):
        return

    from .iterm_parser import is_dark_file

    for t in themes:
        if "dark" not in t:
            t["dark"] = is_dark_file(t.get("path", ""))

    try:
        save_index(index)
    except Exception:
        pass


def search_themes(query, theme_list=None):
    """Filter theme list by search query (fuzzy match — characters must appear in order)."""
    if theme_list is None:
        theme_list = get_theme_list()
    if not query:
        return theme_list
    q = query.lower()

    results = []
    for t in theme_list:
        name_lower = t["name"].lower()
        # Fuzzy: each char in query must appear in order
        qi = 0
        for ch in name_lower:
            if qi < len(q) and ch == q[qi]:
                qi += 1
        if qi == len(q):
            results.append(t)

    return results

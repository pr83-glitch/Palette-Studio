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
import tempfile
import stat
import math
from contextlib import contextmanager


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
_USER_AGENT = "PaletteStudio/1.2.1 (Blender add-on)"

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


def rebase_cache_path(path, old_dir, new_dir):
    """Move only paths inside a legacy cache; external local palettes stay put."""
    if not path:
        return path
    try:
        if os.path.commonpath((os.path.abspath(path), os.path.abspath(old_dir))) == os.path.abspath(old_dir):
            return os.path.join(new_dir, os.path.relpath(path, old_dir))
    except ValueError:
        pass
    return path


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
            index = load_index()
            for theme in index["themes"]:
                theme['path'] = rebase_cache_path(theme['path'], old_dir, new_dir)
            save_index(index)
            return True
        except Exception:
            continue
    return False


# LOCAL and REMOTE keep separate index files so switching the source mode can
# never overwrite the other mode's snapshot. The remote filename is unchanged,
# so an existing cache keeps loading exactly as before.
INDEX_REMOTE = "remote"
INDEX_LOCAL = "local"


def _index_filename(mode):
    """Index filename for a mode; the legacy name stays the remote one."""
    return "theme_index.json" if mode == INDEX_REMOTE else "theme_index_local.json"


def get_index_path(mode=INDEX_REMOTE):
    """Get the index JSON file path for a mode (remote by default)."""
    return os.path.join(get_cache_dir(), _index_filename(mode))


def _index_path(cache_dir=None, mode=INDEX_REMOTE):
    """Index path for an explicit cache directory, else the resolved one."""
    filename = _index_filename(mode)
    return os.path.join(cache_dir, filename) if cache_dir else get_index_path(mode)


def _validate_index(data):
    """Validate the consumed fields, while retaining legacy optional metadata."""
    if not isinstance(data, dict) or not isinstance(data.get("themes"), list):
        raise ValueError("Invalid theme index")
    if not isinstance(data.get("sources"), list) or not all(isinstance(s, str) for s in data["sources"]):
        raise ValueError("Invalid index sources")
    stamp = data.get("last_updated")
    if isinstance(stamp, bool) or not isinstance(stamp, (int, float)) or not math.isfinite(stamp):
        raise ValueError("Invalid index timestamp")
    for theme in data["themes"]:
        if not isinstance(theme, dict) or not all(isinstance(theme.get(k), str) for k in ("name", "path", "source")):
            raise ValueError("Invalid theme entry")
        if "dark" in theme and not isinstance(theme["dark"], bool):
            raise ValueError("Invalid dark flag")
        if "variant" in theme and not isinstance(theme["variant"], str):
            raise ValueError("Invalid variant")
    return data


def load_index(mode=INDEX_REMOTE):
    """Read one complete validated snapshot; corrupt/missing caches are empty.

    ``mode`` selects LOCAL or REMOTE; REMOTE is the default so existing
    callers keep reading the legacy index file unchanged.
    """
    try:
        with open(_index_path(mode=mode), "r", encoding="utf-8") as f:
            return _validate_index(json.load(f))
    except (OSError, ValueError, TypeError):
        return {"themes": [], "last_updated": 0, "sources": []}


def save_index(index_data, cache_dir=None, mode=INDEX_REMOTE):
    """Validate and atomically replace the index, retaining the old on failure.

    ``cache_dir`` lets a worker thread publish without resolving the cache
    through Blender; when omitted the cache path is looked up as usual.
    ``mode`` picks the LOCAL or REMOTE index file (REMOTE by default).
    """
    _validate_index(index_data)
    index_path = _index_path(cache_dir, mode)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=os.path.dirname(index_path),
                                         prefix=".theme-index-", delete=False) as f:
            temporary = f.name
            json.dump(index_data, f, indent=2, allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, index_path)
    finally:
        if temporary and os.path.exists(temporary):
            os.remove(temporary)


def has_index(mode=INDEX_REMOTE):
    """True when a saved index exists and still points at real theme files."""
    try:
        themes = load_index(mode).get("themes", [])
    except Exception:
        return False
    if not themes:
        return False
    return any(os.path.isfile(t["path"]) for t in themes)


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


def _merge_local_noctalia(themes):
    """Add the user's own Noctalia schemes to an index, without duplicates.

    The local schemes are the files Noctalia itself reads, so they win over a
    downloaded community copy of the same scheme. Duplicates are matched by
    name for the ``noctalia`` source and by path otherwise - the latter covers
    a local folder scan that already found the very same scheme file (e.g. the
    folder IS ``<config>/noctalia/colorschemes``). The same helper is used by
    the download path and the local-folder path so both write one identical
    index.
    """
    local = noctalia_local_themes()
    if not local:
        return list(themes)
    local_names = {e["name"].lower() for e in local}
    local_paths = {os.path.realpath(e["path"]) for e in local}
    kept = []
    for theme in themes:
        if (theme.get("source") == NOCTALIA_TAG
                and theme["name"].lower() in local_names):
            continue
        if os.path.realpath(theme["path"]) in local_paths:
            continue
        kept.append(theme)
    kept.extend(local)
    return kept


# ``settings.json`` is read on every Settings draw, so the answer is cached on
# the file's mtime instead of being re-parsed.
_noctalia_probe = {"stamp": None, "value": None}


def _read_noctalia_current(settings):
    """Resolve (name, variant, path) from a Noctalia settings.json."""
    from .iterm_parser import noctalia_variants

    _noctalia_probe['scheme_path'] = None
    try:
        with open(settings, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
    except Exception:
        return None
    schemes = data.get("colorSchemes") if isinstance(data, dict) else None
    if not isinstance(schemes, dict):
        return None
    name = str(schemes.get("predefinedScheme") or "").strip()
    if not name or name in ('.', '..') or any(c in name for c in '/\\:'):
        return None
    variant = "dark" if schemes.get("darkMode", True) else "light"
    path = os.path.join(get_noctalia_dir(), "colorschemes", name, name + ".json")
    _noctalia_probe['scheme_path'] = path
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

    def signature(path):
        try:
            info = os.stat(path)
            return (info.st_mtime_ns, info.st_ctime_ns, info.st_size, info.st_ino)
        except OSError:
            return None

    # Revalidate just the selected file, including a previously missing one;
    # scanning/statting every installed scheme on each draw is unnecessary.
    def probe_stamp():
        path = _noctalia_probe.get('scheme_path')
        return (settings, signature(settings), path, signature(path) if path else None)

    if _noctalia_probe.get("stamp") != probe_stamp():
        _noctalia_probe["value"] = _read_noctalia_current(settings)
        _noctalia_probe["stamp"] = probe_stamp()
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


def index_local_folder(folder_path, cache_dir=None, cancel=None):
    """Scan a local folder for supported theme files and build an index."""
    from .iterm_parser import scan_folder_detailed

    _check_cancel(cancel)
    themes = scan_folder_detailed(folder_path)
    _check_cancel(cancel)
    entries = [
        {"name": t["name"], "path": t["path"], "source": "local",
         "dark": t["dark"], "variant": t.get("variant", "")}
        for t in themes
    ]
    # The local Noctalia schemes live outside the chosen folder but are local
    # files all the same, so they stay listed in LOCAL mode too - and only
    # once, even when the chosen folder is the Noctalia scheme directory.
    entries = _merge_local_noctalia(entries)
    entries.sort(key=lambda t: t["name"].lower())
    index = {
        "themes": entries,
        "last_updated": time.time(),
        "sources": ["local", NOCTALIA_TAG],
    }
    _check_cancel(cancel)
    save_index(index, cache_dir, INDEX_LOCAL)
    return index


class DownloadCancelled(Exception):
    """Raised when a caller-supplied cancellation signal fires mid-download.

    Callers (the async operator) catch this separately from real failures: the
    cache and index are left exactly as they were before the call.
    """


def _is_cancelled(cancel):
    """True when the caller's cancellation signal asks to stop.

    ``cancel`` is ``None`` (never cancelled), a ``threading.Event``-like object
    with ``is_set()``, or a zero-argument callable. Probes are cheap and never
    touch Blender state; a probe that raises is treated as a request to stop, so
    a broken callback can only end the download early, never break the cache.
    """
    if cancel is None:
        return False
    try:
        is_set = getattr(cancel, "is_set", None)
        if callable(is_set):
            return bool(is_set())
        return bool(cancel())
    except Exception:
        return True


def _check_cancel(cancel):
    """Raise :class:`DownloadCancelled` when the signal is set."""
    if _is_cancelled(cancel):
        raise DownloadCancelled("Theme download cancelled")


def _download_bytes(url, cancel=None):
    """Stream a URL into memory, refusing anything over the size cap.

    ``cancel`` is polled between chunks, so a cancelled download stops within
    one chunk read (the 30-second socket timeout bounds that wait) and leaves
    no partial file behind. TLS certificate verification is always enforced; a
    failed handshake raises instead of silently retrying without verification.
    """
    import urllib.request
    import ssl

    context = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})

    chunks = []
    total = 0
    deadline = time.monotonic() + 120
    with urllib.request.urlopen(req, context=context, timeout=30) as response:
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
        read_chunk = getattr(response, 'read1', response.read)
        while True:
            _check_cancel(cancel)
            if time.monotonic() >= deadline:
                raise TimeoutError("Theme download exceeded the 120-second budget")
            chunk = read_chunk(_DOWNLOAD_CHUNK)
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
    if os.path.islink(cache_subdir) or os.path.realpath(cache_subdir) != os.path.abspath(cache_subdir):
        raise ValueError("Extraction directory must not traverse symlinks")
    count = 0
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        infos = zf.infolist()
        if len(infos) > _MAX_ARCHIVE_ENTRIES:
            raise ValueError(f"Archive has too many entries ({len(infos)})")

        total_uncompressed = 0
        for info in infos:
            if info.is_dir():
                continue
            total_uncompressed += info.file_size
            if total_uncompressed > _MAX_TOTAL_UNCOMPRESSED_BYTES:
                raise ValueError("Archive is too large when uncompressed")

            filename = info.filename.replace("\\", "/")
            basename = filename.rsplit("/", 1)[-1]
            # Flattening must remain safe on Windows too (ADS, drive letters,
            # device names and trailing dots/spaces), irrespective of host OS.
            device = basename.split(".", 1)[0].rstrip(" ").upper()
            if (not basename or basename in (".", "..")
                    or any(ord(c) < 32 or c in '<>:"|?*' for c in basename)
                    or basename.endswith((".", " "))
                    or device in {"CON", "PRN", "AUX", "NUL"}
                    or device in {f"{prefix}{i}" for prefix in ("COM", "LPT") for i in range(1, 10)}):
                continue
            if stat.S_ISLNK(info.external_attr >> 16):
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
            # Never follow a pre-existing target symlink, even when this helper
            # is used directly rather than through the staging download path.
            if os.path.lexists(target):
                if not stat.S_ISREG(os.lstat(target).st_mode):
                    raise ValueError("Extraction target is not a regular file")
                os.unlink(target)  # Duplicate basenames retain the last entry.
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            with zf.open(info) as src, os.fdopen(os.open(target, flags, 0o600), 'wb') as dst:
                shutil.copyfileobj(src, dst, _DOWNLOAD_CHUNK)
            count += 1

    return count


@contextmanager
def _source_transaction():
    """Keep old source snapshots until their replacement index is published."""
    snapshots = []
    try:
        yield snapshots
    except Exception:
        failures = []
        for destination, workspace, had_previous in reversed(snapshots):
            try:
                os.replace(destination, os.path.join(workspace, 'new'))
                if had_previous:
                    os.replace(os.path.join(workspace, 'old'), destination)
            except OSError as ex:
                failures.append(f'{workspace}: {ex}')
            else:
                shutil.rmtree(workspace, ignore_errors=True)
        if failures:
            raise RuntimeError('Source rollback failed; snapshots retained at ' + '; '.join(failures))
        raise
    else:
        for _, workspace, _ in snapshots:
            shutil.rmtree(workspace, ignore_errors=True)


def _has_usable_palette(folder):
    """True when at least one staged file parses into a usable palette.

    A download can extract plenty of files and still contain no palette (wrong
    archive layout, a renamed upstream format, or files that only share the
    extension). Publishing that would silently replace a working cache with
    unusable files, so the stage is parsed before the old snapshot is touched.
    """
    from .iterm_parser import scan_folder_detailed

    return bool(scan_folder_detailed(folder))


def _download_and_extract(url, cache_subdir, extensions, repo_subdir=None,
                          progress_callback=None, transaction=None, cancel=None):
    """
    Download a zip from url, extract files matching extensions
    into cache_subdir. If repo_subdir is set, only extract files
    from paths containing that directory name.
    ``cancel`` is the optional cancellation signal (see :func:`_is_cancelled`);
    it is polled before the download, before extraction and before the snapshot
    is published, so a cancelled call removes its stage and leaves the old cache
    untouched.
    Returns count of extracted files.
    """
    _check_cancel(cancel)
    parent = os.path.dirname(os.path.abspath(cache_subdir))
    os.makedirs(parent, exist_ok=True)
    if os.path.islink(cache_subdir):
        raise ValueError("Source cache must not be a symlink")

    if progress_callback:
        progress_callback(f"Downloading from {url[:60]}...")

    data = _download_bytes(url, cancel=cancel)

    _check_cancel(cancel)
    if progress_callback:
        progress_callback("Extracting themes...")

    # Extract in a fresh sibling directory; CRC/errors never touch the old
    # source. Renames publish the complete snapshot and remove stale files.
    workspace = tempfile.mkdtemp(prefix=".palette-stage-", dir=parent)
    retain_backup = False
    try:
        staged = os.path.join(workspace, "new")
        previous = os.path.join(workspace, "old")
        os.mkdir(staged)
        try:
            count = _extract_theme_files(data, staged, extensions, repo_subdir)
        except zipfile.BadZipFile as ex:
            raise ValueError(f"Downloaded file is not a valid zip: {ex}") from ex
        if not count:
            raise ValueError("Archive contains no matching theme files")
        if not _has_usable_palette(staged):
            raise ValueError("Archive contains no usable theme palettes")
        # Nothing below may be interrupted: the renames either complete or the
        # transaction/rollback restores the previous snapshot.
        _check_cancel(cancel)
        had_previous = os.path.exists(cache_subdir)
        if had_previous:
            os.replace(cache_subdir, previous)
        try:
            os.replace(staged, cache_subdir)
        except OSError:
            if had_previous:
                try:
                    os.replace(previous, cache_subdir)
                except OSError as ex:
                    retain_backup = True
                    raise RuntimeError(f"Could not restore source; old cache retained at {previous}") from ex
            raise
        if transaction is not None:
            transaction.append((cache_subdir, workspace, had_previous))
            retain_backup = True
        return count
    finally:
        if not retain_backup:
            shutil.rmtree(workspace, ignore_errors=True)


def download_repo(repo_url=None, progress_callback=None, cancel=None,
                  cache_dir=None):
    """
    Legacy single-source download. Downloads iTerm2-Color-Schemes.
    Returns the index data dict.
    """
    if repo_url is None:
        repo_url = _source_url(SOURCES["iterm"])

    cache_dir = cache_dir or get_cache_dir()
    schemes_dir = os.path.join(cache_dir, "schemes")

    with _source_transaction() as transaction:
        count = _download_and_extract(
            repo_url, schemes_dir, {".itermcolors"},
            repo_subdir="schemes", progress_callback=progress_callback,
            transaction=transaction, cancel=cancel,
        )
        if progress_callback:
            progress_callback(f"Extracted {count} themes.")
        _check_cancel(cancel)
        return index_local_folder(schemes_dir, cache_dir=cache_dir)


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
    all_themes = _merge_local_noctalia(all_themes)
    if local_noctalia and NOCTALIA_TAG not in sources_done:
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


def download_sources(enabled_sources, progress_callback=None, cancel=None,
                     cache_dir=None):
    """
    Download multiple sources and build a unified, deduplicated index.

    Used by the isolated download process with an explicit ``cache_dir``
    (resolved on the main thread): with ``cache_dir=None`` the cache path is
    looked up through Blender. Do not run Python threads inside Blender. This
    function touches no other Blender state, only :mod:`iterm_parser` (pure
    Python), ``os``/``shutil``/``zipfile`` and the files under ``cache_dir``.

    Args:
        enabled_sources: list of source keys, e.g. ["nvchad", "iterm", "base24"]
        progress_callback: optional function(msg: str), called from this thread
        cancel: optional ``threading.Event``-like object (``is_set()``) or
            zero-argument callable; while it is unset the call is unchanged
        cache_dir: explicit cache directory (main-thread resolved)

    Returns the combined index data dict. Raises :class:`DownloadCancelled`
    without publishing anything (no index write, old snapshots restored) when
    the signal is set.
    """
    cache_dir = cache_dir or get_cache_dir()
    sources_done = []

    # UI tags are not always remote source keys: Noctalia's single toggle
    # includes both the local schemes and the community download.
    selected = dict.fromkeys("community_palettes" if key == NOCTALIA_TAG else key
                             for key in enabled_sources)
    _check_cancel(cancel)
    with _source_transaction() as transaction:
        for source_key in selected:
            _check_cancel(cancel)
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
                    progress_callback=progress_callback, transaction=transaction,
                    cancel=cancel,
                )
                if progress_callback:
                    progress_callback(f"{src['name']}: {count} themes extracted.")
                sources_done.append(source_key)
            except DownloadCancelled:
                # Never swallow a cancellation as a per-source warning: the
                # transaction rolls every published source back.
                raise
            except Exception as e:
                if progress_callback:
                    progress_callback(f"Warning: {src['name']} failed: {e}")
                continue

        # Keep every cached source visible to its toggle. If index publication
        # fails, the transaction restores all successful source replacements.
        _check_cancel(cancel)
        cached = _cached_source_keys(cache_dir)
        index = _scan_sources(cache_dir, cached)
        _check_cancel(cancel)
        save_index(index, cache_dir, INDEX_REMOTE)

    if progress_callback:
        tags = {SOURCES[key].get("tag", key) for key in selected if key in SOURCES}
        visible = sum(1 for t in index["themes"] if t.get("source") in tags)
        progress_callback(
            f"Total: {visible} themes available; {len(sources_done)} source(s) refreshed; "
            f"{len(index['themes'])} cached."
        )

    return index


def get_theme_list(mode=INDEX_REMOTE):
    """Get the current list of themes from the mode's index (remote default)."""
    index = load_index(mode)
    return index.get("themes", [])


def rebuild_remote_index(cache_dir=None):
    """Rebuild the remote index from already-cached sources, without downloading.

    Used when the browser switches back to REMOTE mode: the cached source
    directories are re-scanned so the snapshot matches what is on disk. No
    network access, so it is safe offline and from a preference callback.
    """
    cache_dir = cache_dir or get_cache_dir()
    index = _scan_sources(cache_dir, _cached_source_keys(cache_dir))
    save_index(index, cache_dir, INDEX_REMOTE)
    return index


def ensure_index_flags(mode=INDEX_REMOTE):
    """Backfill per-theme metadata (dark flag) on indexes written by older
    versions, then persist. No-op once every entry carries the flag."""
    try:
        index = load_index(mode)
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
        save_index(index, mode=mode)
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

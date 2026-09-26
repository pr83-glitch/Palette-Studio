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
Self-update support for Palette Studio.

Two update sources are planned:

  - LOCAL   : a folder of built ``.zip`` packages (used while the add-on is
              not published). Only zips whose ``blender_manifest.toml`` has
              ``id == "palette_studio"`` are considered.
  - GITHUB  : a GitHub repository's Releases (stubbed until the add-on is
              published; see ``_check_github``).

The add-on never installs anything silently: the caller shows a confirmation
dialog first, then ``queue_install`` defers the install to a timer so it runs
after the calling operator has returned, then hands the zip to Blender's
extension installer (``extensions.package_install_files``). That is the same
operator used by drag-and-drop / "Install from Disk", and it already disables
the running add-on, clears its modules, installs, and re-enables it. No
restart and no extra reload step is required.
"""

import os
import re
import zipfile


MANIFEST_ID = "palette_studio"
MANIFEST_NAME = "blender_manifest.toml"

_current_version_cache = None

_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:[-+](.+))?$")


def parse_version(text):
    """Parse ``0.5.0`` / ``0.5.0-alpha`` into a comparable key.

    Returns ``(major, minor, patch, is_release, prerelease)`` or None when the
    string is not a plain ``MAJOR.MINOR.PATCH`` semver. ``is_release`` is 1 for
    a final version so it sorts above any prerelease of the same number.
    """
    if not text:
        return None
    match = _VERSION_RE.match(str(text).strip())
    if not match:
        return None
    major, minor, patch, prerelease = match.groups()
    return (
        int(major),
        int(minor),
        int(patch),
        0 if prerelease else 1,
        prerelease or "",
    )


def _read_manifest_text(text):
    """Return ``{"id": ..., "version": ...}`` from manifest text.

    Prefers ``tomllib`` (Blender 4.2+/Python 3.11). Falls back to a small
    regex scan so the updater still works if the stdlib module is missing.
    """
    try:
        import tomllib
        data = tomllib.loads(str(text))
        return {"id": data.get("id", ""), "version": data.get("version", "")}
    except Exception:
        pass

    info = {}
    for key in ("id", "version"):
        match = re.search(
            r"^\s*" + key + r'\s*=\s*"([^"]*)"',
            str(text),
            re.MULTILINE,
        )
        if match:
            info[key] = match.group(1)
    return info


def _manifest_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), MANIFEST_NAME)


def get_current_version():
    """Version string from the installed ``blender_manifest.toml``."""
    global _current_version_cache
    if _current_version_cache is None:
        try:
            with open(_manifest_path(), "r", encoding="utf-8") as handle:
                _current_version_cache = _read_manifest_text(handle.read()).get("version", "")
        except Exception:
            _current_version_cache = ""
    return _current_version_cache


def _read_zip_manifest(zip_path):
    """Read the extension manifest from a zip, without extracting anything."""
    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            candidates = [
                name for name in archive.namelist()
                if os.path.basename(name) == MANIFEST_NAME
            ]
            if not candidates:
                return None
            # Prefer the shallowest match (the package root, e.g.
            # ``palette_studio/blender_manifest.toml``).
            candidates.sort(key=lambda name: name.count("/"))
            with archive.open(candidates[0], "r") as handle:
                return _read_manifest_text(handle.read().decode("utf-8", "replace"))
    except Exception:
        return None


def find_latest_in_folder(folder):
    """Scan a folder of zips and return ``(version, path)`` for the newest.

    Only packages whose manifest id matches this add-on are considered, and
    only versions strictly newer than the installed one are returned.
    """
    folder = os.path.abspath(folder)
    if not os.path.isdir(folder):
        raise ValueError(f"Update folder not found: {folder}")

    current_key = parse_version(get_current_version())
    best = None

    try:
        entries = sorted(os.listdir(folder))
    except OSError as exc:
        raise ValueError(f"Cannot read update folder: {exc}") from exc

    for name in entries:
        if not name.lower().endswith(".zip"):
            continue
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        manifest = _read_zip_manifest(path)
        if not manifest or manifest.get("id") != MANIFEST_ID:
            continue
        version = manifest.get("version", "")
        key = parse_version(version)
        if key is None:
            continue
        if current_key is not None and key <= current_key:
            continue
        if best is not None and key <= best[0]:
            continue
        best = (key, version, path)

    if best is None:
        return None
    return best[1], best[2]


def _check_github(repo_slug, current_version):
    """Placeholder for the published GitHub Releases check.

    Will query the Releases API and download the newest asset. Left disabled
    until the repository is published.
    """
    if not repo_slug or "/" not in repo_slug:
        raise ValueError("Set a GitHub repository (owner/name) in Settings.")
    raise NotImplementedError(
        "GitHub updates are not enabled yet. Use a local ZIP folder for now."
    )


def check_for_update(context):
    """Check the configured source.

    Returns a dict with ``available`` (bool), ``current``, ``latest``, ``path``
    and a human-readable ``message``. Raises on configuration errors.
    """
    import bpy

    prefs = context.preferences.addons[__package__].preferences
    current = get_current_version()
    mode = getattr(prefs, "update_source_mode", 'LOCAL')

    if mode == 'GITHUB':
        latest, path = _check_github(getattr(prefs, "github_repo", ""), current)
    else:
        folder = getattr(prefs, "update_folder", "")
        folder = bpy.path.abspath(folder) if folder else ""
        if not folder:
            raise ValueError("Set an update folder in Settings first.")
        found = find_latest_in_folder(folder)
        if found is None:
            return {
                "available": False,
                "current": current,
                "latest": "",
                "path": "",
                "message": f"Palette Studio {current} is up to date.",
            }
        latest, path = found

    return {
        "available": True,
        "current": current,
        "latest": latest,
        "path": path,
        "message": f"Update available: {current} → {latest}",
    }


def _find_installed_repo_module():
    """Return the repo module (e.g. ``user_default``) this add-on lives in."""
    import bpy

    addon_dir = os.path.dirname(os.path.abspath(__file__))

    try:
        repos = bpy.context.preferences.extensions.repos
    except Exception:
        return ""

    for repo in repos:
        try:
            directory = bpy.path.abspath(getattr(repo, "directory", "") or "")
        except Exception:
            continue
        if not directory:
            continue
        directory = os.path.normpath(directory)
        parent = os.path.dirname(addon_dir)
        if parent == directory or addon_dir.startswith(directory + os.sep):
            return getattr(repo, "module", "") or ""
    return ""


def _legacy_install(zip_path):
    """Fallback for a legacy (non-extension) install.

    ``preferences.addon_install`` does not unload/reload the running add-on the
    way the extension installer does, so a restart may still be needed here.
    """
    import bpy

    bpy.ops.preferences.addon_install(filepath=zip_path, overwrite=True)
    try:
        bpy.ops.preferences.addon_enable(module=__package__)
    except Exception:
        pass


def install_update(zip_path):
    """Install a zip over the current add-on, in place.

    Uses ``extensions.package_install_files`` - the same operator as
    drag-and-drop / "Install from Disk". It disables the running add-on, clears
    its modules, installs the new files, then re-enables it, so no restart and
    no extra reload step is required.

    Raises ValueError when the package is missing or is not this add-on.
    Returns True on success.
    """
    import bpy

    if not zip_path or not os.path.isfile(zip_path):
        raise ValueError("Update package not found.")

    manifest = _read_zip_manifest(zip_path)
    if not manifest or manifest.get("id") != MANIFEST_ID:
        raise ValueError("The selected zip is not a Palette Studio package.")

    ops = getattr(bpy.ops, "extensions", None)
    if ops is not None and hasattr(ops, "package_install_files"):
        repo_module = _find_installed_repo_module()
        if not repo_module:
            raise ValueError(
                "Could not find this extension's repository. "
                "Update with Blender's Install from Disk instead."
            )
        ops.package_install_files(
            filepath=zip_path,
            repo=repo_module,
            enable_on_install=True,
        )
        return True

    _legacy_install(zip_path)
    return True


def queue_install(zip_path):
    """Defer ``install_update`` until after the calling operator returns.

    Installing disables the running add-on, so calling the extension installer
    from inside one of our own operators can re-enter registration. A one-shot
    timer avoids that and keeps the install non-blocking. Returns True when the
    install was queued.
    """
    import bpy

    if not zip_path or not os.path.isfile(zip_path):
        raise ValueError("Update package not found.")

    def _run():
        try:
            install_update(zip_path)
        except Exception as exc:
            print(f"[Palette Studio] Update failed: {exc}")
        return None

    bpy.app.timers.register(_run, first_interval=0.1)
    return True

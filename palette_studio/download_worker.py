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

"""Headless palette-download worker: a SEPARATE process, never a thread.

Blender's official guidance is that Python threads are not supported for
pretty much anything - including blocking downloads - so the add-on runs the
slow part in a separate *process* launched by :mod:`palette_studio.download_job`::

    <blender> --background --factory-startup --disable-autoexec \
              --python download_worker.py -- request.json

The process imports ``repo`` / ``iterm_parser`` through a synthetic package
(``__path__`` pointing at the extension directory) so
``palette_studio/__init__.py`` - and therefore ``bpy`` - is never executed.
It reads local palettes and writes the palette cache. Its own configuration,
home and temporary directories are isolated under the job directory. Job IPC:

    request.json    written by the coordinator before launch (read here)
    progress.log    appended here, tailed by the main-thread timer
    result.json     written atomically here just before exit (authoritative)
    cancel.marker   created by the coordinator to request cancellation

The coordinator polls ``cancel.marker`` through the ``cancel`` callable passed
to ``repo``; the transaction there rolls back any partially published source,
so a cancelled run leaves the cache/index exactly as they were. Socket reads
are bounded by ``repo`` (30 s), so cancellation takes effect within one read.

Exit codes are 0 success, 1 error, 2 cancelled, but ``result.json`` is the
source of truth: the coordinator reads it even when the process exits
abnormally, and falls back to the exit code when it is missing.
"""

import json
import os
import sys
import time
import types
import traceback

sys.dont_write_bytecode = True

# These names are mirrored in ``download_job``; keep both in sync.
PROGRESS_FILE = "progress.log"
RESULT_FILE = "result.json"
CANCEL_MARKER = "cancel.marker"

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_CANCELLED = 2

# The synthetic package name keeps the worker's imports out of the add-on's
# real ``palette_studio`` package namespace.
_PACKAGE = "palette_studio_download_worker"


def _request_path(argv):
    """The request JSON path: the argument after ``--``, else the last arg."""
    if "--" in argv:
        tail = argv[argv.index("--") + 1:]
        if tail:
            return tail[0]
    if argv and argv[-1].endswith(".json"):
        return argv[-1]
    raise ValueError("download_worker: no request path given")


def _read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path, payload):
    """Write JSON atomically so the coordinator never reads a partial result."""
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _load_repo(extension_dir):
    """Import ``repo`` via a synthetic package, without running ``__init__``."""
    import importlib

    if _PACKAGE not in sys.modules:
        package = types.ModuleType(_PACKAGE)
        package.__path__ = [extension_dir]
        sys.modules[_PACKAGE] = package
    return importlib.import_module(_PACKAGE + ".repo")


def _install_url_overrides(repo, overrides):
    """Point selected sources at test URLs (used only by the offline audit)."""
    if not overrides:
        return
    key_by_name = {src["name"]: key for key, src in repo.SOURCES.items()}
    original = repo._source_url

    def patched(src, _original=original):
        url = overrides.get(key_by_name.get(src.get("name")))
        return url or _original(src)

    repo._source_url = patched


def _progress_writer(job_dir):
    """Append-only, line-buffered progress log the coordinator tails."""
    handle = open(os.path.join(job_dir, PROGRESS_FILE), "a", encoding="utf-8", buffering=1)

    def report(message):
        try:
            handle.write(str(message).rstrip("\n") + "\n")
            handle.flush()
        except OSError:
            pass

    return report, handle


def _cancel_probe(job_dir):
    """``repo`` cancellation signal: a callable polling the marker file."""
    marker = os.path.join(job_dir, CANCEL_MARKER)
    return lambda: os.path.exists(marker)


def _run(repo, request, report):
    """Download remote sources or scan a local folder, per the request mode."""
    cache_dir = request["cache_dir"]
    mode = request.get("mode", "remote")

    if mode == "local":
        folder = request.get("folder")
        if not folder:
            raise ValueError("Local mode needs a folder path")
        report("Scanning %s..." % folder)
        index = repo.index_local_folder(folder, cache_dir=cache_dir,
                                        cancel=_cancel_probe(request["job_dir"]))
    else:
        enabled = request.get("enabled_sources") or []
        _install_url_overrides(repo, request.get("url_overrides"))
        index = repo.download_sources(enabled, progress_callback=report,
                                      cancel=_cancel_probe(request["job_dir"]),
                                      cache_dir=cache_dir)

    return index


def _result(mode, status, index=None, error=None, details=None):
    payload = {
        "status": status,
        "mode": mode,
        "count": len((index or {}).get("themes", [])),
        "sources": (index or {}).get("sources", []),
        "error": error,
        "traceback": details,
    }
    return payload


def main(argv):
    job_dir = None
    mode = "remote"
    report = lambda message: None  # noqa: E731 - replaced once job_dir is known
    progress_handle = None
    started = time.time()
    try:
        request = _read_json(_request_path(argv))
        job_dir = request["job_dir"]
        mode = request.get("mode", "remote")
        os.makedirs(job_dir, exist_ok=True)

        report, progress_handle = _progress_writer(job_dir)
        report("Worker started (%s)." % mode)

        repo = _load_repo(request["extension_dir"])
        # Only the palette lookup reads the original config location. Keep the
        # process environment isolated throughout Blender shutdown as well.
        scan_env = request.get("scan_env") or {}
        config_home = scan_env.get("XDG_CONFIG_HOME")
        if config_home:
            repo._config_home = lambda: config_home

        index = _run(repo, request, report)
        payload = _result(mode, "ok", index)
        payload["duration"] = round(time.time() - started, 3)
        report("Finished: %d themes." % payload["count"])
        _write_json(os.path.join(job_dir, RESULT_FILE), payload)
        return EXIT_OK
    except Exception as ex:
        # A cancellation is an expected, clean outcome: the repo transaction
        # has already rolled back, so nothing was published.
        cancelled = False
        try:
            repo = sys.modules.get(_PACKAGE + ".repo")
            cancelled = repo is not None and isinstance(ex, repo.DownloadCancelled)
        except Exception:
            cancelled = False
        if cancelled:
            payload = _result(mode, "cancelled", error=str(ex))
            payload["duration"] = round(time.time() - started, 3)
            report("Cancelled.")
            code = EXIT_CANCELLED
        else:
            payload = _result(mode, "error", error=str(ex),
                              details=traceback.format_exc())
            payload["duration"] = round(time.time() - started, 3)
            report("Error: %s" % ex)
            code = EXIT_ERROR
        if job_dir:
            try:
                _write_json(os.path.join(job_dir, RESULT_FILE), payload)
            except OSError:
                pass
        else:
            traceback.print_exc()
        return code
    finally:
        if progress_handle is not None:
            try:
                progress_handle.close()
            except OSError:
                pass


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

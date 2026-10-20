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

"""Async palette-download coordinator: a child process plus a UI timer.

Blender's official guidance is that Python threads are unsupported for
pretty much anything - including blocking downloads - so this module never
starts a thread. It launches :mod:`palette_studio.download_worker` in a
*separate process* and polls it from ``bpy.app.timers`` on Blender's main
thread (no busy loop: one tick every ``_POLL_INTERVAL`` seconds), which keeps
the UI responsive without touching any ``bpy`` data from the child.

Contract with the UI (see ``__init__.PALETTE_STUDIO_OT_refresh_repo`` and the
Configure block in ``prefs``)::

    start(mode, cache_dir=..., ...)  -> bool   # False when a job is running
    is_running()                     -> bool   # a job is in flight OR a child
                                               # is still exiting (lock held)
    cancel()                         -> bool   # ask the child to stop, no kill
    shutdown()                       -> None   # stop monitoring, no kill
    status_message()                 -> str    # one line for the panel
    result()                         -> dict   # outcome once finished, else None
    pump()                           -> float  # timer tick; None when finished

Lifecycle guarantee: the child's handle (and therefore the single-job lock) is
**never dropped while the child is still alive**. ``shutdown`` may return while
a child is still publishing or rolling back; it only stops monitoring and
leaves the handle in place, so ``is_running`` keeps blocking a new refresh and
the Unload operator until the child exits and is reaped. A detached child (one
with no timer left to pump it) is reaped by ``is_running``/``start`` the moment
it exits, and never wakes a stale ``on_finished`` callback. This mirrors the
fact that ``__init__`` does not ``importlib.reload`` this module, so the state
here survives an add-on disable/enable cycle.

Everything a job owns lives in ``<cache_dir>/.palette-download-jobs/<id>/``:
the request, the child's stdout/stderr log, the progress log and the result.
Those directories are deliberately **retained** (never deleted here) so a
failed run can be inspected; Unload removes the whole cache as usual.
"""

import json
import os
import subprocess
import sys
import time
import traceback
import uuid

# Mirrors the constants in ``download_worker``; keep both in sync.
WORKER_FILENAME = "download_worker.py"
PROGRESS_FILE = "progress.log"
RESULT_FILE = "result.json"
CANCEL_MARKER = "cancel.marker"
REQUEST_FILE = "request.json"
WORKER_LOG = "worker.log"

JOB_ROOT = ".palette-download-jobs"
_POLL_INTERVAL = 0.3
_MAX_PROGRESS_READ = 64 * 1024
_CANCEL_MARKER = CANCEL_MARKER  # internal alias for brevity below

_state = {}


# ----------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------

def _write_json(path, payload):
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _close_log(job):
    handle = job.get("log")
    job["log"] = None
    if handle is not None:
        try:
            handle.close()
        except OSError:
            pass


def _reset_state():
    _state.clear()
    _state.update({
        "process": None,
        "log": None,
        "job_dir": None,
        "mode": None,
        "request": None,
        "status": "idle",
        "message": "",
        "started": 0.0,
        "exit_code": None,
        "result": None,
        "on_finished": None,
        "progress_offset": 0,
        "progress_buffer": "",
        "last_line": "",
        "cancel_requested": False,
        # True while a pump timer is registered and will finalize this job.
        "monitored": False,
        # Internal failure to report even if the child wrote a tidy result.
        "forced_error": None,
    })


_reset_state()


def _user_scan_env():
    """The real user dirs the child may READ (never write) for palettes.

    Blender itself runs isolated to the job directory, but ``repo`` aggregates
    the user's local Noctalia schemes from ``XDG_CONFIG_HOME``; passing the
    real value keeps the worker's index identical to the in-process one.
    """
    home = os.environ.get("HOME") or os.path.expanduser("~")
    return {
        "HOME": home,
        "XDG_CONFIG_HOME": os.environ.get("XDG_CONFIG_HOME") or os.path.join(home, ".config"),
    }


def _child_environment(job_dir):
    """Isolate the child's writable dirs to a unique folder under the job.

    The parent environment is copied (Blender needs its own loader variables)
    and then every writable home/config/temp location is redirected into the
    job directory, so the child can never touch the user's real Blender or
    desktop config. The palette lookup reads the real ``scan_env`` locations,
    which the worker installs itself from the request (see ``download_worker``)
    instead of the parent environment.
    """
    def folder(name):
        path = os.path.join(job_dir, name)
        os.makedirs(path, exist_ok=True)
        return path

    environment = dict(os.environ)
    tmp = folder("tmp")
    environment.update({
        "HOME": folder("home"),
        "TMPDIR": tmp,
        "TMP": tmp,
        "TEMP": tmp,
        "XDG_CONFIG_HOME": folder("xdg-config"),
        "XDG_CACHE_HOME": folder("xdg-cache"),
        "XDG_DATA_HOME": folder("xdg-data"),
        "XDG_STATE_HOME": folder("xdg-state"),
        "BLENDER_USER_CONFIG": folder("blender-config"),
        "BLENDER_USER_SCRIPTS": folder("blender-scripts"),
        "BLENDER_USER_DATAFILES": folder("blender-data"),
        "BLENDER_USER_EXTENSIONS": folder("blender-extensions"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
    })
    return environment


def _new_job_dir(cache_dir):
    root = os.path.join(cache_dir, JOB_ROOT)
    os.makedirs(root, exist_ok=True)
    job_dir = os.path.join(root, time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8])
    os.makedirs(job_dir, exist_ok=True)
    return job_dir


def _build_command(blender, binary, extension_dir, request_path):
    worker = os.path.join(extension_dir, WORKER_FILENAME)
    if blender:
        if binary is None:
            import bpy
            binary = bpy.app.binary_path
        return [binary, "--background", "--factory-startup", "--disable-autoexec",
                "--python", worker, "--", request_path]
    return [binary or sys.executable, worker, "--", request_path]


def _request_cancel(job):
    """Write the cancel marker ``repo`` polls; never kills the child.

    Returns True when a running child was asked to stop. Idempotent: writing
    the marker twice (handled by ``cancel``, ``shutdown`` and the internal
    poll-failure path) is harmless.
    """
    if job.get("process") is None:
        return False
    job_dir = job.get("job_dir")
    if job_dir:
        try:
            with open(os.path.join(job_dir, _CANCEL_MARKER), "a", encoding="utf-8"):
                pass
        except OSError:
            return False
    job["cancel_requested"] = True
    return True


# ----------------------------------------------------------------------
# Main-thread timer
# ----------------------------------------------------------------------

def _register_timer(first_interval=None):
    try:
        import bpy
    except Exception:
        return False
    try:
        if not bpy.app.timers.is_registered(pump):
            bpy.app.timers.register(
                pump, first_interval=_POLL_INTERVAL if first_interval is None else first_interval,
                persistent=True)
        return True
    except Exception:
        return False


def _unregister_timer():
    try:
        import bpy
        if bpy.app.timers.is_registered(pump):
            bpy.app.timers.unregister(pump)
    except Exception:
        pass


def _redraw():
    """Tag areas for redraw so progress is visible while the child works."""
    try:
        import bpy  # noqa: F401 - only meaningful inside Blender
    except Exception:
        return
    try:
        from . import prefs
        prefs._redraw_after_apply()
    except Exception:
        pass


# ----------------------------------------------------------------------
# Public interface
# ----------------------------------------------------------------------

def is_running():
    """True while a job is in flight or a child has not finished exiting.

    A *monitored* job (one with a live pump timer) is reported directly. A
    *detached* job - after ``shutdown``, or when timer registration failed -
    is reaped here as soon as its child exits, so the handle and the single-job
    lock are released without ever waking a stale ``on_finished`` callback.
    """
    if _state.get("process") is None:
        return False
    if _state.get("monitored"):
        return True
    _reap(_state)
    return _state.get("process") is not None


def status_message():
    """One-line status for the preferences panel (empty when idle)."""
    if is_running():
        line = _state.get("last_line") or _state.get("message") or ""
        if _state.get("cancel_requested"):
            return (line + " (cancel requested)").strip()
        return line
    return _state.get("message") or ""


def result():
    """The finished job's result dict, or None while idle/running."""
    return _state.get("result")


def mode():
    """The mode of the current or most recent job ('remote'/'local')."""
    return _state.get("mode")


def job_dir():
    """Directory holding the active/most recent job's request, logs, result."""
    return _state.get("job_dir")


def start(mode, cache_dir=None, folder=None, enabled_sources=None,
          extension_dir=None, binary=None, blender=True, on_finished=None,
          use_timer=True, url_overrides=None, scan_env=None, first_interval=None):
    """Launch the worker in a separate process and begin polling it.

    Returns False when a job is already in flight. ``on_finished(result)`` is
    called once, on the main thread, from the poll timer.
    """
    if is_running():
        return False
    if not cache_dir:
        raise ValueError("download_job.start requires an explicit cache_dir")

    extension_dir = extension_dir or os.path.dirname(os.path.abspath(__file__))
    job_dir = _new_job_dir(cache_dir)
    request = {
        "extension_dir": extension_dir,
        "cache_dir": os.path.abspath(cache_dir),
        "job_dir": job_dir,
        "mode": mode,
        "folder": folder,
        "enabled_sources": list(enabled_sources or []),
        "url_overrides": dict(url_overrides or {}),
        "scan_env": scan_env if scan_env is not None else _user_scan_env(),
    }
    request_path = os.path.join(job_dir, REQUEST_FILE)
    _write_json(request_path, request)

    command = _build_command(blender, binary, extension_dir, request_path)
    environment = _child_environment(job_dir)
    log = open(os.path.join(job_dir, WORKER_LOG), "ab")
    kwargs = {}
    if os.name == "posix":
        kwargs["start_new_session"] = True
    try:
        process = subprocess.Popen(
            command, cwd=job_dir, env=environment, stdin=subprocess.PIPE,
            stdout=log, stderr=subprocess.STDOUT, close_fds=True, **kwargs)
        process.stdin.close()
    except Exception:
        log.close()
        raise

    _reset_state()
    _state.update({
        "process": process,
        "log": log,
        "job_dir": job_dir,
        "mode": mode,
        "request": request,
        "status": "running",
        "message": ("Scanning local palettes..." if mode == "local"
                    else "Downloading palettes..."),
        "started": time.time(),
        "on_finished": on_finished,
    })

    _register_cancel_operator()
    if use_timer:
        if not _register_timer(first_interval):
            # A running child nobody polls would be silently unmonitored (and
            # could never be cancelled or reaped), so cancel it and surface the
            # failure. The handle is retained until the child exits.
            _fail_unmonitored(
                "Could not start the background monitor (timer registration failed).")
            raise RuntimeError(
                "Could not monitor the download (timer registration failed); "
                "the job was cancelled")
        _state["monitored"] = True
    return True


def cancel():
    """Ask the running child to stop; never kills it mid-transaction.

    Writes the marker file ``repo`` polls between download chunks, so the
    child finishes its rollback and writes a ``cancelled`` result. Returns
    False when no job is running.
    """
    if not _request_cancel(_state):
        return False
    _state["message"] = "Cancel requested. Waiting for the current step to finish..."
    _redraw()
    return True


def shutdown():
    """Stop monitoring without killing - or orphaning - a running child.

    Called from the add-on's ``unregister``. The timer is unregistered and the
    callback is cleared (a removed add-on must never be woken), then the child
    is asked to cancel. If the child has *not* already exited, its handle is
    deliberately kept: ``is_running`` keeps blocking a new refresh and Unload
    until the child exits and is reaped, so a still-publishing or rolling-back
    child is never overlapped. Nothing is ever killed, the call never blocks on
    the child, and the job directory (logs) is always retained.
    """
    _unregister_timer()
    _state["monitored"] = False
    _unregister_cancel_operator()

    process = _state.get("process")
    if process is None:
        _close_log(_state)
        _reset_state()
        return

    # A removed add-on must not be called back once the child finally exits.
    _state["on_finished"] = None
    _request_cancel(_state)

    if process.poll() is None:
        # Still working: keep the handle, its log and the lock. ``is_running``
        # and ``start`` reap it once it exits.
        return
    _state["exit_code"] = process.poll()
    _finalize(_state)


def pump():
    """Timer tick (also driven by tests): returns the next interval or None."""
    if _state.get("process") is None:
        return None
    try:
        return _poll()
    except Exception:
        if _state.get("forced_error") is None:
            traceback.print_exc()
        _abort_poll()
        return _POLL_INTERVAL


# ----------------------------------------------------------------------
# Polling internals (main thread)
# ----------------------------------------------------------------------

def _read_progress(job):
    path = os.path.join(job["job_dir"], PROGRESS_FILE)
    try:
        with open(path, "rb") as handle:
            handle.seek(job.get("progress_offset", 0))
            chunk = handle.read(_MAX_PROGRESS_READ)
            job["progress_offset"] = handle.tell()
    except OSError:
        return
    job["progress_buffer"] += chunk.decode("utf-8", "replace")
    lines = job["progress_buffer"].split("\n")
    job["progress_buffer"] = lines.pop()
    for line in lines:
        line = line.strip()
        if line:
            job["last_line"] = line


def _read_result(job):
    try:
        data = _read_json(os.path.join(job["job_dir"], RESULT_FILE))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _outcome_message(outcome, count, error):
    if outcome == "ok":
        return "Updated %d palette%s." % (count, "" if count == 1 else "s")
    if outcome == "cancelled":
        return "Cancelled. Nothing was changed."
    return "Failed: %s" % (error or "unknown error")


def _finalize(job, error=None):
    """Record the outcome and release the handle - only once the child is gone.

    Refuses to drop a live process: a handle is only cleared after ``poll()``
    reports the child has exited, so finalizing can never orphan a process that
    may still be publishing or rolling back.
    """
    process = job.get("process")
    if process is not None:
        code = process.poll()
        if code is None:
            return
        job["exit_code"] = code

    forced = job.pop("forced_error", None)
    if error is None:
        error = forced
    if error is not None:
        payload = {"status": "error", "mode": job.get("mode"), "count": 0,
                   "sources": [], "error": error, "traceback": None}
    else:
        payload = _read_result(job)
        if payload is None:
            code = job.get("exit_code")
            payload = {
                "status": "error", "mode": job.get("mode"), "count": 0, "sources": [],
                "error": "The download process ended without a result (exit %s). "
                         "See the log in the job directory." % code,
                "traceback": None,
            }
    outcome = payload.get("status", "error")
    job["result"] = payload
    job["status"] = outcome
    job["message"] = _outcome_message(outcome, payload.get("count", 0), payload.get("error"))
    job["process"] = None
    job["monitored"] = False
    _close_log(job)
    _unregister_timer()

    # Fire the callback at most once, and never after the handle was dropped.
    callback = job.get("on_finished")
    job["on_finished"] = None
    if callback is not None:
        try:
            callback(payload)
        except Exception:
            traceback.print_exc()


def _reap(job):
    """Finalize a *detached* job whose child has exited; never fires a callback.

    Used by ``is_running``/``start`` so a child that outlived ``shutdown`` (or
    a job whose timer could not be registered) releases its handle and lock the
    moment it exits, without waking the removed add-on's callback.
    """
    process = job.get("process")
    if process is None:
        return False
    code = process.poll()
    if code is None:
        return False
    job["exit_code"] = code
    job["on_finished"] = None
    _finalize(job)
    return True


def _abort_poll():
    """Internal poll failure: cancel the child, keep its handle, report error.

    Dropping the process here would orphan the child and free the single-job
    lock while it still publishes, so instead the child is asked to cancel and
    the handle is kept until it is reaped. The forced error is what the job
    reports even if the child goes on to write a tidy (e.g. cancelled) result.
    """
    job = _state
    message = "Internal error while polling the download"
    job["forced_error"] = message
    job["status"] = "error"
    job["message"] = message
    job["last_line"] = message
    _request_cancel(job)


def _fail_unmonitored(message):
    """A child that no timer will poll: cancel it and report the failure."""
    job = _state
    job["forced_error"] = message
    job["status"] = "error"
    job["message"] = message
    job["last_line"] = message
    job["on_finished"] = None
    job["monitored"] = False
    _request_cancel(job)


def _poll():
    job = _state
    process = job.get("process")
    if process is None:
        return None
    # Check the exit code *before* reading progress: a broken progress reader
    # must never stop an already-exited child from being finalized/reaped.
    code = process.poll()
    if code is not None:
        job["exit_code"] = code
        _finalize(job)
        _redraw()
        return None
    _read_progress(job)
    _redraw()
    return _POLL_INTERVAL


# ----------------------------------------------------------------------
# Cancel operator
# ----------------------------------------------------------------------
#
# The async implementation owns no other ``__init__`` surface, so the small
# "Cancel" button's operator is defined and registered here on demand. It is
# skipped when an operator with the same ``bl_idname`` is already registered
# (for example one added to the add-on's ``classes`` tuple), so registering it
# in both places can never clash.
_CANCEL_OPERATOR = {"class": None, "registered": False}


def _cancel_operator_class():
    if _CANCEL_OPERATOR["class"] is not None:
        return _CANCEL_OPERATOR["class"]
    from bpy.types import Operator

    class PALETTE_STUDIO_OT_cancel_download(Operator):
        """Stop a background palette download"""

        bl_idname = "palette_studio.cancel_download"
        bl_label = "Cancel Download"
        bl_description = "Ask the background download to stop; nothing is applied"
        bl_options = {'REGISTER'}

        def execute(self, context):
            if cancel():
                self.report({'INFO'}, "Cancel requested. Stopping after the current step.")
                return {'FINISHED'}
            self.report({'INFO'}, "No palette download is running.")
            return {'CANCELLED'}

    _CANCEL_OPERATOR["class"] = PALETTE_STUDIO_OT_cancel_download
    return PALETTE_STUDIO_OT_cancel_download


def _register_cancel_operator():
    try:
        import bpy
    except Exception:
        return False
    if _CANCEL_OPERATOR["registered"]:
        return True
    try:
        bpy.utils.register_class(_cancel_operator_class())
    except Exception:
        # A same-idname operator is already registered (e.g. from `classes`);
        # the UI button resolves to it and must keep working.
        pass
    _CANCEL_OPERATOR["registered"] = True
    return True


def _unregister_cancel_operator():
    if not _CANCEL_OPERATOR["registered"] or _CANCEL_OPERATOR["class"] is None:
        return
    try:
        import bpy
        bpy.utils.unregister_class(_CANCEL_OPERATOR["class"])
    except Exception:
        pass
    _CANCEL_OPERATOR["registered"] = False

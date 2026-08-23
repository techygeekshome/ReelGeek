"""Where ReelGeek keeps its settings, its cache, and your finished videos.

Renders default to your Downloads folder. On Windows that is resolved through
the shell's known-folder API rather than assumed to be ~/Downloads, because
plenty of people move Downloads onto another drive.
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

APP_NAME = "ReelGeek"


def app_dir() -> Path:
    """Private working area: uploads, prepped-photo cache, settings."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
        d = base / APP_NAME
    elif sys.platform == "darwin":
        d = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        d = Path.home() / ".reelgeek"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _windows_downloads() -> Path | None:
    """Ask Windows where Downloads actually is (it is not always ~/Downloads)."""
    try:
        import ctypes
        from ctypes import wintypes

        class GUID(ctypes.Structure):
            _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                        ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

        # FOLDERID_Downloads {374DE290-123F-4565-9164-39C4925E467B}
        fid = GUID(0x374DE290, 0x123F, 0x4565,
                   (ctypes.c_ubyte * 8)(0x91, 0x64, 0x39, 0xC4, 0x92, 0x5E, 0x46, 0x7B))
        buf = ctypes.c_wchar_p()
        if ctypes.windll.shell32.SHGetKnownFolderPath(
                ctypes.byref(fid), 0, None, ctypes.byref(buf)) != 0:
            return None
        try:
            return Path(buf.value) if buf.value else None
        finally:
            ctypes.windll.ole32.CoTaskMemFree(buf)
    except Exception:
        return None


def default_output_dir() -> Path:
    if sys.platform == "win32":
        d = _windows_downloads()
        if d and d.is_dir():
            return d
    d = Path.home() / "Downloads"
    return d if d.is_dir() else Path.home()


SETTINGS_FILE = None            # resolved lazily so app_dir() runs once


def _file() -> Path:
    global SETTINGS_FILE
    if SETTINGS_FILE is None:
        SETTINGS_FILE = app_dir() / "settings.json"
    return SETTINGS_FILE


def load() -> dict:
    try:
        return json.loads(_file().read_text(encoding="utf8"))
    except Exception:
        return {}


def save(data: dict) -> None:
    try:
        _file().write_text(json.dumps(data, indent=2), encoding="utf8")
    except Exception:
        pass


def output_dir() -> Path:
    """The folder renders are written to. Falls back if it has gone missing."""
    raw = load().get("output_dir")
    if raw:
        p = Path(raw).expanduser()
        try:
            p.mkdir(parents=True, exist_ok=True)
            if os.access(p, os.W_OK):
                return p
        except Exception:
            pass                 # drive unplugged, folder deleted, no permission
    return default_output_dir()


def set_output_dir(raw: str) -> tuple[Path, str | None]:
    """Validate and store a new output folder. Returns (folder, error or None)."""
    raw = (raw or "").strip().strip('"')
    if not raw:
        d = load()
        d.pop("output_dir", None)
        save(d)
        return default_output_dir(), None
    p = Path(raw).expanduser()
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return output_dir(), f"Could not create that folder: {e}"
    if not os.access(p, os.W_OK):
        return output_dir(), "That folder is not writable."
    d = load()
    d["output_dir"] = str(p)
    save(d)
    return p, None

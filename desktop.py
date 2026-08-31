"""Desktop entry point for the packaged Windows build.

The browser version of ReelGeek asks you to install Python and ffmpeg first.
This does not. Everything it needs travels with it:

  * the Python runtime and the two libraries, courtesy of PyInstaller
  * a copy of ffmpeg.exe in an ffmpeg\\ folder beside the executable

All this file does is put that ffmpeg on PATH so the engine finds it the way
it always has, start the local server on a free port, and open a real window
pointed at it instead of a browser tab.

Nothing here changes how rendering works.
"""
from __future__ import annotations

import os
import socket
import sys
import threading
import webbrowser
from pathlib import Path

APP_NAME = "ReelGeek"


def _bundle_dir() -> Path:
    """Where our files ended up: the PyInstaller temp dir, or the repo root."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


def _add_bundled_ffmpeg_to_path() -> str | None:
    """Put our ffmpeg first on PATH.

    render.py calls shutil.which("ffmpeg") and then runs ["ffmpeg", ...].
    Prepending the folder means the bundled copy wins without a single line
    of the render engine needing to change, and a user who already has their
    own ffmpeg is not affected once the app closes.
    """
    for candidate in (_bundle_dir() / "ffmpeg", Path(sys.executable).parent / "ffmpeg"):
        exe = candidate / "ffmpeg.exe"
        if exe.exists():
            os.environ["PATH"] = str(candidate) + os.pathsep + os.environ.get("PATH", "")
            return str(exe)
    return None


def _silence_console_windows() -> None:
    """Stop the black box flashing up behind the app while ffmpeg runs.

    Windows gives every console child process its own window, even when the
    parent is windowed. render.py starts ffmpeg with a plain subprocess.Popen,
    so on a packaged build you get a console flashing behind the app for the
    length of a render.

    CREATE_NO_WINDOW suppresses it. Patching subprocess.Popen at the module
    level rather than editing the call site means the render engine is
    untouched, and it also covers subprocess.run and check_output, which look
    Popen up as a module global. No effect on any platform but Windows.
    """
    if sys.platform != "win32":
        return

    import subprocess

    flag = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    original = subprocess.Popen

    class _QuietPopen(original):  # type: ignore[misc, valid-type]
        def __init__(self, *args, **kwargs):
            kwargs["creationflags"] = kwargs.get("creationflags", 0) | flag
            super().__init__(*args, **kwargs)

    subprocess.Popen = _QuietPopen


def _free_port(preferred: int = 8765) -> int:
    for port in [preferred, *range(8766, 8800)]:
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return 0


def main() -> int:
    _silence_console_windows()
    _add_bundled_ffmpeg_to_path()

    from reelgeek import server

    port = _free_port()
    url = f"http://127.0.0.1:{port}"

    thread = threading.Thread(
        target=server.serve,
        kwargs={"port": port, "open_browser": False},
        daemon=True,
    )
    thread.start()

    # Wait for the socket to answer rather than sleeping a fixed amount, so a
    # slow machine does not get a blank window.
    for _ in range(200):
        with socket.socket() as s:
            s.settimeout(0.1)
            try:
                s.connect(("127.0.0.1", port))
                break
            except OSError:
                continue

    try:
        import webview  # pywebview, uses the WebView2 runtime on Windows
    except Exception:
        # No window toolkit available. Fall back to the browser rather than
        # failing: the app still works, it just looks less like an app.
        webbrowser.open(url)
        thread.join()
        return 0

    webview.create_window(APP_NAME, url, width=1180, height=880, min_size=(900, 700))
    webview.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# Packaging

Everything needed to turn the repo into a Windows installer. Nothing in here
changes how ReelGeek renders.

| File | What it does |
|---|---|
| `../desktop.py` | Entry point for the packaged build. Puts the bundled ffmpeg on PATH, starts the local server on a free port, opens a real window at it. |
| `reelgeek.spec` | PyInstaller. One folder, not one file, because a one-file build unpacks to a temp folder on every launch and that is the main reason PyInstaller apps get flagged by antivirus. |
| `reelgeek.iss` | Inno Setup. Start menu entry, optional desktop shortcut, uninstaller, Add/Remove Programs entry. |
| `make_icon.py` | Converts `icons/reelgeek.png` into a multi-size `.ico`. |
| `../.github/workflows/build-windows.yml` | Runs all of the above on a Windows runner. |

## Building

Push a tag, or run the workflow by hand from the Actions tab.

```
git tag v1.0.0
git push origin v1.0.0
```

A manual run produces `ReelGeekSetup.exe` as a build artifact. A tagged run
also attaches it to the GitHub release.

## What ends up in the installer

* the Python runtime, Pillow and numpy, courtesy of PyInstaller
* `ffmpeg.exe` from the gyan.dev essentials build
* the app itself and `ui.html`

So the user installs one thing and runs it. No Python, no ffmpeg, no PATH.

## Known rough edges

* **Unsigned.** Windows SmartScreen will warn on first run until code signing
  lands (SIG-06). PyInstaller output draws more antivirus attention than a C#
  build does, so this matters more here than elsewhere in the range.
* **WebView2.** The window uses pywebview, which on Windows uses the WebView2
  runtime. That ships with Windows 11 and with any recent Edge, so in practice
  it is already there. If it is missing, the app falls back to opening in the
  default browser rather than failing.

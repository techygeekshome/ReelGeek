"""Local web app. Nothing leaves your machine -- it binds to 127.0.0.1 only."""
from __future__ import annotations
import json
import mimetypes
import os
import re
import shutil
import socket
import threading
import time
import traceback
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import settings
from .presets import PACES, PRESETS, PRESET_ORDER
from .render import Config, render

ROOT = Path(__file__).resolve().parent
HERE = ROOT / "ui.html"
MAX_UPLOAD = 80 * 1024 * 1024

JOBS: dict = {}
JOBS_LOCK = threading.Lock()

# A browser scrubbing through a video aborts range requests constantly. Every
# platform names that differently -- Windows raises ConnectionAbortedError
# (WinError 10053), Linux BrokenPipeError -- and none of them are errors.
DISCONNECTS = (BrokenPipeError, ConnectionResetError, ConnectionAbortedError,
               TimeoutError)


class Workspace:
    """Private scratch space. Finished videos do NOT live here -- they go to
    whatever output folder the user has chosen (Downloads by default)."""

    def __init__(self, base: Path):
        self.base = base
        self.uploads = base / "uploads"
        self.work = base / "work"
        for d in (self.uploads, self.work):
            d.mkdir(parents=True, exist_ok=True)

    @property
    def out(self) -> Path:
        return settings.output_dir()

    def clear_uploads(self):
        shutil.rmtree(self.uploads, ignore_errors=True)
        self.uploads.mkdir(parents=True, exist_ok=True)


WS: Workspace | None = None


def _run_job(job_id, photos, cfg, out_path):
    def progress(stage, frac, msg):
        with JOBS_LOCK:
            j = JOBS[job_id]
            # preparing photos is roughly the first fifth of the wait
            j["progress"] = (frac * 0.18) if stage == "prep" else (0.18 + frac * 0.82)
            j["message"] = msg
    try:
        info = render(photos, out_path, cfg, workdir=WS.work, progress=progress)
        with JOBS_LOCK:
            JOBS[job_id].update(state="done", progress=1.0, message="Done", info=info)
    except Exception as e:
        traceback.print_exc()
        with JOBS_LOCK:
            JOBS[job_id].update(state="error", message=f"{type(e).__name__}: {e}")


class Handler(BaseHTTPRequestHandler):
    server_version = "ReelGeek"

    def log_message(self, *a):
        pass

    def handle_one_request(self):
        try:
            super().handle_one_request()
        except DISCONNECTS:
            self.close_connection = True

    # ------------------------------------------------------------ helpers --
    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        try:
            self.end_headers()
            self.wfile.write(body)
        except DISCONNECTS:
            self.close_connection = True

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_UPLOAD:
            raise ValueError("file too large")
        return self.rfile.read(n)

    def _serve_file(self, path: Path, ctype=None, attachment=None):
        if not path.is_file():
            return self._json({"error": "not found"}, 404)
        size = path.stat().st_size
        ctype = ctype or mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        code = 200
        if rng:
            m = re.match(r"bytes=(\d*)-(\d*)", rng)
            if m:
                if m.group(1):
                    start = int(m.group(1))
                if m.group(2):
                    end = min(int(m.group(2)), size - 1)
                code = 206
        length = max(0, end - start + 1)
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if code == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        if attachment:
            self.send_header("Content-Disposition", f'attachment; filename="{attachment}"')
        self.send_header("Cache-Control", "no-store")
        try:
            self.end_headers()
        except DISCONNECTS:
            self.close_connection = True
            return
        with open(path, "rb") as f:
            f.seek(start)
            left = length
            while left > 0:
                chunk = f.read(min(262144, left))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except DISCONNECTS:
                    return
                left -= len(chunk)

    # ---------------------------------------------------------------- GET --
    def do_GET(self):
        p = self.path.split("?")[0]
        q = dict(re.findall(r"([^?&=]+)=([^&]*)", self.path.split("?", 1)[-1])) \
            if "?" in self.path else {}
        if p in ("/", "/index.html"):
            return self._serve_file(HERE, "text/html; charset=utf-8")
        if p == "/api/presets":
            return self._json({
                "presets": [{"id": k, "label": PRESETS[k]["label"],
                             "blurb": PRESETS[k]["blurb"], "bpm": PRESETS[k]["bpm"]}
                            for k in PRESET_ORDER],
                "paces": list(PACES),
            })
        if p == "/api/settings":
            return self._json({"output_dir": str(settings.output_dir()),
                               "default_output_dir": str(settings.default_output_dir())})
        if p == "/api/job":
            with JOBS_LOCK:
                j = JOBS.get(q.get("id"))
            return self._json(j or {"error": "unknown job"}, 200 if j else 404)
        if p in ("/api/video", "/api/download"):
            with JOBS_LOCK:
                j = JOBS.get(q.get("id"))
            if not j or j.get("state") != "done":
                return self._json({"error": "not ready"}, 404)
            f = Path(j["info"]["path"])
            return self._serve_file(f, "video/mp4",
                                    attachment=f.name if p == "/api/download" else None)
        return self._json({"error": "not found"}, 404)

    # --------------------------------------------------------------- POST --
    def do_POST(self):
        p = self.path.split("?")[0]
        try:
            if p == "/api/settings":
                data = json.loads(self._body() or b"{}")
                folder, err = settings.set_output_dir(data.get("output_dir", ""))
                return self._json({"output_dir": str(folder), "error": err,
                                   "default_output_dir": str(settings.default_output_dir())})

            if p == "/api/reset":
                WS.clear_uploads()
                return self._json({"ok": True})

            if p == "/api/photo":
                name = self.headers.get("X-Name", "photo.jpg")
                pid = re.sub(r"[^A-Za-z0-9_.-]", "_", self.headers.get("X-Id", uuid.uuid4().hex))
                ext = os.path.splitext(name)[1].lower() or ".jpg"
                if ext not in (".jpg", ".jpeg", ".png", ".webp", ".heic", ".bmp", ".tif", ".tiff"):
                    return self._json({"error": f"unsupported file type {ext}"}, 400)
                dest = WS.uploads / f"{pid}{ext}"
                dest.write_bytes(self._body())
                return self._json({"ok": True, "id": pid, "stored": dest.name})

            if p == "/api/render":
                cfg_in = json.loads(self._body() or b"{}")
                order = cfg_in.pop("order", None) or []
                photos = []
                for pid in order:
                    hits = sorted(WS.uploads.glob(f"{pid}.*"))
                    if hits:
                        photos.append(str(hits[0]))
                if len(photos) < 2:
                    return self._json({"error": "Add at least 2 photos."}, 400)

                preview = bool(cfg_in.pop("preview", False))
                allowed = {f.name for f in Config.__dataclass_fields__.values()}
                kw = {k: v for k, v in cfg_in.items() if k in allowed}
                if isinstance(kw.get("accent"), list):
                    kw["accent"] = tuple(kw["accent"])
                if kw.get("target_seconds") in ("", 0, "0", None):
                    kw["target_seconds"] = None
                elif kw.get("target_seconds"):
                    kw["target_seconds"] = float(kw["target_seconds"])
                cfg = Config.preview(**kw) if preview else Config(**kw)

                job_id = uuid.uuid4().hex[:12]
                stamp = time.strftime("%Y%m%d-%H%M%S")
                tag = "preview" if preview else "HD"
                out = WS.out / f"reelgeek-{cfg.style}-{tag}-{stamp}.mp4"
                out.parent.mkdir(parents=True, exist_ok=True)
                with JOBS_LOCK:
                    JOBS[job_id] = {"state": "running", "progress": 0.0,
                                    "message": "Starting…", "preview": preview}
                threading.Thread(target=_run_job, args=(job_id, photos, cfg, out),
                                 daemon=True).start()
                return self._json({"id": job_id})
        except Exception as e:
            traceback.print_exc()
            return self._json({"error": f"{type(e).__name__}: {e}"}, 500)
        return self._json({"error": "not found"}, 404)


def _free_port(preferred=8765):
    for port in [preferred] + list(range(8766, 8800)):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return 0


def serve(base_dir=None, port=None, open_browser=True):
    global WS
    WS = Workspace(Path(base_dir) if base_dir else settings.app_dir())
    port = port or _free_port()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}"
    print(f"\n  ReelGeek is running at  {url}")
    print(f"  Videos are saved to      {WS.out}")
    print("  (change that in the app under 'Save videos to')")
    print("  Press Ctrl+C to stop.\n")
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")

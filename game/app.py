from flask import Flask, render_template, jsonify, send_from_directory, send_file, abort, request
from pathlib import Path
import json
import io
import subprocess
import hashlib
import threading
import gzip
import os
import tempfile
from werkzeug.http import parse_accept_header
from werkzeug.datastructures import Accept
from PIL import Image

app = Flask(__name__)
ROOT = Path(__file__).resolve().parent
RESOURCE = ROOT / "resource"
THUMB_CACHE = Path(os.environ.get("THUMB_CACHE", str(ROOT / "static" / "cache" / "resource-thumbs")))
THUMB_LOCK = threading.Lock()

def load_json(path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {} if default is None else default

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/resource/<path:name>")
def resource_file(name):
    return send_from_directory(RESOURCE, name)

@app.get("/thumb/<path:name>")
def resource_thumbnail(name):
    source = (RESOURCE / name).resolve()
    resource_root = RESOURCE.resolve()
    if resource_root not in source.parents or not source.is_file():
        abort(404)
    if source.suffix.lower() == ".svg":
        return send_file(source, mimetype="image/svg+xml", max_age=604800)
    THUMB_CACHE.mkdir(parents=True, exist_ok=True)
    target = THUMB_CACHE / f"{hashlib.sha256(name.encode('utf-8')).hexdigest()}.webp"
    if not target.is_file() or target.stat().st_mtime < source.stat().st_mtime:
        with THUMB_LOCK:
            if not target.is_file() or target.stat().st_mtime < source.stat().st_mtime:
                # Each worker needs its own temporary file; publish atomically.
                fd, filename = tempfile.mkstemp(suffix=".webp", dir=THUMB_CACHE)
                os.close(fd)
                temporary = Path(filename)
                try:
                    with Image.open(source) as image:
                        image.thumbnail((480, 320), Image.Resampling.LANCZOS)
                        if image.mode not in ("RGB", "RGBA"):
                            image = image.convert("RGB")
                        image.save(temporary, "WEBP", quality=80, method=4)
                    temporary.replace(target)
                except (OSError, ValueError):
                    abort(415)
                finally:
                    temporary.unlink(missing_ok=True)
    return send_file(target, mimetype="image/webp", max_age=604800)
@app.get("/api/bootstrap")
def bootstrap():
    return jsonify({
        "manifest": load_json(RESOURCE / "manifest.json", {}),
        "topics": load_json(RESOURCE / "topics.json", {}).get("topics", []),
        "games": load_json(RESOURCE / "games.json", {}).get("games", []),
    })

@app.get("/api/topic/<topic_id>")
def topic(topic_id):
    topics = load_json(RESOURCE / "topics.json", {}).get("topics", [])
    entry = next((x for x in topics if x.get("id") == topic_id), None)
    if not entry:
        abort(404)
    return jsonify(load_json(RESOURCE / entry["file"], {}))

@app.get("/api/game-topic/<topic_id>")
def game_topic(topic_id):
    topics = load_json(RESOURCE / "topics.json", {}).get("topics", [])
    entry = next((x for x in topics if x.get("id") == topic_id), None)
    if not entry:
        abort(404)
    data = load_json(RESOURCE / entry["file"], {})
    fields = ("id", "viName", "enName", "image", "enabled")
    items = [{key: item.get(key) for key in fields if key in item} for item in data.get("items", [])]
    return jsonify({"id": data.get("id", topic_id), "items": items})
@app.get("/api/game/<game_id>")
def game(game_id):
    games = load_json(RESOURCE / "games.json", {}).get("games", [])
    entry = next((x for x in games if x.get("id") == game_id), None)
    if not entry or not entry.get("configFile"):
        abort(404)
    return jsonify(load_json(RESOURCE / entry["configFile"], {}))

@app.get("/api/tts")
def text_to_speech():
    text = " ".join(request.args.get("text", "").split())[:500]
    lang = request.args.get("lang", "vi").lower()
    if not text:
        abort(400)
    voice = "en-us" if lang.startswith("en") else "vi"
    speed = "145" if voice == "en-us" else "155"
    try:
        result = subprocess.run(
            ["espeak-ng", "-v", voice, "-s", speed, "--stdout", "--", text],
            check=True, capture_output=True, timeout=10,
        )
    except (subprocess.SubprocessError, OSError):
        abort(503)
    response = send_file(io.BytesIO(result.stdout), mimetype="audio/wav", download_name="speech.wav", max_age=86400)
    response.headers["Cache-Control"] = "public, max-age=86400"
    return response

@app.get("/api/status")
def status():
    manifest = load_json(RESOURCE / "manifest.json", {})
    return jsonify({"online": True, "schema": manifest.get("schemaVersion"), "counts": manifest.get("counts", {})})

@app.get("/healthz")
def health():
    required = ("manifest.json", "topics.json", "games.json")
    ready = all(load_json(RESOURCE / name, None) for name in required)
    return jsonify({"ok": bool(ready)}), 200 if ready else 503

@app.after_request
def cache_and_security_headers(response):
    content_type = response.headers.get("Content-Type", "").lower()
    compressible = content_type.startswith("text/") or "json" in content_type or "javascript" in content_type
    if compressible:
        response.vary.add("Accept-Encoding")
    encodings = parse_accept_header(request.headers.get("Accept-Encoding", ""), Accept)
    if (request.method == "GET" and response.status_code == 200 and not request.headers.get("Range") and not response.headers.get("Content-Encoding") and encodings.quality("gzip") > 0):
        content_type = response.headers.get("Content-Type", "").lower()
        if content_type.startswith("text/") or "json" in content_type or "javascript" in content_type:
            response.direct_passthrough = False
            data = response.get_data()
            if len(data) > 1024:
                compressed = gzip.compress(data, compresslevel=6)
                if len(compressed) < len(data):
                    response.set_data(compressed)
                    response.headers["Content-Encoding"] = "gzip"
                    response.headers["Content-Length"] = str(len(compressed))
                    # The ETag identifies bytes, so vary it for the encoded body.
                    response.set_etag(hashlib.sha256(compressed).hexdigest())
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "same-origin"
    request_path = request.path
    if response.status_code == 200 and (request_path.startswith("/resource/") or request_path.startswith("/thumb/")):
        response.headers["Cache-Control"] = "public, max-age=604800"
    elif response.status_code == 200 and request_path.startswith("/static/"):
        response.headers["Cache-Control"] = "public, max-age=3600, must-revalidate"
    elif response.status_code >= 400:
        response.headers["Cache-Control"] = "no-store"
    elif "Cache-Control" not in response.headers:
        response.headers["Cache-Control"] = "no-cache"
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)

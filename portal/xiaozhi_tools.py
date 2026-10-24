"""Internet lookup tools for the Thien Ha XiaoZhi project."""

from __future__ import annotations

import html
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import subprocess
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

from flask import Blueprint, Response, jsonify, request, send_file, session, stream_with_context


USER_AGENT = "ThienHa-XiaoZhi-Tools/1.0 (+https://thienha.io.vn/projects/xiaozhi-esp32)"
CACHE: dict[str, tuple[float, dict]] = {}
CACHE_LOCK = threading.Lock()
SESSION_LOCK = threading.Lock()
SESSIONS: dict[str, dict] = {}
ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get("THIENHA_DATA_DIR", str(ROOT / "data")))
MUSIC_SESSION_DIR = Path(
    os.environ.get("XIAOZHI_MUSIC_SESSION_DIR", str(DATA / "music_sessions"))
)
SITE_DB = Path(os.environ.get("THIENHA_SITE_DB", str(DATA / "users.db")))
FIRMWARE_DIR = Path(os.environ.get("XIAOZHI_FIRMWARE_DIR", str(ROOT / "static" / "downloads")))
TOOLS = {
    "prepare_music": "Chuẩn bị luồng nhạc Opus riêng cho loa robot.",
    "search_web": "Tra cứu thông tin trên Internet.",
    "get_latest_news": "Cập nhật tin tức mới theo chủ đề.",
    "get_gold_price": "Tra cứu thông tin giá vàng mới nhất tại Việt Nam.",
    "get_fuel_price": "Tra cứu thông tin giá xăng dầu mới nhất tại Việt Nam.",
    "search_music": "Tìm bài hát, nghệ sĩ và bản nghe thử hợp pháp.",
    "chat_with_gpt": "Trò chuyện tiếng Việt với GPT qua OpenAI Responses API.",
    "search_youtube_music": "Tìm video nhạc bằng YouTube Data API chính thức.",
}


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _fetch(url: str, timeout: int = 10) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"upstream HTTP {response.status}")
        return response.read(1_000_001)


def _cached(key: str, ttl: int, loader):
    now = time.monotonic()
    with CACHE_LOCK:
        hit = CACHE.get(key)
        if hit and hit[0] > now:
            result = dict(hit[1])
            result["cached"] = True
            return result
    result = loader()
    result["cached"] = False
    with CACHE_LOCK:
        CACHE[key] = (now + ttl, result)
    return result


def _clean(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", html.unescape(value or ""))
    return re.sub(r"\s+", " ", value).strip()


def _license_db():
    db = sqlite3.connect(SITE_DB, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute(
        "CREATE TABLE IF NOT EXISTS robot_bindings ("
        "session_id TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, "
        "created_at TEXT NOT NULL)"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS tool_licenses ("
        "user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, tool_name TEXT NOT NULL, "
        "expires_at TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1, "
        "PRIMARY KEY(user_id,tool_name))"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS tool_trial_users ("
        "user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE, "
        "initialized_at TEXT NOT NULL)"
    )
    columns = {row[1] for row in db.execute("PRAGMA table_info(robot_bindings)")}
    if "mac_address" not in columns:
        db.execute("ALTER TABLE robot_bindings ADD COLUMN mac_address TEXT")
    db.execute(
        "CREATE TABLE IF NOT EXISTS account_access ("
        "user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE, expires_at TEXT NOT NULL)"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS mac_access ("
        "user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, mac_address TEXT NOT NULL, "
        "expires_at TEXT NOT NULL, PRIMARY KEY(user_id,mac_address))"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS mac_tool_licenses ("
        "user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, "
        "mac_address TEXT NOT NULL, tool_name TEXT NOT NULL, expires_at TEXT NOT NULL, "
        "enabled INTEGER NOT NULL DEFAULT 1, "
        "PRIMARY KEY(user_id,mac_address,tool_name))"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS mac_service_profiles ("
        "user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, "
        "mac_address TEXT NOT NULL, created_at TEXT NOT NULL, "
        "PRIMARY KEY(user_id,mac_address))"
    )
    db.execute(
        "INSERT OR IGNORE INTO mac_service_profiles(user_id,mac_address,created_at) "
        "SELECT user_id,mac_address,created_at FROM robot_bindings "
        "WHERE mac_address IS NOT NULL AND mac_address<>''"
    )
    db.execute(
        "INSERT OR IGNORE INTO mac_tool_licenses(user_id,mac_address,tool_name,expires_at,enabled) "
        "SELECT r.user_id,r.mac_address,t.tool_name,t.expires_at,t.enabled "
        "FROM robot_bindings r JOIN tool_licenses t ON t.user_id=r.user_id "
        "WHERE r.mac_address IS NOT NULL AND r.mac_address<>''"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS firmware_downloads ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id), "
        "mac_address TEXT NOT NULL, filename TEXT NOT NULL, downloaded_at TEXT NOT NULL, "
        "remote_addr TEXT)"
    )
    return db


def _normalize_mac(value: str) -> str:
    compact = re.sub(r"[^0-9A-Fa-f]", "", value or "").upper()
    if len(compact) != 12:
        return ""
    return ":".join(compact[index:index + 2] for index in range(0, 12, 2))


def _service_catalog(db, include_disabled=False):
    where = "" if include_disabled else " WHERE enabled=1"
    try:
        return [dict(row) for row in db.execute(
            "SELECT * FROM service_catalog" + where + " ORDER BY sort_order,display_name"
        )]
    except sqlite3.OperationalError:
        return [{"service_name": name, "display_name": name, "description": description,
                 "price_month": 10000, "price_year": 50000, "price_lifetime": 150000,
                 "enabled": 1, "sort_order": index}
                for index, (name, description) in enumerate(TOOLS.items())]


def _service_names(db):
    return {row["service_name"] for row in _service_catalog(db, True)}


def _active(expires_at: str) -> bool:
    try:
        return datetime.fromisoformat(expires_at) > datetime.now(timezone.utc).astimezone()
    except (TypeError, ValueError):
        return False


def _ensure_trial(db, user_id: int):
    if db.execute("SELECT 1 FROM tool_trial_users WHERE user_id=?", (user_id,)).fetchone():
        return
    user = db.execute("SELECT created_at FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        return
    try:
        created = datetime.fromisoformat(user["created_at"])
    except (TypeError, ValueError):
        created = datetime.now(timezone.utc).astimezone()
    expires = (created + timedelta(days=7)).isoformat(timespec="seconds")
    db.executemany(
        "INSERT OR IGNORE INTO tool_licenses(user_id,tool_name,expires_at,enabled) VALUES(?,?,?,1)",
        [(user_id, name, expires) for name in TOOLS],
    )
    db.execute(
        "INSERT OR IGNORE INTO tool_trial_users(user_id,initialized_at) VALUES(?,?)",
        (user_id, _now()),
    )
    db.execute(
        "INSERT OR IGNORE INTO account_access(user_id,expires_at) VALUES(?,?)",
        (user_id, expires),
    )


def _tool_allowed(session_id: str, tool_name: str) -> tuple[bool, str]:
    with _license_db() as db:
        binding = db.execute(
            "SELECT user_id,mac_address FROM robot_bindings WHERE session_id=?", (session_id,)
        ).fetchone()
        if not binding:
            return False, "robot chưa được liên kết với tài khoản"
        _ensure_trial(db, binding["user_id"])
        row = db.execute(
            "SELECT enabled,expires_at FROM mac_tool_licenses "
            "WHERE user_id=? AND mac_address=? AND tool_name=?",
            (binding["user_id"], binding["mac_address"] or "", tool_name),
        ).fetchone()
        managed = db.execute(
            "SELECT 1 FROM mac_service_profiles WHERE user_id=? AND mac_address=?",
            (binding["user_id"], binding["mac_address"] or ""),
        ).fetchone()
        if not row and not managed:
            row = db.execute(
            "SELECT enabled,expires_at FROM tool_licenses WHERE user_id=? AND tool_name=?",
            (binding["user_id"], tool_name),
            ).fetchone()
        account = db.execute(
            "SELECT expires_at FROM account_access WHERE user_id=?", (binding["user_id"],)
        ).fetchone()
        mac = db.execute(
            "SELECT expires_at FROM mac_access WHERE user_id=? AND mac_address=?",
            (binding["user_id"], binding["mac_address"] or ""),
        ).fetchone()
        db.commit()
    if not row or not row["enabled"]:
        return False, "tool chưa được admin cấp phép"
    active = _active(row["expires_at"])
    subscription = (account and _active(account["expires_at"])) or (
        mac and _active(mac["expires_at"])
    )
    return (True, "") if active and subscription else (False, "quyền dùng tool đã hết hạn")


def _rss(query: str, limit: int = 5) -> dict:
    encoded = urllib.parse.quote_plus(query)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=vi&gl=VN&ceid=VN:vi"
    root = ET.fromstring(_fetch(url))
    items = []
    for node in root.findall("./channel/item")[:limit]:
        source = node.find("source")
        items.append(
            {
                "title": _clean(node.findtext("title", "")),
                "url": node.findtext("link", ""),
                "source": _clean(source.text if source is not None else "Google News"),
                "published_at": node.findtext("pubDate", ""),
            }
        )
    return {
        "ok": True,
        "query": query,
        "summary_vi": " | ".join(item["title"] for item in items[:3]),
        "items": items,
        "updated_at": _now(),
    }


def _search(query: str, limit: int = 5) -> dict:
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote_plus(query)
    body = _fetch(url).decode("utf-8", "replace")
    pattern = re.compile(
        r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</',
        re.I | re.S,
    )
    items = []
    for href, title, snippet in pattern.findall(body)[:limit]:
        parsed = urllib.parse.urlparse(html.unescape(href))
        target = urllib.parse.parse_qs(parsed.query).get("uddg", [href])[0]
        items.append({"title": _clean(title), "url": target, "snippet": _clean(snippet)})
    return {
        "ok": True,
        "query": query,
        "summary_vi": " | ".join(item["title"] for item in items[:3]),
        "items": items,
        "updated_at": _now(),
    }


def _music(query: str, limit: int = 5) -> dict:
    url = (
        "https://itunes.apple.com/search?country=VN&media=music&entity=song&limit="
        + str(limit)
        + "&term="
        + urllib.parse.quote_plus(query)
    )
    payload = json.loads(_fetch(url).decode("utf-8"))
    items = [
        {
            "title": item.get("trackName", ""),
            "artist": item.get("artistName", ""),
            "album": item.get("collectionName", ""),
            "url": item.get("trackViewUrl", ""),
            "preview_url": item.get("previewUrl", ""),
        }
        for item in payload.get("results", [])[:limit]
    ]
    return {
        "ok": True,
        "query": query,
        "summary_vi": " | ".join(f'{x["title"]} — {x["artist"]}' for x in items[:3]),
        "items": items,
        "updated_at": _now(),
    }


def _gpt(message: str) -> dict:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    payload = json.dumps(
        {
            "model": os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
            "instructions": (
                "Bạn là trợ lý tiếng Việt của robot Copper. Trả lời tự nhiên, chính xác, "
                "ngắn gọn để đọc TTS; không khẳng định dữ liệu thời gian thực nếu chưa tra cứu."
            ),
            "input": message,
            "max_output_tokens": 500,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.loads(response.read(1_000_001).decode("utf-8"))
    texts = []
    for output in result.get("output", []):
        for content in output.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                texts.append(content["text"])
    answer = "\n".join(texts).strip()
    if not answer:
        raise RuntimeError("OpenAI response contained no output text")
    return {
        "ok": True,
        "summary_vi": answer,
        "model": result.get("model", ""),
        "response_id": result.get("id", ""),
        "updated_at": _now(),
    }


def _youtube_music(query: str, limit: int = 5) -> dict:
    api_key = os.environ.get("YOUTUBE_API_KEY", "")
    if not api_key:
        raise RuntimeError("YOUTUBE_API_KEY is not configured")
    params = urllib.parse.urlencode(
        {
            "part": "snippet",
            "type": "video",
            "videoCategoryId": "10",
            "maxResults": limit,
            "q": query,
            "regionCode": "VN",
            "relevanceLanguage": "vi",
            "key": api_key,
        }
    )
    payload = json.loads(_fetch("https://www.googleapis.com/youtube/v3/search?" + params).decode())
    items = []
    for item in payload.get("items", []):
        video_id = item.get("id", {}).get("videoId", "")
        snippet = item.get("snippet", {})
        if video_id:
            items.append(
                {
                    "title": _clean(snippet.get("title", "")),
                    "channel": _clean(snippet.get("channelTitle", "")),
                    "video_id": video_id,
                    "url": "https://www.youtube.com/watch?v=" + video_id,
                    "published_at": snippet.get("publishedAt", ""),
                }
            )
    return {
        "ok": True,
        "query": query,
        "summary_vi": " | ".join(f'{x["title"]} — {x["channel"]}' for x in items[:3]),
        "items": items,
        "playback_supported": False,
        "playback_note_vi": (
            "Firmware chỉ phát OGG/Opus trong /ai-music; không tải hoặc giải mã luồng YouTube."
        ),
        "updated_at": _now(),
    }


def register_xiaozhi_tools(app):
    bp = Blueprint("xiaozhi_tools", __name__, url_prefix="/api/xiaozhi")

    def web_user(admin=False):
        uid = session.get("uid")
        if not uid:
            return None
        with _license_db() as db:
            user = db.execute("SELECT id,email,name,role FROM users WHERE id=?", (uid,)).fetchone()
        if not user or (admin and user["role"] != "admin"):
            return None
        return user

    def valid_csrf():
        supplied = request.headers.get("X-CSRF-Token", "") or request.form.get("csrf", "")
        expected = session.get("csrf", "")
        return bool(expected and supplied and secrets.compare_digest(expected, supplied))

    @bp.before_request
    def authorize():
        if request.endpoint in {
            "xiaozhi_tools.health",
            "xiaozhi_tools.list_tools",
            "xiaozhi_tools.account_access",
            "xiaozhi_tools.bind_robot",
            "xiaozhi_tools.unbind_robot",
            "xiaozhi_tools.account_toggle_service",
            "xiaozhi_tools.admin_access",
            "xiaozhi_tools.admin_devices",
            "xiaozhi_tools.admin_device_service",
            "xiaozhi_tools.admin_remove_device",
            "xiaozhi_tools.firmware_download",
            "xiaozhi_tools.music_stream",
        }:
            return None
        expected = os.environ.get("XIAOZHI_TOOLS_TOKEN", "")
        supplied = request.headers.get("Authorization", "")
        if not expected or supplied != f"Bearer {expected}":
            return jsonify(ok=False, error="unauthorized"), 401
        return None

    @bp.get("/health")
    def health():
        return jsonify(ok=True, service="thienha-xiaozhi-tools", version="1.0", time=_now())

    @bp.get("/tools/list")
    def list_tools():
        return jsonify(ok=True, tools=[{"name": k, "description": v} for k, v in TOOLS.items()])

    @bp.get("/account/access")
    def account_access():
        user = web_user()
        if not user:
            return jsonify(ok=False, error="login required"), 401
        with _license_db() as db:
            _ensure_trial(db, user["id"])
            robots = [dict(x) for x in db.execute(
                "SELECT session_id,mac_address,created_at FROM robot_bindings WHERE user_id=? ORDER BY created_at DESC",
                (user["id"],),
            )]
            licenses = [dict(x) for x in db.execute(
                "SELECT tool_name,enabled,expires_at FROM tool_licenses WHERE user_id=? ORDER BY tool_name",
                (user["id"],),
            )]
            account = db.execute(
                "SELECT expires_at FROM account_access WHERE user_id=?", (user["id"],)
            ).fetchone()
            mac_access = [dict(x) for x in db.execute(
                "SELECT mac_address,expires_at FROM mac_access WHERE user_id=? ORDER BY mac_address",
                (user["id"],),
            )]
            for robot in robots:
                specific = [dict(x) for x in db.execute(
                    "SELECT tool_name,enabled,expires_at FROM mac_tool_licenses "
                    "WHERE user_id=? AND mac_address=? ORDER BY tool_name",
                    (user["id"], robot["mac_address"] or ""),
                )]
                managed = db.execute(
                    "SELECT 1 FROM mac_service_profiles WHERE user_id=? AND mac_address=?",
                    (user["id"], robot["mac_address"] or ""),
                ).fetchone()
                robot["services"] = specific if managed else licenses
                access = next((x for x in mac_access if x["mac_address"] == robot["mac_address"]), None)
                robot["access_expires_at"] = access["expires_at"] if access else (account["expires_at"] if account else None)
            catalog = _service_catalog(db)
            db.commit()
        return jsonify(ok=True, robots=robots, licenses=licenses,
                       account_access=dict(account) if account else None,
                       mac_access=mac_access, trial_days=7,
                       services_catalog=[{"name": x["service_name"], **x} for x in catalog])

    @bp.post("/account/toggle-service")
    def account_toggle_service():
        user = web_user()
        if not user:
            return jsonify(ok=False, error="Bạn cần đăng nhập"), 401
        if not valid_csrf():
            return jsonify(ok=False, error="Phiên làm việc không hợp lệ"), 400
        body = request.get_json(silent=True) or {}
        mac = _normalize_mac(str(body.get("mac_address", "")))
        tool = str(body.get("tool_name", ""))[:64]
        enabled = 1 if body.get("enabled", True) else 0
        with _license_db() as db:
            if not db.execute("SELECT 1 FROM robot_bindings WHERE user_id=? AND mac_address=?", (user["id"], mac)).fetchone():
                return jsonify(ok=False, error="Thiết bị không thuộc tài khoản này"), 403
            changed = db.execute("UPDATE mac_tool_licenses SET enabled=? WHERE user_id=? AND mac_address=? AND tool_name=?", (enabled, user["id"], mac, tool)).rowcount
            if not changed:
                return jsonify(ok=False, error="Dịch vụ chưa được kích hoạt; hãy chọn mua dịch vụ"), 404
            db.commit()
        return jsonify(ok=True, enabled=bool(enabled))

    @bp.post("/account/bind-robot")
    def bind_robot():
        user = web_user()
        if not user:
            return jsonify(ok=False, error="login required"), 401
        if not valid_csrf():
            return jsonify(ok=False, error="invalid csrf"), 400
        body = request.get_json(silent=True) or {}
        mac_address = _normalize_mac(str(body.get("mac_address", "")))
        robot_id = str(body.get("session_id", "")).strip()[:80]
        if mac_address and not robot_id:
            robot_id = "th-" + hashlib.sha256(("thienha-device:" + mac_address).encode()).hexdigest()[:32]
        if not re.fullmatch(r"[A-Za-z0-9._:-]{8,80}", robot_id):
            return jsonify(ok=False, error="invalid robot UUID"), 400
        if not mac_address:
            return jsonify(ok=False, error="invalid robot MAC"), 400
        with _license_db() as db:
            _ensure_trial(db, user["id"])
            db.execute(
                "INSERT INTO robot_bindings(session_id,user_id,created_at,mac_address) VALUES(?,?,?,?) "
                "ON CONFLICT(session_id) DO UPDATE SET user_id=excluded.user_id,mac_address=excluded.mac_address",
                (robot_id, user["id"], _now(), mac_address),
            )
            db.execute(
                "INSERT OR IGNORE INTO mac_service_profiles(user_id,mac_address,created_at) VALUES(?,?,?)",
                (user["id"], mac_address, _now()),
            )
            db.execute(
                "INSERT OR IGNORE INTO mac_tool_licenses(user_id,mac_address,tool_name,expires_at,enabled) "
                "SELECT user_id,?,tool_name,expires_at,enabled FROM tool_licenses WHERE user_id=?",
                (mac_address, user["id"]),
            )
            db.commit()
        return jsonify(ok=True, session_id=robot_id, mac_address=mac_address)

    @bp.post("/account/unbind-robot")
    def unbind_robot():
        user = web_user()
        if not user:
            return jsonify(ok=False, error="Bạn cần đăng nhập"), 401
        if not valid_csrf():
            return jsonify(ok=False, error="Phiên làm việc không hợp lệ"), 400
        session_id = str((request.get_json(silent=True) or {}).get("session_id", ""))[:80]
        with _license_db() as db:
            robot = db.execute(
                "SELECT mac_address FROM robot_bindings WHERE session_id=? AND user_id=?",
                (session_id, user["id"]),
            ).fetchone()
            if not robot:
                return jsonify(ok=False, error="Không tìm thấy thiết bị"), 404
            db.execute("DELETE FROM robot_bindings WHERE session_id=? AND user_id=?", (session_id, user["id"]))
            db.commit()
        return jsonify(ok=True)

    @bp.get("/admin/devices")
    def admin_devices():
        if not web_user(admin=True):
            return jsonify(ok=False, error="Bạn không có quyền quản trị"), 403
        with _license_db() as db:
            catalog = _service_catalog(db, True)
            user_rows = db.execute(
                "SELECT id AS user_id,email,name,last_login_at FROM users "
                "WHERE last_login_at IS NOT NULL ORDER BY email"
            ).fetchall()
            robot_rows = [dict(x) for x in db.execute(
                "SELECT r.session_id,r.mac_address,r.created_at,r.user_id,u.email,u.name "
                "FROM robot_bindings r JOIN users u ON u.id=r.user_id "
                "ORDER BY u.email,r.mac_address"
            )]
            users = []
            devices = []
            for user_row in user_rows:
                user_id = user_row["user_id"]
                owner = {"user_id": user_id, "email": user_row["email"], "name": user_row["name"], "devices": []}
                account_services = [dict(x) for x in db.execute(
                    "SELECT tool_name,enabled,expires_at FROM tool_licenses WHERE user_id=? ORDER BY tool_name",
                    (user_id,),
                )]
                game = db.execute(
                    "SELECT service_name AS tool_name,enabled,expires_at FROM account_project_licenses "
                    "WHERE user_id=? AND service_name='game-of-thien'",
                    (user_id,),
                ).fetchone()
                account_services = [x for x in account_services if x["tool_name"] != "game-of-thien"]
                if game:
                    account_services.append(dict(game))
                account = {
                    "session_id": f"account-{user_id}", "mac_address": "ACCOUNT",
                    "created_at": user_row["last_login_at"], "user_id": user_id,
                    "email": user_row["email"], "name": user_row["name"],
                    "services": account_services,
                    "available_services": [{"name": x["service_name"], **x} for x in catalog],
                    "account_level": True,
                }
                owner["devices"].append(account)
                devices.append(account)
                for robot in (x for x in robot_rows if x["user_id"] == user_id):
                    services = [dict(x) for x in db.execute(
                        "SELECT tool_name,enabled,expires_at FROM mac_tool_licenses "
                        "WHERE user_id=? AND mac_address=?",
                        (user_id, robot["mac_address"] or ""),
                    )]
                    legacy = [dict(x) for x in db.execute(
                        "SELECT tool_name,enabled,expires_at FROM tool_licenses WHERE user_id=? ORDER BY tool_name",
                        (user_id,),
                    )]
                    managed = db.execute(
                        "SELECT 1 FROM mac_service_profiles WHERE user_id=? AND mac_address=?",
                        (user_id, robot["mac_address"] or ""),
                    ).fetchone()
                    robot["services"] = services if managed else legacy
                    robot["available_services"] = [{"name": x["service_name"], **x} for x in catalog]
                    robot["account_level"] = False
                    owner["devices"].append(robot)
                    devices.append(robot)
                users.append(owner)
        return jsonify(ok=True, devices=devices, users=users, catalog=catalog)
    @bp.post("/admin/device-service")
    def admin_device_service():
        if not web_user(admin=True):
            return jsonify(ok=False, error="Bạn không có quyền quản trị"), 403
        if not valid_csrf():
            return jsonify(ok=False, error="Phiên làm việc không hợp lệ"), 400
        body = request.get_json(silent=True) or {}
        try:
            user_id = int(body.get("user_id")); days = max(0, min(int(body.get("days", 30)), 3650))
        except (TypeError, ValueError):
            return jsonify(ok=False, error="Người dùng hoặc số ngày không hợp lệ"), 400
        raw_mac = str(body.get("mac_address", ""))
        mac = "ACCOUNT" if raw_mac.upper() == "ACCOUNT" else _normalize_mac(raw_mac)
        tool = str(body.get("tool_name", ""))[:64]
        action = str(body.get("action", "save"))
        with _license_db() as db:
            if not mac or tool not in _service_names(db):
                return jsonify(ok=False, error="Tài khoản, MAC hoặc dịch vụ không hợp lệ"), 400
            period = str(body.get("billing_period", "custom"))
            if period == "lifetime":
                expires = "9999-12-31T23:59:59+00:00"
            else:
                period_days = {"month": 30, "year": 365}.get(period, days)
                if mac == "ACCOUNT" and tool == "game-of-thien":
                    existing = db.execute(
                        "SELECT expires_at FROM account_project_licenses WHERE user_id=? AND service_name=?",
                        (user_id, tool),
                    ).fetchone()
                elif mac == "ACCOUNT":
                    existing = db.execute(
                        "SELECT expires_at FROM tool_licenses WHERE user_id=? AND tool_name=?",
                        (user_id, tool),
                    ).fetchone()
                else:
                    existing = db.execute(
                        "SELECT expires_at FROM mac_tool_licenses WHERE user_id=? AND mac_address=? AND tool_name=?",
                        (user_id, mac, tool),
                    ).fetchone()
                start = datetime.now(timezone.utc).astimezone()
                try:
                    old = datetime.fromisoformat(existing["expires_at"] if existing else "")
                    if old > start: start = old
                except (TypeError, ValueError):
                    pass
                expires = (start + timedelta(days=period_days)).isoformat(timespec="seconds")
            enabled = 1 if body.get("enabled", True) else 0
            if mac == "ACCOUNT":
                if action == "delete":
                    if tool == "game-of-thien":
                        db.execute("DELETE FROM account_project_licenses WHERE user_id=? AND service_name=?", (user_id, tool))
                    else:
                        db.execute("DELETE FROM tool_licenses WHERE user_id=? AND tool_name=?", (user_id, tool))
                elif tool == "game-of-thien":
                    stamp = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
                    db.execute(
                        "INSERT INTO account_project_licenses(user_id,service_name,expires_at,enabled,activated_at,updated_at) "
                        "VALUES(?,?,?,?,?,?) ON CONFLICT(user_id,service_name) DO UPDATE SET "
                        "expires_at=excluded.expires_at,enabled=excluded.enabled,updated_at=excluded.updated_at",
                        (user_id, tool, expires, enabled, stamp, stamp),
                    )
                else:
                    db.execute(
                        "INSERT INTO tool_licenses(user_id,tool_name,expires_at,enabled) VALUES(?,?,?,?) "
                        "ON CONFLICT(user_id,tool_name) DO UPDATE SET expires_at=excluded.expires_at,enabled=excluded.enabled",
                        (user_id, tool, expires, enabled),
                    )
                db.commit()
                return jsonify(ok=True, expires_at=expires, action=action)
            if not db.execute("SELECT 1 FROM robot_bindings WHERE user_id=? AND mac_address=?", (user_id, mac)).fetchone():
                return jsonify(ok=False, error="Thiết bị không thuộc người dùng này"), 404
            if action == "delete":
                db.execute("DELETE FROM mac_tool_licenses WHERE user_id=? AND mac_address=? AND tool_name=?", (user_id, mac, tool))
            else:
                db.execute(
                    "INSERT INTO mac_tool_licenses(user_id,mac_address,tool_name,expires_at,enabled) VALUES(?,?,?,?,?) "
                    "ON CONFLICT(user_id,mac_address,tool_name) DO UPDATE SET expires_at=excluded.expires_at,enabled=excluded.enabled",
                    (user_id, mac, tool, expires, enabled),
                )
            db.commit()
        return jsonify(ok=True, expires_at=expires, action=action)
    @bp.post("/admin/remove-device")
    def admin_remove_device():
        if not web_user(admin=True):
            return jsonify(ok=False, error="Bạn không có quyền quản trị"), 403
        if not valid_csrf():
            return jsonify(ok=False, error="Phiên làm việc không hợp lệ"), 400
        body = request.get_json(silent=True) or {}
        try: user_id = int(body.get("user_id"))
        except (TypeError, ValueError): return jsonify(ok=False, error="Người dùng không hợp lệ"), 400
        session_id = str(body.get("session_id", ""))[:80]
        with _license_db() as db:
            robot = db.execute("SELECT mac_address FROM robot_bindings WHERE user_id=? AND session_id=?", (user_id, session_id)).fetchone()
            if not robot: return jsonify(ok=False, error="Không tìm thấy thiết bị"), 404
            db.execute("DELETE FROM robot_bindings WHERE user_id=? AND session_id=?", (user_id, session_id))
            db.execute("DELETE FROM mac_tool_licenses WHERE user_id=? AND mac_address=?", (user_id, robot["mac_address"] or ""))
            db.execute("DELETE FROM mac_service_profiles WHERE user_id=? AND mac_address=?", (user_id, robot["mac_address"] or ""))
            db.commit()
        return jsonify(ok=True)

    @bp.post("/admin/access")
    def admin_access():
        admin = web_user(admin=True)
        if not admin:
            return jsonify(ok=False, error="admin required"), 403
        if not valid_csrf():
            return jsonify(ok=False, error="invalid csrf"), 400
        body = request.get_json(silent=True) or {}
        try:
            user_id = int(body.get("user_id"))
            days = max(0, min(int(body.get("days", 7)), 3650))
        except (TypeError, ValueError):
            return jsonify(ok=False, error="invalid user or duration"), 400
        tool_name = str(body.get("tool_name", ""))[:64]
        scope = str(body.get("scope", "tool"))[:16]
        mac_address = _normalize_mac(str(body.get("mac_address", "")))
        enabled = 1 if body.get("enabled", True) else 0
        if scope == "tool" and tool_name not in TOOLS:
            return jsonify(ok=False, error="unknown tool"), 400
        expires = (datetime.now(timezone.utc).astimezone() + timedelta(days=days)).isoformat(
            timespec="seconds"
        )
        with _license_db() as db:
            if scope == "account":
                db.execute(
                    "INSERT INTO account_access(user_id,expires_at) VALUES(?,?) "
                    "ON CONFLICT(user_id) DO UPDATE SET expires_at=excluded.expires_at",
                    (user_id, expires),
                )
            elif scope == "mac" and mac_address:
                db.execute(
                    "INSERT INTO mac_access(user_id,mac_address,expires_at) VALUES(?,?,?) "
                    "ON CONFLICT(user_id,mac_address) DO UPDATE SET expires_at=excluded.expires_at",
                    (user_id, mac_address, expires),
                )
            elif scope == "tool":
                db.execute(
                    "INSERT INTO tool_licenses(user_id,tool_name,expires_at,enabled) VALUES(?,?,?,?) "
                    "ON CONFLICT(user_id,tool_name) DO UPDATE SET expires_at=excluded.expires_at,"
                    "enabled=excluded.enabled",
                    (user_id, tool_name, expires, enabled),
                )
            else:
                return jsonify(ok=False, error="invalid access scope or MAC"), 400
            db.commit()
        return jsonify(ok=True, user_id=user_id, scope=scope, tool_name=tool_name,
                       mac_address=mac_address, expires_at=expires, enabled=bool(enabled))

    @bp.get("/firmware/download/<path:filename>")
    def firmware_download(filename: str):
        user = web_user()
        if not user:
            return jsonify(ok=False, error="login required"), 401
        mac_address = _normalize_mac(request.args.get("mac", ""))
        if not mac_address:
            return jsonify(ok=False, error="MAC robot không hợp lệ"), 400
        safe_name = Path(filename).name
        target = FIRMWARE_DIR / safe_name
        if not target.is_file() or target.suffix.lower() not in {".bin", ".zip"}:
            return jsonify(ok=False, error="firmware không tồn tại"), 404
        with _license_db() as db:
            _ensure_trial(db, user["id"])
            account = db.execute(
                "SELECT expires_at FROM account_access WHERE user_id=?", (user["id"],)
            ).fetchone()
            mac = db.execute(
                "SELECT expires_at FROM mac_access WHERE user_id=? AND mac_address=?",
                (user["id"], mac_address),
            ).fetchone()
            if not ((account and _active(account["expires_at"])) or
                    (mac and _active(mac["expires_at"]))):
                return jsonify(ok=False, error="tài khoản hoặc MAC đã hết hạn"), 403
            db.execute(
                "INSERT INTO firmware_downloads(user_id,mac_address,filename,downloaded_at,remote_addr) "
                "VALUES(?,?,?,?,?)",
                (user["id"], mac_address, safe_name, _now(), request.remote_addr),
            )
            db.commit()
        return send_file(target, as_attachment=True, download_name=safe_name)

    @bp.get("/music/<session_id>/stream.ogg")
    def music_stream(session_id: str):
        token = request.args.get("token", "")
        with SESSION_LOCK:
            state = dict(SESSIONS.get(session_id, {}))
        session_file = MUSIC_SESSION_DIR / f"{session_id}.json"
        if session_file.is_file():
            try:
                state = json.loads(session_file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                state = {}
        if not token or not secrets.compare_digest(token, state.get("music_token", "")):
            return jsonify(ok=False, error="invalid music session"), 403
        source = state.get("music_source", "")
        if not source.startswith("https://audio-ssl.itunes.apple.com/"):
            return jsonify(ok=False, error="music source unavailable"), 404

        def generate():
            process = subprocess.Popen(
                ["ffmpeg", "-nostdin", "-loglevel", "error", "-i", source, "-vn",
                 "-ac", "1", "-ar", "24000", "-c:a", "libopus", "-b:a", "48k",
                 "-frame_duration", "60", "-f", "ogg", "pipe:1"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            try:
                while True:
                    chunk = process.stdout.read(4096)
                    if not chunk:
                        break
                    yield chunk
            finally:
                if process.poll() is None:
                    process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()

        return Response(stream_with_context(generate()), mimetype="audio/ogg",
                        headers={"Cache-Control": "no-store", "X-Xiaozhi-Session": session_id})

    @bp.post("/tools/call")
    def call_tool():
        session_id = request.headers.get("X-Xiaozhi-Session", "").strip()[:80]
        if not re.fullmatch(r"[A-Za-z0-9._:-]{8,80}", session_id):
            return jsonify(ok=False, error="missing or invalid isolated session"), 400
        body = request.get_json(silent=True) or {}
        name = str(body.get("name", ""))[:64]
        args = body.get("arguments") if isinstance(body.get("arguments"), dict) else {}
        query = str(args.get("query") or args.get("topic") or "").strip()[:240]
        limit = max(1, min(int(args.get("limit", 5)), 8))
        allowed, reason = _tool_allowed(session_id, name)
        if not allowed:
            return jsonify(ok=False, error=reason, tool=name, session_id=session_id), 403
        try:
            if name == "search_web" and query:
                result = _cached(f"search:{query}:{limit}", 300, lambda: _search(query, limit))
            elif name == "get_latest_news":
                query = query or "tin tức Việt Nam mới nhất when:1d"
                result = _cached(f"news:{query}:{limit}", 300, lambda: _rss(query, limit))
            elif name == "get_gold_price":
                query = "giá vàng SJC hôm nay Việt Nam when:1d"
                result = _cached("gold", 300, lambda: _rss(query, limit))
            elif name == "get_fuel_price":
                query = "giá xăng dầu mới nhất Việt Nam when:7d"
                result = _cached("fuel", 900, lambda: _rss(query, limit))
            elif name == "search_music" and query:
                result = _cached(f"music:{query}:{limit}", 3600, lambda: _music(query, limit))
            elif name == "prepare_music" and query:
                music = _music(query, 1)
                item = next((x for x in music.get("items", []) if x.get("preview_url")), None)
                if not item:
                    raise RuntimeError("no playable music result")
                token = secrets.token_urlsafe(24)
                with SESSION_LOCK:
                    SESSIONS[session_id] = {
                        "music_source": item["preview_url"], "music_token": token,
                        "updated_at": _now(),
                    }
                    MUSIC_SESSION_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
                    session_file = MUSIC_SESSION_DIR / f"{session_id}.json"
                    temporary = session_file.with_suffix(".tmp")
                    temporary.write_text(json.dumps(SESSIONS[session_id]), encoding="utf-8")
                    os.chmod(temporary, 0o600)
                    temporary.replace(session_file)
                result = {
                    "ok": True, "title": item.get("title", ""),
                    "artist": item.get("artist", ""),
                    "stream_url": (
                        f"{request.url_root.rstrip('/')}/api/xiaozhi/music/{session_id}/stream.ogg?"
                        + urllib.parse.urlencode({"token": token})
                    ),
                    "format": "Ogg Opus 24 kHz mono", "output": "robot_speaker",
                    "updated_at": _now(),
                }
            elif name == "chat_with_gpt" and query:
                result = _gpt(query)
            elif name == "search_youtube_music" and query:
                result = _cached(
                    f"youtube:{query}:{limit}", 900, lambda: _youtube_music(query, limit)
                )
            else:
                return jsonify(ok=False, error="unknown tool or missing query"), 400
            with SESSION_LOCK:
                state = SESSIONS.setdefault(session_id, {})
                state.update({"last_tool": name, "last_query": query, "updated_at": _now()})
                if len(SESSIONS) > 2048:
                    oldest = next(iter(SESSIONS))
                    SESSIONS.pop(oldest, None)
            result["session_id"] = session_id
            result["tool"] = name
            return jsonify(result)
        except Exception as exc:
            app.logger.warning("XiaoZhi tool %s failed: %s", name, exc)
            return jsonify(ok=False, tool=name, error="upstream unavailable", updated_at=_now()), 502

    app.register_blueprint(bp)

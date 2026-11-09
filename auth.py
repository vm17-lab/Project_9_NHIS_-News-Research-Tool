"""
auth.py
-------
simple username/password authentication (Python standard library only).

* Passwords are never stored: only a salted PBKDF2-SHA256 hash is saved.
* Accounts live in data/users.json, each user's chats in data/chats/<username>.json.
* 5 wrong passwords lock the account for 5 minutes (basic brute-force protection).
"""
import hashlib
import hmac
import json
import math
import os
import re
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DATA_DIR = Path(__file__).with_name("data")
LOGIN_PAGE = Path(__file__).with_name("login.html")
USERNAME_RE = re.compile(r"^[a-z0-9_]{3,20}$")
MIN_PASSWORD_LEN, MAX_PASSWORD_LEN = 8, 128
MAX_FAILS, LOCK_SECONDS = 5, 300
ITERATIONS = 200_000
SESSION_SECONDS = 7 * 24 * 3600  # stay logged in for 7 days

_lock = threading.RLock()


def _users_file():
    return DATA_DIR / "users.json"


def _load():
    try:
        return json.loads(_users_file().read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(users):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _users_file().with_suffix(".tmp")
    tmp.write_text(json.dumps(users, indent=2), encoding="utf-8")
    tmp.replace(_users_file())


def _hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS).hex()


def signup(username, password, confirm, invite_code=""):
    username = (username or "").strip().lower()
    required = os.getenv("SIGNUP_CODE", "")
    if required and not hmac.compare_digest((invite_code or "").encode(), required.encode()):
        return False, "Invalid invite code."
    if not USERNAME_RE.match(username):
        return False, "Username must be 3-20 characters: letters, numbers or underscore."
    if not (MIN_PASSWORD_LEN <= len(password or "") <= MAX_PASSWORD_LEN):
        return False, f"Password must be {MIN_PASSWORD_LEN}-{MAX_PASSWORD_LEN} characters."
    if password != confirm:
        return False, "Passwords do not match."
    users = _load()
    if username in users:
        return False, "That username is already taken."
    salt = secrets.token_bytes(16)
    users[username] = {
        "salt": salt.hex(),
        "hash": _hash(password, salt),
        "created": time.strftime("%Y-%m-%d %H:%M"),
        "fails": 0,
        "locked_until": 0,
    }
    _save(users)
    return True, "Account created. You can log in now."


def login(username, password):
    """Check credentials. Returns (ok, message)."""
    username = (username or "").strip().lower()
    password = password or ""
    users = _load()
    user = users.get(username)
    now = time.time()
    if user and user.get("locked_until", 0) > now:
        minutes = math.ceil((user["locked_until"] - now) / 60)
        return False, f"Too many failed attempts. Try again in {minutes} minute(s)."
    salt = bytes.fromhex(user["salt"]) if user else b"\0" * 16
    candidate = _hash(password[:MAX_PASSWORD_LEN], salt)
    if user and hmac.compare_digest(candidate, user["hash"]):
        user["fails"], user["locked_until"] = 0, 0
        _save(users)
        return True, ""
    if user:
        user["fails"] = user.get("fails", 0) + 1
        if user["fails"] >= MAX_FAILS:
            user["fails"], user["locked_until"] = 0, now + LOCK_SECONDS
        _save(users)
    return False, "Invalid username or password."


def chats_file(username):
    if not USERNAME_RE.match(username or ""):
        raise ValueError("invalid username")
    return DATA_DIR / "chats" / f"{username}.json"


# ---------------------------------------------------------------- sessions
def _secret():
    f = DATA_DIR / "secret.key"
    if not f.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        f.write_text(secrets.token_hex(32), encoding="utf-8")
    return bytes.fromhex(f.read_text(encoding="utf-8").strip())


def _sign(body):
    return hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()


def create_session(username):
    body = f"{username}|{int(time.time()) + SESSION_SECONDS}"
    return f"{body}|{_sign(body)}"


def verify_session(token):
    try:
        username, expiry, sig = (token or "").split("|")
        if (hmac.compare_digest(sig, _sign(f"{username}|{expiry}"))
                and int(expiry) > time.time() and USERNAME_RE.match(username)):
            return username
    except Exception:
        pass
    return None


# ---------------------------------------------------------------- web server
class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json", headers=()):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj, headers=()):
        self._send(200, json.dumps(obj), headers=headers)

    def _redirect(self, where):
        self.send_response(302)
        self.send_header("Location", where)
        self.end_headers()

    def _user(self):
        for part in self.headers.get("Cookie", "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == "session":
                return verify_session(v)
        return None

    def do_GET(self):
        path, user = self.path.split("?")[0], self._user()
        if path == "/":
            if user:
                return self._redirect("/app")
            return self._send(200, LOGIN_PAGE.read_text(encoding="utf-8"), "text/html")
        if path == "/app":
            if not user:
                return self._redirect("/")
            page = (f"<body style='font-family:system-ui;padding:40px'><h2>Welcome, {user}</h2>"
                    "<p>You are logged in.</p><button onclick=\"fetch('/api/logout',{method:'POST'})"
                    ".then(()=>location='/')\">Log out</button></body>")
            return self._send(200, page, "text/html")
        if path == "/api/config":
            return self._json({"invite_required": bool(os.getenv("SIGNUP_CODE"))})
        if path == "/api/me":
            return self._json({"user": user})
        self._send(404, "Not found", "text/plain")

    def do_POST(self):
        path = self.path.split("?")[0]
        try:
            size = min(int(self.headers.get("Content-Length", 0)), 10_000)
            data = json.loads(self.rfile.read(size) or b"{}")
        except Exception:
            data = {}
        if path == "/api/signup":
            with _lock:
                ok, msg = signup(data.get("username"), data.get("password"),
                                 data.get("confirm"), data.get("invite_code"))
            return self._json({"ok": ok, "message": msg})
        if path == "/api/login":
            with _lock:
                ok, msg = login(data.get("username"), data.get("password"))
            if not ok:
                return self._json({"ok": False, "message": msg})
            name = (data.get("username") or "").strip().lower()
            cookie = (f"session={create_session(name)}; Path=/; HttpOnly; "
                      f"SameSite=Lax; Max-Age={SESSION_SECONDS}")
            return self._json({"ok": True, "message": "", "next": "/app"},
                              headers=[("Set-Cookie", cookie)])
        if path == "/api/logout":
            return self._json({"ok": True},
                              headers=[("Set-Cookie", "session=; Path=/; HttpOnly; Max-Age=0")])
        self._send(404, "Not found", "text/plain")

    def log_message(self, *args):
        pass

def run(port=8000):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Login page running at http://localhost:{port}  (Ctrl+C to stop)")
    server.serve_forever()


if __name__ == "__main__":
    run()
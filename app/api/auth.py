"""Google OIDC login with verified identities and revocable server-side sessions."""

import hashlib
import hmac
import re
import os
import secrets
import sqlite3
import time
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.middleware.sessions import SessionMiddleware


def password_policy_error(password, identity):
    if not 12 <= len(password) <= 128:
        return "Use 12–128 characters for your password."
    if not (re.search(r"[A-Z]", password) and re.search(r"[a-z]", password)
            and re.search(r"[0-9]", password)
            and any(not c.isalnum() and not c.isspace() for c in password)):
        return "Include an uppercase letter, a lowercase letter, a number and a symbol."
    folded = password.casefold()
    common = ("password", "qwerty", "letmein", "welcome", "changeme", "123456", "abcdef")
    if any(word in folded for word in common) or len(set(folded)) < 6:
        return "Avoid common passwords, predictable sequences and repeated characters."
    account_name = identity.split("@", 1)[0].casefold()
    if len(account_name) >= 3 and account_name in folded:
        return "Your password must not contain your username or the name part of your email."
    return None


class Accounts:
    def __init__(self):
        self.sessions = {}

    def login(self, claims, database):
        if (
            claims.get("email_verified") is not True
            or not claims.get("sub")
            or not claims.get("email")
        ):
            raise ValueError("A verified Google email is required")
        email = claims["email"].lower()
        with sqlite3.connect(database) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS users (subject TEXT PRIMARY KEY, email TEXT NOT NULL, name TEXT NOT NULL, joined REAL NOT NULL)"
            )
            db.execute(
                "INSERT INTO users VALUES (?,?,?,?) ON CONFLICT(subject) DO UPDATE SET email=excluded.email,name=excluded.name",
                (claims["sub"], email, claims.get("name", email), time.time()),
            )
        now = time.time()
        self.sessions = {k: v for k, v in self.sessions.items() if v["expires"] > now}
        sid = secrets.token_urlsafe(32)
        self.sessions[sid] = dict(
            email=email,
            name=claims.get("name", email),
            csrf=secrets.token_urlsafe(32),
            expires=now + 28800,
        )
        return sid

    def user(self, session):
        sid = session.get("sid", "")
        user = self.sessions.get(sid)
        if user and user["expires"] > time.time():
            return user
        self.sessions.pop(sid, None)
        return None


def configure_auth(app, assets):
    mode = os.getenv("RDRS_AUTH_MODE", "password")
    if mode not in ("password", "google", "local"):
        raise ValueError("RDRS_AUTH_MODE must be password, google or local")
    origin = os.getenv("RDRS_PUBLIC_URL", "http://127.0.0.1:8000").rstrip("/")
    parsed = urlsplit(origin)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.path
        or parsed.query
        or parsed.fragment
        or parsed.username
    ):
        raise ValueError("RDRS_PUBLIC_URL must be an absolute origin without a path")
    local_origin = parsed.hostname in ("localhost", "127.0.0.1", "testserver", "::1")
    if not local_origin and (mode == "local" or parsed.scheme != "https"):
        raise ValueError("Public deployments require login and HTTPS")
    key = os.getenv("RDRS_SESSION_SECRET", "")
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    configured = bool(client_id and client_secret and len(key) >= 32)
    if not local_origin and (len(key) < 32 or (mode == "google" and not configured)):
        raise ValueError(
            "Configure Google credentials and a session secret of at least 32 characters"
        )
    accounts = Accounts()
    app.state.accounts = accounts
    app.state.auth_mode = mode
    app.state.auth_origin = origin
    app.state.admin_emails = {
        e.strip().lower() for e in os.getenv("RDRS_ADMIN_EMAILS", "").split(",") if e.strip()
    }
    oauth = OAuth()
    google = oauth.register(
        "google",
        client_id=client_id,
        client_secret=client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile", "code_challenge_method": "S256"},
    )
    app.state.google = google
    env = Environment(loader=FileSystemLoader(assets / "templates"), autoescape=select_autoescape())

    @app.middleware("http")
    async def protect(request: Request, call_next):
        path = request.url.path
        public = path in (
            "/health",
            "/login",
            "/signup",
            "/auth/google",
            "/auth/callback",
        ) or path.startswith("/static/")
        if mode != "local" and not public and not accounts.user(request.session):
            if path == "/":
                return RedirectResponse("/login", status_code=303)
            return JSONResponse({"detail": "Sign in to continue"}, status_code=401)
        response = await call_next(request)
        if not path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    app.add_middleware(
        SessionMiddleware,
        secret_key=key or secrets.token_urlsafe(32),
        session_cookie="rdrs_session",
        max_age=28800,
        same_site="lax",
        https_only=parsed.scheme == "https",
    )

    @app.get("/login", response_class=HTMLResponse)
    @app.get("/signup", response_class=HTMLResponse)
    async def login_page(request: Request):
        if accounts.user(request.session):
            return RedirectResponse("/", status_code=303)
        return HTMLResponse(
            env.get_template("login.html").render(
                password_mode=mode == "password",
                csrf=request.session.setdefault("form_csrf", secrets.token_urlsafe(32)),
                error=request.query_params.get("error", ""),
                created=bool(request.query_params.get("created")),
                signup=request.url.path == "/signup",
                configured=configured,
                local=mode == "local",
                failed=bool(request.query_params.get("error")),
            )
        )

    attempts = {}

    @app.post("/signup")
    @app.post("/login")
    async def password_login(request: Request):
        if mode != "password":
            raise HTTPException(404, "Local accounts are disabled")
        body = await request.body()
        if len(body) > 4096:
            raise HTTPException(413, "Form is too large")
        form = {k: v[0] for k, v in parse_qs(body.decode("utf-8", errors="replace")).items()}
        csrf = request.session.get("form_csrf", "")
        if (request.headers.get("origin") != origin or not csrf
                or not secrets.compare_digest(form.get("csrf", ""), csrf)):
            raise HTTPException(403, "Refresh the page and try again")
        now = time.time()
        for key in list(attempts):
            if attempts[key][1] < now - 300:
                del attempts[key]
        ip = request.client.host if request.client else "unknown"
        count, started = attempts.get(ip, (0, now))
        if count >= 20 or len(attempts) > 10000:
            raise HTTPException(429, "Too many attempts. Try again in five minutes")
        attempts[ip] = (count + 1, started)
        identity = form.get("identity", "").strip().lower()
        password = form.get("password", "")
        signup = request.url.path == "/signup"
        policy_error = password_policy_error(password, identity) if signup else None
        if policy_error:
            return HTMLResponse(env.get_template("login.html").render(signup=True, password_mode=True, csrf=csrf, error=policy_error), status_code=400)
        error = "Use a username (3–64 letters, numbers, dots, underscores or hyphens) or an email address."
        valid = re.fullmatch(r"[a-z0-9_.-]{3,64}", identity) or re.fullmatch(r"[^\s@]{1,64}@[^\s@.]+(?:\.[^\s@.]+)+", identity)
        if valid and len(identity) <= 254 and 10 <= len(password) <= 128:
            database = Path(app.state.runtime.config.database.path).parent / "accounts.db"
            with sqlite3.connect(database) as db:
                db.execute("CREATE TABLE IF NOT EXISTS local_users (identity TEXT PRIMARY KEY, salt BLOB NOT NULL, digest BLOB NOT NULL)")
                row = db.execute("SELECT salt,digest FROM local_users WHERE identity=?", (identity,)).fetchone()
                salt = row[0] if row else secrets.token_bytes(16)
                digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
                if signup:
                    try:
                        db.execute("INSERT INTO local_users VALUES (?,?,?)", (identity, salt, digest))
                    except sqlite3.IntegrityError:
                        error = "That email or username is already registered. Please log in."
                    else:
                        return RedirectResponse("/login?created=1", status_code=303)
                elif row and hmac.compare_digest(row[1], digest):
                    sid = secrets.token_urlsafe(32)
                    accounts.sessions = {k: v for k, v in accounts.sessions.items() if v["expires"] > now}
                    accounts.sessions[sid] = dict(email=identity, name=identity, csrf=secrets.token_urlsafe(32), expires=now + 28800)
                    request.session.clear()
                    request.session["sid"] = sid
                    return RedirectResponse("/", status_code=303)
                else:
                    error = "Incorrect email/username or password."
        elif valid:
            error = "Choose a password between 10 and 128 characters." if signup else "Incorrect email/username or password."
        return HTMLResponse(env.get_template("login.html").render(signup=signup, password_mode=True, csrf=csrf, error=error), status_code=400)

    @app.get("/auth/google")
    async def login_google(request: Request):
        if not configured:
            return RedirectResponse("/login?error=configuration", status_code=303)
        request.session.clear()
        return await google.authorize_redirect(
            request, origin + "/auth/callback", prompt="select_account"
        )

    @app.get("/auth/callback")
    async def callback(request: Request):
        try:
            if not configured:
                raise ValueError("Google is not configured")
            token = await google.authorize_access_token(request)
            claims = token.get(
                "userinfo", {}
            )  # Authlib validates signature, issuer, audience, expiry and nonce.
            db = Path(app.state.runtime.config.database.path).parent / "accounts.db"
            sid = accounts.login(claims, db)
        except Exception:
            request.session.clear()
            return RedirectResponse("/login?error=verification", status_code=303)
        request.session.clear()
        request.session["sid"] = sid  # Never persist Google's access/refresh tokens.
        return RedirectResponse("/", status_code=303)

    @app.get("/auth/me")
    def me(request: Request):
        user = accounts.user(request.session)
        return dict(
            mode=mode,
            user={k: user[k] for k in ("email", "name", "csrf")} if user else None,
            admin=bool(user and user["email"] in app.state.admin_emails),
        )

    @app.post("/auth/logout")
    async def logout(request: Request):
        require_session_write(request)
        accounts.sessions.pop(request.session.get("sid"), None)
        request.session.clear()
        return {"signed_out": True}

    return parsed.hostname


def require_session_write(request, admin=False):
    user = request.app.state.accounts.user(request.session)
    if not user:
        raise HTTPException(401, "Sign in to continue")
    if request.headers.get("origin") != request.app.state.auth_origin or not secrets.compare_digest(
        request.headers.get("x-csrf-token", ""), user["csrf"]
    ):
        raise HTTPException(403, "Refresh the page and retry this action")
    if admin and user["email"] not in request.app.state.admin_emails:
        raise HTTPException(403, "Administrator access is required for this action")
    return user

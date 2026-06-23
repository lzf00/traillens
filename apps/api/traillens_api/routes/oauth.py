"""OAuth 一键登录骨架(Google / GitHub)。

需要 env 配置:
  GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET / GOOGLE_REDIRECT_URI
  GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET / GITHUB_REDIRECT_URI

流程:
  GET /v1/auth/oauth/{provider}/start         → 302 第三方 authorize
  GET /v1/auth/oauth/{provider}/callback      → 用 code 换 access_token,
                                                 拉用户 profile,upsert users,
                                                 写 traillens_session cookie

当前实现:
  - start 路由能跳第三方(需 env 全配齐,否则 503)
  - callback 待 env 配齐后接通
"""

from __future__ import annotations

import os
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

router = APIRouter()

# auth URL 浏览器跳,直连即可(浏览器在用户侧,不受国内服务器墙影响)
# token + userinfo 是后端调,国内可配 OAUTH_PROXY_BASE 走 CF Worker 中转
_PROXY = os.environ.get("OAUTH_PROXY_BASE", "").rstrip("/")

def _token_url(provider: str, default: str) -> str:
    return f"{_PROXY}/{provider}/token" if _PROXY else default

def _userinfo_url(provider: str, default: str) -> str:
    # userinfo 路径在 worker 里映射为 /provider/userinfo or /provider/user
    if not _PROXY:
        return default
    suffix = "userinfo" if provider == "google" else "user"
    return f"{_PROXY}/{provider}/{suffix}"


PROVIDERS = {
    "google": {
        "auth": "https://accounts.google.com/o/oauth2/v2/auth",
        "token": _token_url("google", "https://oauth2.googleapis.com/token"),
        "userinfo": _userinfo_url("google", "https://www.googleapis.com/oauth2/v3/userinfo"),
        "scope": "openid email profile",
    },
    "github": {
        "auth": "https://github.com/login/oauth/authorize",
        "token": _token_url("github", "https://github.com/login/oauth/access_token"),
        "userinfo": _userinfo_url("github", "https://api.github.com/user"),
        "scope": "read:user user:email",
    },
}


def _cfg(provider: str) -> dict:
    p = provider.upper()
    cid = os.environ.get(f"{p}_CLIENT_ID")
    csec = os.environ.get(f"{p}_CLIENT_SECRET")
    redir = os.environ.get(f"{p}_REDIRECT_URI",
                            f"https://traillens.zorotreeking.online/v1/auth/oauth/{provider}/callback")
    if not (cid and csec):
        raise HTTPException(503, f"{provider} OAuth 未配置(缺 {p}_CLIENT_ID / _SECRET)")
    return {"client_id": cid, "client_secret": csec, "redirect_uri": redir, **PROVIDERS[provider]}


@router.get("/oauth/{provider}/start")
def oauth_start(provider: str, request: Request):
    if provider not in PROVIDERS:
        raise HTTPException(404, "unknown_provider")
    c = _cfg(provider)
    state = secrets.token_urlsafe(16)
    qs = urlencode({
        "client_id": c["client_id"],
        "redirect_uri": c["redirect_uri"],
        "scope": c["scope"],
        "response_type": "code",
        "state": state,
    })
    resp = RedirectResponse(f"{c['auth']}?{qs}", status_code=302)
    resp.set_cookie("oauth_state", state, max_age=600, httponly=True, samesite="lax")
    return resp


@router.get("/oauth/{provider}/callback")
def oauth_callback(provider: str, code: str, state: str, request: Request, response: Response):
    if provider not in PROVIDERS:
        raise HTTPException(404, "unknown_provider")
    if request.cookies.get("oauth_state") != state:
        raise HTTPException(400, "state_mismatch")
    c = _cfg(provider)

    import httpx
    # OAUTH_HTTP_PROXY=http://user:pass@host:port (国内服务器调海外 OAuth 必备)
    proxy = os.environ.get("OAUTH_HTTP_PROXY") or os.environ.get("HTTPS_PROXY")
    client_kwargs = {"timeout": 30.0}
    if proxy:
        client_kwargs["proxy"] = proxy

    try:
        with httpx.Client(**client_kwargs) as hc:
            token_resp = hc.post(
                c["token"],
                data={
                    "client_id": c["client_id"],
                    "client_secret": c["client_secret"],
                    "code": code,
                    "redirect_uri": c["redirect_uri"],
                    "grant_type": "authorization_code",
                },
                headers={"Accept": "application/json"},
            )
    except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as e:
        raise HTTPException(
            502,
            f"OAuth provider 不可达(国内服务器到 {provider} token endpoint 网络受限)。"
            f"配 OAUTH_HTTP_PROXY=http://proxy:port 后重试。原始错误: {type(e).__name__}",
        )

    if token_resp.status_code != 200:
        raise HTTPException(400, f"token_exchange_failed: {token_resp.text[:200]}")
    access_token = token_resp.json().get("access_token")

    try:
        with httpx.Client(**client_kwargs) as hc:
            user_resp = hc.get(
                c["userinfo"],
                headers={"Authorization": f"Bearer {access_token}"},
            )
    except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as e:
        raise HTTPException(502, f"userinfo 不可达: {type(e).__name__}")

    if user_resp.status_code != 200:
        raise HTTPException(400, "userinfo_failed")
    profile = user_resp.json()

    email = profile.get("email")
    name = profile.get("name") or profile.get("login")
    if not email:
        raise HTTPException(400, "no_email_in_profile")

    # upsert user(已存在按 email 查;不存在 sign_up 无密码)
    from ..services import auth as auth_svc
    from ..routes.auth import _set_session_cookie

    existing_sql_id = None
    try:
        info = auth_svc.sign_up(email, secrets.token_urlsafe(32), name=name)
        token = info["token"]
    except ValueError:
        # 已注册 → 直接 issue token
        # 简化:不 verify password,直接按 email 拿 user row 签 token
        from ..services import db
        from sqlalchemy import text
        with db.session() as s:
            row = s.execute(text("SELECT id FROM users WHERE lower(email)=:e"),
                            {"e": email.lower()}).first()
        if not row:
            raise HTTPException(500, "upsert_failed")
        token = auth_svc.make_session_token(str(row.id), email)

    _set_session_cookie(response, token)
    return RedirectResponse("/trails", status_code=302, headers=dict(response.headers))

"""/v1/auth — 真实邮箱密码 auth(替换 dev 桥)。"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field

from ..deps import CurrentUser, get_current_user
from ..services import auth as auth_svc

router = APIRouter()

SESSION_COOKIE = "traillens_session"
COOKIE_DAYS = int(os.environ.get("TRAILLENS_SESSION_DAYS", "30"))


def _set_session_cookie(resp: Response, token: str, email: str | None = None) -> None:
    secure = os.environ.get("TRAILLENS_ENV", "local") == "prod"
    resp.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=COOKIE_DAYS * 24 * 3600,
        path="/",
    )
    # 兼容旧 dev 桥:annotation 容器 + 部分老脚本读 traillens_user_email
    # 让 settings 页的"标注后台"模块对新 auth 用户也工作
    if email:
        resp.set_cookie(
            key="traillens_user_email",
            value=email,
            httponly=True,
            secure=secure,
            samesite="lax",
            max_age=COOKIE_DAYS * 24 * 3600,
            path="/",
        )


class SignUpBody(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    name: str | None = None


class SignInBody(BaseModel):
    email: EmailStr
    password: str


@router.post("/sign-up", status_code=201)
def sign_up(body: SignUpBody, response: Response) -> dict:
    try:
        out = auth_svc.sign_up(body.email, body.password, body.name)
    except ValueError as e:
        code = str(e)
        msg_map = {
            "email_already_exists": "邮箱已注册",
            "invalid_email": "邮箱格式不对",
            "password_too_short": "密码至少 6 位",
        }
        raise HTTPException(400, detail=msg_map.get(code, code))
    _set_session_cookie(response, out.pop("token"), email=out.get("email"))
    return out


@router.post("/sign-in")
def sign_in(body: SignInBody, response: Response) -> dict:
    try:
        out = auth_svc.sign_in(body.email, body.password)
    except ValueError:
        raise HTTPException(401, "邮箱或密码错误")
    _set_session_cookie(response, out.pop("token"), email=out.get("email"))
    return out


@router.post("/sign-out")
def sign_out(request: Request) -> Response:
    """登出 + 跳首页(浏览器表单 POST 时直接跳转,不让用户看到裸 JSON)。

    fetch() / 非浏览器调用看 Accept 头 → 如果不要 HTML 就返 JSON。
    """
    secure = os.environ.get("TRAILLENS_ENV", "local") == "prod"
    accept = (request.headers.get("accept") or "").lower()
    wants_html = "text/html" in accept

    if wants_html:
        resp = RedirectResponse(url="/", status_code=303)
    else:
        from fastapi.responses import JSONResponse
        resp = JSONResponse({"ok": True})
    for ck in (SESSION_COOKIE, "traillens_user_email"):
        resp.delete_cookie(
            ck,
            path="/",
            httponly=True,
            secure=secure,
            samesite="lax",
        )
    return resp


@router.get("/me")
def me(user: CurrentUser = Depends(get_current_user)) -> dict:
    """返回当前登录 user 的 profile;未登录 401。"""
    info = auth_svc.get_user(user.id)
    if not info:
        # dev local user 或 user 被删除
        return {
            "user_id": user.id,
            "email": user.email,
            "name": None,
            "plan": user.plan,
            "quota_remaining": user.quota_remaining,
        }
    return info

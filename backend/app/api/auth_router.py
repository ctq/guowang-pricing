import hashlib
import random
from datetime import datetime, timedelta
from os import environ

from app.utils import now
from pathlib import Path
from typing import Annotated
from xml.etree import ElementTree as ET

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_token
from app.auth.rate_limit import check_ip
from app.db.models import LoginQRCode, User
from app.db.session import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])
wechat_router = APIRouter(tags=["wechat"])

DbDep = Annotated[AsyncSession, Depends(get_db)]

QRCODE_IMAGE_PATH = Path(environ.get("QRCODE_IMAGE_PATH", "data/qrcode.jpg"))


class QRCodeResponse(BaseModel):
    code: str
    qrcode_url: str
    expires_at: datetime


class StatusResponse(BaseModel):
    status: str
    token: str | None = None


@router.post("/qrcode")
async def generate_code(request: Request, db: DbDep) -> QRCodeResponse:
    ip = request.client.host if request.client else "unknown"
    if not check_ip(ip):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="请求太频繁，请 60 秒后再试")

    code = f"{random.randint(1000, 9999)}"
    expires_at = now() + timedelta(minutes=5)

    db.add(LoginQRCode(code=code, status="pending", expires_at=expires_at))
    await db.commit()

    return QRCodeResponse(
        code=code,
        qrcode_url="/api/auth/qrcode-image",
        expires_at=expires_at,
    )


@router.get("/qrcode-image")
async def qrcode_image() -> Response:
    if QRCODE_IMAGE_PATH.exists():
        return FileResponse(str(QRCODE_IMAGE_PATH), media_type="image/jpeg")
    return Response(status_code=404, content="QR code image not found")


@router.get("/status")
async def query_status(code: str, db: DbDep) -> StatusResponse:
    result = await db.execute(select(LoginQRCode).where(LoginQRCode.code == code))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="验证码不存在")

    if record.status == "logged_in":
        if record.openid:
            token = create_token(record.openid)
            return StatusResponse(status="logged_in", token=token)
        return StatusResponse(status="logged_in")
    if record.expires_at < now():
        record.status = "expired"
        await db.commit()
        return StatusResponse(status="expired")
    return StatusResponse(status=record.status)


# ---- 微信回调 ----

WECHAT_TOKEN = environ.get("WECHAT_TOKEN", "")


def _parse_xml(text: str) -> dict[str, str]:
    root = ET.fromstring(text)
    return {child.tag: child.text or "" for child in root}


def _reply_text(to: str, from_: str, content: str) -> str:
    ts = int(now().timestamp())
    return f"""<xml>
<ToUserName><![CDATA[{to}]]></ToUserName>
<FromUserName><![CDATA[{from_}]]></FromUserName>
<CreateTime>{ts}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>"""


@wechat_router.get("/api/wechat/callback")
async def wechat_verify(request: Request) -> Response:
    params = dict(request.query_params)
    signature = params.get("signature", "")
    timestamp = params.get("timestamp", "")
    nonce = params.get("nonce", "")
    echostr = params.get("echostr", "")

    arr = sorted([WECHAT_TOKEN, timestamp, nonce])
    if hashlib.sha1("".join(arr).encode()).hexdigest() == signature:
        return Response(content=echostr, media_type="text/plain")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="verify failed")


@wechat_router.post("/api/wechat/callback")
async def wechat_callback(request: Request, db: DbDep) -> str:
    body = await request.body()
    xml = _parse_xml(body.decode())
    to_user = xml.get("ToUserName", "")
    from_user = xml.get("FromUserName", "")
    msg_type = xml.get("MsgType", "")

    # 关注事件 → 引导用户发送验证码
    if msg_type == "event" and xml.get("Event") == "subscribe":
        return _reply_text(from_user, to_user, "感谢关注！请回复网页上的验证码（4位数字）完成登录。")

    # 文本消息 → 验证码处理
    if msg_type == "text":
        code = xml.get("Content", "").strip()
        if code.isdigit() and len(code) == 4:
            result = await db.execute(
                select(LoginQRCode).where(LoginQRCode.code == code, LoginQRCode.status == "pending")
            )
            record = result.scalar_one_or_none()
            if record:
                if record.expires_at < now():
                    return _reply_text(from_user, to_user, "验证码已过期，请刷新网页重新获取。")
                record.openid = from_user
                record.status = "logged_in"
                # 自动注册或更新用户
                user_result = await db.execute(select(User).where(User.openid == from_user))
                user = user_result.scalar_one_or_none()
                if not user:
                    user = User(openid=from_user, last_login=now())
                    db.add(user)
                else:
                    user.last_login = now()
                await db.commit()
                return _reply_text(from_user, to_user, "登录成功，欢迎使用电算宝！")
            result2 = await db.execute(
                select(LoginQRCode).where(LoginQRCode.code == code)
            )
            old = result2.scalar_one_or_none()
            if old and old.status == "logged_in":
                return _reply_text(from_user, to_user, "该验证码已使用，请刷新网页重新获取。")
        return _reply_text(from_user, to_user, "验证码无效，请输入网页上显示的4位数字。")

    return "success"

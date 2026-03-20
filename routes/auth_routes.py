from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from core.security import (
    clear_auth_cookie,
    get_session_user,
    hash_password,
    set_auth_cookie,
    validate_password,
    validate_username,
    verify_password,
)
from core.state import create_user, find_user, update_user_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/status", response_class=JSONResponse)
async def auth_status(request: Request):
    user = get_session_user(request)

    return {
        "ok": True,
        "authenticated": bool(user),
        "user": user,
    }


@router.post("/register", response_class=JSONResponse)
async def register(request: Request, response: Response):
    body = await request.json()

    try:
        username = validate_username(body.get("username"))
        password = validate_password(body.get("password"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if find_user(username):
        raise HTTPException(status_code=409, detail="User already exists.")

    password_hash = hash_password(password)
    user = create_user(username, password_hash)
    session_user = set_auth_cookie(response, username)

    return {
        "ok": True,
        "message": "Registration successful.",
        "user": {
            "id": user.get("id"),
            "username": user.get("username"),
        },
        "session": session_user,
    }


@router.post("/login", response_class=JSONResponse)
async def login(request: Request, response: Response):
    body = await request.json()

    username = str(body.get("username", "")).strip()
    password = str(body.get("password", ""))

    user = find_user(username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    stored_hash = str(user.get("password_hash", ""))
    if not verify_password(password, stored_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    session_user = set_auth_cookie(response, username)

    return {
        "ok": True,
        "message": "Login successful.",
        "session": session_user,
    }


@router.post("/logout", response_class=JSONResponse)
async def logout(response: Response):
    result = clear_auth_cookie(response)
    return result


@router.post("/change-password", response_class=JSONResponse)
async def change_password(request: Request):
    body = await request.json()

    session_user = get_session_user(request)
    if not session_user:
        raise HTTPException(status_code=401, detail="Authentication required.")

    username = str(session_user.get("username", "")).strip()
    current_password = str(body.get("current_password", ""))
    new_password_raw = body.get("new_password")

    user = find_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    stored_hash = str(user.get("password_hash", ""))
    if not verify_password(current_password, stored_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect.")

    try:
        new_password = validate_password(new_password_raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    updated = update_user_password(username, hash_password(new_password))

    return {
        "ok": True,
        "message": "Password changed successfully.",
        "user": {
            "id": updated.get("id"),
            "username": updated.get("username"),
        },
    }
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from services.auth_service import authenticate_user, create_user, normalize_username

router = APIRouter(prefix="/api/auth", tags=["auth"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def build_login_response(username: str):
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="nova_username",
        value=username,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24 * 30,
    )
    return response


@router.get("/status")
async def auth_status(request: Request):
    username = request.cookies.get("nova_username", "").strip().lower()
    return {
        "authenticated": bool(username),
        "username": username or None,
    }


@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    clean_username = normalize_username(username)

    if not authenticate_user(clean_username, password):
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Invalid username or password.",
                "register_error": "",
                "register_success": "",
                "active_tab": "login",
                "prefill_username": clean_username,
                "prefill_register_username": "",
            },
            status_code=401,
        )

    return build_login_response(clean_username)


@router.post("/register")
async def register(request: Request, username: str = Form(...), password: str = Form(...)):
    clean_username = normalize_username(username)
    ok, message = create_user(clean_username, password)

    if not ok:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "",
                "register_error": message,
                "register_success": "",
                "active_tab": "register",
                "prefill_username": "",
                "prefill_register_username": clean_username,
            },
            status_code=400,
        )

    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": "",
            "register_error": "",
            "register_success": "Account created. Now sign in.",
            "active_tab": "login",
            "prefill_username": clean_username,
            "prefill_register_username": "",
        },
        status_code=200,
    )


@router.post("/logout")
async def logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie(key="nova_username")
    return response
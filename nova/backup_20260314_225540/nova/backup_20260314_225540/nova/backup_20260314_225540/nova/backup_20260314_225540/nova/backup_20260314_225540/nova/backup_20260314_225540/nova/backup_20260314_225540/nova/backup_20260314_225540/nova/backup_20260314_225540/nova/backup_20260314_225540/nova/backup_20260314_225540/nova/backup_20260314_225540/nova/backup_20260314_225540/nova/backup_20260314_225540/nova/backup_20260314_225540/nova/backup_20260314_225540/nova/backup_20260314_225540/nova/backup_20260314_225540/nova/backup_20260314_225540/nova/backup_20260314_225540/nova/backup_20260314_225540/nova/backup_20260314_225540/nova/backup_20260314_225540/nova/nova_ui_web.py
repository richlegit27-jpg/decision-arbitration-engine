# C:\Users\Owner\nova\nova_ui_web.py

import json
import asyncio
from pathlib import Path
from typing import AsyncGenerator

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.responses import JSONResponse
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


BASE_DIR = Path(__file__).resolve().parent

STATIC_DIR = BASE_DIR / "static"
TEMPLATE_DIR = BASE_DIR / "templates"

OLLAMA_URL = "http://127.0.0.1:11434"


app = FastAPI(title="Nova UI")


app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static"
)


templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


# ----------------------------------------------------
# ROUTES
# ----------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request
        }
    )


@app.get("/app", response_class=HTMLResponse)
async def app_page(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request
        }
    )


# ----------------------------------------------------
# MODELS API
# ----------------------------------------------------

@app.get("/api/models")
async def list_models():

    try:

        async with httpx.AsyncClient(timeout=10) as client:

            r = await client.get(
                f"{OLLAMA_URL}/api/tags"
            )

            data = r.json()

            models = [
                m["name"]
                for m in data.get("models", [])
            ]

            return {
                "ok": True,
                "models": models
            }

    except Exception:

        return {
            "ok": True,
            "models": [
                "llama3.1:8b"
            ]
        }


# ----------------------------------------------------
# CHAT STREAM
# ----------------------------------------------------

@app.post("/api/chat_stream")
async def chat_stream(request: Request):

    body = await request.json()

    text = body.get("text", "")
    model = body.get("model", "llama3.1:8b")

    async def stream() -> AsyncGenerator[str, None]:

        try:

            yield "event: meta\ndata: " + json.dumps({
                "cmd": "ollama",
                "model": model
            }) + "\n\n"

            async with httpx.AsyncClient(timeout=None) as client:

                async with client.stream(
                    "POST",
                    f"{OLLAMA_URL}/api/generate",
                    json={
                        "model": model,
                        "prompt": text,
                        "stream": True
                    }
                ) as r:

                    async for line in r.aiter_lines():

                        if not line:
                            continue

                        try:
                            obj = json.loads(line)
                        except Exception:
                            continue

                        token = obj.get("response", "")

                        if token:

                            yield "event: token\ndata: " + json.dumps({
                                "t": token
                            }) + "\n\n"

                        if obj.get("done"):

                            yield "event: done\ndata: {}\n\n"
                            break

        except asyncio.CancelledError:
            raise

        except Exception as e:

            yield "event: error\ndata: " + json.dumps({
                "error": str(e)
            }) + "\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream"
    )


# ----------------------------------------------------
# HEALTH CHECK
# ----------------------------------------------------

@app.get("/health")
async def health():

    return {
        "ok": True,
        "app": "nova",
        "status": "healthy"
    }
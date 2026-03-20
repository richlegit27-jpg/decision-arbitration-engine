from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

router = APIRouter()

_executor = ThreadPoolExecutor(max_workers=2)


class ImageRequest(BaseModel):
    prompt: str


def _generate_image_sync(prompt: str) -> dict:
    if OpenAI is None:
        raise RuntimeError("OpenAI library not available.")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set.")

    client = OpenAI(api_key=api_key, timeout=90.0)

    result = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1024"
    )

    image_base64 = ""

    try:
        image_base64 = getattr(result.data[0], "b64_json", "") or ""
    except Exception:
        image_base64 = ""

    if not image_base64 and isinstance(result, dict):
        image_base64 = (
            result.get("image_base64")
            or result.get("b64_json")
            or ((result.get("data") or [{}])[0].get("b64_json"))
            or ""
        )

    image_base64 = str(image_base64 or "").strip()

    if not image_base64:
        raise RuntimeError("No image data returned from OpenAI.")

    return {
        "type": "image",
        "prompt": prompt,
        "image_base64": image_base64
    }


@router.post("/api/images/generate")
async def generate_image(payload: ImageRequest):
    prompt = (payload.prompt or "").strip()

    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt required.")

    try:
        future = _executor.submit(_generate_image_sync, prompt)
        result = future.result(timeout=120)
        return result
    except FuturesTimeoutError:
        raise HTTPException(status_code=504, detail="Image generation timed out.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
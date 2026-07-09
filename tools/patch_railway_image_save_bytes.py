from pathlib import Path

path = Path("nova_backend/services/chat_service.py")
text = path.read_text(encoding="utf-8")

old = '''        if remote_image_url:
            image_url = remote_image_url
        else:
            if not image_b64:
                raise ValueError("Image API returned no image data")

            image_bytes = base64.b64decode(image_b64)
            filename = f"generated_{uuid.uuid4().hex}.png"
            filepath = self.uploads_dir / filename

            with open(filepath, "wb") as f:
                f.write(image_bytes)

            image_url = f"/api/uploads/{filename}"
'''

new = '''        # NOVA_RAILWAY_IMAGE_SAVE_BYTES_20260702
        # Always turn OpenAI image output into a real local uploads file before returning /api/uploads/...
        # Railway was receiving valid image metadata but no verified PNG existed at /app/uploads.
        from pathlib import Path as _NovaImagePath
        import urllib.request as _nova_urllib_request

        image_bytes = b""

        if image_b64:
            image_bytes = base64.b64decode(image_b64)
        elif remote_image_url:
            request = _nova_urllib_request.Request(
                remote_image_url,
                headers={"User-Agent": "Nova/1.0"},
            )
            with _nova_urllib_request.urlopen(request, timeout=45) as response:
                image_bytes = response.read()
        else:
            raise ValueError("Image API returned no image data")

        if not image_bytes:
            raise ValueError("Image API returned empty image bytes")

        filename = f"generated_{uuid.uuid4().hex}.png"
        uploads_dir = _NovaImagePath(self.uploads_dir)
        uploads_dir.mkdir(parents=True, exist_ok=True)
        filepath = uploads_dir / filename

        with open(filepath, "wb") as f:
            f.write(image_bytes)

        if not filepath.exists() or filepath.stat().st_size <= 0:
            raise ValueError(f"Generated image file was not saved: {filepath}")

        print(
            "[NOVA_RAILWAY_IMAGE_SAVE_BYTES_20260702] saved",
            str(filepath),
            filepath.stat().st_size,
        )

        image_url = f"/api/uploads/{filename}"
'''

if old not in text:
    raise SystemExit("target block not found")

text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
print("patched railway image save bytes")

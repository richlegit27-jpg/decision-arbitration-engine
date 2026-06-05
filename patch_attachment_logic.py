# --- PATCH: TARGETED ATTACHMENT LOGIC UPDATE ---
# Run this patch once; it will overwrite only the attachment handling blocks.

from pathlib import Path
import shutil
import logging

UPLOADS_DIR = Path(__file__).resolve().parent / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# --- HELPERS ---
def save_attachment(file_info: dict) -> Path:
    filename = str(file_info.get("filename") or "unnamed_attachment")
    local_path = file_info.get("local_path")
    content = file_info.get("content")
    save_path = UPLOADS_DIR / filename
    try:
        if content:
            save_path.write_text(content, encoding="utf-8")
        elif local_path and Path(local_path).exists():
            shutil.copy(local_path, save_path)
        else:
            logging.warning(f"[Attachment] no content or invalid local_path for {filename}")
    except Exception as e:
        logging.warning(f"[Attachment] failed to save {filename}: {e}")
        return None
    return save_path

def read_attachment(filename: str) -> str:
    path = UPLOADS_DIR / filename
    if not path.exists():
        logging.warning(f"[Attachment] file does not exist: {filename}")
        return "[Attachment file not found]"
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        logging.info(f"[Attachment] binary or unreadable: {filename}")
        return "[Attachment binary or unreadable]"

def analyze_binary_attachment(attachment_path, mime_type):
    path_obj = Path(attachment_path)
    if not path_obj.exists():
        return ""
    try:
        if mime_type.lower() == "application/pdf" or path_obj.suffix.lower() == ".pdf":
            import fitz
            doc = fitz.open(str(path_obj))
            pieces = []
            for i in range(min(len(doc), 5)):
                page_text = doc[i].get_text("text") or ""
                page_text = page_text.strip()
                if page_text:
                    pieces.append(f"[PDF page {i+1}]\n{page_text[:2000]}")
            doc.close()
            return "\n\n".join(pieces) if pieces else "[PDF received, no selectable text]"
        if mime_type.startswith("image/") or path_obj.suffix.lower() in {".jpg",".jpeg",".png",".bmp",".webp"}:
            from PIL import Image
            import pytesseract
            img = Image.open(str(path_obj))
            ocr_text = pytesseract.image_to_string(img) or ""
            return f"[Image OCR text]\n{ocr_text[:3000]}" if ocr_text else "[Image received, no readable OCR]"
    except Exception as e:
        return f"[Attachment analysis failed: {e}]"
    return ""

# --- PATCH TARGET ---
# Replace the content_snippet block inside your attachment injection loop with this:
# for attachment in remembered_session_attachments:
#     ...
#     old:
#         content_snippet = file_path.read_text(encoding="utf-8")[:4000]
#     new:
def patch_content_snippet(file_path, attachment):
    content_snippet = ""
    try:
        if file_path.exists() and file_path.is_file() and str(file_path).startswith(str(UPLOADS_DIR.resolve())):
            is_binary = str(attachment.get("mime_type","")).lower().startswith(("image/","audio/","video/")) \
                        or file_path.suffix.lower() in (".jpg",".jpeg",".png",".gif",".bmp",".webp",".pdf",".zip")
            if is_binary:
                content_snippet = analyze_binary_attachment(file_path,str(attachment.get("mime_type","")))[:4000]
            else:
                content_snippet = read_attachment(file_path.name)[:4000]
        else:
            content_snippet = "[Attachment file not found]"
    except Exception as e:
        content_snippet = f"[Attachment read failed: {e}]"
    return content_snippet
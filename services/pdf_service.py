# notepad C:\Users\Owner\nova\services\pdf_service.py

from __future__ import annotations
from pathlib import Path
from typing import Dict

def analyze_pdf_attachment(file_path: str) -> Dict:
    """
    Dummy PDF analysis (no external packages required).
    Returns placeholder content.
    """
    path = Path(file_path)
    if not path.exists() or path.suffix.lower() != ".pdf":
        return {"error": "File not found or not a PDF"}

    return {
        "filename": path.name,
        "pages": 1,
        "content": "Sample PDF content (dummy)",
    }


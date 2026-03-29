# notepad C:\Users\Owner\nova\services\document_service.py
from __future__ import annotations
import uuid
from typing import Dict, List

DOCUMENTS: Dict[str, Dict] = {}

def _new_id() -> str:
    return str(uuid.uuid4())

def list_documents() -> List[Dict]:
    return list(DOCUMENTS.values())

def save_document(title: str, content: str) -> Dict:
    doc_id = _new_id()
    doc = {"id": doc_id, "title": title, "content": content}
    DOCUMENTS[doc_id] = doc
    return doc

def delete_document(doc_id: str) -> bool:
    if doc_id in DOCUMENTS:
        del DOCUMENTS[doc_id]
        return True
    return False
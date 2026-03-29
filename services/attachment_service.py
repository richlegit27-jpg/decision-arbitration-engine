import os, uuid
from pathlib import Path
from typing import Any, Dict
import mimetypes

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {".png",".jpg",".jpeg",".gif",".bmp",".webp",".mp4",".mov",".avi"}

class AttachmentService:
    def __init__(self): self.upload_dir = UPLOAD_DIR

    def allowed_file(self, filename:str)->bool:
        return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS

    def save_file(self, file)->Dict[str,Any]:
        if not self.allowed_file(file.filename): return {"ok":False,"error":"File type not allowed."}
        filename = f"{uuid.uuid4().hex}_{file.filename}"
        filepath = self.upload_dir / filename
        file.save(filepath)
        return {"ok":True,"id":filename,"filename":file.filename,"path":str(filepath),"type":file.mimetype}

    def get_file_info(self, file_id:str)->Dict[str,Any]:
        filepath = self.upload_dir / file_id
        if not filepath.exists(): return None
        return {"id":file_id,"filename":file_id.split('_',1)[-1],"path":str(filepath),"type":self._guess_mimetype(filepath)}

    def _guess_mimetype(self, filepath:Path)->str:
        mimetype,_ = mimetypes.guess_type(str(filepath))
        return mimetype or "application/octet-stream"
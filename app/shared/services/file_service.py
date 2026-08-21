import os
import uuid
from pathlib import Path
from fastapi import UploadFile, HTTPException
from app.core.config import settings, get_upload_dir

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".jpg", ".jpeg", ".png"}


async def save_upload(file: UploadFile, user_id: str) -> tuple[str, str, int]:
    """
    Save uploaded file to disk.
    Returns (stored_path, original_filename, size_bytes)
    """
    ext = Path(file.filename or "resume").suffix.lower()
    # Allow any file type to be uploaded


    # Use absolute path to ensure file is saved correctly
    base_dir = get_upload_dir()
    if not base_dir.is_absolute():
        # Make it relative to the backend directory
        base_dir = get_upload_dir()
    
    upload_dir = base_dir / "resumes" / user_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"{uuid.uuid4().hex}{ext}"
    file_path = upload_dir / safe_name

    content = await file.read()
    size_bytes = len(content)

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if size_bytes > max_bytes:
        raise HTTPException(status_code=413, detail=f"File too large. Max {settings.MAX_UPLOAD_MB}MB allowed.")

    with open(file_path, "wb") as f:
        f.write(content)

    return str(file_path), file.filename or safe_name, size_bytes

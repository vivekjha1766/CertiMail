from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from backend.app.core.config import EXTRACT_DIR
from backend.app.services.zip_service import ZipService

router = APIRouter(prefix="/api/certificates", tags=["Certificates"])

@router.get("/thumbnail/{batch_id}/{filename:path}")
async def get_certificate_thumbnail(batch_id: str, filename: str):
    base_dir = EXTRACT_DIR / batch_id
    target_path = (base_dir / filename).resolve()
    
    if not ZipService.is_safe_path(base_dir, target_path) or not target_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate image not found.")

    thumb_path = ZipService.get_or_create_thumbnail(target_path)
    return FileResponse(thumb_path, media_type="image/png")

@router.get("/full/{batch_id}/{filename:path}")
async def get_certificate_full(batch_id: str, filename: str):
    base_dir = EXTRACT_DIR / batch_id
    target_path = (base_dir / filename).resolve()
    
    if not ZipService.is_safe_path(base_dir, target_path) or not target_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate image not found.")

    return FileResponse(target_path, media_type="image/png")

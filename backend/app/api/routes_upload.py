import os
import uuid
import json
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, status
from backend.app.core.config import UPLOAD_DIR, settings
from backend.app.core.database import get_db_connection
from backend.app.services.excel_service import ExcelService
from backend.app.services.zip_service import ZipService
from backend.app.schemas.excel import ExcelUploadResponse, SheetInfo
from backend.app.schemas.mapping import ZipBatchInfo
from backend.app.api.session_store import SessionStore

router = APIRouter(prefix="/api/uploads", tags=["Uploads"])

@router.post("/excel", response_model=ExcelUploadResponse)
async def upload_excel(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    sheet_name: Optional[str] = Form(None)
):
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Please upload a valid Excel workbook (.xlsx or .xls)."
        )

    current_session_id = session_id or str(uuid.uuid4())
    session = SessionStore.get_session(current_session_id)

    safe_filename = Path(file.filename).name
    save_path = UPLOAD_DIR / f"{current_session_id}_{safe_filename}"

    contents = await file.read()
    if len(contents) > settings.MAX_EXCEL_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Excel file exceeds maximum allowed size ({settings.MAX_EXCEL_BYTES // (1024 * 1024)}MB)."
        )

    with open(save_path, "wb") as f:
        f.write(contents)

    try:
        sheets = ExcelService.get_sheet_names(save_path)
        selected_sheet = sheet_name if sheet_name in sheets else sheets[0]
        columns, row_count, sample_rows = ExcelService.read_sheet(save_path, selected_sheet)
        suggestions = ExcelService.suggest_mappings(columns)

        session["excel_path"] = save_path
        session["sheets"] = sheets
        session["selected_sheet"] = selected_sheet
        session["detected_columns"] = columns

        # Update or record in database
        conn = get_db_connection()
        try:
            conn.execute("""
            INSERT OR REPLACE INTO upload_sessions (
                id, excel_filename, excel_path, sheet_names_json, selected_sheet,
                detected_columns_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                current_session_id,
                safe_filename,
                str(save_path),
                json.dumps(sheets),
                selected_sheet,
                json.dumps(columns)
            ))
            conn.commit()
        finally:
            conn.close()

        return ExcelUploadResponse(
            session_id=current_session_id,
            filename=safe_filename,
            sheets=sheets,
            selected_sheet=selected_sheet,
            detected_columns=columns,
            row_count=row_count,
            column_suggestions=suggestions,
            sample_rows=sample_rows
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse Excel workbook: {str(e)}"
        )


@router.post("/certificates", response_model=ZipBatchInfo)
async def upload_certificates_zip(
    session_id: str = Form(...),
    position: int = Form(...), # 1 to 6
    file: UploadFile = File(...)
):
    if position < 1 or position > 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Position must be between 1 and 6.")

    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please upload a valid ZIP archive (.zip).")

    session = SessionStore.get_session(session_id)
    safe_filename = Path(file.filename).name
    batch_id = f"{session_id}_pos_{position}"
    zip_path = UPLOAD_DIR / f"{batch_id}_{safe_filename}"

    contents = await file.read()
    if len(contents) > settings.MAX_ZIP_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ZIP archive exceeds maximum size ({settings.MAX_ZIP_BYTES // (1024 * 1024)}MB)."
        )

    with open(zip_path, "wb") as f:
        f.write(contents)

    try:
        batch_info, number_to_path = ZipService.extract_and_inspect_zip(zip_path, batch_id, position)
        
        # Store in session
        session["batches_dict"][position] = number_to_path
        
        # Update batch_infos in session
        session["batch_infos"] = [b for b in session.get("batch_infos", []) if b.position != position]
        session["batch_infos"].append(batch_info)
        session["batch_infos"].sort(key=lambda b: b.position)

        return batch_info
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract and process ZIP file: {str(e)}"
        )


@router.get("/batches/{session_id}", response_model=List[ZipBatchInfo])
async def get_uploaded_batches(session_id: str):
    session = SessionStore.get_session(session_id)
    return session.get("batch_infos", [])

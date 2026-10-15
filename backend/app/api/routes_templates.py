import uuid
from typing import List
from fastapi import APIRouter, HTTPException, status
from backend.app.core.database import get_db_connection
from backend.app.schemas.template import (
    TemplateCreate,
    TemplateUpdate,
    TemplateResponse,
    RenderPreviewRequest,
    RenderPreviewResponse
)
from backend.app.services.email_service import EmailService

router = APIRouter(prefix="/api/templates", tags=["Templates"])

@router.get("", response_model=List[TemplateResponse])
async def list_templates():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM templates ORDER BY is_default DESC, created_at DESC")
        rows = cursor.fetchall()
        return [
            TemplateResponse(
                id=r["id"],
                name=r["name"],
                subject=r["subject"],
                body=r["body"],
                is_default=bool(r["is_default"]),
                created_at=str(r["created_at"])
            )
            for r in rows
        ]
    finally:
        conn.close()

@router.post("", response_model=TemplateResponse)
async def create_template(template: TemplateCreate):
    conn = get_db_connection()
    try:
        new_id = str(uuid.uuid4())
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO templates (id, name, subject, body, is_default, created_at)
        VALUES (?, ?, ?, ?, 0, CURRENT_TIMESTAMP)
        """, (new_id, template.name, template.subject, template.body))
        conn.commit()

        cursor.execute("SELECT * FROM templates WHERE id = ?", (new_id,))
        r = cursor.fetchone()
        return TemplateResponse(
            id=r["id"],
            name=r["name"],
            subject=r["subject"],
            body=r["body"],
            is_default=bool(r["is_default"]),
            created_at=str(r["created_at"])
        )
    finally:
        conn.close()

@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(template_id: str, template: TemplateUpdate):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE templates
        SET name = ?, subject = ?, body = ?
        WHERE id = ?
        """, (template.name, template.subject, template.body, template_id))
        conn.commit()

        cursor.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
        r = cursor.fetchone()
        if not r:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found.")
        return TemplateResponse(
            id=r["id"],
            name=r["name"],
            subject=r["subject"],
            body=r["body"],
            is_default=bool(r["is_default"]),
            created_at=str(r["created_at"])
        )
    finally:
        conn.close()

@router.delete("/{template_id}")
async def delete_template(template_id: str):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT is_default FROM templates WHERE id = ?", (template_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found.")
        if row["is_default"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete default template.")

        cursor.execute("DELETE FROM templates WHERE id = ?", (template_id,))
        conn.commit()
        return {"message": "Template deleted successfully."}
    finally:
        conn.close()

@router.post("/preview", response_model=RenderPreviewResponse)
async def preview_rendered_template(request: RenderPreviewRequest):
    rendered_subject = EmailService.render_template(request.subject, request.team_data)
    rendered_body = EmailService.render_template(request.body, request.team_data)

    detected_subject = EmailService.validate_placeholders(request.subject)
    detected_body = EmailService.validate_placeholders(request.body)
    all_placeholders = list(dict.fromkeys(detected_subject + detected_body))

    missing = [p for p in all_placeholders if p not in request.team_data or not request.team_data[p]]

    return RenderPreviewResponse(
        rendered_subject=rendered_subject,
        rendered_body=rendered_body,
        detected_placeholders=all_placeholders,
        missing_placeholders=missing,
        is_valid=len(missing) == 0
    )

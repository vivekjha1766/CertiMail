from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class TemplateBase(BaseModel):
    name: str
    subject: str
    body: str

class TemplateCreate(TemplateBase):
    pass

class TemplateUpdate(TemplateBase):
    pass

class TemplateResponse(TemplateBase):
    id: str
    is_default: bool = False
    created_at: str

class RenderPreviewRequest(BaseModel):
    subject: str
    body: str
    team_data: Dict[str, Any]

class RenderPreviewResponse(BaseModel):
    rendered_subject: str
    rendered_body: str
    detected_placeholders: List[str]
    missing_placeholders: List[str]
    is_valid: bool

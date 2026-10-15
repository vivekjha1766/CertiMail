from pydantic import BaseModel, Field
from typing import List, Optional

class DeliveryLogItem(BaseModel):
    id: str
    campaign_id: str
    team_id: Optional[str] = None
    team_name: Optional[str] = None
    recipient_email: str
    cc_recipients: Optional[str] = ""
    bcc_count: int = 0
    attachment_count: int = 0
    attachment_names: List[str] = []
    status: str
    error_message: Optional[str] = ""
    retry_count: int = 0
    is_test: bool = False
    created_at: str

class DeliveryLogListResponse(BaseModel):
    total: int
    items: List[DeliveryLogItem]

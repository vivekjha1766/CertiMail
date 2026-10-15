from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class CampaignCreate(BaseModel):
    name: str = "Hack-O-Sprint 4.0 Certificate Distribution"
    session_id: str
    subject: str
    body: str
    global_cc: Optional[str] = ""
    global_bcc: Optional[str] = ""
    delay_seconds: float = 2.0
    campaign_type: str = "certificate_distribution" # certificate_distribution or general_mailing
    proceed_with_current_mapping: bool = False
    mismatch_ack_reviewer: Optional[str] = None
    mismatch_ack_reason: Optional[str] = None
    mismatch_ack_confirmed: bool = False

class CampaignResponse(BaseModel):
    id: str
    name: str
    status: str
    campaign_type: str = "certificate_distribution"
    total_teams: int
    sent_count: int
    failed_count: int
    pending_count: int
    uncertain_count: int = 0
    total_certificates: int
    estimated_size_mb: float
    current_template_revision: int = 1
    is_paused: bool = False
    created_at: str

class CampaignStatusResponse(BaseModel):
    campaign_id: str
    status: str # draft, prepared, sending, paused, interrupted, completed, failed, cancelled
    campaign_type: str = "certificate_distribution"
    total_teams: int
    sent_count: int
    failed_count: int
    pending_count: int
    uncertain_count: int = 0
    progress_percent: float
    current_team: Optional[str] = None
    current_template_revision: int = 1
    is_paused: bool = False
    is_completed: bool = False
    error_message: Optional[str] = None

class TestSendRequest(BaseModel):
    session_id: str
    team_id: str
    test_recipient_email: str
    subject: str
    body: str
    test_cc: Optional[str] = ""
    test_bcc: Optional[str] = ""
    include_attachments: bool = True
    smtp_password: Optional[str] = None

class TestSendResponse(BaseModel):
    success: bool
    message: str
    actual_recipient: str
    real_leader_email_protected: str
    attachment_count: int
    attachment_names: List[str]

class SendCampaignRequest(BaseModel):
    delay_seconds: float = 2.0
    max_retries: int = 2
    smtp_password: Optional[str] = None

class TemplateRevisionResponse(BaseModel):
    id: str
    campaign_id: str
    revision_number: int
    subject: str
    body: str
    global_cc: str = ""
    global_bcc: str = ""
    created_by: str = "Admin"
    change_summary: str = ""
    is_active: bool = True
    created_at: str

class UpdateCampaignTemplateRequest(BaseModel):
    choice: str = "OPTION_B_APPLY_TO_REMAINING" # OPTION_A_KEEP_ORIGINAL or OPTION_B_APPLY_TO_REMAINING
    subject: str
    body: str
    global_cc: Optional[str] = ""
    global_bcc: Optional[str] = ""
    reviewer: Optional[str] = "Admin"
    reason: Optional[str] = ""

class ResolveUncertainRequest(BaseModel):
    recipient_id: str
    action: str # authorize_retry, mark_accepted, mark_skipped
    reviewer: Optional[str] = "Admin"
    reason: Optional[str] = ""

class RetryFailedRequest(BaseModel):
    reviewer: Optional[str] = "Admin"
    reason: Optional[str] = ""

class CampaignRecipientItem(BaseModel):
    id: str
    recipient_id: str
    row_index: int
    team_name: str
    team_identifier: Optional[str] = None
    leader_name: str
    leader_email: str
    normalized_email: str
    delivery_status: str # PENDING, IN_PROGRESS, SMTP_ACCEPTED, FAILED, DELIVERY_UNKNOWN, SKIPPED
    delivery_attempts: int = 0
    last_error: Optional[str] = ""
    template_revision_used: int = 1
    delivery_timestamp: Optional[str] = None
    retry_authorized: bool = False
    certificate_count: int = 0
    certificate_names: List[str] = []

class CampaignDetailResponse(BaseModel):
    campaign: CampaignResponse
    revisions: List[TemplateRevisionResponse]
    recipients: List[CampaignRecipientItem]
    audit_logs: List[Dict[str, Any]]
    summary_counts: Dict[str, int]

class CampaignRecoveryItem(BaseModel):
    id: str
    name: str
    campaign_type: str
    status: str
    total_recipients: int
    accepted_count: int
    pending_count: int
    failed_count: int
    uncertain_count: int
    remaining_count: int
    current_template_revision: int
    last_activity: str
    is_resumable: bool


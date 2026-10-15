from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from backend.app.schemas.excel import ColumnMapping

class CertificateFileInfo(BaseModel):
    position: int
    filename: str
    relative_path: str
    batch_name: str
    exists: bool = False
    size_bytes: int = 0
    participant_name: Optional[str] = ""
    ref_number: Optional[str] = ""

class ZipBatchInfo(BaseModel):
    position: int # 1 to 6
    batch_id: str
    filename: str
    file_count: int
    min_number: Optional[int] = None
    max_number: Optional[int] = None
    has_nested: bool = False
    warnings: List[str] = []

class TeamMappingItem(BaseModel):
    team_id: str
    row_index: int
    team_name: str
    team_identifier: Optional[str] = None
    leader_name: str
    leader_email: str
    participant_names: List[str]
    ref_numbers: List[str]
    certificate_files: List[CertificateFileInfo]
    validation_status: str # VALID, MISSING CERTIFICATE, REFERENCE_MISMATCH, OVERRIDE_APPROVED, OVERRIDE_REJECTED, OVERRIDE_REVOKED, DUPLICATE EMAIL, INVALID EMAIL, MANUAL REVIEW REQUIRED
    validation_errors: List[str] = []
    manual_override: bool = False
    override_status: Optional[str] = None
    override_reviewer: Optional[str] = None
    override_reason: Optional[str] = None
    override_timestamp: Optional[str] = None
    detected_reference_mismatch: Optional[str] = None
    custom_subject: Optional[str] = None
    custom_body: Optional[str] = None
    cc_recipients: Optional[str] = ""
    bcc_recipients: Optional[str] = ""

class ValidateMappingRequest(BaseModel):
    session_id: str
    column_mapping: ColumnMapping
    numbering_offset: int = 0
    selected_sheet: Optional[str] = None

class MismatchAcknowledgement(BaseModel):
    policy: str = "PROCEED_WITH_CURRENT_MAPPING"
    reviewer: str
    reason: str
    acknowledged_at: str
    mismatches_count: int
    unresolved_summary: List[Dict[str, Any]] = []

class ValidationSummary(BaseModel):
    total_teams: int
    valid_teams: int
    error_teams: int
    duplicate_emails: int
    missing_certificates: int
    reference_mismatches: int
    approved_overrides: int = 0
    total_certificates_detected: int
    can_send: bool
    has_fatal_errors: bool = False
    fatal_error_count: int = 0
    can_proceed_with_current_mapping: bool = False
    mismatch_acknowledgement: Optional[MismatchAcknowledgement] = None

class ValidationReportResponse(BaseModel):
    summary: ValidationSummary
    teams: List[TeamMappingItem]
    batches: List[ZipBatchInfo]

class ManualOverrideRequest(BaseModel):
    session_id: str
    team_id: str
    team_identifier: Optional[str] = None
    row_index: Optional[int] = None
    certificate_filenames: Optional[List[str]] = None
    leader_email: Optional[str] = None
    leader_name: Optional[str] = None
    cc_recipients: Optional[str] = None
    bcc_recipients: Optional[str] = None
    status: Optional[str] = "OVERRIDE_APPROVED" # OVERRIDE_APPROVED, OVERRIDE_REJECTED, OVERRIDE_REVOKED
    reviewer: Optional[str] = "Admin Reviewer"
    reason: Optional[str] = "Approved by administrator"
    approve_override: bool = True

class AcknowledgeMismatchesRequest(BaseModel):
    session_id: str
    reviewer: str = Field(..., min_length=1, description="Reviewer name or administrator identity")
    reason: str = Field(..., min_length=1, description="Audit reason for proceeding with current mapping despite mismatches")
    confirmed: bool = Field(True, description="Explicit confirmation to proceed with current mapping")

class ResetMismatchesRequest(BaseModel):
    session_id: str


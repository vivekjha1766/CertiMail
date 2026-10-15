from pathlib import Path
from typing import Dict, List, Optional, Any
from backend.app.schemas.mapping import ZipBatchInfo
from backend.app.core.config import settings

class SessionStore:
    # session_id -> {
    #   "excel_path": Path,
    #   "selected_sheet": str,
    #   "sheets": List[str],
    #   "detected_columns": List[str],
    #   "column_mapping": ColumnMapping,
    #   "batches_dict": Dict[int, Dict[int, Path]], # position (1..6) -> {num: Path}
    #   "batch_infos": List[ZipBatchInfo],
    #   "teams_data": List[Dict[str, Any]],
    #   "overrides": Dict[str, Dict[str, Any]],
    #   "latest_report": ValidationReportResponse
    # }
    sessions: Dict[str, Dict[str, Any]] = {}
    
    # Active in-memory SMTP credentials for the current backend instance
    smtp_memory_config: Dict[str, Any] = {
        "host": settings.SMTP_HOST or "smtp.gmail.com",
        "port": settings.SMTP_PORT or 587,
        "use_tls": settings.SMTP_USE_TLS if settings.SMTP_USE_TLS is not None else True,
        "use_ssl": settings.SMTP_USE_SSL or False,
        "sender_name": settings.SMTP_SENDER_NAME or "Hack-O-Sprint 4.0 Organizing Team",
        "sender_email": settings.SMTP_SENDER_EMAIL or "",
        "username": settings.SMTP_USERNAME or "",
        "password": settings.SMTP_PASSWORD or "",
        "global_cc": settings.GLOBAL_CC or "",
        "global_bcc": settings.GLOBAL_BCC or "",
    }

    @classmethod
    def get_session(cls, session_id: str) -> Dict[str, Any]:
        if session_id not in cls.sessions:
            cls.sessions[session_id] = {
                "excel_path": None,
                "selected_sheet": None,
                "sheets": [],
                "detected_columns": [],
                "column_mapping": None,
                "batches_dict": {},
                "batch_infos": [],
                "teams_data": [],
                "overrides": {},
                "mismatch_acknowledgement": None,
                "latest_report": None
            }
        return cls.sessions[session_id]

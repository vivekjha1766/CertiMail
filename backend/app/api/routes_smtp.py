from fastapi import APIRouter, HTTPException, status
from backend.app.schemas.smtp import (
    SMTPConfigPublic,
    SMTPConfigUpdate,
    SMTPTestRequest,
    SMTPTestResponse
)
from backend.app.services.smtp_service import SMTPService
from backend.app.api.session_store import SessionStore

router = APIRouter(prefix="/api/smtp", tags=["SMTP Settings"])

@router.get("/config", response_model=SMTPConfigPublic)
async def get_smtp_config():
    cfg = SessionStore.smtp_memory_config
    return SMTPConfigPublic(
        host=cfg.get("host", "smtp.gmail.com"),
        port=cfg.get("port", 587),
        use_tls=cfg.get("use_tls", True),
        use_ssl=cfg.get("use_ssl", False),
        sender_name=cfg.get("sender_name", "Hack-O-Sprint 4.0 Organizing Team"),
        sender_email=cfg.get("sender_email", ""),
        username=cfg.get("username", ""),
        has_password=bool(cfg.get("password")),
        global_cc=cfg.get("global_cc", ""),
        global_bcc=cfg.get("global_bcc", "")
    )

@router.post("/config", response_model=SMTPConfigPublic)
async def update_smtp_config(update: SMTPConfigUpdate):
    cfg = SessionStore.smtp_memory_config
    cfg["host"] = update.host
    cfg["port"] = update.port
    cfg["use_tls"] = update.use_tls
    cfg["use_ssl"] = update.use_ssl
    cfg["sender_name"] = update.sender_name
    cfg["sender_email"] = update.sender_email
    cfg["username"] = update.username
    if update.password:
        cfg["password"] = update.password
    if update.global_cc is not None:
        cfg["global_cc"] = update.global_cc
    if update.global_bcc is not None:
        cfg["global_bcc"] = update.global_bcc

    return SMTPConfigPublic(
        host=cfg["host"],
        port=cfg["port"],
        use_tls=cfg["use_tls"],
        use_ssl=cfg["use_ssl"],
        sender_name=cfg["sender_name"],
        sender_email=cfg["sender_email"],
        username=cfg["username"],
        has_password=bool(cfg.get("password")),
        global_cc=cfg["global_cc"],
        global_bcc=cfg["global_bcc"]
    )

@router.post("/test", response_model=SMTPTestResponse)
async def test_smtp_connection(req: SMTPTestRequest):
    # If password is not provided in request, use session password if available
    password = req.password or SessionStore.smtp_memory_config.get("password", "")
    if not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is required to test SMTP connection."
        )

    success, message, details = SMTPService.test_connection(
        host=req.host,
        port=req.port,
        use_tls=req.use_tls,
        use_ssl=req.use_ssl,
        username=req.username,
        password=password
    )

    return SMTPTestResponse(
        success=success,
        message=message,
        error_details=details
    )

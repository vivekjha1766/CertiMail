import asyncio
import json
import uuid
import smtplib
import ssl
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, status
from backend.app.core.database import (
    get_db_connection,
    log_campaign_audit,
    get_campaign_audit_logs,
    create_template_revision,
    get_template_revisions,
    get_active_template_revision
)
from backend.app.schemas.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignStatusResponse,
    TestSendRequest,
    TestSendResponse,
    SendCampaignRequest,
    TemplateRevisionResponse,
    UpdateCampaignTemplateRequest,
    ResolveUncertainRequest,
    RetryFailedRequest,
    CampaignRecipientItem,
    CampaignDetailResponse,
    CampaignRecoveryItem
)
from backend.app.services.email_service import EmailService
from backend.app.services.smtp_service import SMTPService, CampaignRunner, campaign_tasks
from backend.app.api.session_store import SessionStore

router = APIRouter(prefix="/api/campaigns", tags=["Campaigns"])

@router.post("", response_model=CampaignResponse)
async def create_campaign(req: CampaignCreate):
    session = SessionStore.get_session(req.session_id)
    camp_type = req.campaign_type or "certificate_distribution"

    # Process and validate Option A election parameters if provided in request
    if req.proceed_with_current_mapping:
        reviewer = (req.mismatch_ack_reviewer or "").strip()
        reason = (req.mismatch_ack_reason or "").strip()
        if not reviewer or not reason or not req.mismatch_ack_confirmed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incomplete authorization: Reviewer name, reason, and explicit confirmation are required to proceed with current mapping."
            )
        from datetime import datetime
        session["mismatch_acknowledgement"] = {
            "policy": "PROCEED_WITH_CURRENT_MAPPING",
            "reviewer": reviewer,
            "reason": reason,
            "confirmed": True,
            "acknowledged_at": datetime.now().isoformat()
        }

    # Re-evaluate authoritative validation state against database overrides and session acknowledgement
    from backend.app.services.matching_engine import MatchingEngine
    if session.get("teams_data"):
        report = MatchingEngine.match_teams(
            teams_data=session["teams_data"],
            batches_dict=session.get("batches_dict", {}),
            batch_infos=session.get("batch_infos", []),
            numbering_offset=session.get("numbering_offset", 0),
            existing_overrides=session.get("overrides", {}),
            mismatch_acknowledgement=session.get("mismatch_acknowledgement")
        )
        session["latest_report"] = report
    else:
        report = session.get("latest_report")

    if not report:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create campaign: no validated teams found. Please run validation first."
        )

    # For certificate distribution, enforce certificate validation safety
    if camp_type == "certificate_distribution":
        if report.summary.has_fatal_errors:
            fatal_reasons = []
            if report.summary.missing_certificates > 0:
                fatal_reasons.append(f"{report.summary.missing_certificates} missing certificate(s)")
            if report.summary.duplicate_emails > 0:
                fatal_reasons.append(f"{report.summary.duplicate_emails} duplicate email(s)")
            detail_msg = ", ".join(fatal_reasons) or "unresolved fatal errors"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot create campaign: {report.summary.fatal_error_count} fatal error(s) detected ({detail_msg}). Missing certificates and recipient errors cannot be bypassed."
            )

        if not report.summary.can_send:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot create campaign: {report.summary.error_teams} teams have unresolved errors. Please review and resolve or override all errors before sending, or explicitly authorize proceeding with current mapping."
            )

    campaign_id = str(uuid.uuid4())
    conn = get_db_connection()
    try:
        ack_data = session.get("mismatch_acknowledgement")
        mapping_policy = "PROCEED_WITH_CURRENT_MAPPING" if (ack_data and report.summary.reference_mismatches > 0) else "INDIVIDUAL_REVIEW"

        config_data = {
            "session_id": req.session_id,
            "subject": req.subject,
            "body": req.body,
            "global_cc": req.global_cc or "",
            "global_bcc": req.global_bcc or "",
            "delay_seconds": req.delay_seconds,
            "campaign_type": camp_type,
            "mapping_policy": mapping_policy,
            "mismatch_acknowledgement": ack_data,
            "unresolved_reference_mismatches": report.summary.reference_mismatches
        }

        # Snapshot of recipient dataset and mapping for safe session-independent recovery
        snapshot_data = {
            "campaign_id": campaign_id,
            "campaign_type": camp_type,
            "total_recipients": len(report.teams),
            "created_at": "CURRENT_TIMESTAMP",
            "column_mapping": session.get("column_mapping").model_dump() if session.get("column_mapping") and hasattr(session.get("column_mapping"), "model_dump") else session.get("column_mapping"),
            "excel_filename": session.get("excel_path").name if session.get("excel_path") else None
        }

        total_certs = sum(len(t.certificate_files) for t in report.teams) if camp_type == "certificate_distribution" else 0
        total_size_bytes = sum(c.size_bytes for t in report.teams for c in t.certificate_files if c.exists) if camp_type == "certificate_distribution" else 0
        est_size_mb = round(total_size_bytes / (1024 * 1024), 2)

        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO campaigns (
            id, name, status, total_teams, sent_count, failed_count, config_json,
            campaign_type, is_paused, is_cancelled, current_template_revision, snapshot_json,
            created_at, updated_at
        ) VALUES (?, ?, 'prepared', ?, 0, 0, ?, ?, 0, 0, 1, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (
            campaign_id,
            req.name,
            report.summary.total_teams,
            json.dumps(config_data),
            camp_type,
            json.dumps(snapshot_data)
        ))

        # Insert Revision 1 into template_revisions table
        create_template_revision(
            campaign_id=campaign_id,
            subject=req.subject,
            body=req.body,
            global_cc=req.global_cc or "",
            global_bcc=req.global_bcc or "",
            created_by="Admin",
            change_summary="Initial campaign template revision (Revision 1)",
            set_as_active=True,
            conn=conn
        )

        # Insert audit log entry into delivery_logs if Option A was elected
        if ack_data:
            cursor.execute("""
            INSERT INTO delivery_logs (
                id, campaign_id, team_id, team_name, recipient_email, cc_recipients,
                bcc_count, attachment_count, attachment_names_json, status,
                error_message, retry_count, is_test, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                str(uuid.uuid4()),
                campaign_id,
                "AUDIT_POLICY",
                "MAPPING_POLICY_ELECTION",
                f"Authorized by: {ack_data.get('reviewer', 'Unknown')}",
                "",
                0,
                0,
                json.dumps([]),
                "OPTION_A_PROCEED_WITH_CURRENT_MAPPING",
                f"Reviewer: {ack_data.get('reviewer')}; Reason: {ack_data.get('reason')}; Acknowledged Mismatches: {report.summary.reference_mismatches}",
                0,
                1
            ))

        # Insert each recipient into teams ledger table
        for t in report.teams:
            stable_recipient_id = f"{campaign_id}_{t.team_identifier or t.team_id or t.row_index}"
            norm_email = (t.leader_email or "").strip().lower()

            cursor.execute("""
            INSERT INTO teams (
                id, campaign_id, row_index, team_name, team_identifier,
                leader_name, leader_email, participant_names_json, ref_numbers_json,
                certificate_files_json, validation_status, validation_errors_json,
                manual_override, custom_subject, custom_body, cc_recipients, bcc_recipients,
                recipient_id, normalized_email, delivery_status, delivery_attempts,
                last_error, template_revision_used, retry_authorized
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', 0, '', 1, 0)
            """, (
                f"{campaign_id}_{t.team_id}",
                campaign_id,
                t.row_index,
                t.team_name,
                t.team_identifier,
                t.leader_name,
                t.leader_email,
                json.dumps(t.participant_names),
                json.dumps(t.ref_numbers),
                json.dumps([c.model_dump() for c in t.certificate_files]),
                t.validation_status,
                json.dumps(t.validation_errors),
                1 if t.manual_override else 0,
                t.custom_subject,
                t.custom_body,
                t.cc_recipients,
                t.bcc_recipients,
                stable_recipient_id,
                norm_email
            ))

        conn.commit()

        log_campaign_audit(
            campaign_id=campaign_id,
            event_type="CAMPAIGN_PREPARED",
            details={
                "name": req.name,
                "campaign_type": camp_type,
                "total_recipients": report.summary.total_teams,
                "mapping_policy": mapping_policy
            },
            conn=conn
        )

        return CampaignResponse(
            id=campaign_id,
            name=req.name,
            status="prepared",
            campaign_type=camp_type,
            total_teams=report.summary.total_teams,
            sent_count=0,
            failed_count=0,
            pending_count=report.summary.total_teams,
            uncertain_count=0,
            total_certificates=total_certs,
            estimated_size_mb=est_size_mb,
            current_template_revision=1,
            is_paused=False,
            created_at="Just now"
        )
    finally:
        conn.close()


@router.get("", response_model=List[CampaignResponse])
async def list_campaigns():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM campaigns ORDER BY created_at DESC")
        rows = cursor.fetchall()
        result = []
        for r in rows:
            cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN delivery_status = 'SMTP_ACCEPTED' THEN 1 ELSE 0 END) as accepted,
                SUM(CASE WHEN delivery_status = 'FAILED' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN delivery_status = 'DELIVERY_UNKNOWN' THEN 1 ELSE 0 END) as uncertain,
                SUM(CASE WHEN delivery_status = 'PENDING' THEN 1 ELSE 0 END) as pending
            FROM teams WHERE campaign_id = ?
            """, (r["id"],))
            counts = cursor.fetchone()
            tot = counts["total"] or r["total_teams"] or 0
            acc = counts["accepted"] or r["sent_count"] or 0
            fld = counts["failed"] or r["failed_count"] or 0
            unc = counts["uncertain"] or 0
            pnd = counts["pending"] or max(0, tot - acc - fld - unc)

            result.append(CampaignResponse(
                id=r["id"],
                name=r["name"],
                status=r["status"],
                campaign_type=r["campaign_type"] if "campaign_type" in r.keys() else "certificate_distribution",
                total_teams=tot,
                sent_count=acc,
                failed_count=fld,
                pending_count=pnd,
                uncertain_count=unc,
                total_certificates=tot * 6 if (r["campaign_type"] if "campaign_type" in r.keys() else "") == "certificate_distribution" else 0,
                estimated_size_mb=0.0,
                current_template_revision=r["current_template_revision"] if "current_template_revision" in r.keys() else 1,
                is_paused=bool(r["is_paused"]) if "is_paused" in r.keys() else False,
                created_at=str(r["created_at"])
            ))
        return result
    finally:
        conn.close()


@router.get("/recovery", response_model=List[CampaignRecoveryItem])
async def list_recoverable_campaigns():
    """
    Returns list of all campaigns with status breakdown for the Campaign Recovery Screen.
    Survives browser refreshes and backend restarts.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM campaigns ORDER BY updated_at DESC")
        rows = cursor.fetchall()
        recovery_list = []
        for r in rows:
            c_id = r["id"]
            cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN delivery_status = 'SMTP_ACCEPTED' THEN 1 ELSE 0 END) as accepted,
                SUM(CASE WHEN delivery_status = 'FAILED' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN delivery_status = 'DELIVERY_UNKNOWN' THEN 1 ELSE 0 END) as uncertain,
                SUM(CASE WHEN delivery_status = 'PENDING' THEN 1 ELSE 0 END) as pending
            FROM teams WHERE campaign_id = ?
            """, (c_id,))
            counts = cursor.fetchone()
            tot = counts["total"] or r["total_teams"] or 0
            acc = counts["accepted"] or 0
            fld = counts["failed"] or 0
            unc = counts["uncertain"] or 0
            pnd = counts["pending"] or 0
            rem = pnd + fld + unc

            status_str = r["status"]
            is_resumable = status_str in ["paused", "interrupted", "failed", "prepared"] and rem > 0

            recovery_list.append(CampaignRecoveryItem(
                id=c_id,
                name=r["name"],
                campaign_type=r["campaign_type"] if "campaign_type" in r.keys() else "certificate_distribution",
                status=status_str,
                total_recipients=tot,
                accepted_count=acc,
                pending_count=pnd,
                failed_count=fld,
                uncertain_count=unc,
                remaining_count=rem,
                current_template_revision=r["current_template_revision"] if "current_template_revision" in r.keys() else 1,
                last_activity=str(r["updated_at"] or r["created_at"]),
                is_resumable=is_resumable
            ))
        return recovery_list
    finally:
        conn.close()


@router.get("/{campaign_id}", response_model=CampaignDetailResponse)
async def get_campaign_detail(campaign_id: str):
    """
    Returns full details for a campaign including:
    - Campaign metadata
    - Template revision history
    - Recipient delivery ledger
    - Immutable audit logs
    - Status counts
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
        camp = cursor.fetchone()
        if not camp:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")

        # Revisions
        revisions_raw = get_template_revisions(campaign_id)
        revisions = [
            TemplateRevisionResponse(
                id=rev["id"],
                campaign_id=rev["campaign_id"],
                revision_number=rev["revision_number"],
                subject=rev["subject"],
                body=rev["body"],
                global_cc=rev.get("global_cc", "") or "",
                global_bcc=rev.get("global_bcc", "") or "",
                created_by=rev.get("created_by", "Admin"),
                change_summary=rev.get("change_summary", "") or "",
                is_active=bool(rev.get("is_active", 1)),
                created_at=str(rev.get("created_at"))
            ) for rev in revisions_raw
        ]

        # Audit logs
        audit_logs = get_campaign_audit_logs(campaign_id)

        # Recipients delivery ledger
        cursor.execute("""
        SELECT * FROM teams WHERE campaign_id = ? ORDER BY row_index ASC
        """, (campaign_id,))
        team_rows = cursor.fetchall()

        recipients = []
        counts = {"total": 0, "accepted": 0, "pending": 0, "failed": 0, "uncertain": 0, "skipped": 0}

        for t in team_rows:
            counts["total"] += 1
            st = t["delivery_status"] or "PENDING"
            if st == "SMTP_ACCEPTED":
                counts["accepted"] += 1
            elif st == "FAILED":
                counts["failed"] += 1
            elif st == "DELIVERY_UNKNOWN":
                counts["uncertain"] += 1
            elif st == "SKIPPED":
                counts["skipped"] += 1
            else:
                counts["pending"] += 1

            cert_files_list = json.loads(t["certificate_files_json"] or "[]")
            cert_names = [c.get("filename") for c in cert_files_list if c.get("filename")]

            recipients.append(CampaignRecipientItem(
                id=t["id"],
                recipient_id=t["recipient_id"] or t["team_identifier"] or t["id"],
                row_index=t["row_index"],
                team_name=t["team_name"],
                team_identifier=t["team_identifier"],
                leader_name=t["leader_name"],
                leader_email=t["leader_email"],
                normalized_email=t["normalized_email"] or t["leader_email"].strip().lower(),
                delivery_status=st,
                delivery_attempts=t["delivery_attempts"] or 0,
                last_error=t["last_error"] or "",
                template_revision_used=t["template_revision_used"] or 1,
                delivery_timestamp=str(t["delivery_timestamp"]) if t["delivery_timestamp"] else None,
                retry_authorized=bool(t["retry_authorized"]),
                certificate_count=len(cert_names),
                certificate_names=cert_names
            ))

        camp_resp = CampaignResponse(
            id=camp["id"],
            name=camp["name"],
            status=camp["status"],
            campaign_type=camp["campaign_type"] if "campaign_type" in camp.keys() else "certificate_distribution",
            total_teams=counts["total"],
            sent_count=counts["accepted"],
            failed_count=counts["failed"],
            pending_count=counts["pending"],
            uncertain_count=counts["uncertain"],
            total_certificates=counts["total"] * 6 if (camp["campaign_type"] if "campaign_type" in camp.keys() else "") == "certificate_distribution" else 0,
            estimated_size_mb=0.0,
            current_template_revision=camp["current_template_revision"] if "current_template_revision" in camp.keys() else 1,
            is_paused=bool(camp["is_paused"]) if "is_paused" in camp.keys() else False,
            created_at=str(camp["created_at"])
        )

        return CampaignDetailResponse(
            campaign=camp_resp,
            revisions=revisions,
            recipients=recipients,
            audit_logs=audit_logs,
            summary_counts=counts
        )
    finally:
        conn.close()


@router.post("/{campaign_id}/template")
async def update_campaign_template(campaign_id: str, req: UpdateCampaignTemplateRequest):
    """
    Template Revision Handling (Option A vs Option B):
    - Option A: Continue with the original template. Retains existing revision for remaining recipients.
    - Option B: Apply updated template to remaining recipients. Creates a new immutable template revision.
    Never retroactively alters already SMTP_ACCEPTED deliveries.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
        camp = cursor.fetchone()
        if not camp:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")

        # Recipient delivery breakdown
        cursor.execute("""
        SELECT 
            SUM(CASE WHEN delivery_status = 'SMTP_ACCEPTED' THEN 1 ELSE 0 END) as accepted,
            SUM(CASE WHEN delivery_status = 'PENDING' THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN delivery_status = 'FAILED' THEN 1 ELSE 0 END) as failed,
            SUM(CASE WHEN delivery_status = 'DELIVERY_UNKNOWN' THEN 1 ELSE 0 END) as uncertain
        FROM teams WHERE campaign_id = ?
        """, (campaign_id,))
        counts = cursor.fetchone()
        accepted_cnt = counts["accepted"] or 0
        pending_cnt = counts["pending"] or 0
        failed_cnt = counts["failed"] or 0
        uncertain_cnt = counts["uncertain"] or 0

        current_rev = camp["current_template_revision"] if "current_template_revision" in camp.keys() else 1

        if req.choice == "OPTION_B_APPLY_TO_REMAINING":
            # Create new immutable template revision
            new_rev = create_template_revision(
                campaign_id=campaign_id,
                subject=req.subject,
                body=req.body,
                global_cc=req.global_cc or "",
                global_bcc=req.global_bcc or "",
                created_by=req.reviewer or "Admin",
                change_summary=req.reason or "Updated template applied to remaining recipients",
                set_as_active=True
            )
            next_rev = new_rev["revision_number"]
            action_desc = f"New immutable Revision {next_rev} activated for remaining recipients."
        else:
            # Option A: Keep original revision
            next_rev = current_rev
            action_desc = f"Original Revision {current_rev} retained for remaining recipients."
            log_campaign_audit(
                campaign_id=campaign_id,
                event_type="TEMPLATE_OPTION_A_RETAINED",
                details={
                    "revision_retained": current_rev,
                    "reviewer": req.reviewer,
                    "reason": req.reason
                },
                reviewer=req.reviewer or "Admin"
            )

        return {
            "success": True,
            "choice": req.choice,
            "message": action_desc,
            "accepted_count": accepted_cnt,
            "pending_count": pending_cnt,
            "failed_count": failed_cnt,
            "uncertain_count": uncertain_cnt,
            "previous_revision": current_rev,
            "active_revision": next_rev
        }
    finally:
        conn.close()


@router.post("/{campaign_id}/resolve-uncertain")
async def resolve_uncertain_delivery(campaign_id: str, req: ResolveUncertainRequest):
    """
    Strict resolution for DELIVERY_UNKNOWN recipients:
    - authorize_retry: Reset status to PENDING and mark retry_authorized = 1.
    - mark_accepted: User confirmed external receipt; mark SMTP_ACCEPTED and increment sent_count.
    - mark_skipped: User decided to skip this recipient; mark SKIPPED.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM teams WHERE campaign_id = ? AND (id = ? OR recipient_id = ?)", (campaign_id, req.recipient_id, req.recipient_id))
        rec = cursor.fetchone()
        if not rec:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient not found in campaign.")

        team_id = rec["id"]
        leader_email = rec["leader_email"]

        if req.action == "authorize_retry":
            cursor.execute("""
            UPDATE teams 
            SET delivery_status = 'PENDING', 
                retry_authorized = 1,
                last_error = ? 
            WHERE id = ?
            """, (f"Retry authorized by {req.reviewer}: {req.reason}", team_id))
            event_type = "UNCERTAIN_RETRY_AUTHORIZED"
        elif req.action == "mark_accepted":
            cursor.execute("""
            UPDATE teams 
            SET delivery_status = 'SMTP_ACCEPTED', 
                retry_authorized = 0,
                last_error = ? 
            WHERE id = ?
            """, (f"Manually confirmed accepted by {req.reviewer}: {req.reason}", team_id))
            cursor.execute("UPDATE campaigns SET sent_count = sent_count + 1 WHERE id = ?", (campaign_id,))
            event_type = "UNCERTAIN_MARKED_ACCEPTED"
        elif req.action == "mark_skipped":
            cursor.execute("""
            UPDATE teams 
            SET delivery_status = 'SKIPPED', 
                retry_authorized = 0,
                last_error = ? 
            WHERE id = ?
            """, (f"Skipped by {req.reviewer}: {req.reason}", team_id))
            event_type = "UNCERTAIN_MARKED_SKIPPED"
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid action: {req.action}")

        conn.commit()

        log_campaign_audit(
            campaign_id=campaign_id,
            event_type=event_type,
            details={
                "recipient_id": req.recipient_id,
                "email": leader_email,
                "action": req.action,
                "reason": req.reason
            },
            reviewer=req.reviewer or "Admin"
        )

        return {"success": True, "message": f"Recipient {leader_email} resolved with {req.action}."}
    finally:
        conn.close()


@router.post("/{campaign_id}/retry-failed")
async def retry_failed_recipients(campaign_id: str, req: RetryFailedRequest):
    """
    Authorizes retry for all FAILED recipients in a campaign.
    Does NOT touch SMTP_ACCEPTED or DELIVERY_UNKNOWN without explicit separate authorization.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE teams 
        SET delivery_status = 'PENDING', 
            retry_authorized = 1,
            last_error = ?
        WHERE campaign_id = ? AND delivery_status = 'FAILED'
        """, (f"Batch retry authorized by {req.reviewer}: {req.reason}", campaign_id))
        updated_count = cursor.rowcount
        conn.commit()

        log_campaign_audit(
            campaign_id=campaign_id,
            event_type="BATCH_RETRY_FAILED_AUTHORIZED",
            details={
                "recipients_affected": updated_count,
                "reviewer": req.reviewer,
                "reason": req.reason
            },
            reviewer=req.reviewer or "Admin"
        )

        return {"success": True, "affected_recipients": updated_count, "message": f"Authorized retry for {updated_count} failed recipient(s)."}
    finally:
        conn.close()


@router.post("/test-send", response_model=TestSendResponse)
async def send_test_email(req: TestSendRequest):
    """
    Dedicated test send workflow. Overrides recipient to test_recipient_email
    and guarantees the real team leader is never emailed.
    Uses the exact template subject and body passed from the frontend.
    """
    session = SessionStore.get_session(req.session_id)
    report = session.get("latest_report")
    if not report:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session has no validated teams to test with."
        )

    # Find the target team
    target_team = next((t for t in report.teams if t.team_id == req.team_id), None)
    if not target_team:
        # Default to first team if not matched
        target_team = report.teams[0]

    # Validate test email address
    if not EmailService.parse_email_list(req.test_recipient_email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid test recipient email address."
        )

    # Resolve SMTP credentials
    smtp_cfg = dict(SessionStore.smtp_memory_config)
    if req.smtp_password:
        smtp_cfg["password"] = req.smtp_password

    if not smtp_cfg.get("password") or not smtp_cfg.get("username"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SMTP credentials not configured. Please enter your SMTP username and password in Settings."
        )

    # Render template with target team's context using the EXACT composed subject & body
    context = {
        "team_name": target_team.team_name,
        "leader_name": target_team.leader_name,
        "leader_email": target_team.leader_email,
        "team_id": target_team.team_identifier or target_team.team_id,
        "event_name": "Hack-O-Sprint 4.0 – SIH Internal Round 2026",
    }
    for i in range(1, 7):
        context[f"member_{i}"] = target_team.participant_names[i-1] if i-1 < len(target_team.participant_names) else f"Member {i}"
        context[f"ref_{i}"] = target_team.ref_numbers[i-1] if i-1 < len(target_team.ref_numbers) else ""

    rendered_subject = f"[TEST MODE] {EmailService.render_template(req.subject, context)}"
    rendered_body = f"*** THIS IS A TEST EMAIL (Real Leader: {target_team.leader_name} <{target_team.leader_email}>) ***\n\n" + EmailService.render_template(req.body, context)

    # Parse test CC/BCC (strictly using test input, ignoring global CC/BCC to prevent accidental leaks)
    test_cc = EmailService.parse_email_list(req.test_cc) if req.test_cc else []
    test_bcc = EmailService.parse_email_list(req.test_bcc) if req.test_bcc else []

    # Prepare attachments
    attachments: List[Tuple[Path, str]] = []
    attachment_names: List[str] = []
    if req.include_attachments:
        for idx, c in enumerate(target_team.certificate_files):
            if c.exists and c.relative_path:
                f_path = Path(c.relative_path)
                m_name = EmailService.clean_filename(target_team.participant_names[idx] if idx < len(target_team.participant_names) else f"Member_{idx+1}")
                clean_t_name = EmailService.clean_filename(target_team.team_name)
                custom_name = f"HackOSprint_{clean_t_name}_Member_{idx+1}_{m_name}.png"
                attachments.append((f_path, custom_name))
                attachment_names.append(custom_name)

    msg = EmailService.build_email_message(
        sender_name=smtp_cfg.get("sender_name", ""),
        sender_email=smtp_cfg.get("sender_email", ""),
        to_email=req.test_recipient_email,
        subject=rendered_subject,
        body_text=rendered_body,
        cc_emails=test_cc,
        bcc_emails=test_bcc,
        attachments=attachments
    )

    try:
        SMTPService.send_single_message(
            host=smtp_cfg["host"],
            port=smtp_cfg["port"],
            use_tls=smtp_cfg.get("use_tls", True),
            use_ssl=smtp_cfg.get("use_ssl", False),
            username=smtp_cfg["username"],
            password=smtp_cfg["password"],
            message=msg,
            to_email=req.test_recipient_email,
            cc_emails=test_cc,
            bcc_emails=test_bcc
        )

        # Log test email
        conn = get_db_connection()
        try:
            conn.execute("""
            INSERT INTO delivery_logs (
                id, campaign_id, team_id, team_name, recipient_email,
                cc_recipients, bcc_count, attachment_count, attachment_names_json,
                status, error_message, retry_count, is_test, created_at
            ) VALUES (?, 'test-session', ?, ?, ?, ?, ?, ?, ?, 'SENT', '', 0, 1, CURRENT_TIMESTAMP)
            """, (
                str(uuid.uuid4()),
                target_team.team_id,
                target_team.team_name,
                req.test_recipient_email,
                ", ".join(test_cc),
                len(test_bcc),
                len(attachments),
                json.dumps(attachment_names)
            ))
            conn.commit()
        finally:
            conn.close()

        return TestSendResponse(
            success=True,
            message="Test email sent successfully! Please check your inbox.",
            actual_recipient=req.test_recipient_email,
            real_leader_email_protected=target_team.leader_email,
            attachment_count=len(attachments),
            attachment_names=attachment_names
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send test email: {str(e)}"
        )


@router.post("/{campaign_id}/send")
async def start_sending_campaign(campaign_id: str, req: SendCampaignRequest):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
        camp = cursor.fetchone()
        if not camp:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")

        # Check if already running in memory
        active_task = campaign_tasks.get(campaign_id)
        if active_task and active_task.get("status") == "sending":
            return {"message": "Campaign is already running.", "status": "sending"}

        smtp_cfg = dict(SessionStore.smtp_memory_config)
        if req.smtp_password:
            smtp_cfg["password"] = req.smtp_password

        if not smtp_cfg.get("password") or not smtp_cfg.get("username"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SMTP credentials required. Please configure username and password in Settings."
            )

        # Launch background runner
        asyncio.create_task(CampaignRunner.run_campaign(
            campaign_id=campaign_id,
            smtp_config=smtp_cfg,
            delay_seconds=req.delay_seconds,
            max_retries=req.max_retries
        ))

        return {"message": "Campaign sending started in background.", "campaign_id": campaign_id, "status": "sending"}
    finally:
        conn.close()


@router.post("/{campaign_id}/pause")
async def pause_campaign(campaign_id: str):
    success = CampaignRunner.pause_campaign(campaign_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Campaign cannot be paused.")
    return {"message": "Campaign pause requested cleanly at safe checkpoint.", "campaign_id": campaign_id}


@router.post("/{campaign_id}/resume")
async def resume_campaign(campaign_id: str, req: Optional[SendCampaignRequest] = None):
    """
    Resumes a campaign safely across sessions or application restarts.
    - Updates DB is_paused = 0.
    - If background runner is not currently executing, launches it asynchronously.
    - Skips already SMTP_ACCEPTED recipients unconditionally.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
        camp = cursor.fetchone()
        if not camp:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")

        if camp["status"] == "completed":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot resume a completed campaign.")

        CampaignRunner.resume_campaign(campaign_id)

        # If runner is not currently sending in memory, start it
        active_task = campaign_tasks.get(campaign_id)
        if not active_task or active_task.get("status") != "sending":
            smtp_cfg = dict(SessionStore.smtp_memory_config)
            if req and req.smtp_password:
                smtp_cfg["password"] = req.smtp_password

            delay = req.delay_seconds if req else 2.0
            retries = req.max_retries if req else 2

            asyncio.create_task(CampaignRunner.run_campaign(
                campaign_id=campaign_id,
                smtp_config=smtp_cfg,
                delay_seconds=delay,
                max_retries=retries
            ))

        return {"message": "Campaign resumed safely.", "campaign_id": campaign_id, "status": "sending"}
    finally:
        conn.close()


@router.post("/{campaign_id}/cancel")
async def cancel_campaign(campaign_id: str):
    success = CampaignRunner.cancel_campaign(campaign_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Campaign cannot be cancelled.")
    return {"message": "Campaign cancellation requested. In-flight operations reach checkpoint and stop.", "campaign_id": campaign_id}


@router.get("/{campaign_id}/status", response_model=CampaignStatusResponse)
async def get_campaign_status(campaign_id: str):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
        camp = cursor.fetchone()
        if not camp:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")

        task_state = campaign_tasks.get(campaign_id, {})
        status_str = task_state.get("status") or camp["status"]
        current_team = task_state.get("current_team")
        error_msg = task_state.get("error_message")

        cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN delivery_status = 'SMTP_ACCEPTED' THEN 1 ELSE 0 END) as accepted,
            SUM(CASE WHEN delivery_status = 'FAILED' THEN 1 ELSE 0 END) as failed,
            SUM(CASE WHEN delivery_status = 'DELIVERY_UNKNOWN' THEN 1 ELSE 0 END) as uncertain,
            SUM(CASE WHEN delivery_status = 'PENDING' THEN 1 ELSE 0 END) as pending
        FROM teams WHERE campaign_id = ?
        """, (campaign_id,))
        counts = cursor.fetchone()

        total = counts["total"] or camp["total_teams"] or 1
        sent = counts["accepted"] or camp["sent_count"] or 0
        failed = counts["failed"] or camp["failed_count"] or 0
        uncertain = counts["uncertain"] or 0
        pending = counts["pending"] or max(0, total - sent - failed - uncertain)
        progress = round(((sent + failed) / total) * 100, 1) if total > 0 else 0.0

        is_paused = bool(camp["is_paused"]) or task_state.get("is_paused", False)
        is_completed = status_str in ["completed", "cancelled"]

        return CampaignStatusResponse(
            campaign_id=campaign_id,
            status=status_str,
            campaign_type=camp["campaign_type"] if "campaign_type" in camp.keys() else "certificate_distribution",
            total_teams=total,
            sent_count=sent,
            failed_count=failed,
            pending_count=pending,
            uncertain_count=uncertain,
            progress_percent=progress,
            current_team=current_team,
            current_template_revision=camp["current_template_revision"] if "current_template_revision" in camp.keys() else 1,
            is_paused=is_paused,
            is_completed=is_completed,
            error_message=error_msg
        )
    finally:
        conn.close()

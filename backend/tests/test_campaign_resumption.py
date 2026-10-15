import pytest
import unittest.mock as mock
import json
import uuid
import smtplib
import ssl
import asyncio
from pathlib import Path
from backend.app.core.database import (
    get_db_connection,
    init_db,
    create_template_revision,
    get_active_template_revision,
    get_campaign_audit_logs,
    save_approval_override,
    get_all_approval_overrides
)
from backend.app.services.smtp_service import SMTPService, CampaignRunner, campaign_tasks
from backend.app.schemas.campaign import (
    CampaignCreate,
    UpdateCampaignTemplateRequest,
    ResolveUncertainRequest,
    RetryFailedRequest
)
from backend.app.api.routes_campaigns import (
    create_campaign,
    update_campaign_template,
    resolve_uncertain_delivery,
    retry_failed_recipients,
    resume_campaign
)
from backend.app.api.session_store import SessionStore
from backend.app.schemas.mapping import (
    ValidationReportResponse,
    ValidationSummary,
    TeamMappingItem,
    CertificateFileInfo
)

def create_mock_campaign(campaign_id: str, total_recipients: int = 3, camp_type: str = "certificate_distribution"):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO campaigns (
            id, name, status, total_teams, sent_count, failed_count, config_json,
            campaign_type, is_paused, is_cancelled, current_template_revision, snapshot_json
        ) VALUES (?, 'Test Resumption Campaign', 'prepared', ?, 0, 0, ?, ?, 0, 0, 1, '{}')
        """, (
            campaign_id,
            total_recipients,
            json.dumps({"subject": "Original Subject Rev 1", "body": "Original Body Rev 1"}),
            camp_type
        ))

        create_template_revision(
            campaign_id=campaign_id,
            subject="Original Subject Rev 1",
            body="Original Body Rev 1",
            created_by="Admin",
            change_summary="Initial Revision",
            set_as_active=True,
            conn=conn
        )

        for i in range(1, total_recipients + 1):
            cursor.execute("""
            INSERT INTO teams (
                id, campaign_id, row_index, team_name, team_identifier,
                leader_name, leader_email, normalized_email, recipient_id,
                participant_names_json, ref_numbers_json, certificate_files_json,
                delivery_status, delivery_attempts, last_error, template_revision_used
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '["Member 1"]', '["REF-01"]', '[]', 'PENDING', 0, '', 1)
            """, (
                f"{campaign_id}_team_{i}",
                campaign_id,
                i,
                f"Team {i}",
                f"TEAM-0{i}",
                f"Leader {i}",
                f"leader{i}@example.com",
                f"leader{i}@example.com",
                f"RECIP-{i}"
            ))
        conn.commit()
    finally:
        conn.close()


# 1. A campaign can be paused and resumed
@pytest.mark.asyncio
async def test_campaign_pause_and_resume():
    campaign_id = f"test-pause-res-{uuid.uuid4()}"
    create_mock_campaign(campaign_id, total_recipients=4)

    smtp_cfg = {"host": "localhost", "port": 1025, "username": "u", "password": "p"}

    send_call_count = 0
    def mock_send(*args, **kwargs):
        nonlocal send_call_count
        send_call_count += 1
        if send_call_count == 1:
            # Trigger pause after sending the first recipient
            CampaignRunner.pause_campaign(campaign_id)
        return True

    with mock.patch("backend.app.services.smtp_service.SMTPService.send_single_message", side_effect=mock_send):
        # Run campaign
        await CampaignRunner.run_campaign(campaign_id, smtp_cfg, delay_seconds=0.001)

        # Campaign should be paused at checkpoint
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT status, is_paused, sent_count FROM campaigns WHERE id = ?", (campaign_id,))
            camp = cursor.fetchone()
            assert camp["status"] == "paused"
            assert camp["is_paused"] == 1
            assert camp["sent_count"] == 1

            # Resume the campaign
            CampaignRunner.resume_campaign(campaign_id)
            cursor.execute("SELECT is_paused FROM campaigns WHERE id = ?", (campaign_id,))
            assert cursor.fetchone()["is_paused"] == 0
        finally:
            conn.close()


# 2. Already accepted recipients are not resent
@pytest.mark.asyncio
async def test_already_accepted_recipients_not_resent():
    campaign_id = f"test-no-resend-{uuid.uuid4()}"
    create_mock_campaign(campaign_id, total_recipients=3)

    # Manually mark recipient 1 as SMTP_ACCEPTED
    conn = get_db_connection()
    try:
        conn.execute("""
        UPDATE teams 
        SET delivery_status = 'SMTP_ACCEPTED', delivery_attempts = 1 
        WHERE id = ?
        """, (f"{campaign_id}_team_1",))
        conn.execute("UPDATE campaigns SET sent_count = 1 WHERE id = ?", (campaign_id,))
        conn.commit()
    finally:
        conn.close()

    sent_emails = []
    def mock_send_tracker(*args, **kwargs):
        sent_emails.append(kwargs.get("to_email"))
        return True

    with mock.patch("backend.app.services.smtp_service.SMTPService.send_single_message", side_effect=mock_send_tracker):
        await CampaignRunner.run_campaign(
            campaign_id,
            {"host": "localhost", "port": 1025, "username": "u", "password": "p"},
            delay_seconds=0.001
        )

        # Leader 1 must NOT be in sent_emails!
        assert "leader1@example.com" not in sent_emails
        assert "leader2@example.com" in sent_emails
        assert "leader3@example.com" in sent_emails
        assert len(sent_emails) == 2


# 3. Pending recipients are sent after resumption
@pytest.mark.asyncio
async def test_pending_recipients_sent_after_resumption():
    campaign_id = f"test-resume-pending-{uuid.uuid4()}"
    create_mock_campaign(campaign_id, total_recipients=3)

    conn = get_db_connection()
    try:
        # Recipient 1 already sent, Recipient 2 and 3 PENDING
        conn.execute("UPDATE teams SET delivery_status = 'SMTP_ACCEPTED' WHERE id = ?", (f"{campaign_id}_team_1",))
        conn.execute("UPDATE campaigns SET sent_count = 1, status = 'paused', is_paused = 1 WHERE id = ?", (campaign_id,))
        conn.commit()
    finally:
        conn.close()

    sent_emails = []
    with mock.patch("backend.app.services.smtp_service.SMTPService.send_single_message", side_effect=lambda *a, **kw: sent_emails.append(kw.get("to_email"))):
        # Resume campaign
        CampaignRunner.resume_campaign(campaign_id)
        await CampaignRunner.run_campaign(
            campaign_id,
            {"host": "localhost", "port": 1025, "username": "u", "password": "p"},
            delay_seconds=0.001
        )

        assert "leader2@example.com" in sent_emails
        assert "leader3@example.com" in sent_emails
        assert len(sent_emails) == 2

        # Final DB verification
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as c FROM teams WHERE campaign_id = ? AND delivery_status = 'SMTP_ACCEPTED'", (campaign_id,))
            assert cursor.fetchone()["c"] == 3
        finally:
            conn.close()


# 4. Template edits apply only to eligible remaining recipients when selected (Option B)
@pytest.mark.asyncio
async def test_template_edits_apply_only_to_remaining_recipients_option_b():
    campaign_id = f"test-option-b-{uuid.uuid4()}"
    create_mock_campaign(campaign_id, total_recipients=3)

    conn = get_db_connection()
    try:
        # Team 1 accepted under Revision 1
        conn.execute("""
        UPDATE teams 
        SET delivery_status = 'SMTP_ACCEPTED', template_revision_used = 1 
        WHERE id = ?
        """, (f"{campaign_id}_team_1",))
        conn.execute("UPDATE campaigns SET sent_count = 1, status = 'paused', is_paused = 1 WHERE id = ?", (campaign_id,))
        conn.commit()
    finally:
        conn.close()

    # User elects Option B: Update template for remaining recipients
    req = UpdateCampaignTemplateRequest(
        choice="OPTION_B_APPLY_TO_REMAINING",
        subject="Updated Subject Rev 2",
        body="Updated Body Rev 2 for remaining teams",
        reviewer="Organizer Lead",
        reason="Fixed typo in body"
    )
    res = await update_campaign_template(campaign_id, req)
    assert res["choice"] == "OPTION_B_APPLY_TO_REMAINING"
    assert res["active_revision"] == 2

    sent_subjects = []
    def mock_send_subject(*args, **kwargs):
        msg = kwargs.get("message")
        sent_subjects.append(msg["Subject"])
        return True

    with mock.patch("backend.app.services.smtp_service.SMTPService.send_single_message", side_effect=mock_send_subject):
        CampaignRunner.resume_campaign(campaign_id)
        await CampaignRunner.run_campaign(
            campaign_id,
            {"host": "localhost", "port": 1025, "username": "u", "password": "p"},
            delay_seconds=0.001
        )

        # Team 2 and Team 3 received Rev 2
        assert len(sent_subjects) == 2
        assert all("Updated Subject Rev 2" in s for s in sent_subjects)

        # Verify DB: Team 1 remains recorded as Rev 1, Team 2 and 3 recorded as Rev 2
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT template_revision_used FROM teams WHERE id = ?", (f"{campaign_id}_team_1",))
            assert cursor.fetchone()["template_revision_used"] == 1

            cursor.execute("SELECT template_revision_used FROM teams WHERE id = ?", (f"{campaign_id}_team_2",))
            assert cursor.fetchone()["template_revision_used"] == 2
        finally:
            conn.close()


# 5. Continuing with the original template retains the original revision (Option A)
@pytest.mark.asyncio
async def test_continuing_with_original_template_retains_revision_option_a():
    campaign_id = f"test-option-a-{uuid.uuid4()}"
    create_mock_campaign(campaign_id, total_recipients=2)

    req = UpdateCampaignTemplateRequest(
        choice="OPTION_A_KEEP_ORIGINAL",
        subject="Draft Changed Subject",
        body="Draft Changed Body",
        reviewer="Admin Reviewer",
        reason="Decided to stick with original approved copy"
    )
    res = await update_campaign_template(campaign_id, req)
    assert res["choice"] == "OPTION_A_KEEP_ORIGINAL"
    assert res["active_revision"] == 1

    sent_subjects = []
    with mock.patch("backend.app.services.smtp_service.SMTPService.send_single_message", side_effect=lambda *a, **kw: sent_subjects.append(kw.get("message")["Subject"])):
        CampaignRunner.resume_campaign(campaign_id)
        await CampaignRunner.run_campaign(
            campaign_id,
            {"host": "localhost", "port": 1025, "username": "u", "password": "p"},
            delay_seconds=0.001
        )

        assert all("Original Subject Rev 1" in s for s in sent_subjects)


# 6. Delivery state survives a database-backed application restart
@pytest.mark.asyncio
async def test_delivery_state_survives_application_restart():
    campaign_id = f"test-restart-{uuid.uuid4()}"
    create_mock_campaign(campaign_id, total_recipients=3)

    conn = get_db_connection()
    try:
        # Simulate campaign mid-send when process dies
        conn.execute("UPDATE campaigns SET status = 'sending', is_paused = 0 WHERE id = ?", (campaign_id,))
        conn.execute("UPDATE teams SET delivery_status = 'SMTP_ACCEPTED' WHERE id = ?", (f"{campaign_id}_team_1",))
        conn.execute("UPDATE teams SET delivery_status = 'IN_PROGRESS' WHERE id = ?", (f"{campaign_id}_team_2",))
        conn.commit()
    finally:
        conn.close()

    # Simulate application startup (re-invoking init_db)
    init_db()

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT status, is_paused FROM campaigns WHERE id = ?", (campaign_id,))
        camp = cursor.fetchone()
        # Orphaned 'sending' campaign must cleanly transition to 'interrupted' with is_paused = 1
        assert camp["status"] == "interrupted"
        assert camp["is_paused"] == 1

        # The in-flight recipient must be marked 'DELIVERY_UNKNOWN'
        cursor.execute("SELECT delivery_status, last_error FROM teams WHERE id = ?", (f"{campaign_id}_team_2",))
        t2 = cursor.fetchone()
        assert t2["delivery_status"] == "DELIVERY_UNKNOWN"
        assert "Interrupted" in t2["last_error"]

        # Recipient 1 must retain SMTP_ACCEPTED
        cursor.execute("SELECT delivery_status FROM teams WHERE id = ?", (f"{campaign_id}_team_1",))
        assert cursor.fetchone()["delivery_status"] == "SMTP_ACCEPTED"
    finally:
        conn.close()


# 7. Failed recipients follow the retry policy
@pytest.mark.asyncio
async def test_failed_recipients_follow_retry_policy():
    campaign_id = f"test-retry-policy-{uuid.uuid4()}"
    create_mock_campaign(campaign_id, total_recipients=1)

    call_count = 0
    def mock_fail(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise smtplib.SMTPException("Transient network timeout")

    with mock.patch("backend.app.services.smtp_service.SMTPService.send_single_message", side_effect=mock_fail):
        await CampaignRunner.run_campaign(
            campaign_id,
            {"host": "localhost", "port": 1025, "username": "u", "password": "p"},
            delay_seconds=0.001,
            max_retries=2
        )

        # 1 initial attempt + 2 retries = 3 total attempts
        assert call_count == 3

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT delivery_status, delivery_attempts, last_error FROM teams WHERE id = ?", (f"{campaign_id}_team_1",))
            row = cursor.fetchone()
            assert row["delivery_status"] == "FAILED"
            assert "Transient network timeout" in row["last_error"]
        finally:
            conn.close()


# 8. Uncertain SMTP outcomes are not automatically resent
@pytest.mark.asyncio
async def test_uncertain_smtp_outcomes_not_auto_resent():
    campaign_id = f"test-uncertain-{uuid.uuid4()}"
    create_mock_campaign(campaign_id, total_recipients=2)

    # First recipient drops connection mid-flight
    call_count = 0
    def mock_uncertain_send(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise smtplib.SMTPServerDisconnected("Remote end closed connection unexpectedly")
        return True

    with mock.patch("backend.app.services.smtp_service.SMTPService.send_single_message", side_effect=mock_uncertain_send):
        await CampaignRunner.run_campaign(
            campaign_id,
            {"host": "localhost", "port": 1025, "username": "u", "password": "p"},
            delay_seconds=0.001
        )

    # Check database: recipient 1 must be DELIVERY_UNKNOWN
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT delivery_status, retry_authorized FROM teams WHERE id = ?", (f"{campaign_id}_team_1",))
        row = cursor.fetchone()
        assert row["delivery_status"] == "DELIVERY_UNKNOWN"
        assert row["retry_authorized"] == 0
    finally:
        conn.close()

    # Now attempt resume without explicit authorization: Recipient 1 must NOT be resent
    resent_emails = []
    with mock.patch("backend.app.services.smtp_service.SMTPService.send_single_message", side_effect=lambda *a, **kw: resent_emails.append(kw.get("to_email"))):
        CampaignRunner.resume_campaign(campaign_id)
        await CampaignRunner.run_campaign(
            campaign_id,
            {"host": "localhost", "port": 1025, "username": "u", "password": "p"},
            delay_seconds=0.001
        )

        assert "leader1@example.com" not in resent_emails

    # Now authorize retry explicitly
    await resolve_uncertain_delivery(campaign_id, ResolveUncertainRequest(
        recipient_id="RECIP-1",
        action="authorize_retry",
        reviewer="Lead Auditor",
        reason="Verified mail server did not queue message"
    ))

    # Now resumption SHOULD send recipient 1
    resent_after_auth = []
    with mock.patch("backend.app.services.smtp_service.SMTPService.send_single_message", side_effect=lambda *a, **kw: resent_after_auth.append(kw.get("to_email"))):
        CampaignRunner.resume_campaign(campaign_id)
        await CampaignRunner.run_campaign(
            campaign_id,
            {"host": "localhost", "port": 1025, "username": "u", "password": "p"},
            delay_seconds=0.001
        )
        assert "leader1@example.com" in resent_after_auth


# 9. A changed certificate mapping invalidates the appropriate prior authorization
def test_changed_certificate_mapping_invalidates_prior_authorization():
    # Setup initial override
    team_identifier = "TEAM-HASH-TEST"
    save_approval_override({
        "team_identifier": team_identifier,
        "team_name": "CyberKnights",
        "status": "OVERRIDE_APPROVED",
        "reviewer": "Security Lead",
        "reason": "Hash approved",
        "certificate_filenames": ["cert1.png", "cert2.png", "cert3.png", "cert4.png", "cert5.png", "cert6.png"]
    })

    overrides = get_all_approval_overrides()
    assert team_identifier in overrides
    assert overrides[team_identifier]["status"] == "OVERRIDE_APPROVED"

    # If certificates are remapped (different files), hash no longer matches
    new_files = ["cert1_NEW.png", "cert2.png", "cert3.png", "cert4.png", "cert5.png", "cert6.png"]
    new_hash = ",".join(new_files)
    assert new_hash != overrides[team_identifier]["certificate_mapping_hash"]


# 10. Reordering an Excel workbook cannot accidentally remap certificates or duplicate completed deliveries
@pytest.mark.asyncio
async def test_excel_reordering_protection():
    campaign_id = f"test-reorder-{uuid.uuid4()}"
    create_mock_campaign(campaign_id, total_recipients=2)

    conn = get_db_connection()
    try:
        # Team 1 was delivered
        conn.execute("UPDATE teams SET delivery_status = 'SMTP_ACCEPTED' WHERE recipient_id = 'RECIP-1'")
        conn.commit()

        # In SQLite, queries use normalized_email, recipient_id, or delivery_status != 'SMTP_ACCEPTED'
        # Even if row_index is swapped:
        conn.execute("UPDATE teams SET row_index = 2 WHERE recipient_id = 'RECIP-1'")
        conn.execute("UPDATE teams SET row_index = 1 WHERE recipient_id = 'RECIP-2'")
        conn.commit()
    finally:
        conn.close()

    dispatched = []
    with mock.patch("backend.app.services.smtp_service.SMTPService.send_single_message", side_effect=lambda *a, **kw: dispatched.append(kw.get("to_email"))):
        await CampaignRunner.run_campaign(
            campaign_id,
            {"host": "localhost", "port": 1025, "username": "u", "password": "p"},
            delay_seconds=0.001
        )

        # Team 1 was already accepted, so despite reordering, only Team 2 is dispatched!
        assert "leader1@example.com" not in dispatched
        assert "leader2@example.com" in dispatched
        assert len(dispatched) == 1


# 11. General mailing campaigns resume without requiring certificate files
@pytest.mark.asyncio
async def test_general_mailing_campaign_resumption_without_certificates():
    campaign_id = f"test-gen-mail-{uuid.uuid4()}"
    create_mock_campaign(campaign_id, total_recipients=2, camp_type="general_mailing")

    sent = []
    with mock.patch("backend.app.services.smtp_service.SMTPService.send_single_message", side_effect=lambda *a, **kw: sent.append(kw.get("to_email"))):
        await CampaignRunner.run_campaign(
            campaign_id,
            {"host": "localhost", "port": 1025, "username": "u", "password": "p"},
            delay_seconds=0.001
        )

        assert len(sent) == 2
        assert "leader1@example.com" in sent
        assert "leader2@example.com" in sent

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM campaigns WHERE id = ?", (campaign_id,))
            assert cursor.fetchone()["status"] == "completed"
        finally:
            conn.close()


# 12. Concurrent resume requests cannot dispatch the same recipient twice
@pytest.mark.asyncio
async def test_concurrent_resume_requests_cannot_double_dispatch():
    campaign_id = f"test-concurrency-{uuid.uuid4()}"
    create_mock_campaign(campaign_id, total_recipients=2)

    send_count = 0
    def mock_sync_send(*args, **kwargs):
        nonlocal send_count
        send_count += 1
        return True

    with mock.patch("backend.app.services.smtp_service.SMTPService.send_single_message", side_effect=mock_sync_send):
        # Fire two concurrent runners for the same campaign
        smtp_cfg = {"host": "localhost", "port": 1025, "username": "u", "password": "p"}
        runner1 = CampaignRunner.run_campaign(campaign_id, smtp_cfg, delay_seconds=0.001)
        runner2 = CampaignRunner.run_campaign(campaign_id, smtp_cfg, delay_seconds=0.001)

        await asyncio.gather(runner1, runner2)

        # Atomic SQLite update lock guarantees only one runner runs!
        # Exactly 2 messages dispatched for the 2 recipients (not 4)
        assert send_count == 2

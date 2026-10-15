import pytest
import unittest.mock as mock
import smtplib
import json
import uuid
from pathlib import Path
from backend.app.services.smtp_service import SMTPService, CampaignRunner
from backend.app.services.email_service import EmailService
from backend.app.core.database import get_db_connection

def test_smtp_auth_error_handling():
    with mock.patch("smtplib.SMTP") as mock_smtp_class:
        instance = mock_smtp_class.return_value
        instance.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Authentication credentials invalid")
        
        success, msg, details = SMTPService.test_connection(
            host="smtp.gmail.com",
            port=587,
            use_tls=True,
            use_ssl=False,
            username="user@example.com",
            password="wrongpassword"
        )
        assert success is False
        assert "Authentication failed" in msg
        assert "App Password" in msg # helpful guidance for Gmail

def test_test_email_recipient_override():
    # Verify that in test mode, the actual recipient is the test address, not the real leader
    real_leader_email = "real.leader@college.edu"
    test_user_email = "organizer.test@gmail.com"

    msg = EmailService.build_email_message(
        sender_name="Organizer",
        sender_email="admin@event.org",
        to_email=test_user_email, # Overridden
        subject="[TEST MODE] Your Certificates",
        body_text="Testing delivery."
    )

    with mock.patch("backend.app.services.smtp_service.SMTPService.get_smtp_client") as mock_client:
        server_instance = mock.MagicMock()
        mock_client.return_value = server_instance

        SMTPService.send_single_message(
            host="localhost",
            port=1025,
            use_tls=False,
            use_ssl=False,
            username="",
            password="",
            message=msg,
            to_email=test_user_email
        )

        server_instance.send_message.assert_called_once()
        args, kwargs = server_instance.send_message.call_args
        sent_recipients = kwargs.get("to_addrs", [])
        assert test_user_email in sent_recipients
        assert real_leader_email not in sent_recipients # Real leader protected!

@pytest.mark.asyncio
async def test_campaign_runner_idempotency_and_logging():
    conn = get_db_connection()
    campaign_id = f"test-camp-{uuid.uuid4()}"
    team_id_1 = f"team-1-{uuid.uuid4()}"
    team_id_2 = f"team-2-{uuid.uuid4()}"

    try:
        # Create campaign and teams in db
        conn.execute("""
        INSERT INTO campaigns (id, name, status, total_teams, config_json)
        VALUES (?, 'Test Campaign', 'prepared', 2, ?)
        """, (campaign_id, json.dumps({"subject": "Test Subj", "body": "Test Body"})))

        conn.execute("""
        INSERT INTO teams (id, campaign_id, row_index, team_name, leader_name, leader_email)
        VALUES (?, ?, 1, 'Team Alpha', 'Leader Alpha', 'alpha@example.com')
        """, (team_id_1, campaign_id))

        conn.execute("""
        INSERT INTO teams (id, campaign_id, row_index, team_name, leader_name, leader_email)
        VALUES (?, ?, 2, 'Team Beta', 'Leader Beta', 'beta@example.com')
        """, (team_id_2, campaign_id))

        # Mark team 1 as already SENT in delivery_logs to test idempotency
        conn.execute("""
        INSERT INTO delivery_logs (id, campaign_id, team_id, recipient_email, status, created_at)
        VALUES (?, ?, ?, 'alpha@example.com', 'SENT', CURRENT_TIMESTAMP)
        """, (str(uuid.uuid4()), campaign_id, team_id_1))
        conn.commit()

        # Run campaign with mocked SMTP send
        with mock.patch("backend.app.services.smtp_service.SMTPService.send_single_message") as mock_send:
            mock_send.return_value = True

            await CampaignRunner.run_campaign(
                campaign_id=campaign_id,
                smtp_config={"host": "localhost", "port": 1025, "username": "u", "password": "p"},
                delay_seconds=0.01,
                max_retries=1
            )

            # mock_send should ONLY be called once for Team Beta! (Team Alpha was skipped due to idempotency)
            assert mock_send.call_count == 1

        # Check logs in db: verify no password or sensitive credentials stored in logs
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM delivery_logs WHERE campaign_id = ?", (campaign_id,))
        logs = cursor.fetchall()
        for log_row in logs:
            log_str = json.dumps(dict(log_row))
            assert "p" not in log_row["error_message"]
            assert "password" not in log_str.lower()
    finally:
        conn.close()

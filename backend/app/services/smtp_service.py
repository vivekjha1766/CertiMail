import asyncio
import json
import logging
import smtplib
import ssl
import time
import uuid
from email.message import EmailMessage
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from backend.app.core.config import settings
from backend.app.core.database import get_db_connection
from backend.app.services.email_service import EmailService

logger = logging.getLogger(__name__)

# Active background campaign state
campaign_tasks: Dict[str, Dict[str, Any]] = {}

class SMTPService:
    @staticmethod
    def get_smtp_client(
        host: str,
        port: int,
        use_tls: bool,
        use_ssl: bool,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 25
    ) -> smtplib.SMTP:
        """
        Creates and authenticates an SMTP connection with verified TLS/SSL.
        """
        ssl_context = ssl.create_default_context()
        
        if use_ssl:
            server = smtplib.SMTP_SSL(host, port, context=ssl_context, timeout=timeout)
        else:
            server = smtplib.SMTP(host, port, timeout=timeout)
            server.ehlo()
            if use_tls:
                server.starttls(context=ssl_context)
                server.ehlo()
                
        if username and password:
            server.login(username, password)
            
        return server

    @classmethod
    def test_connection(
        cls,
        host: str,
        port: int,
        use_tls: bool,
        use_ssl: bool,
        username: str,
        password: str
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Tests authentication and connection to SMTP server without sending email.
        """
        try:
            server = cls.get_smtp_client(
                host=host,
                port=port,
                use_tls=use_tls,
                use_ssl=use_ssl,
                username=username,
                password=password,
                timeout=15
            )
            server.quit()
            return True, "SMTP connection and authentication successful!", None
        except smtplib.SMTPAuthenticationError as e:
            msg = "Authentication failed. Please verify your username and password."
            if "gmail" in host.lower():
                msg += " For Gmail, you MUST use a 16-character App Password (not your standard Google account password). Go to Google Account > Security > 2-Step Verification > App Passwords."
            return False, msg, str(e)
        except (ssl.SSLError, smtplib.SMTPConnectError) as e:
            return False, f"TLS/SSL Connection error: {str(e)}", str(e)
        except Exception as e:
            return False, f"Connection failed: {str(e)}", str(e)

    @classmethod
    def send_single_message(
        cls,
        host: str,
        port: int,
        use_tls: bool,
        use_ssl: bool,
        username: str,
        password: str,
        message: EmailMessage,
        to_email: str,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None
    ) -> bool:
        """Sends an EmailMessage to To, CC, and BCC recipients."""
        recipients = [to_email]
        if cc_emails:
            recipients.extend(cc_emails)
        if bcc_emails:
            recipients.extend(bcc_emails)
            
        # Clean and deduplicate recipient list
        recipients = list(dict.fromkeys([r.strip() for r in recipients if r.strip()]))

        server = cls.get_smtp_client(
            host=host,
            port=port,
            use_tls=use_tls,
            use_ssl=use_ssl,
            username=username,
            password=password
        )
        try:
            server.send_message(message, to_addrs=recipients)
            return True
        finally:
            try:
                server.quit()
            except Exception:
                pass


class CampaignRunner:
    @classmethod
    async def run_campaign(
        cls,
        campaign_id: str,
        smtp_config: Dict[str, Any],
        delay_seconds: float = 2.0,
        max_retries: int = 2
    ):
        """
        Database-backed persistent campaign executor.
        Guarantees:
        - Atomic concurrency lock preventing duplicate workers.
        - Idempotent recipient processing: skips SMTP_ACCEPTED recipients unconditionally.
        - Checkpoint safety: pauses cleanly between messages without interrupting in-flight SMTP calls.
        - Detection of uncertain SMTP outcomes (marked DELIVERY_UNKNOWN).
        - Audit trail for all transitions.
        """
        conn = get_db_connection()
        try:
            from backend.app.core.database import (
                log_campaign_audit,
                get_active_template_revision
            )

            cursor = conn.cursor()

            # Atomic concurrency check: Ensure only one runner can execute for this campaign
            cursor.execute("""
            UPDATE campaigns 
            SET status = 'sending', is_paused = 0, is_cancelled = 0, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ? AND status IN ('prepared', 'paused', 'interrupted', 'failed');
            """, (campaign_id,))
            if cursor.rowcount == 0:
                logger.warning(f"Campaign {campaign_id} is already running or in non-runnable state.")
                return
            conn.commit()

            # Register in active tasks map
            state = {
                "campaign_id": campaign_id,
                "status": "sending",
                "is_paused": False,
                "is_cancelled": False,
                "current_team": None,
                "error_message": None,
                "consecutive_failures": 0
            }
            campaign_tasks[campaign_id] = state

            log_campaign_audit(
                campaign_id=campaign_id,
                event_type="CAMPAIGN_EXECUTION_STARTED",
                details={"delay_seconds": delay_seconds, "max_retries": max_retries}
            )

            # Retrieve campaign metadata and active template revision
            cursor.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
            camp_row = cursor.fetchone()
            if not camp_row:
                logger.error(f"Campaign {campaign_id} not found in database.")
                return

            camp_type = camp_row["campaign_type"] if "campaign_type" in camp_row.keys() else "certificate_distribution"
            camp_config = json.loads(camp_row["config_json"] or "{}")

            active_revision = get_active_template_revision(campaign_id)
            if active_revision:
                active_rev_num = active_revision["revision_number"]
                active_subject = active_revision["subject"]
                active_body = active_revision["body"]
                active_global_cc = active_revision.get("global_cc", "")
                active_global_bcc = active_revision.get("global_bcc", "")
            else:
                active_rev_num = 1
                active_subject = camp_config.get("subject", "Hack-O-Sprint 4.0 Notification")
                active_body = camp_config.get("body", "")
                active_global_cc = camp_config.get("global_cc", "")
                active_global_bcc = camp_config.get("global_bcc", "")

            # Query eligible recipients:
            # - Strictly skip SMTP_ACCEPTED
            # - Strictly skip SKIPPED
            # - Process PENDING
            # - Process FAILED if retry_authorized == 1 or delivery_attempts < max_retries
            # - Strictly hold DELIVERY_UNKNOWN until retry_authorized == 1
            cursor.execute("""
            SELECT * FROM teams 
            WHERE campaign_id = ? 
              AND delivery_status != 'SMTP_ACCEPTED'
              AND delivery_status != 'SKIPPED'
              AND id NOT IN (
                  SELECT team_id FROM delivery_logs 
                  WHERE campaign_id = ? AND status IN ('SENT', 'SMTP_ACCEPTED')
              )
              AND (
                  delivery_status = 'PENDING'
                  OR (delivery_status = 'FAILED' AND (retry_authorized = 1 OR delivery_attempts < ?))
                  OR (delivery_status = 'DELIVERY_UNKNOWN' AND retry_authorized = 1)
              )
            ORDER BY row_index ASC
            """, (campaign_id, campaign_id, max_retries))
            eligible_recipients = cursor.fetchall()

            for team in eligible_recipients:
                team_id = team["id"]
                team_name = team["team_name"]
                leader_email = team["leader_email"]
                normalized_email = (team["normalized_email"] or leader_email).strip().lower()

                # Pre-send checkpoint: check if paused or cancelled in database or in-memory state
                cursor.execute("SELECT is_paused, is_cancelled, status FROM campaigns WHERE id = ?", (campaign_id,))
                camp_check = cursor.fetchone()
                if not camp_check or camp_check["is_cancelled"] or state.get("is_cancelled"):
                    state["status"] = "cancelled"
                    state["error_message"] = "Campaign cancelled by user at safe checkpoint."
                    log_campaign_audit(campaign_id, "CAMPAIGN_CANCELLED", {"checkpoint_recipient": leader_email})
                    cursor.execute("UPDATE campaigns SET status = 'cancelled', is_cancelled = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (campaign_id,))
                    conn.commit()
                    break

                if camp_check["is_paused"] or state.get("is_paused"):
                    state["status"] = "paused"
                    log_campaign_audit(campaign_id, "CAMPAIGN_PAUSED", {"checkpoint_recipient": leader_email})
                    cursor.execute("UPDATE campaigns SET status = 'paused', is_paused = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (campaign_id,))
                    conn.commit()
                    break

                # Circuit breaker check: abort if 3 consecutive failures
                if state["consecutive_failures"] >= 3:
                    state["status"] = "failed"
                    state["error_message"] = "Circuit Breaker: Aborted after 3 consecutive email send failures. Check your SMTP settings and provider limits."
                    log_campaign_audit(campaign_id, "CIRCUIT_BREAKER_TRIGGERED", {"consecutive_failures": state["consecutive_failures"]})
                    cursor.execute("UPDATE campaigns SET status = 'failed', is_paused = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (campaign_id,))
                    conn.commit()
                    break

                # Double-check idempotency against database delivery ledger and logs: NEVER resend to an already accepted recipient
                cursor.execute("""
                SELECT delivery_status FROM teams WHERE id = ?
                """, (team_id,))
                current_ledger_row = cursor.fetchone()
                if current_ledger_row and current_ledger_row["delivery_status"] == "SMTP_ACCEPTED":
                    logger.info(f"Skipping already accepted recipient {leader_email} ({team_id})")
                    continue

                cursor.execute("""
                SELECT 1 FROM delivery_logs WHERE campaign_id = ? AND team_id = ? AND status IN ('SENT', 'SMTP_ACCEPTED')
                """, (campaign_id, team_id))
                if cursor.fetchone():
                    logger.info(f"Skipping recipient with prior accepted delivery log {leader_email} ({team_id})")
                    continue

                state["current_team"] = team_name
                state["status"] = "sending"

                # Mark recipient as IN_PROGRESS
                cursor.execute("""
                UPDATE teams 
                SET delivery_status = 'IN_PROGRESS', 
                    delivery_attempts = delivery_attempts + 1,
                    template_revision_used = ?
                WHERE id = ?
                """, (active_rev_num, team_id))
                conn.commit()

                # Build template context
                participants = json.loads(team["participant_names_json"] or "[]")
                ref_numbers = json.loads(team["ref_numbers_json"] or "[]")
                cert_files_info = json.loads(team["certificate_files_json"] or "[]")

                context = {
                    "team_name": team_name,
                    "leader_name": team["leader_name"],
                    "leader_email": leader_email,
                    "team_id": team["team_identifier"] or team_id,
                    "event_name": "Hack-O-Sprint 4.0 – SIH Internal Round 2026",
                }
                for i in range(1, 7):
                    context[f"member_{i}"] = participants[i-1] if i-1 < len(participants) else f"Member {i}"
                    context[f"ref_{i}"] = ref_numbers[i-1] if i-1 < len(ref_numbers) else ""

                # Subject and body resolution (custom overrides on team take precedence, otherwise active template revision)
                subject_tmpl = team["custom_subject"] or active_subject
                body_tmpl = team["custom_body"] or active_body
                rendered_subject = EmailService.render_template(subject_tmpl, context)
                rendered_body = EmailService.render_template(body_tmpl, context)

                # CC / BCC resolution
                combined_cc = EmailService.parse_email_list(f"{active_global_cc} {team['cc_recipients'] or ''}")
                combined_bcc = EmailService.parse_email_list(f"{active_global_bcc} {team['bcc_recipients'] or ''}")

                # Attachments resolution
                attachments_list: List[Tuple[Path, str]] = []
                attachment_display_names: List[str] = []

                if camp_type == "certificate_distribution":
                    # Certificate attachments
                    for idx, c_info in enumerate(cert_files_info):
                        pos = c_info.get("position", idx + 1)
                        rel_path = c_info.get("relative_path")
                        if rel_path:
                            f_path = Path(rel_path)
                            if f_path.exists():
                                m_name = EmailService.clean_filename(participants[pos-1] if pos-1 < len(participants) else f"Member_{pos}")
                                clean_t_name = EmailService.clean_filename(team_name)
                                custom_filename = f"HackOSprint_{clean_t_name}_Member_{pos}_{m_name}.png"
                                attachments_list.append((f_path, custom_filename))
                                attachment_display_names.append(custom_filename)
                            else:
                                logger.warning(f"Certificate file missing on disk: {rel_path}")

                # Build Email Message
                msg = EmailService.build_email_message(
                    sender_name=smtp_config.get("sender_name", ""),
                    sender_email=smtp_config.get("sender_email", ""),
                    to_email=leader_email,
                    subject=rendered_subject,
                    body_text=rendered_body,
                    cc_emails=combined_cc,
                    bcc_emails=combined_bcc,
                    attachments=attachments_list
                )

                # Send execution with exact failure / uncertain categorization
                send_success = False
                is_uncertain = False
                error_msg = ""
                attempts = 0

                while attempts <= max_retries and not send_success and not is_uncertain:
                    attempts += 1
                    try:
                        SMTPService.send_single_message(
                            host=smtp_config["host"],
                            port=smtp_config["port"],
                            use_tls=smtp_config.get("use_tls", True),
                            use_ssl=smtp_config.get("use_ssl", False),
                            username=smtp_config.get("username", ""),
                            password=smtp_config.get("password", ""),
                            message=msg,
                            to_email=leader_email,
                            cc_emails=combined_cc,
                            bcc_emails=combined_bcc
                        )
                        send_success = True
                        state["consecutive_failures"] = 0
                    except (smtplib.SMTPServerDisconnected, ssl.SSLError) as disc_err:
                        # Server disconnected or dropped socket mid-flight.
                        # Message may or may not have been accepted by SMTP server.
                        # Strict Safety Rule: Categorize as DELIVERY_UNKNOWN. Never auto-resend!
                        is_uncertain = True
                        error_msg = f"Uncertain SMTP Outcome: Connection dropped during transmission ({str(disc_err)}). Requires manual review before retrying."
                        logger.error(f"Uncertain delivery outcome for recipient {leader_email}: {disc_err}")
                        break
                    except smtplib.SMTPAuthenticationError as auth_err:
                        error_msg = f"Fatal SMTP Authentication Error: {str(auth_err)}"
                        state["consecutive_failures"] = 999
                        break
                    except Exception as err:
                        error_msg = str(err)
                        logger.warning(f"Send attempt {attempts} failed for {leader_email}: {err}")
                        if attempts <= max_retries:
                            await asyncio.sleep(2.0 * attempts)

                # Determine terminal delivery status
                if send_success:
                    final_status = "SMTP_ACCEPTED"
                    cursor.execute("""
                    UPDATE teams 
                    SET delivery_status = 'SMTP_ACCEPTED', 
                        last_error = '', 
                        retry_authorized = 0,
                        delivery_timestamp = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """, (team_id,))
                    cursor.execute("UPDATE campaigns SET sent_count = sent_count + 1 WHERE id = ?", (campaign_id,))
                elif is_uncertain:
                    final_status = "DELIVERY_UNKNOWN"
                    cursor.execute("""
                    UPDATE teams 
                    SET delivery_status = 'DELIVERY_UNKNOWN', 
                        last_error = ?,
                        retry_authorized = 0,
                        delivery_timestamp = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """, (error_msg, team_id))
                    state["consecutive_failures"] += 1
                else:
                    final_status = "FAILED"
                    state["consecutive_failures"] += 1
                    cursor.execute("""
                    UPDATE teams 
                    SET delivery_status = 'FAILED', 
                        last_error = ?,
                        retry_authorized = 0,
                        delivery_timestamp = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """, (error_msg, team_id))
                    cursor.execute("UPDATE campaigns SET failed_count = failed_count + 1 WHERE id = ?", (campaign_id,))

                # Record in delivery_logs for audit
                cursor.execute("""
                INSERT INTO delivery_logs (
                    id, campaign_id, team_id, team_name, recipient_email,
                    cc_recipients, bcc_count, attachment_count, attachment_names_json,
                    status, error_message, retry_count, is_test, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP)
                """, (
                    str(uuid.uuid4()),
                    campaign_id,
                    team_id,
                    team_name,
                    leader_email,
                    ", ".join(combined_cc),
                    len(combined_bcc),
                    len(attachments_list),
                    json.dumps(attachment_display_names),
                    final_status,
                    error_msg,
                    attempts - 1 if attempts > 0 else 0
                ))
                conn.commit()

                # Delay between messages
                if delay_seconds > 0:
                    await asyncio.sleep(delay_seconds)

            # Final evaluation of campaign completion
            cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN delivery_status = 'SMTP_ACCEPTED' THEN 1 ELSE 0 END) as accepted,
                SUM(CASE WHEN delivery_status = 'FAILED' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN delivery_status = 'DELIVERY_UNKNOWN' THEN 1 ELSE 0 END) as uncertain,
                SUM(CASE WHEN delivery_status = 'PENDING' THEN 1 ELSE 0 END) as pending
            FROM teams 
            WHERE campaign_id = ?
            """, (campaign_id,))
            counts = cursor.fetchone()
            total_recs = counts["total"] or 0
            accepted_recs = counts["accepted"] or 0
            failed_recs = counts["failed"] or 0
            uncertain_recs = counts["uncertain"] or 0
            pending_recs = counts["pending"] or 0

            # Determine final campaign status
            cursor.execute("SELECT is_paused, is_cancelled FROM campaigns WHERE id = ?", (campaign_id,))
            final_check = cursor.fetchone()
            if final_check and final_check["is_cancelled"]:
                campaign_final_status = "cancelled"
            elif final_check and final_check["is_paused"]:
                campaign_final_status = "paused"
            elif accepted_recs == total_recs and total_recs > 0:
                campaign_final_status = "completed"
            elif state["consecutive_failures"] >= 3:
                campaign_final_status = "failed"
            elif pending_recs > 0 or uncertain_recs > 0:
                campaign_final_status = "paused"
            else:
                campaign_final_status = "completed"

            state["status"] = campaign_final_status
            state["current_team"] = None

            cursor.execute("""
            UPDATE campaigns 
            SET status = ?, is_paused = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
            """, (campaign_final_status, 1 if campaign_final_status in ["paused", "interrupted"] else 0, campaign_id))
            conn.commit()

            log_campaign_audit(
                campaign_id=campaign_id,
                event_type="CAMPAIGN_EXECUTION_FINISHED",
                details={
                    "final_status": campaign_final_status,
                    "accepted": accepted_recs,
                    "failed": failed_recs,
                    "uncertain": uncertain_recs,
                    "pending": pending_recs
                }
            )

        except Exception as e:
            logger.exception(f"Unexpected error in CampaignRunner: {e}")
            state["status"] = "failed"
            state["error_message"] = str(e)
            try:
                conn.execute("UPDATE campaigns SET status = 'failed', is_paused = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (campaign_id,))
                conn.commit()
            except Exception:
                pass
        finally:
            conn.close()

    @classmethod
    def pause_campaign(cls, campaign_id: str, reviewer: str = "Admin") -> bool:
        """Sets is_paused flag in database and in-memory state for safe checkpoint pause."""
        conn = get_db_connection()
        try:
            from backend.app.core.database import log_campaign_audit
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE campaigns 
            SET is_paused = 1, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ? AND status = 'sending';
            """, (campaign_id,))
            conn.commit()
            if campaign_id in campaign_tasks:
                campaign_tasks[campaign_id]["is_paused"] = True

            log_campaign_audit(
                campaign_id=campaign_id,
                event_type="PAUSE_REQUESTED",
                details={"requested_by": reviewer},
                reviewer=reviewer
            )
            return True
        finally:
            conn.close()

    @classmethod
    def resume_campaign(cls, campaign_id: str, reviewer: str = "Admin") -> bool:
        """Clears is_paused flag in database and in-memory state."""
        conn = get_db_connection()
        try:
            from backend.app.core.database import log_campaign_audit
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE campaigns 
            SET is_paused = 0, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ? AND status IN ('paused', 'interrupted', 'prepared', 'failed');
            """, (campaign_id,))
            conn.commit()
            if campaign_id in campaign_tasks:
                campaign_tasks[campaign_id]["is_paused"] = False

            log_campaign_audit(
                campaign_id=campaign_id,
                event_type="RESUME_REQUESTED",
                details={"requested_by": reviewer},
                reviewer=reviewer
            )
            return True
        finally:
            conn.close()

    @classmethod
    def cancel_campaign(cls, campaign_id: str, reviewer: str = "Admin") -> bool:
        """Sets is_cancelled flag in database and in-memory state."""
        conn = get_db_connection()
        try:
            from backend.app.core.database import log_campaign_audit
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE campaigns 
            SET is_cancelled = 1, status = 'cancelled', updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?;
            """, (campaign_id,))
            conn.commit()
            if campaign_id in campaign_tasks:
                campaign_tasks[campaign_id]["is_cancelled"] = True

            log_campaign_audit(
                campaign_id=campaign_id,
                event_type="CANCEL_REQUESTED",
                details={"requested_by": reviewer},
                reviewer=reviewer
            )
            return True
        finally:
            conn.close()


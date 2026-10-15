import sqlite3
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

def get_db_connection() -> sqlite3.Connection:
    """Returns a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(settings.DATABASE_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db():
    """Initializes tables and default data if they do not exist."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Campaigns table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS campaigns (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            total_teams INTEGER DEFAULT 0,
            sent_count INTEGER DEFAULT 0,
            failed_count INTEGER DEFAULT 0,
            config_json TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Teams table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id TEXT PRIMARY KEY,
            campaign_id TEXT NOT NULL,
            row_index INTEGER NOT NULL,
            team_name TEXT NOT NULL,
            team_identifier TEXT,
            leader_name TEXT NOT NULL,
            leader_email TEXT NOT NULL,
            participant_names_json TEXT DEFAULT '[]',
            ref_numbers_json TEXT DEFAULT '[]',
            certificate_files_json TEXT DEFAULT '[]',
            validation_status TEXT NOT NULL DEFAULT 'PENDING',
            validation_errors_json TEXT DEFAULT '[]',
            manual_override INTEGER DEFAULT 0,
            custom_subject TEXT,
            custom_body TEXT,
            cc_recipients TEXT DEFAULT '',
            bcc_recipients TEXT DEFAULT '',
            FOREIGN KEY (campaign_id) REFERENCES campaigns (id) ON DELETE CASCADE
        );
        """)

        # Delivery Logs table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS delivery_logs (
            id TEXT PRIMARY KEY,
            campaign_id TEXT NOT NULL,
            team_id TEXT,
            team_name TEXT,
            recipient_email TEXT NOT NULL,
            cc_recipients TEXT DEFAULT '',
            bcc_count INTEGER DEFAULT 0,
            attachment_count INTEGER DEFAULT 0,
            attachment_names_json TEXT DEFAULT '[]',
            status TEXT NOT NULL,
            error_message TEXT DEFAULT '',
            retry_count INTEGER DEFAULT 0,
            is_test INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Email Templates table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS templates (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            is_default INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Upload Sessions table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS upload_sessions (
            id TEXT PRIMARY KEY,
            excel_filename TEXT,
            excel_path TEXT,
            sheet_names_json TEXT DEFAULT '[]',
            selected_sheet TEXT,
            detected_columns_json TEXT DEFAULT '[]',
            column_mapping_json TEXT DEFAULT '{}',
            zip_batches_json TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Approval Overrides table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS approval_overrides (
            id TEXT PRIMARY KEY,
            team_identifier TEXT,
            row_index INTEGER,
            team_name TEXT,
            status TEXT NOT NULL DEFAULT 'OVERRIDE_APPROVED',
            reviewer TEXT DEFAULT 'Admin Reviewer',
            reason TEXT NOT NULL,
            certificate_filenames_json TEXT DEFAULT '[]',
            certificate_mapping_hash TEXT,
            detected_mismatch TEXT,
            original_reference TEXT,
            actual_reference TEXT,
            leader_name TEXT,
            leader_email TEXT,
            cc_recipients TEXT DEFAULT '',
            bcc_recipients TEXT DEFAULT '',
            custom_subject TEXT,
            custom_body TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Template Revisions table (immutable audit history of template modifications)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS template_revisions (
            id TEXT PRIMARY KEY,
            campaign_id TEXT NOT NULL,
            revision_number INTEGER NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            global_cc TEXT DEFAULT '',
            global_bcc TEXT DEFAULT '',
            created_by TEXT DEFAULT 'Admin',
            change_summary TEXT DEFAULT '',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (campaign_id) REFERENCES campaigns (id) ON DELETE CASCADE
        );
        """)

        # Campaign Audit Logs table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS campaign_audit_logs (
            id TEXT PRIMARY KEY,
            campaign_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            details_json TEXT DEFAULT '{}',
            reviewer TEXT DEFAULT 'System',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (campaign_id) REFERENCES campaigns (id) ON DELETE CASCADE
        );
        """)

        # Safe migrations: Check and add columns to campaigns table
        cursor.execute("PRAGMA table_info(campaigns);")
        camp_cols = {row["name"] for row in cursor.fetchall()}
        if "campaign_type" not in camp_cols:
            cursor.execute("ALTER TABLE campaigns ADD COLUMN campaign_type TEXT DEFAULT 'certificate_distribution';")
        if "is_paused" not in camp_cols:
            cursor.execute("ALTER TABLE campaigns ADD COLUMN is_paused INTEGER DEFAULT 0;")
        if "is_cancelled" not in camp_cols:
            cursor.execute("ALTER TABLE campaigns ADD COLUMN is_cancelled INTEGER DEFAULT 0;")
        if "current_template_revision" not in camp_cols:
            cursor.execute("ALTER TABLE campaigns ADD COLUMN current_template_revision INTEGER DEFAULT 1;")
        if "snapshot_json" not in camp_cols:
            cursor.execute("ALTER TABLE campaigns ADD COLUMN snapshot_json TEXT DEFAULT '{}';")

        # Safe migrations: Check and add columns to teams table (recipient delivery ledger)
        cursor.execute("PRAGMA table_info(teams);")
        team_cols = {row["name"] for row in cursor.fetchall()}
        if "recipient_id" not in team_cols:
            cursor.execute("ALTER TABLE teams ADD COLUMN recipient_id TEXT;")
        if "normalized_email" not in team_cols:
            cursor.execute("ALTER TABLE teams ADD COLUMN normalized_email TEXT;")
        if "delivery_status" not in team_cols:
            cursor.execute("ALTER TABLE teams ADD COLUMN delivery_status TEXT DEFAULT 'PENDING';")
        if "delivery_attempts" not in team_cols:
            cursor.execute("ALTER TABLE teams ADD COLUMN delivery_attempts INTEGER DEFAULT 0;")
        if "last_error" not in team_cols:
            cursor.execute("ALTER TABLE teams ADD COLUMN last_error TEXT DEFAULT '';")
        if "template_revision_used" not in team_cols:
            cursor.execute("ALTER TABLE teams ADD COLUMN template_revision_used INTEGER DEFAULT 1;")
        if "delivery_timestamp" not in team_cols:
            cursor.execute("ALTER TABLE teams ADD COLUMN delivery_timestamp TIMESTAMP;")
        if "retry_authorized" not in team_cols:
            cursor.execute("ALTER TABLE teams ADD COLUMN retry_authorized INTEGER DEFAULT 0;")

        # Populate normalized_email and recipient_id for existing rows if needed
        cursor.execute("""
        UPDATE teams 
        SET normalized_email = LOWER(TRIM(leader_email)),
            recipient_id = COALESCE(team_identifier, id)
        WHERE normalized_email IS NULL OR recipient_id IS NULL;
        """)

        # Sync existing delivery_logs status to teams.delivery_status if teams still show PENDING
        cursor.execute("""
        UPDATE teams
        SET delivery_status = 'SMTP_ACCEPTED'
        WHERE delivery_status = 'PENDING'
          AND id IN (SELECT team_id FROM delivery_logs WHERE status IN ('SENT', 'SMTP_ACCEPTED'));
        """)

        # Clean restart recovery: Any campaign marked 'sending' when the app initializes was interrupted mid-flight
        cursor.execute("SELECT id FROM campaigns WHERE status = 'sending';")
        orphaned_campaigns = cursor.fetchall()
        for o_camp in orphaned_campaigns:
            c_id = o_camp["id"]
            cursor.execute("""
            UPDATE campaigns 
            SET status = 'interrupted', is_paused = 1, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?;
            """, (c_id,))
            
            # Any team marked 'IN_PROGRESS' when server stopped is uncertain
            cursor.execute("""
            UPDATE teams 
            SET delivery_status = 'DELIVERY_UNKNOWN', 
                last_error = 'Interrupted: Server stopped while delivery was in progress' 
            WHERE campaign_id = ? AND delivery_status = 'IN_PROGRESS';
            """, (c_id,))

            import uuid
            cursor.execute("""
            INSERT INTO campaign_audit_logs (id, campaign_id, event_type, details_json, reviewer, created_at)
            VALUES (?, ?, 'SYSTEM_INTERRUPTED_RECOVERY', ?, 'System', CURRENT_TIMESTAMP);
            """, (str(uuid.uuid4()), c_id, json.dumps({"reason": "Application restarted while campaign was running. Transitioned to interrupted."})))

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_teams_campaign ON teams(campaign_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_teams_delivery_status ON teams(campaign_id, delivery_status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_teams_norm_email ON teams(campaign_id, normalized_email);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_campaign ON delivery_logs(campaign_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_team ON delivery_logs(team_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_overrides_team_id ON approval_overrides(team_identifier);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_overrides_row_idx ON approval_overrides(row_index);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_revisions_campaign ON template_revisions(campaign_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_campaign_audit_campaign ON campaign_audit_logs(campaign_id);")

        # Insert default template if none exists
        cursor.execute("SELECT COUNT(*) as count FROM templates WHERE is_default = 1;")
        row = cursor.fetchone()
        if row and row["count"] == 0:
            default_id = "default-hackosprint"
            default_name = "Hack-O-Sprint 4.0 Default"
            default_subject = "Congratulations on Your Selection Among the Top Teams | Hack-O-Sprint 4.0"
            default_body = """Dear {{leader_name}},

Congratulations to you and your entire team, {{team_name}}, on being selected among the Top Teams in Hack-O-Sprint 4.0 – SIH Internal Round 2026, organized by the IEEE Student Branch and IEEE Computer Society Student Branch Chapter, IIIT Bhopal.

Your selection reflects your team's effort, creativity, and commitment to developing innovative solutions. We appreciate your participation and wish all six team members the very best for the next stages of the Smart India Hackathon journey.

Please find attached the participation certificates for all six members of your team.

Congratulations once again, and best wishes for your future endeavours!

Regards,  
IEEE Student Branch & IEEE Computer Society SBC  
Indian Institute of Information Technology, Bhopal"""
            cursor.execute("""
            INSERT INTO templates (id, name, subject, body, is_default, created_at)
            VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP);
            """, (default_id, default_name, default_subject, default_body))

        conn.commit()
        logger.info("Database initialized successfully.")
    finally:
        conn.close()


def save_approval_override(override_data: Dict[str, Any]) -> Dict[str, Any]:
    """Persists or updates an approval override in SQLite."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        team_identifier = (override_data.get("team_identifier") or "").strip()
        row_index = override_data.get("row_index")
        
        # Determine stable identifier
        if team_identifier:
            override_id = f"ovr_{team_identifier}"
        elif row_index is not None:
            override_id = f"ovr_row_{row_index}"
        else:
            override_id = f"ovr_{override_data.get('team_id', 'unknown')}"

        cert_files = override_data.get("certificate_filenames") or []
        cert_hash = ",".join(cert_files)

        cursor.execute("""
        INSERT INTO approval_overrides (
            id, team_identifier, row_index, team_name, status, reviewer,
            reason, certificate_filenames_json, certificate_mapping_hash,
            detected_mismatch, original_reference, actual_reference,
            leader_name, leader_email, cc_recipients, bcc_recipients,
            custom_subject, custom_body, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET
            status = excluded.status,
            reviewer = excluded.reviewer,
            reason = excluded.reason,
            certificate_filenames_json = excluded.certificate_filenames_json,
            certificate_mapping_hash = excluded.certificate_mapping_hash,
            detected_mismatch = excluded.detected_mismatch,
            original_reference = excluded.original_reference,
            actual_reference = excluded.actual_reference,
            leader_name = excluded.leader_name,
            leader_email = excluded.leader_email,
            cc_recipients = excluded.cc_recipients,
            bcc_recipients = excluded.bcc_recipients,
            custom_subject = excluded.custom_subject,
            custom_body = excluded.custom_body,
            updated_at = CURRENT_TIMESTAMP
        """, (
            override_id,
            team_identifier,
            row_index,
            override_data.get("team_name"),
            override_data.get("status", "OVERRIDE_APPROVED"),
            override_data.get("reviewer", "Admin Reviewer"),
            override_data.get("reason", "Approved by administrator"),
            json.dumps(cert_files),
            cert_hash,
            override_data.get("detected_mismatch", ""),
            override_data.get("original_reference", ""),
            override_data.get("actual_reference", ""),
            override_data.get("leader_name"),
            override_data.get("leader_email"),
            override_data.get("cc_recipients", ""),
            override_data.get("bcc_recipients", ""),
            override_data.get("custom_subject"),
            override_data.get("custom_body")
        ))
        conn.commit()

        # Fetch and return the saved record
        cursor.execute("SELECT * FROM approval_overrides WHERE id = ?", (override_id,))
        row = cursor.fetchone()
        if row:
            res = dict(row)
            res["certificate_filenames"] = json.loads(res.get("certificate_filenames_json") or "[]")
            return res
        return override_data
    finally:
        conn.close()

def get_all_approval_overrides() -> Dict[str, Dict[str, Any]]:
    """Returns a dict mapping stable keys (team_identifier and f'team-{row_index}') to override dicts."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM approval_overrides")
        rows = cursor.fetchall()
        result: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            data = dict(r)
            data["certificate_filenames"] = json.loads(data.get("certificate_filenames_json") or "[]")
            data["approve_override"] = (data.get("status") == "OVERRIDE_APPROVED")
            
            # Map by override id
            result[data["id"]] = data
            
            # Map by team_identifier if present
            if data.get("team_identifier"):
                result[data["team_identifier"]] = data
                
            # Map by team-{row_index} if present
            if data.get("row_index") is not None:
                result[f"team-{data['row_index']}"] = data
                
        return result
    finally:
        conn.close()

def delete_approval_override(override_id: str) -> bool:
    """Deletes an approval override record by its ID or identifier."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
        DELETE FROM approval_overrides
        WHERE id = ? OR team_identifier = ? OR id = ?
        """, (override_id, override_id, f"ovr_{override_id}"))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()

def log_campaign_audit(
    campaign_id: str,
    event_type: str,
    details: Dict[str, Any],
    reviewer: str = "System",
    conn: Optional[sqlite3.Connection] = None
) -> str:
    """Logs an immutable campaign audit event in SQLite."""
    own_conn = False
    if conn is None:
        conn = get_db_connection()
        own_conn = True
    try:
        import uuid
        event_id = str(uuid.uuid4())
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO campaign_audit_logs (id, campaign_id, event_type, details_json, reviewer, created_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (event_id, campaign_id, event_type, json.dumps(details), reviewer))
        if own_conn:
            conn.commit()
        return event_id
    finally:
        if own_conn:
            conn.close()

def get_campaign_audit_logs(campaign_id: str) -> List[Dict[str, Any]]:
    """Returns all audit events for a campaign ordered chronologically."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT * FROM campaign_audit_logs 
        WHERE campaign_id = ? 
        ORDER BY created_at ASC
        """, (campaign_id,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["details"] = json.loads(d.get("details_json") or "{}")
            except Exception:
                d["details"] = {}
            result.append(d)
        return result
    finally:
        conn.close()

def create_template_revision(
    campaign_id: str,
    subject: str,
    body: str,
    global_cc: str = "",
    global_bcc: str = "",
    created_by: str = "Admin",
    change_summary: str = "",
    set_as_active: bool = True,
    conn: Optional[sqlite3.Connection] = None
) -> Dict[str, Any]:
    """Creates an immutable template revision for a campaign."""
    own_conn = False
    if conn is None:
        conn = get_db_connection()
        own_conn = True
    try:
        import uuid
        cursor = conn.cursor()
        # Get next revision number
        cursor.execute("SELECT COALESCE(MAX(revision_number), 0) + 1 AS next_rev FROM template_revisions WHERE campaign_id = ?", (campaign_id,))
        next_rev = cursor.fetchone()["next_rev"]
        
        rev_id = str(uuid.uuid4())
        if set_as_active:
            cursor.execute("UPDATE template_revisions SET is_active = 0 WHERE campaign_id = ?", (campaign_id,))
            cursor.execute("UPDATE campaigns SET current_template_revision = ? WHERE id = ?", (next_rev, campaign_id))

        cursor.execute("""
        INSERT INTO template_revisions (
            id, campaign_id, revision_number, subject, body, global_cc, global_bcc,
            created_by, change_summary, is_active, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (rev_id, campaign_id, next_rev, subject, body, global_cc, global_bcc, created_by, change_summary, 1 if set_as_active else 0))

        log_campaign_audit(
            campaign_id=campaign_id,
            event_type="TEMPLATE_REVISION_CREATED",
            details={
                "revision_number": next_rev,
                "revision_id": rev_id,
                "subject": subject,
                "change_summary": change_summary,
                "is_active": set_as_active
            },
            reviewer=created_by,
            conn=conn
        )

        if own_conn:
            conn.commit()
        return {
            "id": rev_id,
            "campaign_id": campaign_id,
            "revision_number": next_rev,
            "subject": subject,
            "body": body,
            "global_cc": global_cc,
            "global_bcc": global_bcc,
            "created_by": created_by,
            "change_summary": change_summary,
            "is_active": set_as_active
        }
    finally:
        if own_conn:
            conn.close()

def get_template_revisions(campaign_id: str) -> List[Dict[str, Any]]:
    """Returns all revisions of a campaign's template."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM template_revisions WHERE campaign_id = ? ORDER BY revision_number ASC", (campaign_id,))
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

def get_active_template_revision(campaign_id: str) -> Optional[Dict[str, Any]]:
    """Returns current active template revision for campaign."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM template_revisions WHERE campaign_id = ? AND is_active = 1 ORDER BY revision_number DESC LIMIT 1", (campaign_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

# Auto-initialize database schema on startup
try:
    init_db()
except Exception as _e:
    logger.warning(f"Initial schema init deferred: {_e}")


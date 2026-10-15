import io
import csv
import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Response, status
from backend.app.core.database import get_db_connection
from backend.app.schemas.log import DeliveryLogItem, DeliveryLogListResponse

router = APIRouter(prefix="/api/logs", tags=["Logs & Exports"])

@router.get("", response_model=DeliveryLogListResponse)
async def get_delivery_logs(
    campaign_id: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = "SELECT * FROM delivery_logs WHERE 1=1"
        params = []

        if campaign_id:
            query += " AND campaign_id = ?"
            params.append(campaign_id)
        if status_filter and status_filter.upper() != "ALL":
            query += " AND status = ?"
            params.append(status_filter.upper())
        if search:
            query += " AND (team_name LIKE ? OR recipient_email LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        # Count total
        count_query = query.replace("SELECT *", "SELECT COUNT(*) as cnt")
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()["cnt"]

        # Fetch page
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor.execute(query, params)
        rows = cursor.fetchall()

        items = []
        for r in rows:
            attach_names = json.loads(r["attachment_names_json"] or "[]")
            items.append(DeliveryLogItem(
                id=r["id"],
                campaign_id=r["campaign_id"],
                team_id=r["team_id"],
                team_name=r["team_name"],
                recipient_email=r["recipient_email"],
                cc_recipients=r["cc_recipients"] or "",
                bcc_count=r["bcc_count"] or 0,
                attachment_count=r["attachment_count"] or 0,
                attachment_names=attach_names,
                status=r["status"],
                error_message=r["error_message"] or "",
                retry_count=r["retry_count"] or 0,
                is_test=bool(r["is_test"]),
                created_at=str(r["created_at"])
            ))

        return DeliveryLogListResponse(total=total_count, items=items)
    finally:
        conn.close()


@router.get("/stats")
async def get_overview_stats():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(total_teams) as total, SUM(sent_count) as sent, SUM(failed_count) as failed FROM campaigns")
        row = cursor.fetchone()
        
        total_teams = row["total"] or 0
        total_sent = row["sent"] or 0
        total_failed = row["failed"] or 0
        pending = max(0, total_teams - total_sent - total_failed)

        cursor.execute("SELECT COUNT(*) as cnt FROM campaigns WHERE status = 'sending'")
        active_campaigns = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) as cnt FROM delivery_logs WHERE is_test = 1")
        total_tests = cursor.fetchone()["cnt"]

        return {
            "total_teams": total_teams,
            "total_sent": total_sent,
            "total_failed": total_failed,
            "pending": pending,
            "active_campaigns": active_campaigns,
            "total_tests": total_tests
        }
    finally:
        conn.close()


@router.get("/export/{export_type}")
async def export_logs_csv(export_type: str, campaign_id: Optional[str] = None):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = "SELECT * FROM delivery_logs WHERE 1=1"
        params = []

        if campaign_id:
            query += " AND campaign_id = ?"
            params.append(campaign_id)

        if export_type == "sent":
            query += " AND status = 'SENT'"
        elif export_type == "failed":
            query += " AND status = 'FAILED'"

        query += " ORDER BY created_at DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Timestamp",
            "Log ID",
            "Campaign ID",
            "Team ID",
            "Team Name",
            "Recipient Email",
            "CC Recipients",
            "BCC Count",
            "Attachment Count",
            "Status",
            "Error Details",
            "Retry Count",
            "Is Test"
        ])

        for r in rows:
            writer.writerow([
                r["created_at"],
                r["id"],
                r["campaign_id"],
                r["team_id"],
                r["team_name"],
                r["recipient_email"],
                r["cc_recipients"],
                r["bcc_count"],
                r["attachment_count"],
                r["status"],
                r["error_message"],
                r["retry_count"],
                "YES" if r["is_test"] else "NO"
            ])

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=CertiMail_Delivery_Logs_{export_type}.csv"}
        )
    finally:
        conn.close()

import pytest
import sqlite3
import json
from pathlib import Path
from unittest.mock import patch
from backend.app.schemas.mapping import (
    ZipBatchInfo,
    ManualOverrideRequest,
    ValidationReportResponse,
    TeamMappingItem
)
from backend.app.services.matching_engine import MatchingEngine
from backend.app.core.database import (
    get_db_connection,
    save_approval_override,
    get_all_approval_overrides,
    delete_approval_override,
    init_db
)
from backend.app.api.session_store import SessionStore
from backend.app.api.routes_mapping import submit_manual_override
from fastapi import HTTPException

@pytest.fixture(autouse=True)
def clean_db():
    init_db()
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM approval_overrides;")
        conn.commit()
    finally:
        conn.close()
    yield
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM approval_overrides;")
        conn.commit()
    finally:
        conn.close()

def create_mock_batches(tmp_path, cert_numbers=None):
    if cert_numbers is None:
        cert_numbers = [1, 2, 3]
    batches_dict = {pos: {} for pos in range(1, 7)}
    for pos in range(1, 7):
        for num in cert_numbers:
            p = tmp_path / f"batch_{pos}_{num}.png"
            p.write_bytes(b"dummy")
            batches_dict[pos][num] = p

    batch_infos = [
        ZipBatchInfo(position=p, batch_id=f"b_{p}", filename=f"b_{p}.zip", file_count=len(cert_numbers))
        for p in range(1, 7)
    ]
    return batches_dict, batch_infos

@pytest.mark.asyncio
async def test_complete_reference_override_lifecycle(tmp_path):
    batches_dict, batch_infos = create_mock_batches(tmp_path, cert_numbers=[1, 2, 3])
    
    # 1. A team starts with an unresolved reference mismatch:
    # Team 1 has reference number "99" which does not match certificate #1
    teams_data = [
        {
            "row_index": 1,
            "team_name": "Team Delta",
            "team_identifier": "HOS-T001",
            "leader_name": "Lead One",
            "leader_email": "lead1@example.com",
            "participants": [f"M{p}" for p in range(1, 7)],
            "ref_numbers": ["99", "HOS-2026-001-2", "HOS-2026-001-3", "HOS-2026-001-4", "HOS-2026-001-5", "HOS-2026-001-6"]
        },
        {
            "row_index": 2,
            "team_name": "Team Unrelated Error",
            "team_identifier": "HOS-T002",
            "leader_name": "Lead Two",
            "leader_email": "invalid-email-format", # Unrelated error!
            "participants": [f"M{p}" for p in range(1, 7)],
            "ref_numbers": [f"HOS-2026-002-{p}" for p in range(1, 7)]
        }
    ]

    session_id = "test-session-lifecycle"
    session = SessionStore.get_session(session_id)
    session["teams_data"] = teams_data
    session["batches_dict"] = batches_dict
    session["batch_infos"] = batch_infos
    session["numbering_offset"] = 0
    session["overrides"] = {}

    # Step 1: Initial validation -> Team 1 has REFERENCE_MISMATCH, Team 2 has INVALID EMAIL
    initial_report = MatchingEngine.match_teams(teams_data, batches_dict, batch_infos)
    assert initial_report.teams[0].validation_status == "REFERENCE_MISMATCH"
    assert initial_report.teams[0].manual_override is False
    assert initial_report.teams[1].validation_status == "INVALID EMAIL"
    assert initial_report.summary.can_send is False
    assert initial_report.summary.reference_mismatches >= 1

    # Step 2: The user approves the override with explicit reason and reviewer
    cert_files = [f"batch_{pos}_1.png" for pos in range(1, 7)]
    override_req = ManualOverrideRequest(
        session_id=session_id,
        team_id="team-1",
        team_identifier="HOS-T001",
        row_index=1,
        status="OVERRIDE_APPROVED",
        reviewer="Prof. Kumar, IEEE Counselor",
        reason="Verified offline registration sheet; ref 99 was an administrative typo for cert 1",
        certificate_filenames=cert_files,
        approve_override=True
    )

    # Step 3: Backend route handler persists the override to SQLite
    res_report = await submit_manual_override(override_req)

    # Step 4: Revalidation changes status to OVERRIDE_APPROVED
    assert res_report.teams[0].validation_status == "OVERRIDE_APPROVED"
    assert res_report.teams[0].manual_override is True
    assert res_report.teams[0].override_reviewer == "Prof. Kumar, IEEE Counselor"
    assert "ref 99" in res_report.teams[0].override_reason

    # Step 5: The team mapping item preserves the original detected reference mismatch
    assert res_report.teams[0].detected_reference_mismatch is not None
    assert "99" in res_report.teams[0].detected_reference_mismatch

    # Step 6: Refreshing page / retrieving from SQLite preserves the approved state
    stored_overrides = get_all_approval_overrides()
    assert "HOS-T001" in stored_overrides
    assert stored_overrides["HOS-T001"]["status"] == "OVERRIDE_APPROVED"
    assert stored_overrides["HOS-T001"]["reason"] == "Verified offline registration sheet; ref 99 was an administrative typo for cert 1"

    # Step 7: Restarting application (wiping in-memory SessionStore) preserves approved state
    SessionStore.sessions.clear()
    fresh_session = SessionStore.get_session("brand-new-session")
    fresh_session["teams_data"] = teams_data
    fresh_session["batches_dict"] = batches_dict
    fresh_session["batch_infos"] = batch_infos
    fresh_report = MatchingEngine.match_teams(teams_data, batches_dict, batch_infos)
    assert fresh_report.teams[0].validation_status == "OVERRIDE_APPROVED"
    assert fresh_report.teams[0].manual_override is True

    # Step 8: Validation CSV reflects the approved override accurately
    csv_content = MatchingEngine.generate_csv_report(fresh_report.teams)
    assert "OVERRIDE_APPROVED" in csv_content
    assert "Prof. Kumar, IEEE Counselor" in csv_content
    assert "Verified offline registration sheet" in csv_content

    # Step 9: Campaign sending barrier permits the reviewed mismatch,
    # but continues to block unrelated unresolved errors (Team 2 invalid email)
    assert fresh_report.summary.can_send is False # Team 2 still has invalid email!
    assert fresh_report.summary.valid_teams == 1 # Team 1 is valid via approved override
    assert fresh_report.summary.error_teams == 1 # Team 2 is invalid

    # Now resolve Team 2's email
    teams_data[1]["leader_email"] = "valid.lead2@example.com"
    full_valid_report = MatchingEngine.match_teams(teams_data, batches_dict, batch_infos)
    assert full_valid_report.teams[0].validation_status == "OVERRIDE_APPROVED"
    assert full_valid_report.teams[1].validation_status == "VALID"
    assert full_valid_report.summary.can_send is True # Unlocked because only approved override + valid remain!

    # Step 10: Changing the certificate mapping invalidates the relevant override
    # If certificate for position 1 changes to a different file, override must be revoked
    altered_batches = {pos: dict(batches_dict[pos]) for pos in range(1, 7)}
    # Change pos 1 to use a different filename "batch_1_2.png" instead of "batch_1_1.png"
    altered_teams_data = [dict(teams_data[0])]
    # Manually re-match with offset or changed cert filename
    # Override stored mapping was batch_1_1.png..
    # Re-running with a changed mapping where files don't match the approved hash
    tampered_override = dict(stored_overrides["HOS-T001"])
    tampered_override["certificate_mapping_hash"] = "different_mapping_1.png,different_2.png"
    revoked_report = MatchingEngine.match_teams(
        altered_teams_data,
        batches_dict,
        batch_infos,
        existing_overrides={"HOS-T001": tampered_override}
    )
    assert revoked_report.teams[0].validation_status == "OVERRIDE_REVOKED"
    assert revoked_report.teams[0].manual_override is False
    assert revoked_report.summary.can_send is False

    # Step 11: A failed database write raises HTTP 500 and does not produce success
    sess = SessionStore.get_session(session_id)
    sess["teams_data"] = teams_data
    sess["batches_dict"] = batches_dict
    sess["batch_infos"] = batch_infos

    with patch("backend.app.core.database.save_approval_override", side_effect=sqlite3.OperationalError("Disk I/O error")):
        with pytest.raises(HTTPException) as exc_info:
            await submit_manual_override(override_req)
        assert exc_info.value.status_code == 500
        assert "Database write failure" in exc_info.value.detail

    # Step 12: Duplicate or repeated save requests do not create duplicate or inconsistent state
    # Calling submit_manual_override multiple times updates existing record idempotently
    repeat_report1 = await submit_manual_override(override_req)
    repeat_report2 = await submit_manual_override(override_req)
    assert repeat_report1.teams[0].validation_status == "OVERRIDE_APPROVED"
    assert repeat_report2.teams[0].validation_status == "OVERRIDE_APPROVED"
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM approval_overrides WHERE team_identifier = 'HOS-T001'")
        assert cur.fetchone()[0] == 1 # Exactly one record, no duplicates!
    finally:
        conn.close()

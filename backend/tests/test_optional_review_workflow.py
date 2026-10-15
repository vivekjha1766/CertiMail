import pytest
import sqlite3
import json
import uuid
from pathlib import Path
from fastapi import HTTPException

from backend.app.schemas.mapping import (
    ZipBatchInfo,
    AcknowledgeMismatchesRequest,
    ResetMismatchesRequest,
    ManualOverrideRequest,
    ValidationReportResponse
)
from backend.app.schemas.campaign import CampaignCreate
from backend.app.services.matching_engine import MatchingEngine
from backend.app.core.database import (
    get_db_connection,
    init_db
)
from backend.app.api.session_store import SessionStore
from backend.app.api.routes_mapping import (
    acknowledge_mismatches,
    reset_mismatch_acknowledgement,
    submit_manual_override
)
from backend.app.api.routes_campaigns import create_campaign

@pytest.fixture(autouse=True)
def clean_db():
    init_db()
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM approval_overrides;")
        conn.execute("DELETE FROM delivery_logs;")
        conn.execute("DELETE FROM teams;")
        conn.execute("DELETE FROM campaigns;")
        conn.commit()
    finally:
        conn.close()
    yield
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM approval_overrides;")
        conn.execute("DELETE FROM delivery_logs;")
        conn.execute("DELETE FROM teams;")
        conn.execute("DELETE FROM campaigns;")
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
            p.write_bytes(b"mock_certificate_data")
            batches_dict[pos][num] = p

    batch_infos = [
        ZipBatchInfo(position=p, batch_id=f"b_{p}", filename=f"b_{p}.zip", file_count=len(cert_numbers))
        for p in range(1, 7)
    ]
    return batches_dict, batch_infos

def create_mock_teams_data():
    return [
        {
            "row_index": 1,
            "team_name": "Alpha Pioneers",
            "team_identifier": "ALPHA-01",
            "leader_name": "Alice Lead",
            "leader_email": "alice@example.com",
            "participants": ["Alice", "Bob", "Charlie", "David", "Eve", "Frank"],
            # Row 1 matches certificate #1
            "ref_numbers": ["REF-001", "REF-001", "REF-001", "REF-001", "REF-001", "REF-001"]
        },
        {
            "row_index": 2,
            "team_name": "Beta Hackers",
            "team_identifier": "BETA-02",
            "leader_name": "Bob Lead",
            "leader_email": "bob@example.com",
            "participants": ["Member 1", "Member 2", "Member 3", "Member 4", "Member 5", "Member 6"],
            # Row 2 receives cert #2, but sheet has REF-999 (intentional reference mismatch)
            "ref_numbers": ["REF-999", "REF-999", "REF-999", "REF-999", "REF-999", "REF-999"]
        },
        {
            "row_index": 3,
            "team_name": "Gamma Devs",
            "team_identifier": "GAMMA-03",
            "leader_name": "Charlie Lead",
            "leader_email": "charlie@example.com",
            "participants": ["G1", "G2", "G3", "G4", "G5", "G6"],
            # Row 3 receives cert #3, but sheet has REF-888 (intentional reference mismatch)
            "ref_numbers": ["REF-888", "REF-888", "REF-888", "REF-888", "REF-888", "REF-888"]
        }
    ]

# 1. Mapper produces exactly the same assignments as before this change
def test_mapper_assignments_unchanged_before_and_after(tmp_path):
    batches_dict, batch_infos = create_mock_batches(tmp_path, cert_numbers=[1, 2, 3])
    teams_data = create_mock_teams_data()

    # Baseline mapping without Option A acknowledgement
    baseline = MatchingEngine.match_teams(
        teams_data=teams_data,
        batches_dict=batches_dict,
        batch_infos=batch_infos,
        numbering_offset=0,
        mismatch_acknowledgement=None
    )

    # Mapping with Option A acknowledgement
    ack_dict = {
        "policy": "PROCEED_WITH_CURRENT_MAPPING",
        "reviewer": "Audit Admin",
        "reason": "Verified numbering layout",
        "confirmed": True
    }
    with_option_a = MatchingEngine.match_teams(
        teams_data=teams_data,
        batches_dict=batches_dict,
        batch_infos=batch_infos,
        numbering_offset=0,
        mismatch_acknowledgement=ack_dict
    )

    assert len(baseline.teams) == len(with_option_a.teams) == 3
    for t_base, t_opt_a in zip(baseline.teams, with_option_a.teams):
        # Certificate filenames and count must be identical
        assert [c.filename for c in t_base.certificate_files] == [c.filename for c in t_opt_a.certificate_files]
        # Certificate positions and paths must match exactly
        assert [c.position for c in t_base.certificate_files] == [c.position for c in t_opt_a.certificate_files]
        # Participant names and reference numbers must match exactly
        assert t_base.participant_names == t_opt_a.participant_names
        assert t_base.ref_numbers == t_opt_a.ref_numbers
        # Validation statuses on teams remain identical (mismatches are NOT rewritten to valid)
        assert t_base.validation_status == t_opt_a.validation_status

# 2. User can choose to proceed with current assignments despite reference mismatches
@pytest.mark.asyncio
async def test_option_a_proceed_with_current_mapping_success(tmp_path):
    session_id = f"sess_{uuid.uuid4()}"
    batches_dict, batch_infos = create_mock_batches(tmp_path, cert_numbers=[1, 2, 3])
    teams_data = create_mock_teams_data()

    session = SessionStore.get_session(session_id)
    session["teams_data"] = teams_data
    session["batches_dict"] = batches_dict
    session["batch_infos"] = batch_infos
    session["numbering_offset"] = 0
    session["overrides"] = {}

    # Initial validation shows can_send is False due to reference mismatches
    initial_report = MatchingEngine.match_teams(
        teams_data=teams_data,
        batches_dict=batches_dict,
        batch_infos=batch_infos,
        numbering_offset=0
    )
    assert initial_report.summary.can_send is False
    assert initial_report.summary.reference_mismatches == 2
    assert initial_report.summary.can_proceed_with_current_mapping is True
    assert initial_report.summary.has_fatal_errors is False

    # Elect Option A via API
    req = AcknowledgeMismatchesRequest(
        session_id=session_id,
        reviewer="Organizing Lead",
        reason="Reference sequence mismatch acknowledged; team member order is authoritative",
        confirmed=True
    )
    res = await acknowledge_mismatches(req)

    # Verification: can_send is now unlocked
    assert res.summary.can_send is True
    assert res.summary.reference_mismatches == 2
    assert res.summary.mismatch_acknowledgement is not None
    assert res.summary.mismatch_acknowledgement.policy == "PROCEED_WITH_CURRENT_MAPPING"
    assert res.summary.mismatch_acknowledgement.reviewer == "Organizing Lead"
    assert res.summary.mismatch_acknowledgement.mismatches_count == 2

    # Verification: Team statuses are preserved and NOT fabricated as valid or approved
    beta_team = next(t for t in res.teams if t.team_identifier == "BETA-02")
    assert beta_team.validation_status == "REFERENCE_MISMATCH"
    assert beta_team.manual_override is False

# 3. Application does not require approving each affected team individually
@pytest.mark.asyncio
async def test_no_individual_team_overrides_required(tmp_path):
    session_id = f"sess_{uuid.uuid4()}"
    batches_dict, batch_infos = create_mock_batches(tmp_path, cert_numbers=[1, 2, 3])
    teams_data = create_mock_teams_data()

    session = SessionStore.get_session(session_id)
    session["teams_data"] = teams_data
    session["batches_dict"] = batches_dict
    session["batch_infos"] = batch_infos

    # Authorize Option A
    await acknowledge_mismatches(AcknowledgeMismatchesRequest(
        session_id=session_id,
        reviewer="Master Reviewer",
        reason="Bulk waiver for reference numbers",
        confirmed=True
    ))

    # The individual approval_overrides database table must remain completely empty
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM approval_overrides;")
        count = cursor.fetchone()["count"]
        assert count == 0, "Option A must not create individual team override records in the database"
    finally:
        conn.close()

# 4. Alternative manual-review workflow (Option B) continues to work
@pytest.mark.asyncio
async def test_alternative_manual_review_option_b_still_works(tmp_path):
    session_id = f"sess_{uuid.uuid4()}"
    batches_dict, batch_infos = create_mock_batches(tmp_path, cert_numbers=[1, 2, 3])
    teams_data = create_mock_teams_data()

    session = SessionStore.get_session(session_id)
    session["teams_data"] = teams_data
    session["batches_dict"] = batches_dict
    session["batch_infos"] = batch_infos
    session["overrides"] = {}

    # Reviewer decides on Option B for team BETA-02
    ovr_req = ManualOverrideRequest(
        session_id=session_id,
        team_id="team-2",
        team_identifier="BETA-02",
        row_index=2,
        status="OVERRIDE_APPROVED",
        reviewer="Specialist Reviewer",
        reason="Manually inspected certs for Team Beta",
        approve_override=True
    )
    report = await submit_manual_override(ovr_req)

    # BETA-02 should now have OVERRIDE_APPROVED status
    beta = next(t for t in report.teams if t.team_identifier == "BETA-02")
    assert beta.validation_status == "OVERRIDE_APPROVED"
    assert beta.manual_override is True
    assert beta.override_reviewer == "Specialist Reviewer"

    # GAMMA-03 still has unresolved REFERENCE_MISMATCH, so can_send remains False
    assert report.summary.can_send is False
    assert report.summary.reference_mismatches == 1

# 5. User's decision persists and appears in the audit trail
@pytest.mark.asyncio
async def test_decision_persists_in_audit_trail_and_campaign(tmp_path):
    session_id = f"sess_{uuid.uuid4()}"
    batches_dict, batch_infos = create_mock_batches(tmp_path, cert_numbers=[1, 2, 3])
    teams_data = create_mock_teams_data()

    session = SessionStore.get_session(session_id)
    session["teams_data"] = teams_data
    session["batches_dict"] = batches_dict
    session["batch_infos"] = batch_infos

    # Create campaign passing Option A acknowledgement parameters
    camp_req = CampaignCreate(
        name="Annual SIH Hackathon 2026",
        session_id=session_id,
        subject="Selected Teams Announcement",
        body="Hello {{leader_name}}, attached are certificates.",
        proceed_with_current_mapping=True,
        mismatch_ack_reviewer="Dr. Jane Doe, Head Coordinator",
        mismatch_ack_reason="Verified physical certificates align with Excel names; sequence gap is benign",
        mismatch_ack_confirmed=True
    )
    camp_res = await create_campaign(camp_req)
    assert camp_res.total_teams == 3
    assert camp_res.status == "prepared"

    # Verify campaign config in database
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT config_json FROM campaigns WHERE id = ?", (camp_res.id,))
        row = cursor.fetchone()
        assert row is not None
        config = json.loads(row["config_json"])
        assert config["mapping_policy"] == "PROCEED_WITH_CURRENT_MAPPING"
        assert config["mismatch_acknowledgement"]["reviewer"] == "Dr. Jane Doe, Head Coordinator"
        assert config["mismatch_acknowledgement"]["reason"] == "Verified physical certificates align with Excel names; sequence gap is benign"
        assert config["unresolved_reference_mismatches"] == 2

        # Verify audit trail in delivery_logs
        cursor.execute("SELECT * FROM delivery_logs WHERE campaign_id = ? AND team_id = 'AUDIT_POLICY'", (camp_res.id,))
        audit_log = cursor.fetchone()
        assert audit_log is not None
        assert audit_log["status"] == "OPTION_A_PROCEED_WITH_CURRENT_MAPPING"
        assert "Jane Doe" in audit_log["recipient_email"]
        assert "Benign" in audit_log["error_message"].lower() or "benign" in audit_log["error_message"]
    finally:
        conn.close()

# 6. Unrelated blocking errors still prevent dispatch
@pytest.mark.asyncio
async def test_unrelated_blocking_errors_still_prevent_dispatch(tmp_path):
    session_id = f"sess_{uuid.uuid4()}"
    batches_dict, batch_infos = create_mock_batches(tmp_path, cert_numbers=[1, 2])
    # Teams data has 3 teams, but batches only have certs 1 and 2 (Team 3 cert is missing!)
    teams_data = create_mock_teams_data()

    session = SessionStore.get_session(session_id)
    session["teams_data"] = teams_data
    session["batches_dict"] = batches_dict
    session["batch_infos"] = batch_infos

    # Attempt to acknowledge mismatches when a certificate is physically missing
    req = AcknowledgeMismatchesRequest(
        session_id=session_id,
        reviewer="Admin",
        reason="Trying to waive missing file",
        confirmed=True
    )
    with pytest.raises(HTTPException) as exc_info:
        await acknowledge_mismatches(req)
    assert exc_info.value.status_code == 400
    assert "fatal validation errors present" in exc_info.value.detail.lower()

    # Attempt to create campaign with missing cert even if proceed_with_current_mapping is requested
    camp_req = CampaignCreate(
        name="Invalid Campaign",
        session_id=session_id,
        subject="Test",
        body="Test",
        proceed_with_current_mapping=True,
        mismatch_ack_reviewer="Admin",
        mismatch_ack_reason="Trying to bypass fatal error",
        mismatch_ack_confirmed=True
    )
    with pytest.raises(HTTPException) as camp_exc:
        await create_campaign(camp_req)
    assert camp_exc.value.status_code == 400
    assert "fatal error" in camp_exc.value.detail.lower()

# 7. A campaign cannot bypass authorization by sending a forged or incomplete frontend request
@pytest.mark.asyncio
async def test_forged_or_incomplete_requests_rejected(tmp_path):
    session_id = f"sess_{uuid.uuid4()}"
    batches_dict, batch_infos = create_mock_batches(tmp_path, cert_numbers=[1, 2, 3])
    teams_data = create_mock_teams_data()

    session = SessionStore.get_session(session_id)
    session["teams_data"] = teams_data
    session["batches_dict"] = batches_dict
    session["batch_infos"] = batch_infos

    # Case 7a: Missing reviewer name
    req_no_rev = CampaignCreate(
        name="Forged 1",
        session_id=session_id,
        subject="Test",
        body="Test",
        proceed_with_current_mapping=True,
        mismatch_ack_reviewer="",
        mismatch_ack_reason="Valid Reason",
        mismatch_ack_confirmed=True
    )
    with pytest.raises(HTTPException) as exc1:
        await create_campaign(req_no_rev)
    assert exc1.value.status_code == 400
    assert "incomplete authorization" in exc1.value.detail.lower()

    # Case 7b: Missing confirmation boolean
    req_no_conf = CampaignCreate(
        name="Forged 2",
        session_id=session_id,
        subject="Test",
        body="Test",
        proceed_with_current_mapping=True,
        mismatch_ack_reviewer="Reviewer",
        mismatch_ack_reason="Valid Reason",
        mismatch_ack_confirmed=False
    )
    with pytest.raises(HTTPException) as exc2:
        await create_campaign(req_no_conf)
    assert exc2.value.status_code == 400
    assert "incomplete authorization" in exc2.value.detail.lower()

    # Case 7c: proceed_with_current_mapping is False while reference mismatches exist
    req_false = CampaignCreate(
        name="Blocked 3",
        session_id=session_id,
        subject="Test",
        body="Test",
        proceed_with_current_mapping=False
    )
    with pytest.raises(HTTPException) as exc3:
        await create_campaign(req_false)
    assert exc3.value.status_code == 400
    assert "unresolved errors" in exc3.value.detail.lower()

# 8. Option A reset allows switching back to Option B manual review
@pytest.mark.asyncio
async def test_option_a_reset_reverts_to_option_b(tmp_path):
    session_id = f"sess_{uuid.uuid4()}"
    batches_dict, batch_infos = create_mock_batches(tmp_path, cert_numbers=[1, 2, 3])
    teams_data = create_mock_teams_data()

    session = SessionStore.get_session(session_id)
    session["teams_data"] = teams_data
    session["batches_dict"] = batches_dict
    session["batch_infos"] = batch_infos

    # First authorize Option A
    await acknowledge_mismatches(AcknowledgeMismatchesRequest(
        session_id=session_id,
        reviewer="Reviewer",
        reason="Reason",
        confirmed=True
    ))
    assert session["latest_report"].summary.can_send is True

    # User elects to reset / revoke Option A and return to manual review
    reset_report = await reset_mismatch_acknowledgement(ResetMismatchesRequest(session_id=session_id))
    assert reset_report.summary.can_send is False
    assert reset_report.summary.mismatch_acknowledgement is None
    assert session["mismatch_acknowledgement"] is None

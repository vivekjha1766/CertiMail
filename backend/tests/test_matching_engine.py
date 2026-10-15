import pytest
from pathlib import Path
from backend.app.services.matching_engine import MatchingEngine
from backend.app.schemas.mapping import ZipBatchInfo

def test_matching_engine_valid_72_teams(tmp_path):
    # Setup mock 6 batches with certs 1 to 72
    batches_dict = {}
    batch_infos = []
    for pos in range(1, 7):
        b_dict = {}
        for num in range(1, 73):
            file_p = tmp_path / f"batch_{pos}_{num}.png"
            file_p.write_bytes(b"dummy png bytes")
            b_dict[num] = file_p
        batches_dict[pos] = b_dict
        batch_infos.append(ZipBatchInfo(
            position=pos,
            batch_id=f"batch_{pos}",
            filename=f"bulk_{pos}.zip",
            file_count=72,
            min_number=1,
            max_number=72
        ))

    # 72 teams
    teams_data = []
    for i in range(1, 73):
        teams_data.append({
            "row_index": i,
            "team_name": f"Team {i}",
            "team_identifier": f"T{i:03d}",
            "leader_name": f"Leader {i}",
            "leader_email": f"leader_{i}@example.com",
            "participants": [f"Member {i}-{p}" for p in range(1, 7)],
            "ref_numbers": [f"REF-{i}-{p}" for p in range(1, 7)]
        })

    report = MatchingEngine.match_teams(
        teams_data=teams_data,
        batches_dict=batches_dict,
        batch_infos=batch_infos,
        numbering_offset=0
    )

    assert report.summary.total_teams == 72
    assert report.summary.valid_teams == 72
    assert report.summary.error_teams == 0
    assert report.summary.can_send is True
    assert len(report.teams) == 72

    # Check team 12 has 6 certificates
    team_12 = report.teams[11]
    assert team_12.validation_status == "VALID"
    assert len(team_12.certificate_files) == 6
    assert all(c.exists for c in team_12.certificate_files)

def test_matching_engine_missing_certificate(tmp_path):
    batches_dict = {pos: {} for pos in range(1, 7)}
    # Populate pos 1 to 5, but leave pos 6 empty for team 5
    for pos in range(1, 6):
        file_p = tmp_path / f"batch_{pos}_5.png"
        file_p.write_bytes(b"dummy")
        batches_dict[pos][5] = file_p

    batch_infos = [
        ZipBatchInfo(position=p, batch_id=f"b_{p}", filename=f"b_{p}.zip", file_count=1)
        for p in range(1, 7)
    ]

    teams_data = [{
        "row_index": 5,
        "team_name": "Team Incomplete",
        "leader_name": "Incomplete Lead",
        "leader_email": "incomplete@example.com",
        "participants": [f"M{p}" for p in range(1, 7)],
        "ref_numbers": []
    }]

    report = MatchingEngine.match_teams(teams_data, batches_dict, batch_infos)
    assert report.summary.valid_teams == 0
    assert report.summary.missing_certificates == 1
    assert report.summary.can_send is False
    assert report.teams[0].validation_status == "MISSING CERTIFICATE"

def test_matching_engine_duplicate_and_invalid_email(tmp_path):
    batches_dict = {pos: {1: tmp_path / "1.png", 2: tmp_path / "2.png", 3: tmp_path / "3.png"} for pos in range(1, 7)}
    for p_dict in batches_dict.values():
        for p in p_dict.values():
            p.write_bytes(b"dummy")

    batch_infos = [ZipBatchInfo(position=p, batch_id=f"b_{p}", filename=f"b_{p}.zip", file_count=3) for p in range(1, 7)]

    teams_data = [
        {"row_index": 1, "team_name": "Team A", "leader_name": "L1", "leader_email": "shared@example.com", "participants": [], "ref_numbers": []},
        {"row_index": 2, "team_name": "Team B", "leader_name": "L2", "leader_email": "shared@example.com", "participants": [], "ref_numbers": []},
        {"row_index": 3, "team_name": "Team C", "leader_name": "L3", "leader_email": "not-an-email", "participants": [], "ref_numbers": []},
    ]

    report = MatchingEngine.match_teams(teams_data, batches_dict, batch_infos)
    assert report.summary.duplicate_emails >= 1
    assert report.teams[0].validation_status == "DUPLICATE EMAIL"
    assert report.teams[1].validation_status == "DUPLICATE EMAIL"
    assert report.teams[2].validation_status == "INVALID EMAIL"
    assert report.summary.can_send is False

def test_matching_engine_manual_override(tmp_path):
    # Setup team with missing cert initially
    batches_dict = {pos: {} for pos in range(1, 7)}
    batch_infos = [ZipBatchInfo(position=p, batch_id=f"b_{p}", filename=f"b_{p}.zip", file_count=0) for p in range(1, 7)]
    teams_data = [{"row_index": 1, "team_name": "Team 1", "leader_name": "L1", "leader_email": "l1@example.com", "participants": [], "ref_numbers": []}]

    # Submit manual override
    overrides = {
        "team-1": {
            "approve_override": True,
            "leader_email": "fixed@example.com"
        }
    }
    report = MatchingEngine.match_teams(teams_data, batches_dict, batch_infos, existing_overrides=overrides)
    assert report.teams[0].validation_status in ["VALID", "OVERRIDE_APPROVED"]
    assert report.teams[0].manual_override is True
    assert report.summary.can_send is True

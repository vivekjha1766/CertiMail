import pytest
from pathlib import Path
from backend.app.services.excel_service import ExcelService
from backend.app.schemas.excel import ColumnMapping

SAMPLE_EXCEL = Path("sample_data/Certificates for top 75 participants new.xlsx")

def test_excel_read_and_suggestions():
    assert SAMPLE_EXCEL.exists(), "Sample excel file must exist"
    sheets = ExcelService.get_sheet_names(SAMPLE_EXCEL)
    assert len(sheets) > 0
    assert "Top 72 Teams" in sheets

    columns, count, sample_rows = ExcelService.read_sheet(SAMPLE_EXCEL, "Top 72 Teams")
    assert count == 72
    assert "Team Name" in columns
    assert "Leader Email" in columns
    assert len(sample_rows) == 5

    suggestions = ExcelService.suggest_mappings(columns)
    assert suggestions.team_name == "Team Name"
    assert suggestions.leader_name == "Leader Name"
    assert suggestions.leader_email == "Leader Email"
    assert suggestions.participant_1 == "Participant 1 Name"
    assert suggestions.participant_6 == "Participant 6 Name"

def test_excel_extract_rows():
    mapping = ColumnMapping(
        team_name="Team Name",
        team_identifier="Team ID",
        leader_name="Leader Name",
        leader_email="Leader Email",
        participant_1="Participant 1 Name",
        participant_2="Participant 2 Name",
        participant_3="Participant 3 Name",
        participant_4="Participant 4 Name",
        participant_5="Participant 5 Name",
        participant_6="Participant 6 Name",
        ref_1="Certificate Ref 1",
        ref_2="Certificate Ref 2",
        ref_3="Certificate Ref 3",
        ref_4="Certificate Ref 4",
        ref_5="Certificate Ref 5",
        ref_6="Certificate Ref 6",
    )
    rows = ExcelService.extract_rows(SAMPLE_EXCEL, mapping, "Top 72 Teams")
    assert len(rows) == 72
    first_team = rows[0]
    assert first_team["row_index"] == 1
    assert "@" in first_team["leader_email"]
    assert len(first_team["participants"]) == 6
    assert len(first_team["ref_numbers"]) == 6

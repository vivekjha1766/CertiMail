from fastapi import APIRouter, HTTPException, Response, status
from backend.app.schemas.mapping import (
    ValidateMappingRequest,
    ValidationReportResponse,
    ManualOverrideRequest,
    AcknowledgeMismatchesRequest,
    ResetMismatchesRequest
)
from backend.app.services.excel_service import ExcelService
from backend.app.services.matching_engine import MatchingEngine
from backend.app.api.session_store import SessionStore

router = APIRouter(prefix="/api/mapping", tags=["Mapping & Validation"])

@router.post("/validate", response_model=ValidationReportResponse)
async def validate_mapping(request: ValidateMappingRequest):
    session = SessionStore.get_session(request.session_id)
    if not session.get("excel_path"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Excel workbook uploaded for this session. Please upload the Excel file first."
        )

    # Extract teams rows using provided column mapping
    try:
        teams_data = ExcelService.extract_rows(
            file_path=session["excel_path"],
            mapping=request.column_mapping,
            sheet_name=request.selected_sheet or session.get("selected_sheet")
        )
        session["teams_data"] = teams_data
        session["column_mapping"] = request.column_mapping
        session["numbering_offset"] = request.numbering_offset

        # Match teams against the 6 batches
        report = MatchingEngine.match_teams(
            teams_data=teams_data,
            batches_dict=session.get("batches_dict", {}),
            batch_infos=session.get("batch_infos", []),
            numbering_offset=request.numbering_offset,
            existing_overrides=session.get("overrides", {}),
            mismatch_acknowledgement=session.get("mismatch_acknowledgement")
        )

        session["latest_report"] = report
        return report
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Mapping validation failed: {str(e)}"
        )


@router.post("/override", response_model=ValidationReportResponse)
async def submit_manual_override(request: ManualOverrideRequest):
    session = SessionStore.get_session(request.session_id)
    if not session.get("teams_data"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session has no validated teams to override."
        )

    # Locate the target team in teams_data to resolve stable identifiers
    target_team = None
    for t in session["teams_data"]:
        t_id = f"team-{t['row_index']}"
        t_ident = (t.get("team_identifier") or "").strip()
        if (
            t_id == request.team_id
            or (t_ident and t_ident == request.team_id)
            or (request.team_identifier and t_ident == request.team_identifier)
            or (request.row_index is not None and t["row_index"] == request.row_index)
        ):
            target_team = t
            break

    row_index = target_team["row_index"] if target_team else request.row_index
    team_identifier = (
        (target_team.get("team_identifier") if target_team else "")
        or request.team_identifier
        or ""
    ).strip()
    team_name = target_team["team_name"] if target_team else f"Team {row_index or request.team_id}"

    # Determine status
    override_status = request.status or ("OVERRIDE_APPROVED" if request.approve_override else "OVERRIDE_REJECTED")

    override_record = {
        "team_id": request.team_id,
        "team_identifier": team_identifier,
        "row_index": row_index,
        "team_name": team_name,
        "status": override_status,
        "reviewer": request.reviewer or "Admin Reviewer",
        "reason": request.reason or "Explicit override reviewed and approved",
        "certificate_filenames": request.certificate_filenames or [],
        "leader_email": request.leader_email,
        "leader_name": request.leader_name,
        "cc_recipients": request.cc_recipients or "",
        "bcc_recipients": request.bcc_recipients or "",
        "approve_override": (override_status == "OVERRIDE_APPROVED")
    }

    # Persist in SQLite database
    try:
        from backend.app.core.database import save_approval_override
        saved_db_override = save_approval_override(override_record)
    except Exception as db_err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database write failure: Failed to persist approval override: {str(db_err)}"
        )

    # Update in-memory session overrides using all key aliases
    session["overrides"][request.team_id] = saved_db_override
    if team_identifier:
        session["overrides"][team_identifier] = saved_db_override
    if row_index is not None:
        session["overrides"][f"team-{row_index}"] = saved_db_override

    # Re-run validation preserving offset
    report = MatchingEngine.match_teams(
        teams_data=session["teams_data"],
        batches_dict=session.get("batches_dict", {}),
        batch_infos=session.get("batch_infos", []),
        numbering_offset=session.get("numbering_offset", 0),
        existing_overrides=session["overrides"],
        mismatch_acknowledgement=session.get("mismatch_acknowledgement")
    )
    session["latest_report"] = report
    return report


@router.post("/acknowledge-mismatches", response_model=ValidationReportResponse)
async def acknowledge_mismatches(request: AcknowledgeMismatchesRequest):
    """Option A: Acknowledges non-fatal reference mismatches for the campaign workflow with an explicit audit trail."""
    session = SessionStore.get_session(request.session_id)
    if not session.get("teams_data"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session has no validated teams to acknowledge. Please run mapping first."
        )

    reviewer = (request.reviewer or "").strip()
    reason = (request.reason or "").strip()
    if not reviewer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reviewer name is required to authorize proceeding with current mapping."
        )
    if not reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An audit reason or justification is required to proceed with current mapping."
        )
    if not request.confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Explicit confirmation is required to proceed with current mapping."
        )

    # Pre-check current validation status to strictly enforce that fatal errors cannot be bypassed
    baseline_report = MatchingEngine.match_teams(
        teams_data=session["teams_data"],
        batches_dict=session.get("batches_dict", {}),
        batch_infos=session.get("batch_infos", []),
        numbering_offset=session.get("numbering_offset", 0),
        existing_overrides=session.get("overrides", {}),
        mismatch_acknowledgement=None
    )

    if baseline_report.summary.has_fatal_errors:
        fatal_reasons = []
        if baseline_report.summary.missing_certificates > 0:
            fatal_reasons.append(f"{baseline_report.summary.missing_certificates} missing certificate(s)")
        if baseline_report.summary.duplicate_emails > 0:
            fatal_reasons.append(f"{baseline_report.summary.duplicate_emails} duplicate email(s)")
        error_detail_str = ", ".join(fatal_reasons) or "unresolved fatal errors"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot proceed with current mapping: Fatal validation errors present ({error_detail_str}). Missing files and recipient errors cannot be bypassed."
        )

    from datetime import datetime
    session["mismatch_acknowledgement"] = {
        "policy": "PROCEED_WITH_CURRENT_MAPPING",
        "reviewer": reviewer,
        "reason": reason,
        "confirmed": True,
        "acknowledged_at": datetime.now().isoformat()
    }

    # Re-evaluate with acknowledgement active
    report = MatchingEngine.match_teams(
        teams_data=session["teams_data"],
        batches_dict=session.get("batches_dict", {}),
        batch_infos=session.get("batch_infos", []),
        numbering_offset=session.get("numbering_offset", 0),
        existing_overrides=session.get("overrides", {}),
        mismatch_acknowledgement=session["mismatch_acknowledgement"]
    )
    session["latest_report"] = report
    return report


@router.post("/reset-mismatches", response_model=ValidationReportResponse)
async def reset_mismatch_acknowledgement(request: ResetMismatchesRequest):
    """Resets the Option A acknowledgement to return to individual review mode (Option B)."""
    session = SessionStore.get_session(request.session_id)
    session["mismatch_acknowledgement"] = None

    if session.get("teams_data"):
        report = MatchingEngine.match_teams(
            teams_data=session["teams_data"],
            batches_dict=session.get("batches_dict", {}),
            batch_infos=session.get("batch_infos", []),
            numbering_offset=session.get("numbering_offset", 0),
            existing_overrides=session.get("overrides", {}),
            mismatch_acknowledgement=None
        )
        session["latest_report"] = report
        return report

    report = session.get("latest_report")
    if not report:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active session data.")
    return report


@router.get("/report/{session_id}")
async def download_validation_report(session_id: str):
    session = SessionStore.get_session(session_id)
    report = session.get("latest_report")
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No validation report generated for this session yet."
        )

    csv_data = MatchingEngine.generate_csv_report(report.teams)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=CertiMail_Validation_Report_{session_id}.csv"}
    )


import io
import re
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from backend.app.schemas.mapping import (
    TeamMappingItem,
    CertificateFileInfo,
    ValidationSummary,
    ValidationReportResponse,
    ZipBatchInfo,
    ManualOverrideRequest,
    MismatchAcknowledgement
)

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

class MatchingEngine:
    @staticmethod
    def validate_email(email: str) -> bool:
        if not email or not isinstance(email, str):
            return False
        return bool(EMAIL_REGEX.match(email.strip()))

    @classmethod
    def match_teams(
        cls,
        teams_data: List[Dict[str, Any]],
        batches_dict: Dict[int, Dict[int, Path]], # position (1..6) -> {cert_number: Path}
        batch_infos: List[ZipBatchInfo],
        numbering_offset: int = 0,
        existing_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
        mismatch_acknowledgement: Optional[Dict[str, Any]] = None
    ) -> ValidationReportResponse:
        """
        Matches teams against the 6 certificate batches and evaluates validation statuses.
        Retrieves persisted approval overrides from SQLite and merges with in-memory overrides.
        """
        # Load persisted overrides from SQLite database and merge
        merged_overrides: Dict[str, Dict[str, Any]] = {}
        try:
            from backend.app.core.database import get_all_approval_overrides
            merged_overrides.update(get_all_approval_overrides())
        except Exception:
            pass
        if existing_overrides:
            merged_overrides.update(existing_overrides)
        
        # Track email occurrences to detect duplicates
        email_counts: Dict[str, int] = {}
        for t in teams_data:
            clean_email = t["leader_email"].strip().lower()
            if clean_email:
                email_counts[clean_email] = email_counts.get(clean_email, 0) + 1

        team_items: List[TeamMappingItem] = []
        
        total_certificates_detected = sum(b.file_count for b in batch_infos)
        missing_cert_count = 0
        duplicate_email_count = 0
        ref_mismatch_count = 0

        for t in teams_data:
            row_idx = t["row_index"]
            team_id = f"team-{row_idx}"
            team_identifier = (t.get("team_identifier") or "").strip()
            
            # Look up override by team_identifier, team_id, or row index
            override = (
                merged_overrides.get(team_identifier)
                or merged_overrides.get(team_id)
                or merged_overrides.get(str(row_idx))
                or {}
            )
            
            team_name = override.get("team_name") or t["team_name"] or f"Team {row_idx}"
            leader_name = override.get("leader_name") or t["leader_name"] or f"Leader {row_idx}"
            leader_email = override.get("leader_email") or t["leader_email"].strip()
            
            participants = t.get("participants", [])
            ref_numbers = t.get("ref_numbers", [])
            
            expected_cert_num = row_idx + numbering_offset
            
            errors: List[str] = []
            cert_files: List[CertificateFileInfo] = []
            
            # 1. Validate Email
            if not leader_email:
                errors.append("Leader email is missing.")
            elif not cls.validate_email(leader_email):
                errors.append(f"Invalid email format: '{leader_email}'")
            elif email_counts.get(leader_email.lower(), 0) > 1 and not override.get("approve_override"):
                errors.append(f"Duplicate email found in multiple teams: '{leader_email}'")
                duplicate_email_count += 1

            # 2. Match 6 Certificates
            team_has_missing_cert = False
            for pos in range(1, 7):
                pos_files_dict = batches_dict.get(pos, {})
                part_name = participants[pos - 1] if pos - 1 < len(participants) else f"Member {pos}"
                ref_num = ref_numbers[pos - 1] if pos - 1 < len(ref_numbers) else ""
                
                # Check if manually overridden for this position
                override_files = override.get("certificate_filenames")
                if override_files and len(override_files) >= pos and override_files[pos - 1]:
                    chosen_file_name = override_files[pos - 1]
                    # Search in pos_files_dict for this filename
                    found_path = None
                    for p in pos_files_dict.values():
                        if p.name == chosen_file_name:
                            found_path = p
                            break
                    exists = found_path is not None and found_path.exists()
                    file_info = CertificateFileInfo(
                        position=pos,
                        filename=chosen_file_name,
                        relative_path=str(found_path) if found_path else chosen_file_name,
                        batch_name=f"Bulk {pos}",
                        exists=exists,
                        size_bytes=found_path.stat().st_size if exists else 0,
                        participant_name=part_name,
                        ref_number=ref_num
                    )
                else:
                    target_path = pos_files_dict.get(expected_cert_num)
                    exists = target_path is not None and target_path.exists()
                    filename = target_path.name if exists else f"{expected_cert_num}.png"
                    
                    file_info = CertificateFileInfo(
                        position=pos,
                        filename=filename,
                        relative_path=str(target_path) if exists else "",
                        batch_name=f"Bulk {pos}",
                        exists=exists,
                        size_bytes=target_path.stat().st_size if exists else 0,
                        participant_name=part_name,
                        ref_number=ref_num
                    )
                
                if not file_info.exists:
                    errors.append(f"Missing certificate for Position {pos} ({part_name}): expected '{file_info.filename}' in Batch {pos}")
                    team_has_missing_cert = True
                    
                cert_files.append(file_info)

            # 3. Check Reference Number Sequence if applicable
            has_ref_mismatch = False
            detected_mismatch_desc: Optional[str] = None
            orig_ref_str = ""
            act_ref_str = ""
            
            for idx_r, ref_val in enumerate(ref_numbers):
                if ref_val:
                    pos = idx_r + 1
                    part_name = participants[idx_r] if idx_r < len(participants) else f"Member {pos}"
                    nums_in_ref = re.findall(r'(\d+)', str(ref_val))
                    
                    # Extract number from assigned certificate filename
                    assigned_cert_filename = cert_files[idx_r].filename if idx_r < len(cert_files) else ""
                    cert_num_match = re.search(r'(\d+)', assigned_cert_filename)
                    assigned_cert_num = int(cert_num_match.group(1)) if cert_num_match else expected_cert_num
                    
                    if nums_in_ref:
                        int_nums = [int(n) for n in nums_in_ref]
                        # If expected cert num, row_idx, or actual assigned cert num is in reference
                        if assigned_cert_num in int_nums or expected_cert_num in int_nums or row_idx in int_nums:
                            pass
                        elif len(nums_in_ref) == 1 and int_nums[0] != assigned_cert_num:
                            mismatch_msg = f"Reference number '{ref_val}' (Pos {pos}) does not match expected #{assigned_cert_num} ({assigned_cert_filename})"
                            errors.append(mismatch_msg)
                            has_ref_mismatch = True
                            detected_mismatch_desc = mismatch_msg
                            orig_ref_str = str(ref_val)
                            act_ref_str = str(assigned_cert_num)
                        elif len(nums_in_ref) > 1 and assigned_cert_num not in int_nums and expected_cert_num not in int_nums:
                            # Sequence mismatch in composite reference
                            mismatch_msg = f"Reference sequence '{ref_val}' (Pos {pos}) does not contain certificate #{assigned_cert_num}"
                            errors.append(mismatch_msg)
                            has_ref_mismatch = True
                            detected_mismatch_desc = mismatch_msg
                            orig_ref_str = str(ref_val)
                            act_ref_str = str(assigned_cert_num)

            # 4. Check Override Status and Invalidation Protection
            # Current certificate assignment mapping hash
            current_cert_hash = ",".join(c.filename for c in cert_files)
            override_cert_hash = override.get("certificate_mapping_hash")
            
            override_status = override.get("status")
            if not override_status and override.get("approve_override"):
                override_status = "OVERRIDE_APPROVED"

            # Invalidate override if certificate assignment was changed after approval
            if override and override_status == "OVERRIDE_APPROVED" and override_cert_hash and override_cert_hash != current_cert_hash:
                override_status = "OVERRIDE_REVOKED"
                revocation_msg = f"Previously approved override was revoked because certificate assignment changed from '{override_cert_hash}' to '{current_cert_hash}'."
                errors.append(revocation_msg)

            is_overridden = (override_status == "OVERRIDE_APPROVED")

            if has_ref_mismatch and not is_overridden:
                ref_mismatch_count += 1

            if team_has_missing_cert and not is_overridden:
                missing_cert_count += 1

            # Determine final validation status
            if is_overridden:
                validation_status = "OVERRIDE_APPROVED"
                display_errors = errors
            elif override_status == "OVERRIDE_REJECTED":
                validation_status = "OVERRIDE_REJECTED"
                display_errors = errors or ["Override explicitly rejected by reviewer."]
            elif override_status == "OVERRIDE_REVOKED":
                validation_status = "OVERRIDE_REVOKED"
                display_errors = errors
            elif not errors:
                validation_status = "VALID"
                display_errors = []
            elif team_has_missing_cert:
                validation_status = "MISSING CERTIFICATE"
                display_errors = errors
            elif any("Duplicate email" in e for e in errors):
                validation_status = "DUPLICATE EMAIL"
                display_errors = errors
            elif any("Invalid email" in e or "missing" in e for e in errors):
                validation_status = "INVALID EMAIL"
                display_errors = errors
            elif has_ref_mismatch:
                validation_status = "REFERENCE_MISMATCH"
                display_errors = errors
            else:
                validation_status = "MANUAL REVIEW REQUIRED"
                display_errors = errors

            team_items.append(TeamMappingItem(
                team_id=team_id,
                row_index=row_idx,
                team_name=team_name,
                team_identifier=team_identifier,
                leader_name=leader_name,
                leader_email=leader_email,
                participant_names=participants,
                ref_numbers=ref_numbers,
                certificate_files=cert_files,
                validation_status=validation_status,
                validation_errors=display_errors,
                manual_override=is_overridden,
                override_status=override_status if override else None,
                override_reviewer=override.get("reviewer"),
                override_reason=override.get("reason"),
                override_timestamp=override.get("updated_at") or override.get("created_at"),
                detected_reference_mismatch=detected_mismatch_desc or override.get("detected_mismatch"),
                custom_subject=override.get("custom_subject"),
                custom_body=override.get("custom_body"),
                cc_recipients=override.get("cc_recipients", ""),
                bcc_recipients=override.get("bcc_recipients", "")
            ))

        total_teams = len(team_items)
        valid_teams = sum(1 for t in team_items if t.validation_status in ["VALID", "OVERRIDE_APPROVED"])
        error_teams = total_teams - valid_teams
        approved_overrides_count = sum(1 for t in team_items if t.validation_status == "OVERRIDE_APPROVED")

        # Fatal errors that block dispatch unconditionally:
        # 1. Missing certificates (either status or physical file missing)
        # 2. Duplicate emails
        # 3. Invalid emails
        # 4. Explicitly rejected or revoked overrides
        fatal_error_count = sum(
            1 for t in team_items
            if t.validation_status in ["MISSING CERTIFICATE", "DUPLICATE EMAIL", "INVALID EMAIL", "OVERRIDE_REJECTED", "OVERRIDE_REVOKED"]
            or any(not c.exists for c in t.certificate_files)
        )
        has_fatal_errors = fatal_error_count > 0
        can_proceed_with_current_mapping = (total_teams > 0 and not has_fatal_errors and ref_mismatch_count > 0)

        # Check explicit mismatch acknowledgement (Option A)
        is_ack_valid = False
        ack_obj: Optional[MismatchAcknowledgement] = None
        if mismatch_acknowledgement and isinstance(mismatch_acknowledgement, dict):
            ack_confirmed = bool(mismatch_acknowledgement.get("confirmed"))
            ack_reviewer = str(mismatch_acknowledgement.get("reviewer") or "").strip()
            ack_reason = str(mismatch_acknowledgement.get("reason") or "").strip()
            
            if ack_confirmed and ack_reviewer and ack_reason and not has_fatal_errors:
                is_ack_valid = True
                unresolved_items = [
                    {
                        "team_id": t.team_id,
                        "team_identifier": t.team_identifier,
                        "team_name": t.team_name,
                        "leader_email": t.leader_email,
                        "detected_reference_mismatch": t.detected_reference_mismatch or (t.validation_errors[0] if t.validation_errors else "")
                    }
                    for t in team_items if t.validation_status == "REFERENCE_MISMATCH"
                ]
                ack_obj = MismatchAcknowledgement(
                    policy="PROCEED_WITH_CURRENT_MAPPING",
                    reviewer=ack_reviewer,
                    reason=ack_reason,
                    acknowledged_at=str(mismatch_acknowledgement.get("acknowledged_at") or datetime.now().isoformat()),
                    mismatches_count=ref_mismatch_count,
                    unresolved_summary=mismatch_acknowledgement.get("unresolved_summary") or unresolved_items
                )

        can_send = total_teams > 0 and ((error_teams == 0) or (is_ack_valid and not has_fatal_errors))

        summary = ValidationSummary(
            total_teams=total_teams,
            valid_teams=valid_teams,
            error_teams=error_teams,
            duplicate_emails=duplicate_email_count,
            missing_certificates=missing_cert_count,
            reference_mismatches=ref_mismatch_count,
            approved_overrides=approved_overrides_count,
            total_certificates_detected=total_certificates_detected,
            can_send=can_send,
            has_fatal_errors=has_fatal_errors,
            fatal_error_count=fatal_error_count,
            can_proceed_with_current_mapping=can_proceed_with_current_mapping,
            mismatch_acknowledgement=ack_obj
        )

        return ValidationReportResponse(
            summary=summary,
            teams=team_items,
            batches=batch_infos
        )

    @staticmethod
    def generate_csv_report(teams: List[TeamMappingItem]) -> str:
        """Generates a downloadable CSV audit report distinguishing unresolved errors from approved overrides."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "Row Index",
            "Team ID",
            "Team Name",
            "Leader Name",
            "Leader Email",
            "Validation Status",
            "Override Status",
            "Override Reviewer",
            "Override Reason",
            "Detected Reference Mismatch",
            "Validation Errors",
            "Participant 1", "Cert 1", "Ref 1",
            "Participant 2", "Cert 2", "Ref 2",
            "Participant 3", "Cert 3", "Ref 3",
            "Participant 4", "Cert 4", "Ref 4",
            "Participant 5", "Cert 5", "Ref 5",
            "Participant 6", "Cert 6", "Ref 6",
        ])
        
        for t in teams:
            row = [
                t.row_index,
                t.team_identifier or t.team_id,
                t.team_name,
                t.leader_name,
                t.leader_email,
                t.validation_status,
                t.override_status or ("APPROVED" if t.manual_override else "NONE"),
                t.override_reviewer or "",
                t.override_reason or "",
                t.detected_reference_mismatch or "",
                "; ".join(t.validation_errors),
            ]
            for pos in range(6):
                p_name = t.participant_names[pos] if pos < len(t.participant_names) else ""
                c_file = t.certificate_files[pos].filename if pos < len(t.certificate_files) else ""
                r_num = t.ref_numbers[pos] if pos < len(t.ref_numbers) else ""
                row.extend([p_name, c_file, r_num])
                
            writer.writerow(row)
            
        return output.getvalue()

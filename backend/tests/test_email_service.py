import pytest
from pathlib import Path
from backend.app.services.email_service import EmailService

def test_template_rendering():
    template = "Hello {{leader_name}}, congratulations to {{team_name}}! Member 1: {{member_1}}, Ref: {{ref_1}}."
    context = {
        "leader_name": "Aarav Sharma",
        "team_name": "Cyber Wizards",
        "member_1": "Aarav Sharma",
        "ref_1": "HOS-001-P1"
    }
    rendered = EmailService.render_template(template, context)
    assert rendered == "Hello Aarav Sharma, congratulations to Cyber Wizards! Member 1: Aarav Sharma, Ref: HOS-001-P1."

def test_cc_bcc_parsing_and_deduplication():
    raw_cc = "mentor@college.edu, faculty@college.edu ; mentor@college.edu \n hod@college.edu"
    parsed = EmailService.parse_email_list(raw_cc)
    assert len(parsed) == 3
    assert "mentor@college.edu" in parsed
    assert "faculty@college.edu" in parsed
    assert "hod@college.edu" in parsed

def test_build_email_message_attachments(tmp_path):
    # Create 6 dummy certificate files
    attachments = []
    original_bytes_list = []
    for i in range(1, 7):
        cert_p = tmp_path / f"cert_{i}.png"
        sample_bytes = f"fake_png_data_{i}".encode("utf-8")
        cert_p.write_bytes(sample_bytes)
        original_bytes_list.append(sample_bytes)
        attachments.append((cert_p, f"HackOSprint_Team_Member_{i}.png"))

    msg = EmailService.build_email_message(
        sender_name="Organizer",
        sender_email="admin@event.org",
        to_email="lead@team.org",
        subject="Your Certificates",
        body_text="Please find certificates attached.",
        cc_emails=["coord@event.org"],
        bcc_emails=["archive@event.org"],
        attachments=attachments
    )

    assert msg["To"] == "lead@team.org"
    assert msg["Cc"] == "coord@event.org"
    assert msg["Bcc"] == "archive@event.org"
    assert msg["Subject"] == "Your Certificates"
    assert msg["From"] == "Organizer <admin@event.org>"

    # Verify attachment count is exactly 6
    attached_parts = [p for p in msg.iter_attachments()]
    assert len(attached_parts) == 6
    for idx, part in enumerate(attached_parts):
        assert part.get_filename() == f"HackOSprint_Team_Member_{idx+1}.png"
        assert part.get_content() == original_bytes_list[idx] # Original bytes preserved!

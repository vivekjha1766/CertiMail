import os
import io
import zipfile
from pathlib import Path
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

SAMPLE_DIR = Path("sample_data")
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

TEAMS_COUNT = 72

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan", "Krishna", "Ishaan",
    "Shaurya", "Atharv", "Advik", "Pranav", "Kabir", "Ananya", "Diya", "Saanvi", "Aadhya", "Pari",
    "Kiara", "Myra", "Riya", "Aarohi", "Isha", "Rohan", "Neha", "Kavya", "Rahul", "Pooja", "Vikram",
    "Meera", "Siddharth", "Tanvi", "Nikhil", "Simran", "Aryan", "Anushka", "Dev", "Sneha", "Kunal"
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Gupta", "Singh", "Kumar", "Mishra", "Joshi", "Bose", "Mehta",
    "Iyer", "Nair", "Reddy", "Chopra", "Malhotra", "Saxena", "Bhatia", "Deshmukh", "Choudhury", "Das"
]

TEAM_PREFIXES = ["Cyber", "Quantum", "Byte", "Neural", "Code", "Algo", "Hyper", "Apex", "Synthetix", "Vector", "Logic", "Binary"]
TEAM_SUFFIXES = ["Crafters", "Wizards", "Knights", "Innovators", "Force", "Pioneers", "Titans", "Squad", "Hackers", "Minds", "Vanguard", "Architects"]

def generate_sample_excel():
    excel_path = SAMPLE_DIR / "Certificates for top 75 participants new.xlsx"
    rows = []

    for i in range(1, TEAMS_COUNT + 1):
        team_name = f"{TEAM_PREFIXES[(i - 1) % len(TEAM_PREFIXES)]} {TEAM_SUFFIXES[(i * 3) % len(TEAM_SUFFIXES)]} {i}"
        team_id = f"HOS-2026-T{i:03d}"
        
        lead_first = FIRST_NAMES[(i * 7) % len(FIRST_NAMES)]
        lead_last = LAST_NAMES[(i * 5) % len(LAST_NAMES)]
        lead_name = f"{lead_first} {lead_last}"
        lead_email = f"team{i}.leader.{lead_first.lower()}@example.com"
        
        row = {
            "Team ID": team_id,
            "Team Name": team_name,
            "Leader Name": lead_name,
            "Leader Email": lead_email
        }
        
        # 6 participants and 6 reference numbers
        for pos in range(1, 7):
            p_first = FIRST_NAMES[(i * 11 + pos * 13) % len(FIRST_NAMES)]
            p_last = LAST_NAMES[(i * 17 + pos * 19) % len(LAST_NAMES)]
            p_name = lead_name if pos == 1 else f"{p_first} {p_last}"
            ref_no = f"HOS4-2026-{i:03d}-{pos}"
            
            row[f"Participant {pos} Name"] = p_name
            row[f"Certificate Ref {pos}"] = ref_no
            
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_excel(excel_path, sheet_name="Top 72 Teams", index=False)
    print(f"Generated sample Excel: {excel_path} ({len(df)} rows)")

def create_certificate_image(cert_number: int, position: int) -> bytes:
    """Generates a realistic mock participation certificate image."""
    width, height = 900, 650
    # Background
    img = Image.new("RGB", (width, height), color=(250, 250, 252))
    draw = ImageDraw.Draw(img)
    
    # Outer elegant border
    border_color = (30, 58, 138) # Navy blue
    gold_accent = (217, 119, 6) # Amber gold
    
    draw.rectangle([15, 15, width - 15, height - 15], outline=border_color, width=4)
    draw.rectangle([25, 25, width - 25, height - 25], outline=gold_accent, width=2)
    
    # Header
    draw.text((width // 2, 80), "CERTIFICATE OF PARTICIPATION", fill=border_color, anchor="mm")
    draw.text((width // 2, 120), "Hack-O-Sprint 4.0 – SIH Internal Round 2026", fill=(71, 85, 105), anchor="mm")
    draw.text((width // 2, 150), "IEEE Student Branch & Computer Society SBC, IIIT Bhopal", fill=(100, 116, 139), anchor="mm")
    
    # Body text
    draw.line([(width // 2 - 200, 180), (width // 2 + 200, 180)], fill=gold_accent, width=2)
    
    draw.text((width // 2, 240), "This is proudly presented to", fill=(100, 116, 139), anchor="mm")
    draw.text((width // 2, 290), f"Participant Position #{position} (Team #{cert_number})", fill=(15, 23, 42), anchor="mm")
    
    draw.text((width // 2, 350), f"for outstanding innovation and selection among the Top 72 Teams.", fill=(71, 85, 105), anchor="mm")
    draw.text((width // 2, 380), f"Certificate #{cert_number}.png | Position Batch #{position}", fill=(148, 163, 184), anchor="mm")
    
    # Verification Badge / Stamp
    badge_x, badge_y = width // 2, 480
    draw.ellipse([badge_x - 45, badge_y - 45, badge_x + 45, badge_y + 45], outline=gold_accent, width=3)
    draw.text((badge_x, badge_y - 8), "VERIFIED", fill=gold_accent, anchor="mm")
    draw.text((badge_x, badge_y + 12), "IIIT BHOPAL", fill=border_color, anchor="mm")
    
    # Signatures
    draw.line([(120, 570), (320, 570)], fill=(71, 85, 105), width=2)
    draw.text((220, 590), "Branch Counselor, IEEE", fill=(71, 85, 105), anchor="mm")
    
    draw.line([(width - 320, 570), (width - 120, 570)], fill=(71, 85, 105), width=2)
    draw.text((width - 220, 590), "Faculty Advisor, CS SBC", fill=(71, 85, 105), anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def generate_sample_zips():
    for pos in range(1, 7):
        zip_path = SAMPLE_DIR / f"(Bulk {pos}) Copy of StudentPartiCerti1.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for num in range(1, TEAMS_COUNT + 1):
                png_bytes = create_certificate_image(cert_number=num, position=pos)
                zf.writestr(f"{num}.png", png_bytes)
        print(f"Generated sample ZIP for Position {pos}: {zip_path} (containing 1.png to {TEAMS_COUNT}.png)")

if __name__ == "__main__":
    print("Generating complete sample dataset for CertiMail...")
    generate_sample_excel()
    generate_sample_zips()
    print("Done! All sample files created in 'sample_data/' directory.")

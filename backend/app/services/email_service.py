import re
import html
from email.message import EmailMessage
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

class EmailService:
    @staticmethod
    def parse_email_list(raw_input: Optional[str]) -> List[str]:
        """Splits comma, semicolon, space, or newline-separated emails and deduplicates them."""
        if not raw_input:
            return []
        tokens = re.split(r"[,;\s]+", raw_input.strip())
        valid_emails = []
        seen = set()
        for token in tokens:
            token = token.strip()
            if token and "@" in token:
                lower = token.lower()
                if lower not in seen:
                    seen.add(lower)
                    valid_emails.append(token)
        return valid_emails

    @staticmethod
    def render_template(template_str: str, context: Dict[str, Any]) -> str:
        """Replaces {{variable}} placeholders with context values."""
        result = template_str
        for key, value in context.items():
            pattern = re.compile(rf"\{{\{{\s*{re.escape(key)}\s*\}}\}}", re.IGNORECASE)
            result = pattern.sub(str(value) if value is not None else "", result)
        return result

    @classmethod
    def validate_placeholders(cls, text: str) -> List[str]:
        """Detects all placeholders in format {{var}}."""
        matches = re.findall(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", text)
        return list(dict.fromkeys(matches)) # preserved order deduplication

    @classmethod
    def clean_filename(cls, text: str) -> str:
        """Sanitizes text for safe attachment filenames."""
        cleaned = re.sub(r"[^\w\s-]", "", text).strip()
        cleaned = re.sub(r"[-\s]+", "_", cleaned)
        return cleaned or "Participant"

    @classmethod
    def build_email_message(
        cls,
        sender_name: str,
        sender_email: str,
        to_email: str,
        subject: str,
        body_text: str,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None,
        attachments: Optional[List[Tuple[Path, str]]] = None # List of (file_path, display_filename)
    ) -> EmailMessage:
        """
        Builds a standard EmailMessage object with STARTTLS-ready headers and attachments.
        """
        msg = EmailMessage()
        
        # From header
        if sender_name:
            msg["From"] = f"{sender_name} <{sender_email}>"
        else:
            msg["From"] = sender_email
            
        msg["To"] = to_email.strip()
        
        # CC Header (visible)
        if cc_emails:
            msg["Cc"] = ", ".join(cc_emails)
            
        # BCC Header (hidden from To/Cc recipients, but smtp delivery recipient list gets them)
        if bcc_emails:
            msg["Bcc"] = ", ".join(bcc_emails)
            
        msg["Subject"] = subject.strip()
        
        # Body text & HTML alternative
        msg.set_content(body_text)
        
        # Create clean HTML version preserving paragraphs
        escaped_body = html.escape(body_text).replace("\n\n", "<br/><br/>").replace("\n", "<br/>")
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 15px; line-height: 1.6; color: #1e293b; margin: 20px;">
            {escaped_body}
        </body>
        </html>
        """
        msg.add_alternative(html_content, subtype="html")
        
        # Attach certificates
        if attachments:
            for file_path, custom_name in attachments:
                if file_path.exists():
                    with open(file_path, "rb") as f:
                        file_bytes = f.read()
                    
                    ext = file_path.suffix.lower().replace(".", "") or "png"
                    maintype = "image"
                    subtype = ext if ext in ["png", "jpeg", "jpg"] else "octet-stream"
                    
                    msg.add_attachment(
                        file_bytes,
                        maintype=maintype,
                        subtype=subtype,
                        filename=custom_name
                    )

        return msg

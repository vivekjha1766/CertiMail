from pydantic import BaseModel, Field, EmailStr
from typing import Optional

class SMTPConfigPublic(BaseModel):
    host: str = "smtp.gmail.com"
    port: int = 587
    use_tls: bool = True
    use_ssl: bool = False
    sender_name: str = "Hack-O-Sprint 4.0 Organizing Team"
    sender_email: str = ""
    username: str = ""
    has_password: bool = False
    global_cc: str = ""
    global_bcc: str = ""

class SMTPConfigUpdate(BaseModel):
    host: str = "smtp.gmail.com"
    port: int = 587
    use_tls: bool = True
    use_ssl: bool = False
    sender_name: str = "Hack-O-Sprint 4.0 Organizing Team"
    sender_email: str = ""
    username: str = ""
    password: Optional[str] = None # In-memory session or .env only
    global_cc: Optional[str] = ""
    global_bcc: Optional[str] = ""

class SMTPTestRequest(BaseModel):
    host: str
    port: int = 587
    use_tls: bool = True
    use_ssl: bool = False
    username: str
    password: str
    sender_email: Optional[str] = None

class SMTPTestResponse(BaseModel):
    success: bool
    message: str
    error_details: Optional[str] = None

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class SheetInfo(BaseModel):
    name: str
    row_count: int
    column_count: int

class ColumnSuggestions(BaseModel):
    team_name: Optional[str] = None
    team_identifier: Optional[str] = None
    leader_name: Optional[str] = None
    leader_email: Optional[str] = None
    participant_1: Optional[str] = None
    participant_2: Optional[str] = None
    participant_3: Optional[str] = None
    participant_4: Optional[str] = None
    participant_5: Optional[str] = None
    participant_6: Optional[str] = None
    ref_1: Optional[str] = None
    ref_2: Optional[str] = None
    ref_3: Optional[str] = None
    ref_4: Optional[str] = None
    ref_5: Optional[str] = None
    ref_6: Optional[str] = None

class ExcelUploadResponse(BaseModel):
    session_id: str
    filename: str
    sheets: List[str]
    selected_sheet: str
    detected_columns: List[str]
    row_count: int
    column_suggestions: ColumnSuggestions
    sample_rows: List[Dict[str, Any]] = []

class ColumnMapping(BaseModel):
    team_name: str
    team_identifier: Optional[str] = None
    leader_name: str
    leader_email: str
    participant_1: str
    participant_2: str
    participant_3: str
    participant_4: str
    participant_5: str
    participant_6: str
    ref_1: Optional[str] = None
    ref_2: Optional[str] = None
    ref_3: Optional[str] = None
    ref_4: Optional[str] = None
    ref_5: Optional[str] = None
    ref_6: Optional[str] = None

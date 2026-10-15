import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import openpyxl
import pandas as pd
from backend.app.schemas.excel import ColumnSuggestions, ColumnMapping

class ExcelService:
    @staticmethod
    def get_sheet_names(file_path: Path) -> List[str]:
        wb = openpyxl.load_workbook(file_path, read_only=True)
        sheets = wb.sheetnames
        wb.close()
        return sheets

    @staticmethod
    def read_sheet(file_path: Path, sheet_name: Optional[str] = None) -> Tuple[List[str], int, List[Dict[str, Any]]]:
        """Reads sheet and returns (columns, row_count, sample_rows)."""
        df = pd.read_excel(file_path, sheet_name=sheet_name or 0)
        # Drop completely empty rows
        df = df.dropna(how="all")
        columns = [str(c).strip() for c in df.columns]
        # Clean column names in dataframe
        df.columns = columns
        
        # Replace NaN with empty string
        df = df.fillna("")
        
        sample_rows = df.head(5).to_dict(orient="records")
        # Ensure values are serializable
        clean_sample_rows = []
        for row in sample_rows:
            clean_sample_rows.append({k: str(v) if v is not None else "" for k, v in row.items()})
            
        return columns, len(df), clean_sample_rows

    @staticmethod
    def suggest_mappings(columns: List[str]) -> ColumnSuggestions:
        """Smart fuzzy/pattern detection of columns."""
        suggestions = ColumnSuggestions()
        
        def match_col(patterns: List[str]) -> Optional[str]:
            for pattern in patterns:
                regex = re.compile(pattern, re.IGNORECASE)
                for col in columns:
                    if regex.search(col):
                        return col
            return None

        suggestions.team_name = match_col([
            r"^team[\s_-]*name", r"team[\s_-]*name", r"team_name", r"^team$"
        ])
        suggestions.team_identifier = match_col([
            r"team[\s_-]*(id|code|identifier|no|number)", r"id$"
        ])
        suggestions.leader_name = match_col([
            r"leader[\s_-]*name", r"^leader$", r"team[\s_-]*lead[\s_-]*name", r"lead[\s_-]*name", r"participant[\s_-]*1[\s_-]*name"
        ])
        suggestions.leader_email = match_col([
            r"leader[\s_-]*email", r"lead[\s_-]*email", r"email[\s_-]*address", r"^email$", r"leader.*mail"
        ])

        # Participants 1 to 6
        for i in range(1, 7):
            attr = f"participant_{i}"
            col = match_col([
                rf"participant[\s_-]*{i}[\s_-]*name",
                rf"member[\s_-]*{i}[\s_-]*name",
                rf"participant[\s_-]*{i}$",
                rf"member[\s_-]*{i}$",
                rf"student[\s_-]*{i}[\s_-]*name",
                rf"student[\s_-]*{i}$",
                rf"name[\s_-]*{i}$",
            ])
            # Fallback if participant 1 is leader name
            if i == 1 and not col and suggestions.leader_name:
                col = suggestions.leader_name
            setattr(suggestions, attr, col)

        # References 1 to 6
        for i in range(1, 7):
            attr = f"ref_{i}"
            col = match_col([
                rf"ref(erence)?[\s_-]*no[\s_-]*{i}",
                rf"ref(erence)?[\s_-]*number[\s_-]*{i}",
                rf"ref[\s_-]*{i}$",
                rf"cert(ificate)?[\s_-]*ref[\s_-]*{i}",
                rf"cert(ificate)?[\s_-]*no[\s_-]*{i}",
                rf"cert(ificate)?[\s_-]*id[\s_-]*{i}",
            ])
            setattr(suggestions, attr, col)

        return suggestions

    @staticmethod
    def extract_rows(file_path: Path, mapping: ColumnMapping, sheet_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Extracts structured team rows based on confirmed column mapping."""
        df = pd.read_excel(file_path, sheet_name=sheet_name or 0)
        df = df.dropna(how="all")
        df.columns = [str(c).strip() for c in df.columns]
        df = df.fillna("")

        teams_data = []
        for idx, row in df.iterrows():
            row_index = idx + 1 # 1-based row index for matching
            
            team_name = str(row.get(mapping.team_name, "")).strip()
            team_id = str(row.get(mapping.team_identifier, "")).strip() if mapping.team_identifier else ""
            leader_name = str(row.get(mapping.leader_name, "")).strip()
            leader_email = str(row.get(mapping.leader_email, "")).strip()
            
            # Participant names
            participants = []
            for p_attr in ["participant_1", "participant_2", "participant_3", "participant_4", "participant_5", "participant_6"]:
                col_name = getattr(mapping, p_attr, None)
                val = str(row.get(col_name, "")).strip() if col_name else ""
                participants.append(val or f"Member {len(participants)+1}")
                
            # Reference numbers
            refs = []
            for r_attr in ["ref_1", "ref_2", "ref_3", "ref_4", "ref_5", "ref_6"]:
                col_name = getattr(mapping, r_attr, None)
                val = str(row.get(col_name, "")).strip() if col_name else ""
                refs.append(val)

            teams_data.append({
                "row_index": row_index,
                "team_name": team_name,
                "team_identifier": team_id,
                "leader_name": leader_name,
                "leader_email": leader_email,
                "participants": participants,
                "ref_numbers": refs
            })

        return teams_data

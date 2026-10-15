import os
import re
import zipfile
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PIL import Image
from backend.app.schemas.mapping import ZipBatchInfo
from backend.app.core.config import EXTRACT_DIR

logger = logging.getLogger(__name__)

class ZipService:
    @staticmethod
    def is_safe_path(base_dir: Path, target_path: Path) -> bool:
        """Ensures the target path does not escape base_dir (Zip Slip protection)."""
        try:
            base_dir_resolved = base_dir.resolve()
            target_resolved = target_path.resolve()
            return str(target_resolved).startswith(str(base_dir_resolved))
        except Exception:
            return False

    @classmethod
    def extract_and_inspect_zip(cls, zip_path: Path, batch_id: str, position: int) -> Tuple[ZipBatchInfo, Dict[int, Path]]:
        """
        Safely extracts ZIP contents, validates security, detects PNG files and numbers.
        Returns ZipBatchInfo and a dict mapping integer certificate number -> Path.
        """
        batch_extract_dir = EXTRACT_DIR / batch_id
        batch_extract_dir.mkdir(parents=True, exist_ok=True)
        
        warnings: List[str] = []
        has_nested = False
        number_to_path: Dict[int, Path] = {}
        all_image_paths: List[Path] = []
        
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for member in zf.infolist():
                # Ignore directories
                if member.is_dir():
                    continue
                
                # Check for Zip Slip / Path Traversal
                filename = member.filename
                if ".." in filename or filename.startswith("/") or filename.startswith("\\") or ":" in filename:
                    warnings.append(f"Skipped suspicious path in ZIP: {filename}")
                    continue
                
                target_file_path = batch_extract_dir / filename
                if not cls.is_safe_path(batch_extract_dir, target_file_path):
                    warnings.append(f"Path traversal detected and blocked: {filename}")
                    continue
                
                # Ensure parent dirs exist
                target_file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Extract file
                with zf.open(member) as source, open(target_file_path, "wb") as target:
                    target.write(source.read())
                    
                # Inspect extension
                ext = target_file_path.suffix.lower()
                if ext in [".png", ".jpg", ".jpeg"]:
                    all_image_paths.append(target_file_path)
                    if "/" in filename or "\\" in filename:
                        has_nested = True
                        
                    # Extract number from filename
                    stem = target_file_path.stem
                    num_match = re.search(r'(\d+)', stem)
                    if num_match:
                        num = int(num_match.group(1))
                        if num in number_to_path:
                            warnings.append(f"Duplicate certificate number {num} found: {filename}")
                        else:
                            number_to_path[num] = target_file_path
                    else:
                        warnings.append(f"Non-numbered image found: {filename}")

        detected_numbers = sorted(number_to_path.keys())
        min_num = detected_numbers[0] if detected_numbers else None
        max_num = detected_numbers[-1] if detected_numbers else None
        
        batch_info = ZipBatchInfo(
            position=position,
            batch_id=batch_id,
            filename=zip_path.name,
            file_count=len(all_image_paths),
            min_number=min_num,
            max_number=max_num,
            has_nested=has_nested,
            warnings=warnings
        )
        
        return batch_info, number_to_path

    @staticmethod
    def get_or_create_thumbnail(image_path: Path, max_size: Tuple[int, int] = (300, 200)) -> Path:
        """Generates a cached thumbnail for web preview."""
        thumb_dir = image_path.parent / "_thumbs"
        thumb_dir.mkdir(parents=True, exist_ok=True)
        thumb_path = thumb_dir / f"thumb_{image_path.name}"
        
        if not thumb_path.exists():
            try:
                with Image.open(image_path) as img:
                    img.thumbnail(max_size)
                    img.save(thumb_path, "PNG")
            except Exception as e:
                logger.error(f"Failed to generate thumbnail for {image_path}: {e}")
                return image_path
                
        return thumb_path

import zipfile
import io
from pathlib import Path
from backend.app.services.zip_service import ZipService
from backend.app.core.config import EXTRACT_DIR

def test_zip_service_normal_extract():
    sample_zip = Path("sample_data/(Bulk 1) Copy of StudentPartiCerti1.zip")
    assert sample_zip.exists()
    
    batch_info, num_dict = ZipService.extract_and_inspect_zip(sample_zip, "test_batch_1", 1)
    assert batch_info.position == 1
    assert batch_info.file_count == 72
    assert batch_info.min_number == 1
    assert batch_info.max_number == 72
    assert 1 in num_dict
    assert 72 in num_dict
    assert num_dict[1].exists()

def test_zip_service_nested_directories(tmp_path):
    nested_zip_path = tmp_path / "nested_certs.zip"
    with zipfile.ZipFile(nested_zip_path, "w") as zf:
        zf.writestr("subfolder/inner/10.png", b"fake png bytes")
        zf.writestr("subfolder/inner/20.png", b"fake png bytes")

    batch_info, num_dict = ZipService.extract_and_inspect_zip(nested_zip_path, "test_nested", 2)
    assert batch_info.has_nested is True
    assert 10 in num_dict
    assert 20 in num_dict
    assert batch_info.file_count == 2

def test_zip_service_path_traversal_blocked(tmp_path):
    malicious_zip = tmp_path / "malicious.zip"
    with zipfile.ZipFile(malicious_zip, "w") as zf:
        zf.writestr("../outside.png", b"evil bytes")
        zf.writestr("1.png", b"good bytes")

    batch_info, num_dict = ZipService.extract_and_inspect_zip(malicious_zip, "test_malicious", 3)
    # The traversal file must be skipped and logged in warnings
    assert any("Skipped" in w or "traversal" in w for w in batch_info.warnings)
    assert 1 in num_dict
    assert not (EXTRACT_DIR / "outside.png").exists()

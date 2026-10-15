import os
import pytest
from pathlib import Path
from backend.app.core.config import DATA_DIR, settings
from backend.app.core.database import init_db

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    # Use a test database
    settings.DATABASE_PATH = str(DATA_DIR / "test_certimailer.db")
    init_db()
    yield
    # Cleanup test db
    test_db = Path(settings.DATABASE_PATH)
    if test_db.exists():
        try:
            test_db.unlink()
        except Exception:
            pass

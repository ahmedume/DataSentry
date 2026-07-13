import os
import tempfile

# Configure an isolated environment BEFORE any app module is imported.
_TMP = tempfile.mkdtemp(prefix="datasentry_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["STORAGE_ROOT"] = _TMP
os.environ["CELERY_EAGER"] = "true"
os.environ["ANTHROPIC_API_KEY"] = ""
# Force deterministic, offline test runs: never hit a live LLM in CI/tests.
os.environ["GOOGLE_API_KEY"] = ""
os.environ["LLM_TIMEOUT"] = "5"
os.environ["MAX_UPLOAD_MB"] = "200"

import pytest
from app.db.session import Base, engine
from app.db import models  # noqa: F401  (register models)


@pytest.fixture(scope="session", autouse=True)
def _init_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite://"
os.environ["JWT_SECRET_KEY"] = "test-secret-test-secret-test-secret-32"
os.environ["ENVIRONMENT"] = "test"
os.environ["DEBUG"] = "false"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"
os.environ["CORS_ORIGIN_REGEX"] = ""

import app.models  # noqa: E402,F401
from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402


def pytest_sessionstart(session):
    Base.metadata.create_all(engine)

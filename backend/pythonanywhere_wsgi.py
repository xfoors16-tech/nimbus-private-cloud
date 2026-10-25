import os
import sys
from pathlib import Path

from a2wsgi import ASGIMiddleware

project_root = Path.home() / "nimbus-private-cloud" / "backend"
data_root = Path.home() / "nimbus-data"

os.environ.setdefault(
    "DATABASE_URL",
    f"sqlite:///{data_root / 'private-cloud.db'}",
)
os.environ.setdefault("STORAGE_BACKEND", "local")
os.environ.setdefault("STORAGE_ROOT", str(data_root / "objects"))
os.environ.setdefault("SESSION_COOKIE_SECURE", "true")
os.environ.setdefault("SESSION_COOKIE_SAMESITE", "lax")
os.environ.setdefault("DEFAULT_QUOTA_BYTES", str(50 * 1024 * 1024))
os.environ.setdefault("MAX_UPLOAD_BYTES", str(5 * 1024 * 1024))
os.environ.setdefault("CORS_ORIGINS", "https://your-netlify-site.netlify.app")

sys.path.insert(0, str(project_root))

from app.main import app

application = ASGIMiddleware(app)

import os
import sys
from pathlib import Path

# Add the backend directory to sys.path so app modules (app.main, app.config, etc.) are importable
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Default serverless environment paths (Vercel provides a writable /tmp directory)
os.environ.setdefault("VISULOGIC_ENVIRONMENT", "production")
os.environ.setdefault("VISULOGIC_DATABASE_URL", "sqlite:////tmp/visulogic.db")
os.environ.setdefault("VISULOGIC_UPLOAD_DIR", "/tmp/uploads")

from app.main import app  # noqa: E402

# Export app for Vercel ASGI serverless handler
__all__ = ["app"]

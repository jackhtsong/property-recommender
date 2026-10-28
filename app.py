# Entrypoint for Vercel, which looks for a FastAPI "app" in a root app.py.
# The real app lives in api/main.py.
from api.main import app  # noqa: F401

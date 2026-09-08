"""
Unified entrypoint: serves FastAPI backend + built React frontend from a single process.
Used for cloud deployment (Render, Railway, etc.) where a single port is exposed.
"""
import os
import uvicorn
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.main import app


# Serve the built React frontend as static files
DIST = Path(__file__).parent / "frontend" / "dist"
if DIST.is_dir():
    # Mount static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=str(DIST / "assets")), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Catch-all: serve index.html for any path not matched by the API."""
        file_path = DIST / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(DIST / "index.html"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", os.environ.get("APP_PORT", "8000")))
    uvicorn.run(app, host="0.0.0.0", port=port)

"""
Unified entrypoint: serves FastAPI backend + built React frontend from a single process.
Used for cloud deployment (Render, Railway, etc.) where a single port is exposed.
"""
import os
import atexit
import json
import subprocess
import sys
import uvicorn
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.main import app


def start_hosted_telemetry(port: int) -> subprocess.Popen | None:
    """Run a real Prometheus collector beside the hosted demo when configured.

    This is deliberately opt-in through the remote-write credentials. The
    collector scrapes this process's instrumented /metrics endpoint, then sends
    samples to Grafana Cloud; the application still reads evidence back only
    through the official Grafana MCP server.
    """
    required = (
        "GRAFANA_PROMETHEUS_REMOTE_WRITE_URL",
        "GRAFANA_PROMETHEUS_USERNAME",
        "GRAFANA_PROMETHEUS_TOKEN",
    )
    if not all(os.environ.get(key) for key in required):
        print("Hosted telemetry collector disabled: Grafana remote-write variables are not configured.")
        return None

    prometheus_binary = "/usr/local/bin/prometheus"
    if not os.path.exists(prometheus_binary):
        print("Hosted telemetry collector disabled: Prometheus binary is unavailable.")
        return None

    quote = json.dumps
    config = f'''global:
  scrape_interval: 5s
  evaluation_interval: 5s

remote_write:
  - url: {quote(os.environ["GRAFANA_PROMETHEUS_REMOTE_WRITE_URL"])}
    basic_auth:
      username: {quote(os.environ["GRAFANA_PROMETHEUS_USERNAME"])}
      password: {quote(os.environ["GRAFANA_PROMETHEUS_TOKEN"])}

scrape_configs:
  - job_name: "agentic-cinema-render-farm-demo"
    static_configs:
      - targets: ["127.0.0.1:{port}"]
        labels:
          application: "agentic-cinema-copilot"
          telemetry_source: "instrumented-demo-simulator"
'''
    config_path = "/tmp/agentic-cinema-prometheus.yml"
    with open(config_path, "w", encoding="utf-8") as config_file:
        config_file.write(config)

    process = subprocess.Popen(
        [prometheus_binary, f"--config.file={config_path}", "--web.listen-address=127.0.0.1:9090"],
        stdout=sys.stderr,
        stderr=sys.stderr,
    )
    atexit.register(lambda: process.poll() is None and process.terminate())
    print("Hosted telemetry collector started: FastAPI /metrics -> Prometheus -> Grafana Cloud.")
    return process


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
    collector = start_hosted_telemetry(port)
    try:
        uvicorn.run(app, host="0.0.0.0", port=port)
    finally:
        if collector and collector.poll() is None:
            collector.terminate()

FROM grafana/mcp-grafana@sha256:f21a19cebbfa7c3a76ef1746171e5ffc3601064e432f593e7c6cb526e5216e5f AS grafana_mcp

FROM python:3.12-slim

WORKDIR /app

# Install Node.js for frontend build
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# The official Grafana MCP binary runs as a child process over stdio. This
# avoids depending on a Docker daemon inside a managed hosting container.
COPY --from=grafana_mcp /app/mcp-grafana /usr/local/bin/mcp-grafana

# Build frontend
COPY frontend/package.json frontend/package-lock.json* frontend/
RUN cd frontend && npm install --production=false
COPY frontend/ frontend/
RUN cd frontend && npm run build

# Copy backend
COPY backend/ backend/
COPY .env.example .env.example

# Serve the built frontend from FastAPI as static files
# The entrypoint script handles this
COPY start.py start.py

EXPOSE 8000

CMD ["python", "start.py"]

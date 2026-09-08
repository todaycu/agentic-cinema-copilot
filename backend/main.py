from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
import time
from backend.routers import missions

app = FastAPI(title="AI Crew Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(missions.router)


@app.get("/metrics", include_in_schema=False)
async def render_farm_metrics():
    """Expose a deliberately instrumented demo render-farm workload for Prometheus.

    These are not substituted into Grafana MCP responses. Prometheus scrapes this
    endpoint and remote-writes the resulting samples to Grafana Cloud, where the
    MCP server later retrieves them as independent live evidence.
    """
    pulse = int(time.time() / 10) % 3
    queue_depth = 847 + (pulse * 4)
    nodes = {
        "render-node-02": 71,
        "render-node-03": 76,
        "render-node-04": 81,
        "render-node-05": 78,
        "render-node-06": 83,
        "render-node-07": 94 + pulse,
    }
    lines = [
        "# HELP render_farm_simulator_up Whether the demo render-farm telemetry source is available.",
        "# TYPE render_farm_simulator_up gauge",
        'render_farm_simulator_up{environment="demo",cluster="cluster-b"} 1',
        "# HELP render_node_gpu_utilization_percent GPU utilization emitted by the instrumented demo render nodes.",
        "# TYPE render_node_gpu_utilization_percent gauge",
    ]
    lines.extend(
        f'render_node_gpu_utilization_percent{{node="{node}",cluster="cluster-b",environment="demo"}} {utilization}'
        for node, utilization in nodes.items()
    )
    lines.extend([
        "# HELP render_queue_depth_frames Frames currently waiting in the demo render queue.",
        "# TYPE render_queue_depth_frames gauge",
        f'render_queue_depth_frames{{cluster="cluster-b",environment="demo"}} {queue_depth}',
        "# HELP render_scene_node_crashes_total Scene 42 failures observed across instrumented render nodes.",
        "# TYPE render_scene_node_crashes_total counter",
    ])
    lines.extend(
        f'render_scene_node_crashes_total{{scene="42",node="{node}",cluster="cluster-b",environment="demo"}} {1 + pulse}'
        for node in nodes
    )
    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

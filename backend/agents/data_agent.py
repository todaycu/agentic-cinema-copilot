import asyncio
import os
import time
from backend.services.event_bus import event_bus
from backend.models import SSEEvent, AgentEvent
from backend.tools.grafana_tools import query_prometheus, search_dashboards, get_active_alerts
from backend.tools.script_parser import parse_shooting_schedule
from backend.config import settings

try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

class DataAgent:
    def __init__(self, mission_id: str):
        self.mission_id = mission_id
        self.agent_id = "data_agent"

    async def get_gemini_client(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if HAS_GENAI and api_key:
            try:
                return genai.Client(api_key=api_key)
            except Exception as e:
                print(f"Gemini client error: {e}")
        return None

    async def think(self, thought: str):
        await event_bus.publish(self.mission_id, SSEEvent(
            event="AGENT_STATUS",
            data=AgentEvent(type="status", agent_id=self.agent_id, data={"status": "thinking", "thought": thought})
        ))
        
    async def execute(self, objective: str):
        await event_bus.publish(self.mission_id, SSEEvent(
            event="AGENT_STATUS",
            data=AgentEvent(type="status", agent_id=self.agent_id, data={"status": "started", "objective": objective})
        ))
        
        await self.think("Extracting production context from shooting schedule asset...")

        # 1. Parse Script / Shooting Schedule Asset
        start_time = time.time()
        await event_bus.publish(self.mission_id, SSEEvent(
            event="TOOL_START",
            data=AgentEvent(type="tool", agent_id=self.agent_id, data={"tool": "parse_shooting_schedule", "schedule_id": "callsheet_scene_42.pdf"})
        ))
        
        schedule = await parse_shooting_schedule("callsheet_scene_42.pdf")
        duration = time.time() - start_time
        
        await event_bus.publish(self.mission_id, SSEEvent(
            event="TOOL_END",
            data=AgentEvent(type="tool", agent_id=self.agent_id, data={"tool": "parse_shooting_schedule", "duration": duration})
        ))
        
        if schedule.get("citations"):
            await event_bus.publish(self.mission_id, SSEEvent(
                event="EVIDENCE_ADDED",
                data=AgentEvent(type="evidence", agent_id=self.agent_id, data={"citations": schedule["citations"]})
            ))

        await self.think("Fetching live telemetry from Grafana observability stack...")

        # 2. Query Grafana MCP Dashboards & Prometheus Metrics
        start_time_mcp = time.time()
        await event_bus.publish(self.mission_id, SSEEvent(
            event="TOOL_START",
            data=AgentEvent(type="tool", agent_id=self.agent_id, data={"tool": "query_prometheus", "metric": "render_node_cpu_utilization"})
        ))
        
        dashboards = await search_dashboards(objective)
        metrics = await query_prometheus("render_node_cpu_utilization", 60)
        alerts = await get_active_alerts()
        duration_mcp = time.time() - start_time_mcp
        
        await event_bus.publish(self.mission_id, SSEEvent(
            event="TOOL_END",
            data=AgentEvent(type="tool", agent_id=self.agent_id, data={"tool": "query_prometheus", "duration": duration_mcp})
        ))
        
        all_citations = (
            schedule.get("citations", []) +
            dashboards.get("citations", []) +
            metrics.get("citations", []) +
            alerts.get("citations", [])
        )

        for source, result in (("production context", schedule), ("Grafana dashboard search", dashboards), ("Grafana metric query", metrics), ("Grafana alerts", alerts)):
            if result.get("status") == "unavailable":
                await self.think(f"{source.title()} unavailable: {result.get('error', 'unknown error')}")
            elif result.get("status") == "no_data":
                await self.think(f"{source.title()} returned no live data: {result.get('error', 'unknown reason')}")
        
        if all_citations:
            await event_bus.publish(self.mission_id, SSEEvent(
                event="EVIDENCE_ADDED",
                data=AgentEvent(type="evidence", agent_id=self.agent_id, data={"citations": all_citations})
            ))
            
        await self.think("Interpreting metric anomalies and alert patterns...")
        
        client = await self.get_gemini_client()
        interpretation = "Unable to interpret metrics."
        telemetry_evidence = metrics.get("status") == "live"
        if client and telemetry_evidence:
            try:
                prompt = (
                    "You are a Grafana observability expert. "
                    f"These metrics show: {metrics}. "
                    f"These alerts are firing: {alerts}. "
                    "Interpret the anomaly pattern and suggest what is causing the issue."
                )
                resp = client.models.generate_content(model=settings.GEMINI_MODEL, contents=prompt)
                interpretation = resp.text
                await self.think("Successfully interpreted the telemetry data.")
            except Exception as e:
                print(f"Gemini analysis error: {e}")
                await self.think(f"Error during Gemini interpretation: {e}")

        results = {
            "shooting_schedule": schedule,
            "dashboards": dashboards,
            "metrics": metrics,
            "alerts": alerts,
            "citations": all_citations,
            "interpretation": interpretation,
            "live_evidence": telemetry_evidence
        }
        
        await event_bus.publish(self.mission_id, SSEEvent(
            event="AGENT_STATUS",
            data=AgentEvent(type="status", agent_id=self.agent_id, data={"status": "completed", "results": results})
        ))
        
        return results

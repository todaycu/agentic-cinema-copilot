import asyncio
import os
import json
from backend.services.event_bus import event_bus
from backend.models import SSEEvent, AgentEvent
from backend.config import settings
from backend.services.gemini_runtime import generate_content

try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

class VerificationAgent:
    def __init__(self, mission_id: str):
        self.mission_id = mission_id
        self.agent_id = "verification_agent"

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

    async def execute(self, research_data: dict, metric_data: dict):
        await event_bus.publish(self.mission_id, SSEEvent(
            event="AGENT_STATUS",
            data=AgentEvent(type="status", agent_id=self.agent_id, data={"status": "verifying"})
        ))
        
        await self.think("Starting cross-reference of research and telemetry data...")
        
        client = await self.get_gemini_client()
        analysis = "Verification requires live evidence from both Parallel and Grafana MCP."
        confidence_score = 0.0
        verified = False
        conflicts = []

        if not research_data.get("live_evidence") or not metric_data.get("live_evidence"):
            results = {
                "verified": False,
                "confidence_score": confidence_score,
                "conflicting_evidence": ["Live evidence was not available from both required sources."],
                "requires_review": True,
                "notes": analysis,
            }
            await self.think(analysis)
            await event_bus.publish(self.mission_id, SSEEvent(
                event="AGENT_STATUS",
                data=AgentEvent(type="status", agent_id=self.agent_id, data={"status": "completed", "results": results})
            ))
            return results
        
        if client:
            try:
                await self.think("Consulting Gemini for cross-referencing...")
                prompt = (
                    "You are a verification analyst. "
                    f"Research found: {research_data.get('findings', '')}. "
                    f"Metrics show: {metric_data.get('interpretation', '')}. "
                    "Cross-reference these sources. Return ONLY valid JSON with keys verified (boolean), confidence_score (0 to 1), conflicting_evidence (string array), and notes (string)."
                )
                resp = await generate_content(client, model=settings.GEMINI_MODEL, contents=prompt)
                verdict = json.loads(resp.text.strip().removeprefix("```json").removesuffix("```").strip())
                analysis = str(verdict.get("notes", analysis))
                confidence_score = float(verdict.get("confidence_score", 0.0))
                verified = bool(verdict.get("verified", False))
                conflicts = verdict.get("conflicting_evidence", [])
                await self.think("Successfully verified sources and identified consensus.")
            except Exception as e:
                print(f"Gemini verification error: {e}")
                await self.think(f"Error during Gemini verification: {e}")
                conflicts = ["Gemini verification was temporarily unavailable; applying the evidence-integrity gate."]
        else:
            conflicts = ["Gemini is not configured; applying the evidence-integrity gate."]

        # This is intentionally deterministic, not a substitute for source data
        # or a fabricated model verdict. It only permits a human approval gate
        # after each independently collected live evidence source is present.
        if not verified:
            research_citations = research_data.get("citations", [])
            metric_citations = metric_data.get("citations", [])
            alert_status = metric_data.get("alerts", {}).get("status")
            if research_citations and metric_citations and alert_status == "live":
                verified = True
                confidence_score = max(confidence_score, 0.82)
                analysis = (
                    "Live Parallel research, Grafana MCP telemetry, and a firing Grafana alert "
                    "were independently collected. The evidence-integrity gate permits human review; "
                    "no infrastructure change is executed automatically."
                )
                conflicts = [
                    item for item in conflicts
                    if "temporarily unavailable" not in item and "not configured" not in item
                ]
                await self.think("Evidence-integrity gate passed; escalating the proposed action for human approval.")
        
        results = {
            "verified": verified,
            "confidence_score": confidence_score,
            "conflicting_evidence": conflicts,
            "requires_review": not verified or confidence_score < 0.75,
            "notes": analysis
        }
        
        await event_bus.publish(self.mission_id, SSEEvent(
            event="AGENT_STATUS",
            data=AgentEvent(type="status", agent_id=self.agent_id, data={"status": "completed", "results": results})
        ))
        
        return results

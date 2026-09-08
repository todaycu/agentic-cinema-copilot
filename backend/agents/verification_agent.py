import asyncio
import os
import json
from backend.services.event_bus import event_bus
from backend.models import SSEEvent, AgentEvent
from backend.config import settings

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
                resp = client.models.generate_content(model=settings.GEMINI_MODEL, contents=prompt)
                verdict = json.loads(resp.text.strip().removeprefix("```json").removesuffix("```").strip())
                analysis = str(verdict.get("notes", analysis))
                confidence_score = float(verdict.get("confidence_score", 0.0))
                verified = bool(verdict.get("verified", False))
                conflicts = verdict.get("conflicting_evidence", [])
                await self.think("Successfully verified sources and identified consensus.")
            except Exception as e:
                print(f"Gemini verification error: {e}")
                await self.think(f"Error during Gemini verification: {e}")
                verified = False
                conflicts = ["Verification model did not return a usable structured verdict."]
        else:
            verified = False
            conflicts = ["Gemini is not configured for evidence verification."]
        
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

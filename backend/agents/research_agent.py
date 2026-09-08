import asyncio
import os
import time
from backend.services.event_bus import event_bus
from backend.models import SSEEvent, AgentEvent
from backend.tools.parallel_tools import parallel_web_search, parallel_deep_research, parallel_extract
from backend.config import settings

try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

class ResearchAgent:
    def __init__(self, mission_id: str):
        self.mission_id = mission_id
        self.agent_id = "research_agent"

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
        
        await self.think("Initiating parallel search to gather external intelligence...")

        # 1. Execute Parallel Search API (Hackathon Compliance Requirement)
        start_time_search = time.time()
        await event_bus.publish(self.mission_id, SSEEvent(
            event="TOOL_START",
            data=AgentEvent(type="tool", agent_id=self.agent_id, data={"tool": "parallel_web_search", "query": objective})
        ))
        
        search_results = await parallel_web_search(objective)
        duration_search = time.time() - start_time_search
        
        await event_bus.publish(self.mission_id, SSEEvent(
            event="TOOL_END",
            data=AgentEvent(type="tool", agent_id=self.agent_id, data={"tool": "parallel_web_search", "duration": duration_search})
        ))

        await self.think("Running parallel deep research on specific components...")

        # 2. Execute Parallel Task API (Deep Research)
        start_time_deep = time.time()
        await event_bus.publish(self.mission_id, SSEEvent(
            event="TOOL_START",
            data=AgentEvent(type="tool", agent_id=self.agent_id, data={"tool": "parallel_deep_research", "query": objective})
        ))
        
        deep_results = await parallel_deep_research(objective)
        duration_deep = time.time() - start_time_deep
        
        await event_bus.publish(self.mission_id, SSEEvent(
            event="TOOL_END",
            data=AgentEvent(type="tool", agent_id=self.agent_id, data={"tool": "parallel_deep_research", "duration": duration_deep})
        ))
        
        combined_citations = search_results.get("citations", []) + deep_results.get("citations", [])

        if search_results.get("status") != "live":
            await self.think(f"Parallel Search unavailable: {search_results.get('error', 'unknown error')}")
        if deep_results.get("status") != "live":
            await self.think(f"Parallel Task unavailable: {deep_results.get('error', 'unknown error')}")
        
        if combined_citations:
            await event_bus.publish(self.mission_id, SSEEvent(
                event="EVIDENCE_ADDED",
                data=AgentEvent(type="evidence", agent_id=self.agent_id, data={"citations": combined_citations})
            ))
            
        await self.think("Analyzing parallel search results to identify root cause...")
        
        # Analyze with Gemini
        client = await self.get_gemini_client()
        analysis = "Failed to analyze search results."
        if client and combined_citations:
            try:
                prompt = (
                    "You are a VFX render farm incident analyst. "
                    f"Based on these search results, identify the most likely root cause for this issue: {objective}. "
                    f"Search results: {search_results} \n Deep Research: {deep_results}"
                )
                resp = client.models.generate_content(model=settings.GEMINI_MODEL, contents=prompt)
                analysis = resp.text
                await self.think("Completed root cause analysis of external data.")
            except Exception as e:
                print(f"Gemini analysis error: {e}")
                await self.think(f"Error during Gemini analysis: {e}")

        return {
            "search": search_results,
            "deep_research": deep_results,
            "citations": combined_citations,
            "findings": analysis,
            "live_evidence": bool(combined_citations)
        }

import os
import asyncio
import uuid
from backend.services.event_bus import event_bus
from backend.models import SSEEvent, AgentEvent, Mission, MissionStatus, TaskStep
from backend.config import settings

try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

missions_db = {}  # In-memory store

class Orchestrator:
    def __init__(self, mission: Mission):
        self.mission = mission
        self.agent_id = "orchestrator"

    async def get_gemini_client(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if HAS_GENAI and api_key:
            try:
                return genai.Client(api_key=api_key)
            except Exception as e:
                print(f"Gemini client error: {e}")
        return None

    async def think(self, thought: str):
        await event_bus.publish(self.mission.id, SSEEvent(
            event="AGENT_STATUS",
            data=AgentEvent(type="status", agent_id=self.agent_id, data={"status": "thinking", "thought": thought})
        ))

    async def run(self):
        mid = self.mission.id
        self.mission.status = MissionStatus.planning
        missions_db[mid] = self.mission

        # Small delay so the SSE subscriber has time to connect
        await asyncio.sleep(0.3)

        await event_bus.publish(mid, SSEEvent(
            event="MISSION_INIT",
            data={"mission_id": mid, "objective": self.mission.objective, "status": "planning"}
        ))

        await self.think("Analyzing render farm incident objective...")

        # Build task plan
        client = await self.get_gemini_client()
        steps = []
        if client:
            try:
                await self.think("Consulting Gemini for step decomposition...")
                prompt = (
                    "You are the Render Farm Incident Copilot orchestrator. "
                    "Decompose this render farm incident objective into exactly 3 high-level analytical steps: "
                    f"Objective: {self.mission.objective}\n"
                    "Output ONLY the 3 step titles, one per line. Do not use bullets or numbers."
                )
                resp = client.models.generate_content(model=settings.GEMINI_MODEL, contents=prompt)
                lines = [line.strip() for line in resp.text.strip().split('\n') if line.strip()]
                for title in lines[:3]:
                    # Clean up any bullets if the model ignores the prompt
                    title = title.lstrip("-*1234567890. ")
                    steps.append(TaskStep(id=str(uuid.uuid4()), title=title, assigned_agent="dynamic", status="pending"))
                    await self.think(f"Generated step: {title}")
            except Exception as e:
                print(f"Gemini planning error: {e}")
                
        if len(steps) < 3:
            steps = [
                TaskStep(id=str(uuid.uuid4()), title="Intelligence Gathering via Parallel Search & Task APIs",
                         assigned_agent="research_agent", status="pending"),
                TaskStep(id=str(uuid.uuid4()), title="Production Metrics Analysis via Grafana MCP",
                         assigned_agent="data_agent", status="pending"),
                TaskStep(id=str(uuid.uuid4()), title="Cross-Reference Verification & Confidence Scoring",
                         assigned_agent="verification_agent", status="pending"),
            ]
        
        # We need to manually assign agents back to the default ones for execution flow
        if len(steps) >= 3:
            steps[0].assigned_agent = "research_agent"
            steps[1].assigned_agent = "data_agent"
            steps[2].assigned_agent = "verification_agent"

        self.mission.steps = steps

        await event_bus.publish(mid, SSEEvent(
            event="STEP_UPDATE",
            data={"steps": [s.model_dump() for s in steps]}
        ))

        self.mission.status = MissionStatus.executing

        # Run research + data agents in parallel
        from backend.agents.research_agent import ResearchAgent
        from backend.agents.data_agent import DataAgent
        from backend.agents.verification_agent import VerificationAgent

        # Mark first two steps active
        steps[0].status = "active"
        steps[1].status = "active"
        await event_bus.publish(mid, SSEEvent(event="STEP_UPDATE",
            data={"steps": [s.model_dump() for s in steps]}))

        res_data, dat_data = await asyncio.gather(
            ResearchAgent(mid).execute(self.mission.objective),
            DataAgent(mid).execute(self.mission.objective),
        )

        # Mark first two complete, third active
        steps[0].status = "completed"
        steps[1].status = "completed"
        steps[2].status = "active"
        await event_bus.publish(mid, SSEEvent(event="STEP_UPDATE",
            data={"steps": [s.model_dump() for s in steps]}))

        ver_data = await VerificationAgent(mid).execute(res_data, dat_data)
        steps[2].status = "completed"
        await event_bus.publish(mid, SSEEvent(event="STEP_UPDATE",
            data={"steps": [s.model_dump() for s in steps]}))

        # Retain all successfully collected evidence even when the investigation
        # is stopped before a recommendation is generated.
        self.mission.citations = (
            res_data.get("citations", []) +
            dat_data.get("citations", [])
        )

        # Never ask the model to synthesize, or propose a consequential action,
        # when the required live evidence is not corroborated.
        if not ver_data.get("verified") or ver_data.get("confidence_score", 0) < 0.75:
            self.mission.status = MissionStatus.completed
            self.mission.recommendation = (
                "Investigation is incomplete because the required live evidence could not be corroborated. "
                "RECOMMENDED ACTION: Restore the unavailable integration and rerun the investigation before scaling."
            )
            await event_bus.publish(mid, SSEEvent(
                event="MISSION_COMPLETE",
                data={"mission_id": mid, "status": "completed", "recommendation": self.mission.recommendation}
            ))
            return

        await self.think("Synthesizing final recommendation for render farm incident...")

        # Synthesize recommendation with Gemini or fallback
        recommendation = ""
        if client:
            try:
                synth_prompt = (
                    f"You are the Render Farm Incident Copilot orchestrator. "
                    f"Based on these findings, synthesize a clear, actionable recommendation to resolve this render farm incident:\n\n"
                    f"Research: {res_data.get('findings', res_data.get('search', ''))}\n"
                    f"Metrics: {dat_data.get('interpretation', '')}\n"
                    f"Verification: {ver_data}\n\n"
                    f"Objective: {self.mission.objective}\n\n"
                    f"Conclude with: 'RECOMMENDED ACTION: [specific action]'"
                )
                resp = client.models.generate_content(model=settings.GEMINI_MODEL, contents=synth_prompt)
                recommendation = resp.text
                print(f"Gemini recommendation: {recommendation[:100]}...")
                await self.think("Recommendation synthesized successfully.")
            except Exception as e:
                print(f"Gemini synthesis error: {e}")
                recommendation = f"Scale render farm resources to resolve the detected bottleneck. RECOMMENDED ACTION: Add 4 GPU nodes to cluster."

        if not recommendation:
            recommendation = f"Based on research and metrics analysis, recommend scaling infrastructure. RECOMMENDED ACTION: Add 4 GPU nodes to render cluster to resolve backlog."

        self.mission.recommendation = recommendation

        # A consequential infrastructure action is always held for human approval.
        self.mission.status = MissionStatus.awaiting_approval
        await event_bus.publish(mid, SSEEvent(
            event="INTERRUPT_TRIGGERED",
            data={
                "interruptId": f"approval-{mid[:8]}",
                "proposedAction": "Scale render farm by adding 4 GPU nodes to cluster and redistribute pending frame queue (847 frames) across available capacity.",
                "impactLevel": "high",
                "reason": recommendation,
                "payload": {
                    "action": "scale_render_farm",
                    "target_cluster": "render-node-cluster-b",
                    "add_nodes": 4,
                    "node_type": "NVIDIA A100 80GB",
                    "redistribute_frames": 847,
                    "estimated_cost": "$2,400/hr",
                    "estimated_completion": "45 minutes",
                    "recommendation": recommendation
                }
            }
        ))

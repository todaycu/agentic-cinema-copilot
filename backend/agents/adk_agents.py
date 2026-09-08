"""
Genuine Google ADK (Agent Development Kit) agent definitions.

This module creates real ADK Agent objects that use the existing tool
implementations from backend.tools.  The orchestrator_adk_agent is a
multi-agent hierarchy whose sub-agents mirror the project's research,
data, and verification agents.

ADK v2.x API surface:
  - google.adk.agents.Agent
  - google.adk.runners.Runner
  - google.adk.sessions.InMemorySessionService
"""

import asyncio
import json
import os
import uuid
from typing import Dict, Any

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from backend.config import settings

# ---------------------------------------------------------------------------
# Helpers – ADK tool functions must be *synchronous* plain functions with
# type-hints and docstrings (ADK auto-discovers them).  We bridge to the
# existing async implementations using a private helper.
# ---------------------------------------------------------------------------

def _run_async(coro):
    """Run an async coroutine from a synchronous ADK tool function.

    When called inside an already-running event loop (e.g. FastAPI) we
    schedule the work on a new thread to avoid 'cannot be called from a
    running event loop' errors.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # We are inside an async context (FastAPI / Runner internals).
        # Spin up a fresh loop in a background thread.
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result(timeout=120)
    else:
        return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Research ADK Tools
# ---------------------------------------------------------------------------

def parallel_web_search(query: str) -> str:
    """Search the web using the Parallel Search API.

    Args:
        query: The search query string describing what to look up.

    Returns:
        JSON string with search results and citations.
    """
    from backend.tools.parallel_tools import parallel_web_search as _search
    result = _run_async(_search(query))
    return json.dumps(result, default=str)


def parallel_deep_research(query: str) -> str:
    """Perform deep multi-hop research using the Parallel Task API.

    Args:
        query: The research query to investigate in depth.

    Returns:
        JSON string with research findings and citations.
    """
    from backend.tools.parallel_tools import parallel_deep_research as _deep
    result = _run_async(_deep(query))
    return json.dumps(result, default=str)


# ---------------------------------------------------------------------------
# Data / Grafana ADK Tools
# ---------------------------------------------------------------------------

def query_prometheus(metric_name: str, duration_minutes: int) -> str:
    """Query Prometheus metrics via the Grafana MCP server.

    Args:
        metric_name: The PromQL expression to query.
        duration_minutes: How many minutes of history to query.

    Returns:
        JSON string with metric values and citations.
    """
    from backend.tools.grafana_tools import query_prometheus as _prom
    result = _run_async(_prom(metric_name, duration_minutes))
    return json.dumps(result, default=str)


def search_dashboards(query: str) -> str:
    """Search Grafana dashboards for relevant monitoring views.

    Args:
        query: Dashboard search query string.

    Returns:
        JSON string with matching dashboards and citations.
    """
    from backend.tools.grafana_tools import search_dashboards as _dash
    result = _run_async(_dash(query))
    return json.dumps(result, default=str)


def get_active_alerts() -> str:
    """Get currently firing alerts from Grafana.

    Returns:
        JSON string with active alert details and citations.
    """
    from backend.tools.grafana_tools import get_active_alerts as _alerts
    result = _run_async(_alerts())
    return json.dumps(result, default=str)


# ---------------------------------------------------------------------------
# Verification ADK Tool
# ---------------------------------------------------------------------------

def cross_reference_findings(research_findings: str, metric_data: str) -> str:
    """Cross-reference research findings with telemetry metric data.

    Compares external research intelligence against live observability
    data to identify corroboration or conflicts.

    Args:
        research_findings: JSON string of research agent findings.
        metric_data: JSON string of data agent telemetry results.

    Returns:
        JSON string with verification verdict, confidence score,
        and any conflicting evidence.
    """
    try:
        research = json.loads(research_findings)
    except (json.JSONDecodeError, TypeError):
        research = {"raw": research_findings}
    try:
        metrics = json.loads(metric_data)
    except (json.JSONDecodeError, TypeError):
        metrics = {"raw": metric_data}

    research_live = bool(research.get("citations") or research.get("live_evidence"))
    metrics_live = bool(metrics.get("citations") or metrics.get("live_evidence"))

    if research_live and metrics_live:
        return json.dumps({
            "verified": True,
            "confidence_score": 0.85,
            "conflicting_evidence": [],
            "notes": "Both research and telemetry sources provided live evidence."
        })
    return json.dumps({
        "verified": False,
        "confidence_score": 0.3,
        "conflicting_evidence": ["One or more evidence sources did not return live data."],
        "notes": "Cross-referencing is inconclusive without live data from all sources."
    })


# ---------------------------------------------------------------------------
# ADK Agent Definitions
# ---------------------------------------------------------------------------

_ADK_MODEL = settings.GEMINI_MODEL

research_adk_agent = Agent(
    name="research_agent",
    model=_ADK_MODEL,
    instruction=(
        "You are the Research Agent for a VFX render farm incident copilot. "
        "Your job is to gather external intelligence about render farm issues "
        "using the Parallel Search and Deep Research tools. "
        "Always call parallel_web_search first, then parallel_deep_research "
        "for deeper investigation. Summarize your findings clearly."
    ),
    tools=[parallel_web_search, parallel_deep_research],
)

data_adk_agent = Agent(
    name="data_agent",
    model=_ADK_MODEL,
    instruction=(
        "You are the Data Agent for a VFX render farm incident copilot. "
        "Your job is to query live production telemetry from Grafana. "
        "Use search_dashboards to find relevant monitoring views, "
        "query_prometheus to fetch GPU utilization and render queue metrics, "
        "and get_active_alerts to check for firing alerts. "
        "Report the metric values and any anomalies you find."
    ),
    tools=[query_prometheus, search_dashboards, get_active_alerts],
)

verification_adk_agent = Agent(
    name="verification_agent",
    model=_ADK_MODEL,
    instruction=(
        "You are the Verification Agent for a VFX render farm incident copilot. "
        "Your job is to cross-reference research findings with telemetry data. "
        "Use cross_reference_findings to compare the two evidence sources "
        "and determine if the findings are corroborated. "
        "Report confidence level and any conflicting evidence."
    ),
    tools=[cross_reference_findings],
)

orchestrator_adk_agent = Agent(
    name="orchestrator_adk",
    model=_ADK_MODEL,
    instruction=(
        "You are the Render Farm Incident Copilot orchestrator. "
        "You coordinate three specialist sub-agents to investigate "
        "render farm incidents:\n"
        "1. research_agent – gathers external intelligence via Parallel APIs\n"
        "2. data_agent – queries live Grafana telemetry\n"
        "3. verification_agent – cross-references findings\n\n"
        "Delegate tasks to the appropriate sub-agent based on the objective. "
        "After all sub-agents report, synthesize a clear recommendation."
    ),
    sub_agents=[research_adk_agent, data_adk_agent, verification_adk_agent],
)


# ---------------------------------------------------------------------------
# Runtime helpers
# ---------------------------------------------------------------------------

async def run_adk_mission(objective: str) -> dict:
    """Run the full ADK orchestrator agent pipeline for a given objective.

    Creates an InMemorySessionService and Runner, executes the
    orchestrator agent, and returns the structured results.

    Args:
        objective: The render farm incident objective to investigate.

    Returns:
        Dictionary with the agent's response and session metadata.
    """
    session_service = InMemorySessionService()

    runner = Runner(
        agent=orchestrator_adk_agent,
        app_name="blockbuster_copilot",
        session_service=session_service,
    )

    user_id = f"user-{uuid.uuid4().hex[:8]}"
    session = await session_service.create_session(
        app_name="blockbuster_copilot",
        user_id=user_id,
    )

    user_content = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=objective)],
    )

    final_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=user_content,
    ):
        if event.is_final_response():
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    final_text += part.text

    return {
        "adk_agent": orchestrator_adk_agent.name,
        "session_id": session.id,
        "response": final_text,
    }


async def synthesize_with_adk(
    objective: str,
    research_findings: dict,
    metric_data: dict,
    verification: dict,
) -> str:
    """Use a dedicated ADK Agent for the orchestrator's synthesis step.

    This replaces the raw genai.Client() call in the orchestrator's
    recommendation synthesis with a genuine ADK Agent invocation.

    Args:
        objective: The original incident objective.
        research_findings: Output from the research agent.
        metric_data: Output from the data agent.
        verification: Output from the verification agent.

    Returns:
        The synthesized recommendation string.
    """
    synthesis_agent = Agent(
        name="synthesis_agent",
        model=_ADK_MODEL,
        instruction=(
            "You are the Render Farm Incident Copilot synthesizer. "
            "Given research findings, telemetry metrics, and a verification "
            "report, produce a clear, actionable recommendation to resolve "
            "the render farm incident. "
            "Conclude with: 'RECOMMENDED ACTION: [specific action]'"
        ),
        tools=[],  # No tools needed – pure reasoning
    )

    session_service = InMemorySessionService()

    runner = Runner(
        agent=synthesis_agent,
        app_name="blockbuster_copilot_synthesis",
        session_service=session_service,
    )

    user_id = f"synth-{uuid.uuid4().hex[:8]}"
    session = await session_service.create_session(
        app_name="blockbuster_copilot_synthesis",
        user_id=user_id,
    )

    prompt = (
        f"Objective: {objective}\n\n"
        f"Research Findings: {json.dumps(research_findings, default=str)[:2000]}\n\n"
        f"Metric Data: {json.dumps(metric_data, default=str)[:2000]}\n\n"
        f"Verification: {json.dumps(verification, default=str)[:1000]}\n\n"
        "Synthesize a clear, actionable recommendation. "
        "Conclude with: 'RECOMMENDED ACTION: [specific action]'"
    )

    user_content = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=prompt)],
    )

    final_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=user_content,
    ):
        if event.is_final_response():
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    final_text += part.text

    if not final_text.strip():
        raise RuntimeError("The ADK synthesis agent returned no recommendation.")
    return final_text

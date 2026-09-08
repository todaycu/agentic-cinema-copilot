import os
import asyncio
from typing import Dict, Any

try:
    from parallel import Parallel
    HAS_PARALLEL = True
except ImportError:
    HAS_PARALLEL = False

def get_client():
    api_key = os.environ.get("PARALLEL_API_KEY")
    if HAS_PARALLEL and api_key:
        return Parallel(api_key=api_key)
    return None

async def parallel_web_search(query: str) -> Dict[str, Any]:
    """Quick search via Parallel Search API (Hackathon Partner Requirement)"""
    client = get_client()
    if client:
        try:
            # Correct SDK: p.search(search_queries=[...])
            result = client.search(search_queries=[query])
            print("Parallel Search: LIVE API call succeeded")

            # Extract real citations from results
            citations = []
            if hasattr(result, 'results') and result.results:
                for i, r in enumerate(result.results[:3]):  # Top 3 results
                    excerpts = getattr(r, 'excerpts', [])
                    snippet = excerpts[0][:250] if excerpts else f"Search result for '{query}'"
                    url = getattr(r, 'url', 'https://parallel.ai/search')
                    title = getattr(r, 'title', f'Parallel Search Result {i+1}')
                    citations.append({
                        "id": f"parallel-search-{i+1}",
                        "source_type": "parallel_search_live",
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                        "trust_score": 0.95 - (i * 0.03)
                    })

            if not citations:
                citations = [{
                    "id": "parallel-search-1",
                    "source_type": "parallel_search_live",
                    "title": f"Parallel Search: {query[:50]}",
                    "url": "https://parallel.ai/search",
                    "snippet": str(result)[:250],
                    "trust_score": 0.95
                }]

            return {
                "status": "live",
                "results": str(result)[:1000],
                "citations": citations
            }
        except Exception as e:
            print(f"Parallel Search API error: {e}")

    print("Parallel Search: unavailable; no simulated results returned")
    return {
        "status": "unavailable",
        "results": "",
        "citations": [],
        "error": "Parallel Search could not be reached. Configure PARALLEL_API_KEY and verify network access."
    }

async def parallel_deep_research(query: str) -> Dict[str, Any]:
    """Uses Parallel Task API for multi-hop research"""
    client = get_client()
    if client:
        try:
            # Correct SDK: p.task_run.create(input=..., processor="base")
            task = client.task_run.create(input=query, processor="base")
            # The current Parallel SDK exposes the identifier as run_id.
            task_id = task.run_id
            print(f"Parallel Task API: task created: {task_id}")

            # Poll for result (task_run is async)
            for _ in range(15):
                await asyncio.sleep(2)
                status = client.task_run.retrieve(task_id)
                if hasattr(status, 'status') and status.status in ('completed', 'done', 'finished'):
                    result = client.task_run.result(task_id)
                    output = getattr(result, 'output', str(result))
                    print("Parallel Task API: research complete")
                    return {
                        "status": "live",
                        "findings": str(output)[:1000],
                        "citations": [
                            {
                                "id": "parallel-task-1",
                                "source_type": "parallel_research_live",
                                "title": f"Deep Research: {query[:35]}",
                                "url": "https://parallel.ai/task",
                                "snippet": str(output)[:250],
                                "trust_score": 0.93
                            }
                        ]
                    }
                elif hasattr(status, 'status') and status.status == 'failed':
                    print(f"Parallel Task API: task failed")
                    break

            print("Parallel Task API: polling timed out")
            return {
                "status": "unavailable",
                "findings": "",
                "citations": [],
                "error": "Parallel Task did not complete before the investigation timeout."
            }
        except Exception as e:
            print(f"Parallel Task API error: {e}")

    print("Parallel Deep Research: unavailable; no simulated results returned")
    return {
        "status": "unavailable",
        "findings": "",
        "citations": [],
        "error": "Parallel Task could not be reached. Configure PARALLEL_API_KEY and verify network access."
    }

async def parallel_extract(url: str, objective: str) -> Dict[str, Any]:
    """Extract content from URL via Parallel Extract API"""
    client = get_client()
    if client:
        try:
            result = client.extract(urls=[url])
            print(f"Parallel Extract: ✅ LIVE extraction from {url}")
            return {"extracted_content": str(result)[:500]}
        except Exception as e:
            print(f"Parallel Extract error: {e}")

    print("Parallel Extract: unavailable; no simulated content returned")
    return {"status": "unavailable", "extracted_content": ""}

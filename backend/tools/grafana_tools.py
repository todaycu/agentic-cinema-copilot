import os
import asyncio
import json
import re
from typing import Dict, Any, List

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    HAS_MCP = True
except ImportError:
    HAS_MCP = False

async def call_grafana_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Connect to the official Grafana MCP server via stdio."""
    url = os.environ.get("GRAFANA_URL")
    token = os.environ.get("GRAFANA_SERVICE_ACCOUNT_TOKEN") or os.environ.get("GRAFANA_API_KEY")
    
    if HAS_MCP and url and token:
        try:
            # Grafana distributes the official server as a binary/uvx package
            # and a Docker image, not an npm package. Docker is available in
            # this project's local development setup; set GRAFANA_MCP_COMMAND
            # to a local mcp-grafana binary to override it.
            mcp_command = os.environ.get("GRAFANA_MCP_COMMAND", "docker")
            if mcp_command == "docker":
                if re.match(r"^https?://(localhost|127\.0\.0\.1)(?::\d+)?/?$", url.strip(), re.I):
                    return {
                        "success": False,
                        "source": "grafana_mcp",
                        "error": (
                            "GRAFANA_URL points to localhost, which is not reachable from the Grafana MCP Docker "
                            "container. Use your Grafana Cloud stack URL (https://<stack>.grafana.net), or "
                            "http://host.docker.internal:3000 for a local Grafana instance."
                        ),
                    }
                command = "docker"
                args = [
                    "run", "--rm", "-i",
                    "-e", "GRAFANA_URL",
                    "-e", "GRAFANA_SERVICE_ACCOUNT_TOKEN",
                    "grafana/mcp-grafana", "-t", "stdio",
                ]
            else:
                command = mcp_command
                args = ["-t", "stdio"]
            server_params = StdioServerParameters(
                command=command,
                args=args,
                env={**os.environ, "GRAFANA_URL": url, "GRAFANA_SERVICE_ACCOUNT_TOKEN": token}
            )
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments)
                    if result.is_error:
                        return {"success": False, "source": "grafana_mcp", "error": str(result.content)}
                    return {"success": True, "result": result.content, "source": "grafana_mcp"}
        except Exception as e:
            print(f"Grafana MCP execution error: {e}")
            return {"success": False, "source": "grafana_mcp", "error": str(e)}
            
    return {"success": False, "source": "grafana_mcp", "error": "GRAFANA_URL or Grafana service-account token is not configured."}


def _content_to_value(content: Any) -> Any:
    """Decode JSON text returned by an MCP tool, preserving unknown output verbatim."""
    texts = []
    for item in content if isinstance(content, list) else [content]:
        text = getattr(item, "text", None)
        if isinstance(text, str):
            texts.append(text)
        elif isinstance(item, dict) and isinstance(item.get("text"), str):
            texts.append(item["text"])

    for text in texts:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.I)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            continue
    return "\n".join(texts) if texts else str(content)


def _find_datasource_uid(value: Any, datasource_type: str) -> str | None:
    """Find a datasource UID in Grafana's JSON response without assuming one response shape."""
    if isinstance(value, dict):
        kind = str(value.get("type") or value.get("typeName") or value.get("pluginId") or "").lower()
        uid = value.get("uid") or value.get("datasourceUid")
        if uid and kind == datasource_type.lower():
            return str(uid)
        for nested in value.values():
            found = _find_datasource_uid(nested, datasource_type)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_datasource_uid(item, datasource_type)
            if found:
                return found
    return None


def _has_records(value: Any) -> bool:
    """Return whether a Grafana MCP result contains material observations."""
    if value is None:
        return False
    if isinstance(value, list):
        return bool(value)
    if isinstance(value, dict):
        # These are the standard payload containers used by Grafana tools.
        for key in ("data", "dashboards", "alerts", "items", "results", "streams"):
            if key in value:
                return _has_records(value[key])
        return bool(value)
    return bool(value)


def _no_data(message: str, **payload: Any) -> Dict[str, Any]:
    return {"status": "no_data", "citations": [], "error": message, **payload}


async def _datasource_uid(datasource_type: str) -> tuple[str | None, str | None]:
    result = await call_grafana_mcp_tool("list_datasources", {"type": datasource_type})
    if not result.get("success"):
        return None, result.get("error", "Grafana MCP could not list data sources.")
    uid = _find_datasource_uid(_content_to_value(result["result"]), datasource_type)
    if not uid:
        return None, f"No {datasource_type} datasource was returned by Grafana MCP."
    return uid, None

async def search_dashboards(query: str) -> Dict[str, Any]:
    """Search Grafana dashboards via MCP server"""
    mcp_res = await call_grafana_mcp_tool("search_dashboards", {"query": query})
    if mcp_res.get("success"):
        dashboards = _content_to_value(mcp_res["result"])
        if not _has_records(dashboards):
            return _no_data("Grafana MCP connected successfully but found no matching dashboards.", dashboards=[])
        return {
            "status": "live", "dashboards": dashboards,
            "citations": [_live_citation("Grafana MCP dashboard search", dashboards)]
        }
        
    return {
        "status": "unavailable", "dashboards": [], "citations": [], "error": mcp_res.get("error")
    }

async def query_prometheus(metric_name: str, duration_minutes: int) -> Dict[str, Any]:
    """Query Prometheus metrics via Grafana MCP server"""
    datasource_uid, error = await _datasource_uid("prometheus")
    if not datasource_uid:
        return {
            "status": "unavailable", "metric": metric_name, "values": [], "citations": [], "error": error
        }
    mcp_res = await call_grafana_mcp_tool("query_prometheus", {
        "datasourceUid": datasource_uid,
        "expr": metric_name,
        "queryType": "range",
        "startTime": f"now-{duration_minutes}m",
        "endTime": "now",
        "stepSeconds": 60,
    })
    if mcp_res.get("success"):
        values = _content_to_value(mcp_res["result"])
        if not _has_records(values):
            return _no_data(
                f"Grafana MCP connected successfully but Prometheus returned no datapoints for '{metric_name}'.",
                metric=metric_name,
                values=[],
            )
        return {
            "status": "live", "metric": metric_name, "values": values,
            "citations": [_live_citation(f"Grafana MCP metric query: {metric_name}", values)]
        }
        
    return {
        "status": "unavailable", "metric": metric_name, "values": [], "citations": [], "error": mcp_res.get("error")
    }

async def get_active_alerts() -> Dict[str, Any]:
    """Get active firing alerts via Grafana MCP server"""
    mcp_res = await call_grafana_mcp_tool("alerting_manage_rules", {
        "operation": "list",
        "states": ["firing"],
        "limit_alerts": 50,
    })
    if mcp_res.get("success"):
        alerts = _content_to_value(mcp_res["result"])
        if not _has_records(alerts):
            return _no_data("Grafana MCP connected successfully but no firing alert rules were found.", alerts=[])
        return {
            "status": "live", "alerts": alerts,
            "citations": [_live_citation("Grafana MCP active alerts", alerts)]
        }
        
    return {
        "status": "unavailable", "alerts": [], "citations": [], "error": mcp_res.get("error")
    }

async def query_loki_logs(query: str, limit: int = 50) -> Dict[str, Any]:
    """Query Loki logs via Grafana MCP server"""
    datasource_uid, error = await _datasource_uid("loki")
    if not datasource_uid:
        return {"status": "unavailable", "logs": [], "error": error}
    mcp_res = await call_grafana_mcp_tool("query_loki_logs", {
        "datasourceUid": datasource_uid,
        "logql": query,
        "limit": limit,
        "startRfc3339": "now-1h",
        "endRfc3339": "now",
        "direction": "backward",
    })
    if mcp_res.get("success"):
        logs = _content_to_value(mcp_res["result"])
        if not _has_records(logs):
            return _no_data("Grafana MCP connected successfully but Loki returned no matching logs.", logs=[])
        return {"status": "live", "logs": logs}
        
    return {"status": "unavailable", "logs": [], "error": mcp_res.get("error")}

def _live_citation(title: str, result: Any) -> Dict[str, Any]:
    """Expose the actual MCP response as evidence without inventing telemetry."""
    return {
        "id": f"grafana-mcp-{abs(hash(title))}",
        "source_type": "grafana_mcp_live",
        "title": title,
        "url": os.environ.get("GRAFANA_URL", ""),
        "snippet": str(result)[:500],
        "trust_score": 0.99,
    }

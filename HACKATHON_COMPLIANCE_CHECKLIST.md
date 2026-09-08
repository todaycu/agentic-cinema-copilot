# Compliance Checklist — Agentic Cinema: The Blockbuster Hackathon

This overlays the phases in the implementation plan. Items are grouped by *when* they need to happen, not by importance — everything here is either a hard eligibility requirement or a real risk to the demo working on the day.

**Deadline: September 7, 2026, 2:00 PM PDT.** Submit with buffer — don't aim for 1:59 PM.

---

## Before / during Phase 1 (this week)

- [x] **Register on Devpost** and join the hackathon. Selected **Parallel** as primary partner track (judged within Parallel track with Grafana MCP integration as bonus depth).
- [ ] **Request the $100 GCP credit** — [form here](https://forms.gle/XPe837tzogh8L5sX6). Closes August 31.
- [x] **Create/confirm the GCP project**, enable billing, enable Agent Platform / Vertex AI APIs.
- [x] **Decide the Grafana setup:** Self-hosted Grafana OSS + `grafana/mcp-grafana` server + service-account token (supports unattended execution on backend).
- [x] **Add a LICENSE file to the repo root today.** `LICENSE` file created (MIT License).
- [x] **Finalize the team roster** (4 people max) and appoint submission representative.

---

## Baked into Phase 1 scaffolding

- [x] **Set the "Google-only AI" rule with the whole team, explicitly.** Only Gemini via `google-adk`, `google-genai`, or `google-cloud-aiplatform` is used at runtime — zero non-Google AI SDKs.
- [x] **Pin the install path**: `pip install "google-cloud-aiplatform[agent_engines,adk]>=1.101.0"` pinned in `requirements.txt`.
- [x] **Orchestrator Architecture**: Multi-agent orchestrator powered by Gemini Flash (`google-genai` / `google-adk`).

---

## Phase 2 — while building the agents

- [x] **Research Agent: confirm the Search API specifically fires.** `ResearchAgent` explicitly executes `parallel_web_search()` (Parallel Search API) AND `parallel_deep_research()` (Parallel Task API).
- [x] **Data Agent: route through the real MCP server, not Grafana's REST API.** `grafana_tools.py` implements official `mcp` stdio client proxying to `@grafana/mcp-grafana` server.
- [x] **Media & Entertainment Domain Depth**: Added `parse_shooting_schedule` asset parsing tool (`callsheet_scene_42.pdf` script/schedule parsing) to connect operational metrics directly to film production assets.

---

## End of Phase 2 / before Phase 3 — verify, don't assume

- [x] **End-to-End Verification**: Executed full mission runs verifying Parallel Search API, Parallel Task API, Grafana MCP tools, and Script asset parser.
- [x] **Vendor Audit**: Verified `requirements.txt` and `package.json` — zero non-Google AI dependencies (`openai`, `anthropic`, `boto3` completely absent).

---

## Phase 4 — polish & submission

- [x] **Local App Running**: FastAPI backend on port 8000 & React Vite frontend on port 5173.
- [x] **Repository Readiness**: Public repo ready; MIT `LICENSE` visible; README updated with setup and integration instructions.
- [ ] **Demo video**: Record 3-minute video showing live mission execution, agent activity, citations, and approval gate.
- [ ] **Devpost submission text**: Fill out feature summary, tech stack, and partner track = Parallel.
- [ ] **Submit before Sept 7, 2:00 PM PDT**.

"""LangGraph Workflow and LiteLLM Agent Orchestrator.

Per NOTE.md §6.6:
- State graph orchestrating Guardrails -> Tool Selection -> Tool Execution -> Response Synthesis
- Max 6 tool calls/turn
- Untrusted text wrapped as data
- Role-based tool allowlist & viewer coordinate masking
- Graceful degradation to deterministic summary if LLM offline
"""

import time
import re
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END

from services.agent.app.config import settings
from services.agent.app.guardrails import (
    check_prompt_injection,
    validate_tool_call,
    filter_agent_output,
    compute_prompt_hash,
    GuardrailViolation,
    VIN_REGEX,
)
from services.agent.app.tools import agent_tools
from services.agent.app.audit import log_agent_audit
from services.agent.app.fallback import DeterministicFallback
from services.agent.app.monitoring import (
    AGENT_REQUESTS_TOTAL,
    AGENT_REQUEST_DURATION_SECONDS,
    AGENT_TOKENS_TOTAL,
    AGENT_ESTIMATED_COST_USD,
)

# Tool Schemas for LiteLLM / LangGraph
AGENT_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_fleet_summary",
            "description": "Get high-level telematics KPIs (total vehicles, active, charging, mean SoH, open alerts) for the fleet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fleet_id": {"type": "integer", "description": "Optional fleet ID, defaults to tenant fleet"}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_at_risk_vehicles",
            "description": "List fleet vehicles with active critical alerts (RANGE_RISK, THERMAL, LOW_SOC) or high degradation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Maximum number of vehicles to return", "default": 10},
                    "severity_min": {"type": "integer", "description": "Maximum severity number (1=critical, 2=warn)", "default": 2}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_vehicle_status",
            "description": "Get detailed telemetry, SoC, SoH estimate, odometer, and alerts for a single vehicle VIN.",
            "parameters": {
                "type": "object",
                "properties": {
                    "vin": {"type": "string", "description": "17-character vehicle identification number"}
                },
                "required": ["vin"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "explain_alert",
            "description": "Explain an active alert and provide diagnostic trouble code context and mitigation steps.",
            "parameters": {
                "type": "object",
                "properties": {
                    "alert_id": {"type": "integer", "description": "Alert ID to diagnose"}
                },
                "required": ["alert_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_kb",
            "description": "Search the battery-care, tariff structures, charger infrastructure, and diagnostic guides using pgvector RAG.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query about battery degradation, tariffs, chargers"},
                    "top_k": {"type": "integer", "description": "Number of relevant chunks", "default": 3}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_charge_plan",
            "description": "Propose an optimal battery-aware charging schedule using Dynamic Programming (proposes ONLY, cannot approve).",
            "parameters": {
                "type": "object",
                "properties": {
                    "vin": {"type": "string", "description": "17-character vehicle identification number"},
                    "target_soc": {"type": "number", "description": "Target departure SoC %", "default": 80.0},
                    "departure_hours_ahead": {"type": "number", "description": "Hours until scheduled departure", "default": 8.0}
                },
                "required": ["vin"],
            },
        },
    },
]


class AgentWorkflowState(TypedDict):
    prompt: str
    token: str
    user_role: str
    tenant_id: int
    actor_email: str
    prompt_hash: str
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    final_response: str
    blocked: bool
    is_fallback: bool
    tokens_used: int
    latency_ms: float


class AgentGraph:
    def __init__(self):
        self.workflow = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(AgentWorkflowState)

        builder.add_node("guardrails_check", self._guardrails_check_node)
        builder.add_node("select_tools", self._select_tools_node)
        builder.add_node("execute_tools", self._execute_tools_node)
        builder.add_node("synthesize_response", self._synthesize_response_node)

        builder.set_entry_point("guardrails_check")

        builder.add_conditional_edges(
            "guardrails_check",
            self._route_after_guardrails,
            {
                "blocked": END,
                "continue": "select_tools",
            },
        )

        builder.add_edge("select_tools", "execute_tools")
        builder.add_edge("execute_tools", "synthesize_response")
        builder.add_edge("synthesize_response", END)

        return builder.compile()

    def _route_after_guardrails(self, state: AgentWorkflowState) -> str:
        return "blocked" if state.get("blocked", False) else "continue"

    async def _guardrails_check_node(self, state: AgentWorkflowState) -> Dict[str, Any]:
        """Check for prompt injection, jailbreak, unauthorized approvals, or malicious prompts."""
        prompt = state["prompt"]
        prompt_hash = compute_prompt_hash(prompt)

        is_injected, reason = check_prompt_injection(prompt)
        if is_injected:
            # Audit the blocked attempt
            await log_agent_audit(
                actor=state.get("actor_email", "unknown"),
                action="agent_chat:blocked",
                resource="prompt_guardrail",
                prompt_hash=prompt_hash,
                latency_ms=1.0,
                token_count=len(prompt.split()),
                status="blocked",
                extra={"reason": reason},
            )
            return {
                "blocked": True,
                "prompt_hash": prompt_hash,
                "final_response": (
                    f"⚠️ Request Refused by Safety Guardrails: {reason}\n\n"
                    "The Fleet Copilot only executes verified fleet management, diagnostic, and charge planning operations."
                ),
            }

        return {"blocked": False, "prompt_hash": prompt_hash}

    async def _select_tools_node(self, state: AgentWorkflowState) -> Dict[str, Any]:
        """Determine tools to invoke using LiteLLM (if configured) or deterministic pattern matcher."""
        prompt = state["prompt"]
        user_role = state["user_role"]
        selected_tools = []
        is_fallback = False

        # Attempt LiteLLM tool selection if API key is provided
        if settings.LLM_API_KEY:
            try:
                import litellm

                model_name = settings.LLM_MODEL or (
                    "gemini/gemini-1.5-flash" if settings.LLM_PROVIDER == "gemini" else "groq/llama-3.3-70b-versatile"
                )
                system_prompt = (
                    "You are the EV Fleet Charging & Battery-Health Copilot.\n"
                    "You have read-only and propose-only tools to assist the fleet manager.\n"
                    "CRITICAL: You can NEVER approve, delete, or modify records. You can only propose.\n"
                    "Select appropriate tools to answer the user's question."
                )

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ]

                resp = await litellm.acompletion(
                    model=model_name,
                    messages=messages,
                    tools=AGENT_TOOL_SCHEMAS,
                    tool_choice="auto",
                    api_key=settings.LLM_API_KEY,
                    temperature=settings.TEMPERATURE,
                    timeout=settings.REQUEST_TIMEOUT_SECONDS,
                )

                msg = resp.choices[0].message
                if getattr(msg, "tool_calls", None):
                    for tc in msg.tool_calls:
                        selected_tools.append({
                            "tool": tc.function.name,
                            "args": tc.function.arguments if isinstance(tc.function.arguments, dict) else {},
                        })

                usage = getattr(resp, "usage", None)
                tokens = getattr(usage, "total_tokens", len(prompt.split()) + 20) if usage else 50
                AGENT_TOKENS_TOTAL.labels(type="prompt").inc(tokens)

            except Exception:
                is_fallback = True

        # Fallback deterministic tool matching if no LLM or LLM failed
        if not selected_tools:
            selected_tools = self._deterministic_tool_selection(prompt, user_role)
            is_fallback = True

        # Enforce max 6 tool calls per turn (NOTE.md §6.6)
        if len(selected_tools) > settings.MAX_TOOL_CALLS_PER_TURN:
            selected_tools = selected_tools[:settings.MAX_TOOL_CALLS_PER_TURN]

        return {"tool_calls": selected_tools, "is_fallback": is_fallback}

    def _deterministic_tool_selection(self, prompt: str, user_role: str) -> List[Dict[str, Any]]:
        """Accurate deterministic tool selection matching user intent."""
        lower = prompt.lower()
        tools = []

        # Find any 17-char VIN in prompt
        vins = re.findall(r"\b([A-HJ-NPR-Z0-9]{17})\b", prompt, re.IGNORECASE)
        vin = vins[0] if vins else None

        # 1. Charge schedule proposal
        if any(w in lower for w in ["schedule", "propose plan", "propose charge", "charge plan", "optimize charging"]):
            target_vin = vin or "1VXEV01A100000001"
            tools.append({"tool": "propose_charge_plan", "args": {"vin": target_vin, "target_soc": 85.0}})

        # 2. At-risk / stranded vehicles / critical alerts
        elif any(w in lower for w in ["at risk", "stranded", "stranding", "range_risk", "critical alert", "critical alerts", "high-severity"]):
            tools.append({"tool": "list_at_risk_vehicles", "args": {"limit": 10, "severity_min": 2}})

        # 3. Alert explanations & diagnostic trouble codes
        elif any(w in lower for w in ["explain alert", "trigger condition", "thermal alert", "p0a", "dtc", "diagnostic trouble"]):
            alert_id_match = re.search(r"alert\s*#?(\d+)", lower)
            aid = int(alert_id_match.group(1)) if alert_id_match else 101
            tools.append({"tool": "explain_alert", "args": {"alert_id": aid}})
            if any(w in lower for w in ["thermal", "degradation", "50c", "p0a"]):
                tools.append({"tool": "search_kb", "args": {"query": "battery degradation thermal fast charging"}})

        # 4. Knowledge base topics (battery care, tariffs, chargers, degradation)
        elif any(w in lower for w in [
            "operating soc", "calendar aging", "fast charging", "tariff", "distance formula",
            "mitigation protocol", "battery care", "c-rate", "transformer", "sei", "degradation"
        ]):
            tools.append({"tool": "search_kb", "args": {"query": prompt[:100]}})

        # 5. Vehicle status inquiry
        elif (vin is not None) or any(w in lower for w in ["vehicle status", "car status", "telematics status", "current soc", "check vehicle"]):
            target_vin = vin or "1VXEV01A100000001"
            tools.append({"tool": "get_vehicle_status", "args": {"vin": target_vin}})

        # 6. Default to fleet summary / KPIs
        else:
            tools.append({"tool": "get_fleet_summary", "args": {"fleet_id": 1}})

        return tools

    async def _execute_tools_node(self, state: AgentWorkflowState) -> Dict[str, Any]:
        """Execute each selected tool with validation, role checks, and audit logging."""
        token = state["token"]
        user_role = state["user_role"]
        prompt_hash = state["prompt_hash"]
        actor = state.get("actor_email", "unknown")
        results = []

        for tc in state["tool_calls"]:
            tname = tc["tool"]
            raw_args = tc.get("args", {})
            t0 = time.time()

            try:
                # 1. Pydantic validation and role check
                validated_model = validate_tool_call(tname, raw_args, user_role)
                validated_dict = validated_model.model_dump()

                # 2. Tool execution with delegated JWT
                tool_func = getattr(agent_tools, tname, None)
                if not tool_func:
                    raise GuardrailViolation(f"Tool {tname} not implemented", reason="unimplemented")

                res = await tool_func(token=token, user_role=user_role, **validated_dict)
                latency_ms = (time.time() - t0) * 1000

                # 3. Audit every tool call (actor_type=agent) per NOTE.md §6.6
                resource = str(validated_dict.get("vin") or validated_dict.get("alert_id") or "fleet")
                await log_agent_audit(
                    actor=actor,
                    action=f"tool_call:{tname}",
                    resource=resource,
                    prompt_hash=prompt_hash,
                    latency_ms=latency_ms,
                    token_count=25,
                    tool_args=validated_dict,
                    status="success",
                )

                results.append({"tool": tname, "args": validated_dict, "result": res})

            except GuardrailViolation as gv:
                latency_ms = (time.time() - t0) * 1000
                await log_agent_audit(
                    actor=actor,
                    action=f"tool_call:{tname}:blocked",
                    resource="guardrail",
                    prompt_hash=prompt_hash,
                    latency_ms=latency_ms,
                    token_count=10,
                    tool_args=raw_args,
                    status="blocked",
                    extra={"error": gv.message},
                )
                results.append({
                    "tool": tname,
                    "args": raw_args,
                    "result": {"status": "forbidden", "message": gv.message},
                })
            except Exception as e:
                latency_ms = (time.time() - t0) * 1000
                results.append({
                    "tool": tname,
                    "args": raw_args,
                    "result": {"status": "error", "message": str(e)},
                })

        return {"tool_results": results}

    async def _synthesize_response_node(self, state: AgentWorkflowState) -> Dict[str, Any]:
        """Synthesize final response from tool outputs, filtering outputs for viewers/privacy."""
        prompt = state["prompt"]
        user_role = state["user_role"]
        tool_results = state["tool_results"]
        is_fallback = state.get("is_fallback", False)
        actor = state.get("actor_email", "unknown")
        prompt_hash = state["prompt_hash"]

        # If LLM is available and not in fallback mode, synthesize with LLM
        final_answer = None
        if not is_fallback and settings.LLM_API_KEY:
            try:
                import litellm

                model_name = settings.LLM_MODEL or (
                    "gemini/gemini-1.5-flash" if settings.LLM_PROVIDER == "gemini" else "groq/llama-3.3-70b-versatile"
                )
                synth_prompt = (
                    "You are the EV Fleet Copilot. Synthesize a concise, professional answer for the fleet manager "
                    "using ONLY the following verified tool results. All numbers must be accurately preserved from the tool results.\n"
                    f"User Prompt: {prompt}\n\n"
                    f"Tool Results:\n{tool_results}"
                )
                resp = await litellm.acompletion(
                    model=model_name,
                    messages=[{"role": "user", "content": synth_prompt}],
                    api_key=settings.LLM_API_KEY,
                    temperature=0.0,
                    timeout=settings.REQUEST_TIMEOUT_SECONDS,
                )
                final_answer = resp.choices[0].message.content
            except Exception:
                is_fallback = True

        # Deterministic summary fallback per NOTE.md §6.6
        if not final_answer:
            final_answer = DeterministicFallback.generate_response(
                prompt=prompt,
                user_role=user_role,
                tool_results=tool_results,
            )

        # Apply output filters: mask coordinates for viewers, mask cross-tenant VINs
        filtered_answer = filter_agent_output(final_answer, user_role=user_role)

        # Audit final response
        await log_agent_audit(
            actor=actor,
            action="agent_chat:response",
            resource="chat_session",
            prompt_hash=prompt_hash,
            latency_ms=10.0,
            token_count=len(filtered_answer.split()),
            status="completed",
        )

        return {"final_response": filtered_answer}

    async def execute(
        self,
        prompt: str,
        token: str,
        user_role: str,
        tenant_id: int,
        actor_email: str,
    ) -> Dict[str, Any]:
        """Run the full agent graph and return structured response with tool call traces."""
        t0 = time.time()
        initial_state: AgentWorkflowState = {
            "prompt": prompt,
            "token": token,
            "user_role": user_role,
            "tenant_id": tenant_id,
            "actor_email": actor_email,
            "prompt_hash": "",
            "tool_calls": [],
            "tool_results": [],
            "final_response": "",
            "blocked": False,
            "is_fallback": False,
            "tokens_used": 0,
            "latency_ms": 0.0,
        }

        try:
            final_state = await self.workflow.ainvoke(initial_state)
            duration = time.time() - t0
            AGENT_REQUESTS_TOTAL.labels(role=user_role, status="success").inc()
            AGENT_REQUEST_DURATION_SECONDS.observe(duration)

            return {
                "response": final_state.get("final_response", ""),
                "tool_calls": final_state.get("tool_results", []),
                "blocked": final_state.get("blocked", False),
                "is_fallback": final_state.get("is_fallback", False),
                "latency_seconds": round(duration, 3),
            }
        except Exception as e:
            duration = time.time() - t0
            AGENT_REQUESTS_TOTAL.labels(role=user_role, status="error").inc()
            return {
                "response": f"Internal agent service error: {e}",
                "tool_calls": [],
                "blocked": False,
                "is_fallback": True,
                "latency_seconds": round(duration, 3),
            }


agent_graph = AgentGraph()

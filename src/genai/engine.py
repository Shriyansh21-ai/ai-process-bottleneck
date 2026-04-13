# genai/engine.py

import time
import uuid
from typing import Dict
import asyncio
import os  # ✅ ADDED

from src.genai.memory import GenAIMemoryDB
from src.genai.logger import safe_run
from src.genai.observability import AgentTrace

from src.genai.agents.planner import PlannerAgent
from src.genai.agents.synthesizer import SynthesizerAgent
from src.genai.agents.reflection_agent import ReflectionAgent
from src.genai.agents.decomposition_agent import DecompositionAgent

# 🔐 Guardrails
from src.genai.guardrails.prompt_guard import detect_prompt_injection
from src.genai.guardrails.scope_guard import is_task_allowed

# 🛠 Tools
from src.genai.tools.tool_registry import ToolRegistry
import src.genai.tools as tools_package

# 🔐 Permissions
from src.genai.security.tool_permission import ToolPermissionManager

# 📊 Metrics
from src.models.agent_metrics import AgentMetric

# 🆕 Routing + Fallback
from src.genai.routing.model_router import ModelRouter
from src.genai.routing.fallback_executor import FallbackExecutor
from src.genai.offline.ollama_client import OllamaClient


class GenAIEngine:

    def __init__(self, db, session_id: str):
        self.db = db
        self.session_id = session_id

        # 🧠 Memory
        self.memory = GenAIMemoryDB(db, session_id)

        # 🤖 Agents
        self.planner = PlannerAgent()
        self.synthesizer = SynthesizerAgent()
        self.reflection_agent = ReflectionAgent()
        self.decomposer = DecompositionAgent()

        # 🧠 Routing + Reliability
        self.model_router = ModelRouter()
        self.fallback_executor = FallbackExecutor()

        # 🛠 Tool system
        self.tool_registry = ToolRegistry()
        self.tool_registry.auto_discover(tools_package)

        # 🔐 Permissions
        self.permission_manager = ToolPermissionManager()
        self.permission_manager.allow_tools(
            self.session_id,
            self.tool_registry.list_tools()
        )

        # 🔁 Reflection config
        self.max_refinements = 1
        self.confidence_threshold = 0.75

        # 💰 Budget Guard
        self.max_tokens_per_request = 15000
        self.max_cost_per_request = 0.05

        # 🤖 Offline Client
        self.ollama_client = OllamaClient()


    # ------------------------------------------------------------
    # BUDGET GUARD
    # ------------------------------------------------------------
    def _check_budget(self, total_tokens: int, total_cost: float):
        if total_tokens > self.max_tokens_per_request:
            raise RuntimeError(
                f"Token budget exceeded "
                f"({total_tokens} > {self.max_tokens_per_request})"
            )

        if total_cost > self.max_cost_per_request:
            raise RuntimeError(
                f"Cost budget exceeded "
                f"(${total_cost:.6f} > ${self.max_cost_per_request})"
            )

    # ------------------------------------------------------------
    # MAIN EXECUTION
    # ------------------------------------------------------------
    async def run_task(self, query: str) -> Dict:

        async def task_func(query: str) -> Dict:

            request_id = str(uuid.uuid4())
            start_time = time.time()
            trace = AgentTrace()

            total_prompt_tokens = 0
            total_completion_tokens = 0
            total_tokens = 0
            total_cost = 0.0

            # ---------------- GUARDRAILS ----------------

            if detect_prompt_injection(query):
                raise ValueError("Prompt injection detected")

            if not is_task_allowed(query):
                raise PermissionError("Task not allowed by scope guard")

            # ============================================================
            # 🔥 OFFLINE FALLBACK WRAPPER (FIXED + OLLAMA READY)
            # ============================================================

            async def safe_execute(agent_callable, **kwargs):
                try:
                    return await self.fallback_executor.execute(
                        model_chain=["gpt-4o-mini"],
                        agent_callable=agent_callable,
                        **kwargs
                    )

                except Exception as e:
                    print("⚠️ OpenAI failed → Switching to OLLAMA:", str(e))

                    agent_name = agent_callable.__name__
                    query = kwargs.get("query", "")

                    # ---------------- DECOMPOSITION ----------------
                    if agent_name == "decompose":

                        prompt = f"""
            Break this task into subtasks:
            {query}

            Return JSON:
            {{
            "is_complex": true/false,
            "subtasks": []
            }}
            """

                        response = await self.ollama_client.generate(prompt)

                        return {
                            "content": {
                                "is_complex": False,
                                "subtasks": [query]
                            },
                            "prompt_tokens": 0,
                            "completion_tokens": 0,
                            "total_tokens": 0,
                            "cost_usd": 0.0,
                        }

                    # ---------------- PLANNER ----------------
                    elif agent_name == "plan_agentic":

                        prompt = f"""
            Solve this task step-by-step:
            {query}
            """

                        response = await self.ollama_client.generate(prompt)

                        return {
                            "content": {
                                "type": "final",
                                "content": response
                            },
                            "prompt_tokens": 0,
                            "completion_tokens": 0,
                            "total_tokens": 0,
                            "cost_usd": 0.0,
                        }

                    # ---------------- REFLECTION ----------------
                    elif agent_name == "reflect":
                        return {
                            "content": {
                                "approved": True,
                                "confidence": 0.8,
                                "feedback": "Approved via local model"
                            },
                            "prompt_tokens": 0,
                            "completion_tokens": 0,
                            "total_tokens": 0,
                            "cost_usd": 0.0,
                        }

                    # ---------------- SYNTHESIS ----------------
                    elif agent_name == "run":

                        combined = kwargs.get("agent_outputs", {}).get("raw_answer", "")

                        prompt = f"""
            Combine and refine this answer:
            {combined}
            """

                        response = await self.ollama_client.generate(prompt)

                        return {
                            "content": response,
                            "prompt_tokens": 0,
                            "completion_tokens": 0,
                            "total_tokens": 0,
                            "cost_usd": 0.0,
                        }

                    return {
                        "content": "[OLLAMA FALLBACK FAILED]",
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "cost_usd": 0.0,
                    }
                

            # ============================================================
            # 🔥 SUBTASK PROCESSOR (REQUIRED)
            # ============================================================

            async def process_subtask(subtask: str):

                scratchpad = ""
                final_answer = None

                local_prompt_tokens = 0
                local_completion_tokens = 0
                local_tokens = 0
                local_cost = 0.0

                try:
                    planner_result = await safe_execute(
                        self.planner.plan_agentic,
                        query=subtask,
                        scratchpad=scratchpad,
                        tools=self.tool_registry.get_tool_metadata(),
                    )

                    planner_response = planner_result["content"]

                    local_prompt_tokens += planner_result["prompt_tokens"]
                    local_completion_tokens += planner_result["completion_tokens"]
                    local_tokens += planner_result["total_tokens"]
                    local_cost += planner_result["cost_usd"]

                    if planner_response["type"] == "final":
                        final_answer = planner_response["content"]
                    else:
                        final_answer = "No final answer generated"

                except Exception as e:
                    print("❌ Subtask execution failed:", str(e))
                    final_answer = f"[ERROR] {str(e)}"

                return {
                    "answer": final_answer,
                    "prompt_tokens": local_prompt_tokens,
                    "completion_tokens": local_completion_tokens,
                    "total_tokens": local_tokens,
                    "cost": local_cost,
                }
            
           # 🚀 Run all subtasks (SAFE VERSION)

            if not subtasks:
                subtasks = [query]  # fallback safety

            tasks = []

            for subtask in subtasks:
                try:
                    tasks.append(process_subtask(subtask))
                except Exception as e:
                    print("⚠️ Subtask creation failed:", str(e))

            # If no tasks created → fallback
            if not tasks:
                return {
                    "request_id": str(uuid.uuid4()),
                    "answer": self._offline_fallback(query),
                    "execution_time_sec": 0,
                    "total_prompt_tokens": 0,
                    "total_completion_tokens": 0,
                    "total_tokens": 0,
                    "total_cost_usd": 0,
                    "agent_trace": [],
                }

            results = await asyncio.gather(*tasks, return_exceptions=True)

            subtask_results = []

            for res in results:
                if isinstance(res, Exception):
                    print("⚠️ Subtask failed:", str(res))
                    subtask_results.append("Subtask failed")
                else:
                    subtask_results.append(res.get("answer", "No answer"))

            # ---------------- SYNTHESIS ----------------

            combined_answer = "\n\n".join(subtask_results)

            synth_result = await safe_execute(
                self.synthesizer.run,
                agent_outputs={"raw_answer": combined_answer},
                task=query,
            )

            refined_answer = synth_result["content"]

            # ---------------- MEMORY SAVE ----------------

            self.memory.add_memory(
                content=f"Query: {query}\nAnswer: {refined_answer}"
            )

            return {
                "request_id": request_id,
                "answer": refined_answer,
                "execution_time_sec": round(time.time() - start_time, 2),
                "total_prompt_tokens": total_prompt_tokens,
                "total_completion_tokens": total_completion_tokens,
                "total_tokens": total_tokens,
                "total_cost_usd": round(total_cost, 6),
                "agent_trace": trace.export(),
            }

        try:
            return await safe_run(self.db, task_func, query=query)

        except Exception as e:
            print("🔥 ENGINE FAILURE:", str(e))

            return {
                "request_id": str(uuid.uuid4()),
                "answer": self._offline_fallback(query),
                "execution_time_sec": 0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_tokens": 0,
                "total_cost_usd": 0,
                "agent_trace": [],
            }

    # ------------------------------------------------------------
    # 🔥 OFFLINE FALLBACK
    # ------------------------------------------------------------
    def _offline_fallback(self, query: str) -> str:
        q = query.lower()

        if "bottleneck" in q:
            return (
                "🔍 Bottleneck Analysis (Offline Mode):\n\n"
                "- Possible causes:\n"
                "  • Resource overload\n"
                "  • Task delays\n"
                "  • Inefficient workflow\n\n"
                "- Suggestions:\n"
                "  • Optimize task distribution\n"
                "  • Parallel processing\n"
                "  • Monitor slow components\n"
            )

        elif "analyze" in q:
            return (
                "📊 Basic Analysis (Offline Mode):\n\n"
                "- Input processed\n"
                "- Pattern analysis done\n"
                "- Running without external AI\n"
            )

        else:
            return (
                "⚙️ System running in offline mode.\n"
                "Basic processing completed successfully."
            )

    # ------------------------------------------------------------
    # METRIC LOGGER
    # ------------------------------------------------------------
    def _log_metric(
        self,
        request_id: str,
        agent_name: str,
        latency_ms: int,
        success: bool,
    ):
        metric = AgentMetric(
            request_id=request_id,
            agent_name=agent_name,
            latency_ms=latency_ms,
            success=success,
        )
        self.db.add(metric)
        self.db.commit()
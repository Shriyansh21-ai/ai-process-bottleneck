# genai/engine.py

import time
import uuid
from typing import Dict
import asyncio

from genai.memory import GenAIMemoryDB
from genai.logger import safe_run
from genai.observability import AgentTrace

from genai.agents.planner import PlannerAgent
from genai.agents.synthesizer import SynthesizerAgent
from genai.agents.reflection_agent import ReflectionAgent
from genai.agents.decomposition_agent import DecompositionAgent

# 🔐 Guardrails
from genai.guardrails.prompt_guard import detect_prompt_injection
from genai.guardrails.scope_guard import is_task_allowed

# 🛠 Tools
from genai.tools.tool_registry import ToolRegistry
import genai.tools as tools_package

# 🔐 Permissions
from genai.security.tool_permission import ToolPermissionManager

# 📊 Metrics
from models.agent_metrics import AgentMetric

# 🆕 Routing + Fallback
from genai.routing.model_router import ModelRouter
from genai.routing.fallback_executor import FallbackExecutor


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

            # ---------------- DECOMPOSITION ----------------

            decomp_start = time.time()

            decomp_route = self.model_router.route(
                agent_type="decomposition",
                task=query,
                complexity="high" if len(query) > 300 else "medium",
            )

            decomp_result = await self.fallback_executor.execute(
                model_chain=decomp_route["model_chain"],
                agent_callable=self.decomposer.decompose,
                query=query,
            )

            decomp_data = decomp_result["content"]

            total_prompt_tokens += decomp_result["prompt_tokens"]
            total_completion_tokens += decomp_result["completion_tokens"]
            total_tokens += decomp_result["total_tokens"]
            total_cost += decomp_result["cost_usd"]

            self._check_budget(total_tokens, total_cost)

            trace.record(
                agent="decomposition-agent",
                input_data=query,
                output_data=decomp_data,
                start_time=decomp_start,
                metadata=decomp_route,
            )

            if not decomp_data["is_complex"]:
                subtasks = [query]
            else:
                subtasks = decomp_data["subtasks"]

            # ---------------- SUBTASK EXECUTION ----------------

            
            async def process_subtask(subtask: str):

                scratchpad = ""
                final_answer = None
                max_steps = 5

                local_prompt_tokens = 0
                local_completion_tokens = 0
                local_tokens = 0
                local_cost = 0.0

                for _ in range(max_steps):

                    plan_start = time.time()

                    planner_route = self.model_router.route(
                        agent_type="planner",
                        task=subtask,
                        complexity="high" if len(subtask) > 300 else "medium",
                    )

                    planner_result = await self.fallback_executor.execute(
                        model_chain=planner_route["model_chain"],
                        agent_callable=self.planner.plan_agentic,
                        query=subtask,
                        scratchpad=scratchpad,
                        tools=self.tool_registry.get_tool_metadata(),
                    )

                    planner_response = planner_result["content"]

                    local_prompt_tokens += planner_result["prompt_tokens"]
                    local_completion_tokens += planner_result["completion_tokens"]
                    local_tokens += planner_result["total_tokens"]
                    local_cost += planner_result["cost_usd"]

                    self._check_budget(total_tokens + local_tokens, total_cost + local_cost)

                    trace.record(
                        agent="planner-agent",
                        input_data=subtask,
                        output_data=planner_response,
                        start_time=plan_start,
                        metadata=planner_route,
                    )

                    if planner_response["type"] == "final":
                        final_answer = planner_response["content"]
                        break

                    if planner_response["type"] == "tool":

                        tool_name = planner_response["tool_name"]
                        tool_input = planner_response["tool_input"]

                        if not self.permission_manager.is_allowed(
                            self.session_id, tool_name
                        ):
                            raise PermissionError(
                                f"Tool '{tool_name}' not allowed"
                            )

                        tool_start = time.time()

                        tool_output = self.tool_registry.execute(
                            tool_name,
                            self,
                            tool_input,
                        )

                        scratchpad += (
                            f"\nThought: Used {tool_name}\n"
                            f"Observation: {str(tool_output)}\n"
                        )

                        trace.record(
                            agent=f"{tool_name}-agent",
                            input_data=tool_input,
                            output_data=str(tool_output),
                            start_time=tool_start,
                        )

                if not final_answer:
                    final_answer = "Subtask did not produce a final answer."

                # ---------------- REFLECTION ----------------

                refinement_count = 0

                while refinement_count <= self.max_refinements:

                    reflection_start = time.time()

                    reflection_route = self.model_router.route(
                        agent_type="reflection",
                        task=subtask,
                        complexity="medium",
                    )

                    reflection_data = await self.fallback_executor.execute(
                        model_chain=reflection_route["model_chain"],
                        agent_callable=self.reflection_agent.reflect,
                        query=subtask,
                        answer=final_answer,
                        scratchpad=scratchpad,
                    )

                    reflection_result = reflection_data["content"]

                    local_prompt_tokens += reflection_data["prompt_tokens"]
                    local_completion_tokens += reflection_data["completion_tokens"]
                    local_tokens += reflection_data["total_tokens"]
                    local_cost += reflection_data["cost_usd"]

                    self._check_budget(total_tokens + local_tokens, total_cost + local_cost)

                    trace.record(
                        agent="reflection-agent",
                        input_data=subtask,
                        output_data=reflection_result,
                        start_time=reflection_start,
                        metadata=reflection_route,
                    )

                    confidence = reflection_result.get("confidence", 1.0)
                    approved = reflection_result.get("approved", True)

                    if approved and confidence >= self.confidence_threshold:
                        break

                    refinement_count += 1

                    refinement_prompt = (
                        f"The previous answer had issues:\n"
                        f"{reflection_result.get('feedback')}\n\n"
                        f"Improve accuracy and completeness."
                    )

                    improved_route = self.model_router.route(
                        agent_type="planner",
                        task=subtask,
                        complexity="high",
                    )

                    improved_result = await self.fallback_executor.execute(
                        model_chain=improved_route["model_chain"],
                        agent_callable=self.planner.plan_agentic,
                        query=subtask + "\n\n" + refinement_prompt,
                        scratchpad=scratchpad,
                        tools=self.tool_registry.get_tool_metadata(),
                    )

                    improved_response = improved_result["content"]

                    local_prompt_tokens += improved_result["prompt_tokens"]
                    local_completion_tokens += improved_result["completion_tokens"]
                    local_tokens += improved_result["total_tokens"]
                    local_cost += improved_result["cost_usd"]

                    self._check_budget(total_tokens + local_tokens, total_cost + local_cost)

                    if improved_response["type"] == "final":
                        final_answer = improved_response["content"]
                    else:
                        break

                return {
                    "answer": final_answer,
                    "prompt_tokens": local_prompt_tokens,
                    "completion_tokens": local_completion_tokens,
                    "total_tokens": local_tokens,
                    "cost": local_cost,
                }


            # 🚀 Run all subtasks in parallel
            tasks = [process_subtask(subtask) for subtask in subtasks]
            results = await asyncio.gather(*tasks)

            subtask_results = []

            for res in results:
                subtask_results.append(res["answer"])

                total_prompt_tokens += res["prompt_tokens"]
                total_completion_tokens += res["completion_tokens"]
                total_tokens += res["total_tokens"]
                total_cost += res["cost"]

                self._check_budget(total_tokens, total_cost)

            # ---------------- SYNTHESIS ----------------

            combined_answer = "\n\n".join(subtask_results)

            synth_start = time.time()

            synth_route = self.model_router.route(
                agent_type="synthesizer",
                task=query,
                estimated_tokens=len(combined_answer),
            )

            synth_result = await self.fallback_executor.execute(
                model_chain=synth_route["model_chain"],
                agent_callable=self.synthesizer.run,
                agent_outputs={"raw_answer": combined_answer},
                task=query,
            )

            refined_answer = synth_result["content"]

            total_prompt_tokens += synth_result["prompt_tokens"]
            total_completion_tokens += synth_result["completion_tokens"]
            total_tokens += synth_result["total_tokens"]
            total_cost += synth_result["cost_usd"]

            self._check_budget(total_tokens, total_cost)

            trace.record(
                agent="synthesizer-agent",
                input_data=query,
                output_data=refined_answer,
                start_time=synth_start,
                metadata=synth_route,
            )

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

        return await safe_run(self.db, task_func, query=query)

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
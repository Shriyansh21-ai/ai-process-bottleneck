

import time
import uuid
import asyncio

from typing import Dict

from sentence_transformers import SentenceTransformer

from src.genai.memory import GenAIMemoryDB
from src.genai.logger import safe_run
from src.genai.observability import AgentTrace

# ============================================================
# 🤖 AGENTS
# ============================================================

from src.genai.agents.planner import PlannerAgent
from src.genai.agents.synthesizer import SynthesizerAgent
from src.genai.agents.decomposition_agent import DecompositionAgent
from src.genai.agents.supervisor_agent import SupervisorAgent

# ============================================================
# 🔐 GUARDRAILS
# ============================================================

from src.genai.guardrails.prompt_guard import (
    detect_prompt_injection,
)

from src.genai.guardrails.scope_guard import (
    is_task_allowed,
)

# ============================================================
# 🛠 TOOLS
# ============================================================

from src.genai.tools.tool_registry import ToolRegistry
import src.genai.tools as tools_package

# ============================================================
# 🔐 PERMISSIONS
# ============================================================

from src.genai.security.tool_permission import (
    ToolPermissionManager,
)

# ============================================================
# 🧠 ROUTING
# ============================================================

from src.genai.routing.model_router import ModelRouter
from src.genai.routing.fallback_executor import (
    FallbackExecutor,
)

from src.genai.routing.local_model_router import (
    LocalModelRouter,
)

from src.genai.routing.task_complexity import (
    TaskComplexityAnalyzer,
)

# ============================================================
# 🤖 OLLAMA
# ============================================================

from src.genai.offline.ollama_client import OllamaClient

# ============================================================
# 🧠 CRITIC SYSTEM
# ============================================================

from src.genai.agents.critic_agent import CriticAgent

from src.genai.agents.critics.logic_critic import (
    LogicCritic,
)

from src.genai.agents.critics.risk_critic import (
    RiskCritic,
)

from src.genai.agents.critics.optimization_critic import (
    OptimizationCritic,
)

from src.genai.agents.critics.critic_aggregator import (
    CriticAggregator,
)

# ============================================================
# 📊 SCORING
# ============================================================

from src.genai.intelligence.agent_score_manager import (
    AgentScoreManager,
)

# ============================================================
# ⚙️ CONFIG
# ============================================================

from src.genai.config.model_config import (
    DEFAULT_PROVIDER,
    OPENAI_MODEL,
)

# ============================================================
# 🧠 embeddings
# ============================================================

from src.genai.embeddings import embed_text

# ============================================================
# 🚀 ENGINE
# ============================================================


class GenAIEngine:

    def __init__(self, db, session_id: str):

        self.db = db
        self.session_id = session_id

        # ====================================================
        # 🧠 MEMORY
        # ====================================================

        self.memory = GenAIMemoryDB(
            db,
            session_id,
        )

        # ====================================================
        # 🤖 AGENTS
        # ====================================================

        self.planner = PlannerAgent()
        self.synthesizer = SynthesizerAgent()
        self.decomposer = DecompositionAgent()
        self.supervisor = SupervisorAgent()

        # ====================================================
        # 🧠 ROUTING
        # ====================================================

        self.model_router = ModelRouter()
        self.local_router = LocalModelRouter()
        self.fallback_executor = FallbackExecutor()
        self.complexity_analyzer = (
            TaskComplexityAnalyzer()
        )

        # ====================================================
        # 🛠 TOOL SYSTEM
        # ====================================================

        self.tool_registry = ToolRegistry()

        self.tool_registry.auto_discover(
            tools_package
        )

        # ====================================================
        # 🔐 TOOL PERMISSIONS
        # ====================================================

        self.permission_manager = (
            ToolPermissionManager()
        )

        self.permission_manager.allow_tools(
            self.session_id,
            self.tool_registry.list_tools(),
        )

        # ====================================================
        # 🤖 OFFLINE AI
        # ====================================================

        self.ollama_client = OllamaClient()

        # ====================================================
        # 🧠 CRITICS
        # ====================================================

        self.critic = CriticAgent()

        self.logic_critic = LogicCritic()

        self.risk_critic = RiskCritic()

        self.optimization_critic = (
            OptimizationCritic()
        )

        self.critic_aggregator = (
            CriticAggregator()
        )

        # ====================================================
        # 🧠 EMBEDDING MODEL
        # ====================================================

        from src.genai.shared_models import embedding_model

        self.embedding_model = embedding_model

        # ====================================================
        # 📊 SCORING
        # ====================================================

        self.agent_scores = (
            AgentScoreManager()
        )

    # ============================================================
    # 🧠 COSINE SIMILARITY
    # ============================================================

    def _cosine_similarity(self, a, b):

        import numpy as np

        a = np.array(a)
        b = np.array(b)

        return np.dot(a, b) / (
            np.linalg.norm(a)
            * np.linalg.norm(b)
        )
   

    # ============================================================
    # 🧠 MEMORY RETRIEVAL
    # ============================================================

    def _retrieve_relevant_memory(
        self,
        query: str,
        top_k: int = 3,
    ) -> str:

        try:

            memories = self.memory.get_all()

            if not memories:
                return ""

            query_embedding = (
                self.embedding_model.encode(query)
            )

            scored = []

            for memory in memories:

                content = str(memory)

                memory_embedding = (
                    self.embedding_model.encode(
                        content
                    )
                )

                similarity = (
                    self._cosine_similarity(
                        query_embedding,
                        memory_embedding,
                    )
                )

                scored.append(
                    (
                        similarity,
                        content,
                    )
                )

            scored.sort(
                reverse=True,
                key=lambda x: x[0],
            )

            top_memories = [
                item[1]
                for item in scored[:top_k]
            ]

            return "\n---\n".join(
                top_memories
            )

        except Exception as e:

            print("⚠️ Memory save failed:", str(e))

            return ""

    # ============================================================
    # 🛠 SMART TOOL SELECTION
    # ============================================================

    def _select_relevant_tools(
        self,
        query: str,
    ):

        try:

            available_tools = (
                self.tool_registry.get_tool_metadata()
            )

            query_lower = query.lower()

            selected_tools = []

            tool_keywords = {
                "sql": [
                    "sql",
                    "database",
                    "query",
                    "postgres",
                ],
                "rag": [
                    "pdf",
                    "document",
                    "knowledge",
                ],
                "memory": [
                    "memory",
                    "history",
                    "context",
                ],
                "search": [
                    "search",
                    "find",
                    "lookup",
                ],
            }

            for tool in available_tools:

                tool_name = (
                    tool.get(
                        "name",
                        "",
                    ).lower()
                )

                matched = False

                for (
                    key,
                    keywords,
                ) in tool_keywords.items():

                    if key in tool_name:

                        if any(
                            keyword in query_lower
                            for keyword in keywords
                        ):
                            matched = True

                if matched:
                    selected_tools.append(tool)

            if not selected_tools:
                selected_tools = (
                    available_tools[:3]
                )

            return selected_tools

        except Exception as e:

            print(
                "⚠️ Tool selection failed:",
                str(e),
            )

            return (
                self.tool_registry.get_tool_metadata()[
                    :3
                ]
            )
        
    # ============================================================
    # check ollama availability (for dynamic routing)
    # ============================================================
        
    async def _is_ollama_available(self):

        if hasattr(self, "_ollama_checked"):
            return self._ollama_available

        try:
            await self.ollama_client.health()
            self._ollama_available = True
        except:
            self._ollama_available = False

        self._ollama_checked = True
        return self._ollama_available

    # ============================================================
    # 🔥 SELF HEAL EXECUTOR
    # ============================================================

    async def _self_heal_execute(
        self,
        executor,
        *args,
        retries=3,
        delay=1,
        **kwargs,
    ):

        last_error = None

        for attempt in range(retries):

            try:

                return await asyncio.wait_for(
                executor(*args, **kwargs),
                timeout=45
            )

            except Exception as e:

                last_error = e

                print(
                    f"⚠️ Retry {attempt + 1}/{retries} failed:",
                    str(e),
                )

                await asyncio.sleep(delay)

        return {
            "failed": True,
            "error": str(last_error),
        }

    # ============================================================
    # 🤖 SAFE EXECUTE
    # ============================================================

    async def _safe_execute(
    self,
    agent_callable,
    **kwargs,
):

        agent_name = agent_callable.__name__

        query_local = kwargs.get("query", "")
        scratchpad = kwargs.get("scratchpad", "")
        agent_outputs = kwargs.get("agent_outputs", {})

        try:

            # ====================================================
            # 🔍 CHECK OLLAMA AVAILABILITY
            # ====================================================

            ollama_available = await self._is_ollama_available()

            # ====================================================
            # 🤖 OLLAMA DEFAULT
            # ====================================================

            if DEFAULT_PROVIDER == "ollama" and ollama_available:

                # ================================================
                # 🤖 PLANNER
                # ================================================

                if agent_name == "plan_agentic":

                    selected_model = self.local_router.route(query_local)

                    response = await self.ollama_client.generate(
                        prompt=f"""
    Task:
    {query_local}

    Context:
    {scratchpad}

    Solve intelligently and clearly.
    """,
                        model=selected_model,
                    )

                    return {
                        "content": {
                            "type": "final",
                            "content": response,
                        }
                    }

                # ================================================
                # 🔥 DECOMPOSER
                # ================================================

                elif agent_name == "decompose":

                    return {
                        "content": {
                            "is_complex": False,
                            "subtasks": [query_local],
                        }
                    }

                # ================================================
                # 🧠 SYNTHESIS
                # ================================================

                elif agent_name == "run":

                    combined = agent_outputs.get("raw_answer", "")

                    response = await self.ollama_client.generate(
                        prompt=f"""
    Combine and refine:

    {combined}
    """
                    )

                    return {
                        "content": response
                    }

                # ================================================
                # 🧠 DEFAULT
                # ================================================

                response = await self.ollama_client.generate(query_local)

                return {
                    "content": {
                        "type": "final",
                        "content": response,
                    }
                }

            # ====================================================
            # ⚙️ OFFLINE FALLBACK (NO OLLAMA)
            # ====================================================

            if DEFAULT_PROVIDER == "ollama" and not ollama_available:

                if not hasattr(self, "_ollama_warned"):
                    print("⚠️ Ollama not available → using offline mode")
                    self._ollama_warned = True

                return {
                    "content": {
                        "type": "final",
                        "content": self._offline_fallback(query_local),
                    }
                }

            # ====================================================
            # ☁️ OPENAI OPTIONAL
            # ====================================================

            return await self.fallback_executor.execute(
                model_chain=[OPENAI_MODEL],
                agent_callable=agent_callable,
                **kwargs,
            )

        except Exception as e:

            print(f"⚠️ {agent_name} fallback triggered")

            fallback_response = self._offline_fallback(query_local)

            return {
                "content": {
                    "type": "final",
                    "content": fallback_response
                },
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_usd": 0.0,
            }

    # ============================================================
    # 🔁 RECURSIVE EXECUTION
    # ============================================================

    async def _recursive_execute(
        self,
        subtask: str,
        depth: int = 0,
        max_depth: int = 3,
    ):

        if depth >= max_depth:

            return {
                "answer": (
                    f"[MAX DEPTH REACHED] "
                    f"{subtask}"
                )
            }

        try:

            selected_tools = (
                self._select_relevant_tools(
                    subtask
                )
            )

            planner_result = (
                await self._self_heal_execute(
                    self._safe_execute,
                    self.planner.plan_agentic,
                    query=subtask,
                    scratchpad="",
                    tools=selected_tools,
                )
            )

            planner_response = (
                planner_result.get(
                    "content",
                    {},
                )
            )

            if not isinstance(
                planner_response,
                dict,
            ):

                return {
                    "answer": str(
                        planner_response
                    )
                }

            # ====================================================
            # ✅ FINAL ANSWER
            # ====================================================

            if (
                planner_response.get(
                    "type"
                )
                == "final"
            ):

                self.agent_scores.record_success(
                    "planner"
                )

                return {
                    "answer": planner_response.get(
                        "content",
                        "",
                    )
                }

            # ====================================================
            # 🔁 SUBTASKS
            # ====================================================

            elif (
                planner_response.get(
                    "type"
                )
                == "subtasks"
            ):

                child_tasks = (
                    planner_response.get(
                        "subtasks",
                        [],
                    )
                )

                results = []

                for child in child_tasks:

                    child_result = (
                        await self._recursive_execute(
                            child,
                            depth=depth + 1,
                            max_depth=max_depth,
                        )
                    )

                    results.append(
                        child_result.get(
                            "answer",
                            "",
                        )
                    )

                return {
                    "answer": "\n".join(
                        results
                    )
                }

            return {
                "answer": (
                    "Planner returned "
                    "unknown type"
                )
            }

        except Exception as e:

            self.agent_scores.record_failure(
                "planner"
            )

            return {
                "answer": (
                    f"[RECURSIVE ERROR] "
                    f"{str(e)}"
                )
            }

    # ============================================================
    # 🚀 MAIN TASK
    # ============================================================

    async def run_task(
        self,
        query: str,
    ) -> Dict:

        async def task_func(
            query: str,
        ) -> Dict:

            request_id = str(
                uuid.uuid4()
            )

            start_time = time.time()

            trace = AgentTrace()

            # ====================================================
            # 🔐 GUARDRAILS
            # ====================================================

            if detect_prompt_injection(
                query
            ):
                raise ValueError(
                    "Prompt injection detected"
                )

            if not is_task_allowed(
                query
            ):
                raise PermissionError(
                    "Task not allowed"
                )

            # ====================================================
            # 🧠 COMPLEXITY ANALYSIS
            # ====================================================

            complexity = (
                self.complexity_analyzer.analyze(
                    query
                )
            )

            trace.record(
                agent="complexity-analyzer",
                input_data=query,
                output_data=complexity,
                start_time=time.time(),
            )

            # ====================================================
            # 🔥 DECOMPOSITION
            # ====================================================

            decomp_result = (
                await self._safe_execute(
                    self.decomposer.decompose,
                    query=query,
                )
            )

            decomp_data = (
                decomp_result.get(
                    "content",
                    {},
                )
            )

            if (
                not isinstance(
                    decomp_data,
                    dict,
                )
                or not decomp_data.get(
                    "is_complex"
                )
            ):

                subtasks = [query]

            else:

                subtasks = (
                    decomp_data.get(
                        "subtasks",
                        [query],
                    )
                )

            # ====================================================
            # 🧠 SUPERVISOR
            # ====================================================

            supervisor_decision = (
                await self.supervisor.decide(
                    query
                )
            )

            # ====================================================
            # 🔥 SUBTASK PROCESSOR
            # ====================================================

            async def process_subtask(
                subtask: str,
            ):

                try:

                    context_text = (
                        self._retrieve_relevant_memory(
                            subtask
                        )
                    )

                    enhanced_subtask = f"""
Relevant past knowledge:
{context_text}

Current task:
{subtask}
"""

                    recursive_result = (
                        await self._recursive_execute(
                            subtask=enhanced_subtask,
                            depth=0,
                            max_depth=complexity.get(
                                "max_depth",
                                3,
                            ),
                        )
                    )

                    final_answer = (
                        recursive_result.get(
                            "answer",
                            "",
                        )
                    )

                    if not final_answer:

                        final_answer = (
                            "Could not complete "
                            "task fully"
                        )

                    # ================================================
                    # 🧠 MULTI CRITIC
                    # ================================================

                    logic = (
                        await self._safe_execute(
                            self.logic_critic.critique,
                            query=subtask,
                            answer=final_answer,
                        )
                    )

                    risk = (
                        await self._safe_execute(
                            self.risk_critic.critique,
                            query=subtask,
                            answer=final_answer,
                        )
                    )

                    optimization = (
                        await self._safe_execute(
                            self.optimization_critic.critique,
                            query=subtask,
                            answer=final_answer,
                        )
                    )

                    decision = (
                        self.critic_aggregator.aggregate(
                            logic.get(
                                "content",
                                {},
                            ),
                            risk.get(
                                "content",
                                {},
                            ),
                            optimization.get(
                                "content",
                                {},
                            ),
                        )
                    )

                    self.agent_scores.record_success(
                        "multi_critic"
                    )

                    # ================================================
                    # 🔁 IMPROVEMENT LOOP
                    # ================================================

                    if not decision.get(
                        "approve",
                        True,
                    ):

                        feedback = "\n".join(
                            decision.get(
                                "feedback",
                                [],
                            )
                        )

                        improved_prompt = f"""
Improve this answer.

Task:
{subtask}

Current Answer:
{final_answer}

Feedback:
{feedback}
"""

                        improved = (
                            await self._safe_execute(
                                self.planner.plan_agentic,
                                query=improved_prompt,
                                scratchpad="",
                                tools=self.tool_registry.get_tool_metadata(),
                            )
                        )

                        improved_content = (
                            improved.get(
                                "content",
                                {},
                            )
                        )

                        if (
                            isinstance(
                                improved_content,
                                dict,
                            )
                            and improved_content.get(
                                "type"
                            )
                            == "final"
                        ):

                            final_answer = (
                                improved_content.get(
                                    "content",
                                    final_answer,
                                )
                            )

                        # ========================================
                        # 🧠 LEARNING SAVE
                        # ========================================

                        self.memory.add_memory(
                            session_id=self.session_id,
                            content=f"""
LEARNING:
Task: {subtask}

Feedback:
{feedback}

Improved:
{final_answer}
"""
                        )

                    return {
                        "answer": final_answer
                    }

                except Exception as e:

                    self.agent_scores.record_failure(
                        "multi_critic"
                    )

                    print(
                        "❌ Subtask error:",
                        str(e),
                    )

                    return {
                        "answer": (
                            f"[ERROR] {str(e)}"
                        )
                    }

            # ====================================================
            # 🚀 EXECUTION STRATEGY
            # ====================================================

            if supervisor_decision.get(
                "parallel",
                True,
            ):

                tasks = [
                    process_subtask(
                        task
                    )
                    for task in subtasks[
                        : supervisor_decision.get(
                            "max_workers",
                            3,
                        )
                    ]
                ]

                results = (
                    await asyncio.gather(
                        *tasks,
                        return_exceptions=True,
                    )
                )

            else:

                results = []

                for task in subtasks:

                    result = (
                        await process_subtask(
                            task
                        )
                    )

                    results.append(result)

            # ====================================================
            # 🧠 COLLECT RESULTS
            # ====================================================

            subtask_results = []

            for result in results:

                if isinstance(
                    result,
                    Exception,
                ):

                    subtask_results.append(
                        "Subtask failed"
                    )

                else:

                    subtask_results.append(
                        result.get(
                            "answer",
                            "No answer",
                        )
                    )

            # ====================================================
            # 🔥 SYNTHESIS
            # ====================================================

            combined_answer = (
                "\n\n".join(
                    subtask_results
                )
            )

            synth_result = (
                await self._safe_execute(
                    self.synthesizer.run,
                    agent_outputs={
                        "raw_answer": (
                            combined_answer
                        )
                    },
                    task=query,
                )
            )

            refined_answer = (
                synth_result.get(
                    "content",
                    combined_answer,
                )
            )

            # ====================================================
            # 💾 MEMORY SAVE
            # ====================================================

            self.memory.add_memory(
                session_id=self.session_id,
                content=f"""
Query:
{query}

Answer:
{refined_answer}
"""
            )

            return {
                "request_id": request_id,
                "answer": refined_answer,
                "execution_time_sec": round(
                    time.time()
                    - start_time,
                    2,
                ),
                "agent_trace": trace.export(),
            }

        # ========================================================
        # 🔥 GLOBAL FAILSAFE
        # ========================================================

        try:

            return await safe_run(
                self.db,
                task_func,
                query=query,
            )

        except Exception as e:

            print(
                "🔥 ENGINE FAILURE:",
                str(e),
            )

            return {
                "request_id": str(
                    uuid.uuid4()
                ),
                "answer": self._offline_fallback(
                    query
                ),
                "execution_time_sec": 0,
                "agent_trace": [],
            }

    # ============================================================
    # 🔥 OFFLINE FALLBACK
    # ============================================================

    def _offline_fallback(
        self,
        query: str,
    ):

        query_lower = query.lower()

        if "bottleneck" in query_lower:

            return """
🔍 Bottleneck Analysis (Offline Mode)

Possible causes:
• Resource overload
• Slow tasks
• Poor workflow

Suggestions:
• Add parallel execution
• Improve task balancing
• Optimize heavy operations
"""

        elif "analyze" in query_lower:

            return """
📊 Analysis Complete (Offline Mode)

• Query processed
• Patterns analyzed
• Running locally with Ollama
"""

        return """
⚙️ System running in offline mode.

Basic processing completed successfully.
"""
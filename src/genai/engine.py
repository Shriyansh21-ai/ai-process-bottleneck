# genai/engine.py

import time
import uuid
from typing import Dict
import asyncio

from src.genai.memory import GenAIMemoryDB
from src.genai.logger import safe_run
from src.genai.observability import AgentTrace

from src.genai.agents.planner import PlannerAgent
from src.genai.agents.synthesizer import SynthesizerAgent
from src.genai.agents.reflection_agent import ReflectionAgent
from src.genai.agents.decomposition_agent import DecompositionAgent
from src.genai.agents.supervisor_agent import SupervisorAgent

# 🔐 Guardrails
from src.genai.guardrails.prompt_guard import detect_prompt_injection
from src.genai.guardrails.scope_guard import is_task_allowed

# 🛠 Tools
from src.genai.tools.tool_registry import ToolRegistry
import src.genai.tools as tools_package

# 🔐 Permissions
from src.genai.security.tool_permission import ToolPermissionManager

# 🧠 Routing + Fallback
from src.genai.routing.model_router import ModelRouter
from src.genai.routing.fallback_executor import FallbackExecutor

# 🤖 Offline
from src.genai.offline.ollama_client import OllamaClient

# 🧠 Critics
from src.genai.agents.critic_agent import CriticAgent
from src.genai.agents.critics.logic_critic import LogicCritic
from src.genai.agents.critics.risk_critic import RiskCritic
from src.genai.agents.critics.optimization_critic import OptimizationCritic
from src.genai.agents.critics.critic_aggregator import CriticAggregator

#semantic search
from sentence_transformers import SentenceTransformer

#scoring system
from src.genai.intelligence.agent_score_manager import AgentScoreManager

class GenAIEngine:

    def __init__(self, db, session_id: str):
        self.db = db
        self.session_id = session_id

        # 🧠 Memory
        self.memory = GenAIMemoryDB(db, session_id)

        # 🤖 Agents
        self.planner = PlannerAgent()
        self.synthesizer = SynthesizerAgent()
        self.decomposer = DecompositionAgent()
        self.supervisor = SupervisorAgent()

        # 🧠 Routing
        self.model_router = ModelRouter()
        self.fallback_executor = FallbackExecutor()

        # 🛠 Tools
        self.tool_registry = ToolRegistry()
        self.tool_registry.auto_discover(tools_package)

        # 🔐 Permissions
        self.permission_manager = ToolPermissionManager()
        self.permission_manager.allow_tools(
            self.session_id,
            self.tool_registry.list_tools()
        )

        # 🤖 Offline
        self.ollama_client = OllamaClient()

        # 🧠 Critics
        self.critic = CriticAgent()
        self.logic_critic = LogicCritic()
        self.risk_critic = RiskCritic()
        self.optimization_critic = OptimizationCritic()
        self.critic_aggregator = CriticAggregator()

        #  Semantic Search 
        self.embedding_model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)
        # Scoring System
        self.agent_score_manager = AgentScoreManager()

    def _retrieve_relevant_memory(
    self,
    query: str,
    top_k: int = 3
) -> str:

        try:
            memories = self.memory.get_all()

            if not memories:
                return ""

            query_embedding = self.embedding_model.encode(query)

            scored = []

            for m in memories:

                content = str(m)

                memory_embedding = self.embedding_model.encode(content)

                similarity = self._cosine_similarity(
                    query_embedding,
                    memory_embedding
                )

                scored.append((similarity, content))

            scored.sort(reverse=True, key=lambda x: x[0])

            top_memories = [
                c for _, c in scored[:top_k]
            ]

            return "\n---\n".join(top_memories)

        except Exception as e:
            print("⚠️ Semantic retrieval failed:", str(e))
            return ""
        
    def _cosine_similarity(self, a, b):

        import numpy as np

        a = np.array(a)
        b = np.array(b)

        return np.dot(a, b) / (
            np.linalg.norm(a) * np.linalg.norm(b)
        )
    
    def _select_relevant_tools(self, query: str):

        try:

            available_tools = self.tool_registry.get_tool_metadata()

            query_lower = query.lower()

            selected_tools = []

            tool_keywords = {
                "sql": ["sql", "database", "query", "postgres"],
                "rag": ["document", "pdf", "knowledge", "retrieve"],
                "memory": ["remember", "history", "context"],
                "search": ["search", "find", "lookup"],
            }

            for tool in available_tools:

                tool_name = tool.get("name", "").lower()

                matched = False

                for key, keywords in tool_keywords.items():

                    if key in tool_name:

                        if any(k in query_lower for k in keywords):
                            matched = True

                if matched:
                    selected_tools.append(tool)

            # fallback safety
            if not selected_tools:
                selected_tools = available_tools[:3]

            return selected_tools

        except Exception as e:
            print("⚠️ Tool selection failed:", str(e))

            return self.tool_registry.get_tool_metadata()[:3]

    # ============================================================
    # 🔥 MAIN EXECUTION
    # ============================================================

    async def _self_heal_execute(
    self,
    executor,
    *args,
    retries=3,
    delay=1,
    **kwargs
):

        last_error = None

        for attempt in range(retries):

            try:

                return await executor(*args, **kwargs)

            except Exception as e:

                last_error = e
                print("🛠 Self-healing activated...")

                print(
                    f"⚠️ Retry {attempt + 1}/{retries} failed:",
                    str(e)
                )

                await asyncio.sleep(delay)

        return {
            "error": str(last_error),
            "failed": True
        }

    async def _recursive_execute(
    self,
    subtask: str,
    depth: int = 0,
    max_depth: int = 3,
):

        if depth >= max_depth:
            return {
                "answer": f"[MAX DEPTH REACHED] {subtask}"
            }

        try:

            # 🧠 Dynamic tool selection
            selected_tools = self._select_relevant_tools(subtask)

            # 🤖 Planner
            planner_result = await self._self_heal_execute(
                self.fallback_executor.execute,
                model_chain=["gpt-4o-mini"],
                agent_callable=self.planner.plan_agentic,
                query=subtask,
                scratchpad="",
                tools=selected_tools,
            )

            planner_response = planner_result["content"]

            if not isinstance(planner_response, dict):

                return {
                    "answer": str(planner_response)
                }

            # ====================================================
            # ✅ FINAL ANSWER
            # ====================================================
            self.agent_scores.record_success("planner")

            if planner_response.get("type") == "final":

                return {
                    "answer": planner_response["content"]
                }

            # ====================================================
            # 🔁 RECURSIVE SUBTASKS
            # ====================================================

            elif planner_response.get("type") == "subtasks":

                child_tasks = planner_response.get(
                    "subtasks",
                    []
                )

                results = []

                for child in child_tasks:

                    child_result = await self._recursive_execute(
                        child,
                        depth=depth + 1,
                        max_depth=max_depth,
                    )

                    results.append(
                        child_result.get("answer", "")
                    )

                combined = "\n".join(results)

                return {
                    "answer": combined
                }

            return {
                "answer": "Planner returned unknown type"
            }

        except Exception as e:

            self.agent_scores.record_failure("planner")

            return {
                "answer": f"[RECURSIVE ERROR] {str(e)}"
            }
        
    
    async def run_task(self, query: str) -> Dict:

        async def task_func(query: str) -> Dict:

            request_id = str(uuid.uuid4())
            start_time = time.time()
            trace = AgentTrace()

            # ---------------- GUARDRAILS ----------------
            if detect_prompt_injection(query):
                raise ValueError("Prompt injection detected")

            if not is_task_allowed(query):
                raise PermissionError("Task not allowed")

            # ============================================================
            # 🔥 SAFE EXECUTE (OPENAI → OLLAMA)
            # ============================================================

            async def safe_execute(agent_callable, **kwargs):
                try:
                    return await self.fallback_executor.execute(
                        model_chain=["gpt-4o-mini"],
                        agent_callable=agent_callable,
                        **kwargs
                    )
                except Exception as e:
                    print("⚠️ OpenAI failed → OLLAMA:", str(e))

                    try:
                        response = await self.ollama_client.generate(
                            f"{kwargs.get('query', '')}"
                        )
                        return {
                            "content": {
                                "type": "final",
                                "content": response
                            }
                        }
                    except Exception:
                        return {"content": "[SYSTEM FALLBACK]"}

            # ============================================================
            # 🧠 LEARNING FROM MEMORY (NEW FEATURE)
            # ============================================================

            past_context = self.memory.search(query, limit=3)
            context_text = "\n".join([m["content"] for m in past_context]) if past_context else ""

            # ============================================================
            # 🔥 DECOMPOSITION
            # ============================================================

            decomp_result = await safe_execute(
                self.decomposer.decompose,
                query=query
            )

            decomp_data = decomp_result["content"]

            if not isinstance(decomp_data, dict) or not decomp_data.get("is_complex"):
                subtasks = [query]
            else:
                subtasks = decomp_data.get("subtasks", [query])

            # ============================================================
            # 🧠 SUPERVISOR
            # ============================================================

            supervisor_decision = await self.supervisor.decide(query)

            # ============================================================
            # 🔥 SUBTASK PROCESSOR
            # ============================================================

            async def process_subtask(subtask: str):

                try:
                    # ============================================================
                    # 🔥 REACT LOOP (THINK → TOOL → OBSERVE)
                    # ============================================================

                    context_text = self._retrieve_relevant_memory(subtask)

                    max_steps = 5
                    scratchpad = ""
                    final_answer = None

                    for step in range(max_steps):

                        enhanced_query = f"""
                    Relevant past knowledge:
                    {context_text}

                    Current task:
                    {subtask}

                    Previous reasoning:
                    {scratchpad}
                    """

                        recursive_result = await self._recursive_execute(
                            subtask=subtask,
                            depth=0,
                            max_depth=3,
                        )

                        final_answer = recursive_result["answer"]

                    # ============================================================
                    # 🧠 FALLBACK IF NO ANSWER
                    # ============================================================

                    if not final_answer:
                        final_answer = "Could not complete task fully"

                    # ============================================================
                    # 🧠 MULTI-CRITIC (ALWAYS RUN)
                    # ============================================================

                    logic = await safe_execute(
                        self.logic_critic.critique,
                        query=subtask,
                        answer=final_answer
                    )

                    risk = await safe_execute(
                        self.risk_critic.critique,
                        query=subtask,
                        answer=final_answer
                    )

                    optimization = await safe_execute(
                        self.optimization_critic.critique,
                        query=subtask,
                        answer=final_answer
                    )

                    decision = self.critic_aggregator.aggregate(
                        logic.get("content", {}),
                        risk.get("content", {}),
                        optimization.get("content", {})
                    )

                    self.agent_scores.record_success("multi_critic")

                    # ============================================================
                    # 🔁 IMPROVEMENT LOOP + LEARNING
                    # ============================================================

                    if not decision.get("approve", True):

                        feedback = "\n".join(decision.get("feedback", []))

                        improved_prompt = f"""
            Improve this answer:

            {subtask}

            Current Answer:
            {final_answer}

            Feedback:
            {feedback}
            """

                        improved = await safe_execute(
                            self.planner.plan_agentic,
                            query=improved_prompt,
                            scratchpad="",
                            tools=self.tool_registry.get_tool_metadata(),
                        )

                        improved_content = improved.get("content", {})

                        if isinstance(improved_content, dict) and improved_content.get("type") == "final":
                            final_answer = improved_content.get("content", final_answer)

                        # 🧠 SAVE LEARNING
                        self.memory.add_memory(
                            content=f"LEARNING:\nTask:{subtask}\nMistake:{feedback}\nImproved:{final_answer}"
                        )

                    return {"answer": final_answer}

                except Exception as e:

                    self.agent_scores.record_failure("multi_critic")
                    print("❌ Subtask error:", str(e))
                    return {"answer": f"[ERROR] {str(e)}"}

            # ============================================================
            # 🚀 EXECUTION STRATEGY
            # ============================================================

            if supervisor_decision.get("parallel", True):
                tasks = [
                    process_subtask(s)
                    for s in subtasks[:supervisor_decision.get("max_workers", 3)]
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
            else:
                results = []
                for s in subtasks:
                    res = await process_subtask(s)
                    results.append(res)

            # ============================================================
            # 🧠 COLLECT RESULTS
            # ============================================================

            subtask_results = []

            for r in results:
                if isinstance(r, Exception):
                    subtask_results.append("Subtask failed")
                else:
                    subtask_results.append(r.get("answer", "No answer"))

            # ============================================================
            # 🔥 SYNTHESIS
            # ============================================================

            combined_answer = "\n\n".join(subtask_results)

            synth_result = await safe_execute(
                self.synthesizer.run,
                agent_outputs={"raw_answer": combined_answer},
                task=query,
            )

            refined_answer = synth_result.get("content", combined_answer)

            # ============================================================
            # 💾 MEMORY SAVE
            # ============================================================

            self.memory.add_memory(
                content=f"Query: {query}\nAnswer: {refined_answer}"
            )

            return {
                "request_id": request_id,
                "answer": refined_answer,
                "execution_time_sec": round(time.time() - start_time, 2),
                "agent_trace": trace.export(),
            }

        # ============================================================
        # 🔥 GLOBAL FALLBACK
        # ============================================================

        try:
            return await safe_run(self.db, task_func, query=query)

        except Exception as e:
            print("🔥 ENGINE FAILURE:", str(e))

            return {
                "request_id": str(uuid.uuid4()),
                "answer": "System fallback response",
                "execution_time_sec": 0,
                "agent_trace": [],
            }
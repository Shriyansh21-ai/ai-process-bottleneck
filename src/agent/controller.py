import asyncio
import os

from src.agent.planner import PlannerAgent
from src.agent.executor import ToolExecutor
from src.agent.verifier import VerifierAgent

from src.genai.memory import (
    add_memory,
    retrieve_memory
)

from src.utils.logger import setup_logger

from src.agent.risk_evaluator import (
    RiskEvaluator
)

from src.services.approval_service import (
    create_approval_request
)

from src.services.audit_service import (
    create_agent_run,
    update_agent_run
)

from src.services.agent_run_service import (
    finalize_agent_run_summary
)

from src.genai.llm_router import (
    get_last_llm_meta
)


CONFIDENCE_THRESHOLD = 0.75
MAX_RETRIES = 2


def _execution_timeout() -> int:
    """Wall-clock bound (seconds) for a single plan-execution phase."""
    try:
        value = int(os.getenv("EXECUTION_TIMEOUT_SECONDS", "300"))
        return value if value > 0 else 300
    except (TypeError, ValueError):
        return 300

logger = setup_logger()


class AgentController:

    def __init__(
        self,
        db,
        session_id="default",
        user_id=None
    ):

        self.db = db

        self.session_id = session_id

        # Owning user id (Milestone 6). Passed through to the AgentRun record
        # for user isolation. This is identity only — no authorization logic
        # lives in the agent core; that stays at the API/security layer.
        self.user_id = user_id

        self.planner = PlannerAgent()

        self.executor = ToolExecutor(
            db=db
        )

        self.verifier = VerifierAgent()

        self.risk_evaluator = RiskEvaluator()

    async def run(
        self,
        user_query: str
    ) -> dict:

        logger.info(
            f"Agent started | query='{user_query}'"
        )

  

        attempt = 0

        last_result = None
        last_verification = None

        memory_context = retrieve_memory(

            query=user_query,

            session_id=self.session_id,

            top_k=5
        )

        logger.info(
            f"Retrieved {len(memory_context)} memory items"
        )

        while attempt <= MAX_RETRIES:
            # ==========================================
            # STEP 1: CREATE PLAN
            # ==========================================

            try:

                if attempt == 0:

                    plan = self.planner.create_plan(

                        user_query=user_query,

                        memory_context=memory_context
                    )

                else:

                    feedback = []

                    if last_verification:

                        feedback = last_verification.get(
                            "issues",
                            []
                        )

                    plan = self.planner.create_plan(

                        user_query=user_query,

                        previous_feedback=feedback,

                        memory_context=memory_context
                    )

            except Exception as e:

                logger.error(
                    f"Planning failed: {str(e)}"
                )

                return {

                    "status": "planning_failed",

                    "error": str(e)
                }

            logger.info(
                f"Plan created | steps={len(plan.get('steps', []))}"
            )

            run = create_agent_run(

            db=self.db,

            session_id=self.session_id,

            user_query=user_query,

            plan=plan,

            execution_result={},

            verification_result={},

            status="running",

            user_id=self.user_id
        )
            self.executor.set_agent_run_id(
    run.id
)

            # ==========================================
            # STEP 2: RISK ANALYSIS
            # ==========================================

            risk = self.risk_evaluator.evaluate(
                plan
            )

            if risk.get(
                "requires_approval",
                False
            ):

                approval = create_approval_request(

                    db=self.db,

                    task=plan,

                    risk_level=risk.get(
                        "risk_level",
                        "medium"
                    ),

                    reason=risk.get(
                        "reason",
                        ""
                    ),

                    user_query=user_query,

                    session_id=self.session_id
                )

                finalize_agent_run_summary(

                    db=self.db,

                    agent_run_id=run.id,

                    status="approval_required",

                    execution_result={},

                    verification_result={
                        "risk": risk
                    },

                    plan=plan,

                    llm_meta=get_last_llm_meta()
                )

                logger.warning(
                    "Execution paused for approval"
                )

                return {

                    "status": "approval_required",

                    "approval_id": approval.id,

                    "risk": risk,

                    "plan": plan
                }

            # ==========================================
            # STEP 3: EXECUTE PLAN
            # ==========================================

            try:

                # Bound the whole execution phase so a stuck plan cannot run
                # forever (per-tool timeouts also apply inside the executor).
                execution_result = await asyncio.wait_for(
                    self.executor.execute_plan(plan),
                    timeout=_execution_timeout(),
                )

            except Exception as e:

                logger.error(
                    f"Execution failed: {str(e)}"
                )

                # Persist the failed state instead of leaving the run orphaned
                # in "running".
                try:
                    finalize_agent_run_summary(
                        db=self.db,
                        agent_run_id=run.id,
                        status="failed",
                        execution_result={},
                        verification_result={"issues": [str(e)]},
                        plan=plan,
                        llm_meta=get_last_llm_meta(),
                    )
                except Exception:
                    logger.warning("Failed to finalize errored run")

                return {

                    "status": "execution_failed",

                    "error": str(e)
                }

            logger.info(
                "Execution completed"
            )

            # ==========================================
            # STEP 4: VERIFY RESULT
            # ==========================================

            try:

                verification = self.verifier.verify(

                    user_query,

                    execution_result
                )

            except Exception as e:

                logger.error(
                    f"Verification failed: {str(e)}"
                )

                verification = {

                    "approved": False,

                    "confidence": 0.0,

                    "issues": [
                        str(e)
                    ]
                }

            confidence = verification.get(
                "confidence",
                0
            )

            logger.info(

                f"Verification completed | "

                f"approved={verification.get('approved')} | "

                f"confidence={confidence}"
            )

            last_result = execution_result
            last_verification = verification

            # ==========================================
            # STATUS CONSISTENCY GUARD
            # ==========================================
            # A run must not be reported as a successful/approved execution when
            # one or more steps actually failed or were skipped. Without this,
            # an over-eager (or degraded) verifier verdict could mark a run
            # "success" while the audit trail shows failed steps — an impossible
            # state. A failed step is one whose result carries an "error" key.
            step_results = (execution_result or {}).get("results", {}) or {}
            execution_had_failure = any(
                isinstance(v, dict) and "error" in v
                for v in step_results.values()
            )
            if execution_had_failure:
                logger.warning(
                    "Execution had failed/skipped steps; not eligible for success"
                )

            # ==========================================
            # STEP 5: SUCCESS
            # ==========================================

            if (

                verification.get(
                    "approved",
                    False
                )

                and

                confidence >= CONFIDENCE_THRESHOLD

                and

                not execution_had_failure
            ):

                logger.info(
                    "Execution approved"
                )

                # ==========================
                # MEMORY STORAGE
                # ==========================

                if confidence >= 0.60:

                    try:

                        memory_text = f"""
            USER QUERY:
            {user_query}

            GOAL:
            {execution_result.get('goal')}

            RESULTS:
            {str(execution_result.get('results'))[:3000]}

            CONFIDENCE:
            {verification.get('confidence')}

            ISSUES:
            {verification.get('issues')}
            """

                        add_memory(

                            content=memory_text,

                            session_id=self.session_id
                        )

                        logger.info(
                            "Memory stored successfully"
                        )

                    except Exception as e:

                        logger.warning(
                            f"Memory storage failed: {str(e)}"
                        )

                # ==========================
                # AUDIT TRAIL
                # ==========================

                finalize_agent_run_summary(

                    db=self.db,

                    agent_run_id=run.id,

                    status="success",

                    execution_result=execution_result,

                    verification_result=verification,

                    plan=plan,

                    llm_meta=get_last_llm_meta()
                )

                return {

                    "status": "success",

                    "run_id": run.id,

                    "attempts": attempt + 1,

                    "execution": execution_result,

                    "verification": verification
                }
            # ==========================================
            # STEP 6: REPLAN
            # ==========================================

            logger.warning(

                "Low confidence detected, generating adaptive replan"
            )

            # Finalize this superseded attempt so it is not left orphaned in
            # "running" state; the next attempt creates its own AgentRun row.
            try:
                finalize_agent_run_summary(
                    db=self.db,
                    agent_run_id=run.id,
                    status="failed",
                    execution_result=execution_result,
                    verification_result=verification,
                    plan=plan,
                    llm_meta=get_last_llm_meta(),
                )
            except Exception as e:
                logger.warning(f"Failed to finalize superseded run: {e}")

            attempt += 1

        # ==========================================
        # STEP 7: FAILURE
        # ==========================================

        logger.error(
            "Agent failed after max retries"
        )

        try:

            add_memory(

                content=f"""
        FAILED EXECUTION

        QUERY:
        {user_query}

        VERIFICATION:
        {last_verification}
        """,

                session_id=self.session_id
            )

        except Exception:

            pass

        finalize_agent_run_summary(

            db=self.db,

            agent_run_id=run.id,

            status="failed",

            execution_result=last_result,

            verification_result=last_verification,

            plan=plan,

            llm_meta=get_last_llm_meta()
        )

        return {

            "status": "failed",

            "run_id": run.id,

            "attempts": attempt,

            "execution": last_result,

            "verification": last_verification,

            "message": (
                "Low confidence after retries. "
                "Manual review recommended."
            )
        }
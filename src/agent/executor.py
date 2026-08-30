import asyncio
import os

from src.utils.logger import (
    setup_logger
)

# Register all tools on startup
from src.tools.register_tools import *

from src.tools.tool_registry import (
    ToolRegistry
)
import time

from src.services.step_audit_service import (
    create_step_log
)




logger = setup_logger()

MAX_TOOL_RETRIES = 3

RETRY_DELAY_SECONDS = 2


def _int_env(name: str, default: int) -> int:
    """Read a positive int from env, falling back to default on bad input."""
    try:
        value = int(os.getenv(name, str(default)))
        return value if value > 0 else default
    except (TypeError, ValueError):
        return default


# --- Runaway-execution safeguards (env-tunable, additive) -------------------
# Bound how long a single (async) tool call may run before being cancelled.
TOOL_TIMEOUT_SECONDS = _int_env("TOOL_TIMEOUT_SECONDS", 60)
# Cap the total number of steps a single plan may contain.
MAX_PLAN_STEPS = _int_env("MAX_PLAN_STEPS", 50)
# Cap how many steps run concurrently in one DAG wave.
MAX_PARALLEL_STEPS = _int_env("MAX_PARALLEL_STEPS", 8)


class ToolExecutor:

    def __init__(
    self,
    db=None
):

        

        self.db = db

        self.agent_run_id = None

        logger.info(
            f"Loaded {len(ToolRegistry.get_tool_names())} tools"
        )

    def set_agent_run_id(
    self,
    agent_run_id
):

        self.agent_run_id = agent_run_id

    # ==========================================
    # EXECUTE SINGLE STEP
    # ==========================================

    async def execute_step(
    self,
    step: dict,
    completed_results: dict
):

        tool_name = step["tool"]

        logger.info(
            f"Executing tool: {tool_name}"
        )

        # ==========================================
        # TOOL LOOKUP
        # ==========================================

        tool = ToolRegistry.get_tool(
            tool_name
        )

        if not tool:

            logger.error(
                f"Unauthorized tool attempted: {tool_name}"
            )

            return {

                "step_id": step["step_id"],

                "tool": tool_name,

                "error": f"Unauthorized tool: {tool_name}"
            }

        tool_function = tool["function"]

        # ==========================================
        # NORMALIZE INPUT
        # ==========================================

        input_payload = step.get(
            "input",
            {}
        )

        if not isinstance(
            input_payload,
            dict
        ):

            input_payload = {

                "query": str(
                    input_payload
                )
            }

        input_payload["context"] = (
            completed_results
        )

        input_payload["db"] = self.db

        # ==========================================
        # RETRY ENGINE
        # ==========================================

        start_time = time.time()

        last_error = None

        for attempt in range(
            MAX_TOOL_RETRIES
        ):

            try:

                logger.info(

                    f"Tool execution started | "

                    f"tool={tool_name} | "

                    f"attempt={attempt + 1}"
                )

                result = tool_function(
                    input_payload
                )

                if asyncio.iscoroutine(
                    result
                ):

                    # Bound async tool calls (e.g. LLM/HTTP) so a hung provider
                    # cannot stall the whole run indefinitely. Sync tools return
                    # directly and are additionally bounded by the run-level
                    # deadline enforced in the controller.
                    result = await asyncio.wait_for(
                        result,
                        timeout=TOOL_TIMEOUT_SECONDS,
                    )

                duration = int(
                    (
                        time.time()
                        - start_time
                    )
                    * 1000
                )

                # ==========================================
                # STEP AUDIT SUCCESS
                # ==========================================

                if (
                    self.db
                    and self.agent_run_id
                ):

                    logger.debug(
                        f"step audit | agent_run_id={self.agent_run_id}"
                    )

                    try:

                        create_step_log(

                            db=self.db,

                            agent_run_id=self.agent_run_id,

                            step_id=step["step_id"],

                            tool_name=tool_name,

                            input_payload=input_payload,

                            output_payload=result,

                            status="success",

                            execution_time_ms=duration,

                            retry_count=attempt
                        )

                    except Exception as e:

                        logger.error(
                            f"STEP AUDIT FAILED: {str(e)}"
                        )

                logger.info(

                    f"Tool completed | "

                    f"tool={tool_name} | "

                    f"attempt={attempt + 1}"
                )

                return {

                    "step_id": step["step_id"],

                    "tool": tool_name,

                    "output": result,

                    "retry_count": attempt
                }

            except Exception as e:

                # Some exceptions (e.g. asyncio.TimeoutError) stringify to "";
                # keep a meaningful, non-empty error message.
                last_error = str(e) or type(e).__name__

                logger.warning(

                    f"Tool failed | "

                    f"tool={tool_name} | "

                    f"attempt={attempt + 1} | "

                    f"error={last_error}"
                )

                if attempt < (
                    MAX_TOOL_RETRIES - 1
                ):

                    wait_time = (
                        RETRY_DELAY_SECONDS
                        * (attempt + 1)
                    )

                    logger.info(

                        f"Retrying tool | "

                        f"tool={tool_name} | "

                        f"wait={wait_time}s"
                    )

                    await asyncio.sleep(
                        wait_time
                    )

                else:

                    logger.error(

                        f"Tool permanently failed | "

                        f"tool={tool_name}"
                    )

        # ==========================================
        # STEP AUDIT FAILURE
        # ==========================================

        duration = int(
            (
                time.time()
                - start_time
            )
            * 1000
        )

        if (
            self.db
            and self.agent_run_id
        ):

            logger.debug(
                f"step audit | agent_run_id={self.agent_run_id}"
            )

            try:

                create_step_log(

                    db=self.db,

                    agent_run_id=self.agent_run_id,

                    step_id=step["step_id"],

                    tool_name=tool_name,

                    input_payload=input_payload,

                    output_payload={},

                    status="failed",

                    error=last_error,

                    execution_time_ms=duration,

                    retry_count=attempt
                )

            except Exception as e:

                logger.error(
                    f"STEP AUDIT FAILED: {str(e)}"
                )

        return {

            "step_id": step["step_id"],

            "tool": tool_name,

            "error": last_error,

            # Number of retries actually performed (== the value recorded in the
            # step_executions audit row above, and consistent with the success
            # path which returns ``attempt``). Previously this returned
            # MAX_TOOL_RETRIES (total attempts), which over-reported retries by
            # one and disagreed with the audit row that summarises it.
            "retry_count": attempt
        }

    # ==========================================
    # DAG EXECUTION ENGINE
    # ==========================================

    async def execute_plan(
        self,
        plan: dict
    ):

        steps = plan.get(
            "steps",
            []
        )

        # ==========================================
        # RUNAWAY-PLAN GUARD
        # ==========================================
        # Reject oversized plans (e.g. a malformed/LLM-authored plan with an
        # enormous step count) before we start executing anything.
        if len(steps) > MAX_PLAN_STEPS:

            raise ValueError(
                f"Plan exceeds maximum of {MAX_PLAN_STEPS} steps "
                f"(got {len(steps)})"
            )

        completed_results = {}

        # Track steps that ultimately failed so their dependents are SKIPPED
        # rather than executed on error data (which would produce plausible but
        # garbage downstream conclusions).
        failed_ids = set()

        # Bound how many steps run at once within a wave.
        semaphore = asyncio.Semaphore(MAX_PARALLEL_STEPS)

        async def _run_guarded(step, ctx):
            async with semaphore:
                return await self.execute_step(step, ctx)

        pending_steps = steps.copy()

        while pending_steps:

            # ==========================================
            # FIND READY STEPS
            # ==========================================

            ready_steps = [

                step for step in pending_steps

                if all(

                    dep in completed_results

                    for dep in step.get(
                        "depends_on",
                        []
                    )
                )
            ]

            # ==========================================
            # CYCLE DETECTION
            # ==========================================

            if not ready_steps:

                raise ValueError(
                    "Circular dependency detected in execution graph"
                )

            # ==========================================
            # SKIP STEPS WHOSE DEPENDENCIES FAILED
            # ==========================================
            # A step is only safe to execute if none of its dependencies
            # errored/were skipped. Otherwise record a "skipped" result so its
            # own dependents also skip — no deadlock, no execution on bad data.
            runnable_steps = []

            for step in ready_steps:

                broken_dep = next(
                    (
                        dep for dep in step.get("depends_on", [])
                        if dep in failed_ids
                    ),
                    None,
                )

                if broken_dep is not None:

                    logger.warning(
                        f"Skipping step {step['step_id']} | "
                        f"upstream dependency failed: {broken_dep}"
                    )

                    completed_results[step["step_id"]] = {
                        "step_id": step["step_id"],
                        "tool": step.get("tool"),
                        "skipped": True,
                        "error": f"skipped: upstream dependency {broken_dep} failed",
                    }
                    failed_ids.add(step["step_id"])

                else:

                    runnable_steps.append(step)

            logger.info(
                f"Executing {len(runnable_steps)} parallel step(s)"
            )

            # ==========================================
            # EXECUTE READY STEPS (bounded concurrency)
            # ==========================================

            tasks = [

                _run_guarded(
                    step,
                    completed_results
                )

                for step in runnable_steps
            ]

            results = await asyncio.gather(
                *tasks
            ) if tasks else []

            # ==========================================
            # STORE RESULTS
            # ==========================================

            for result in results:

                completed_results[
                    result["step_id"]
                ] = result

                # A step is "failed" iff it returned an error payload. Use key
                # presence (not truthiness) so an empty error string still
                # counts as a failure and correctly blocks dependents.
                if "error" in result:

                    failed_ids.add(result["step_id"])

            # ==========================================
            # REMOVE COMPLETED
            # ==========================================

            pending_steps = [

                step for step in pending_steps

                if step not in ready_steps
            ]

        logger.info(
            "Execution graph completed successfully"
        )

        return {

            "goal": plan.get(
                "goal"
            ),

            "results": completed_results
        }
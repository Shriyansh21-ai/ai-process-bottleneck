import asyncio

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

                    result = await result

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

                    logger.info(
                        f"STEP AUDIT DEBUG | agent_run_id={self.agent_run_id}"
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

                            execution_time_ms=duration
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

                last_error = str(e)

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

            logger.info(
                f"STEP AUDIT DEBUG | agent_run_id={self.agent_run_id}"
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

                    execution_time_ms=duration
                )

            except Exception as e:

                logger.error(
                    f"STEP AUDIT FAILED: {str(e)}"
                )

        return {

            "step_id": step["step_id"],

            "tool": tool_name,

            "error": last_error,

            "retry_count": MAX_TOOL_RETRIES
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

        completed_results = {}

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

            logger.info(
                f"Executing {len(ready_steps)} parallel step(s)"
            )

            # ==========================================
            # EXECUTE READY STEPS
            # ==========================================

            tasks = [

                self.execute_step(
                    step,
                    completed_results
                )

                for step in ready_steps
            ]

            results = await asyncio.gather(
                *tasks
            )

            # ==========================================
            # STORE RESULTS
            # ==========================================

            for result in results:

                completed_results[
                    result["step_id"]
                ] = result

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
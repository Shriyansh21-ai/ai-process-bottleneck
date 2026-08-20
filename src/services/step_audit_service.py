import json
import logging

from src.db.models.step_execution import (
    StepExecution
)

logger = logging.getLogger("step_audit")


def create_step_log(
    db,
    agent_run_id,
    step_id,
    tool_name,
    input_payload,
    output_payload,
    status,
    error=None,
    execution_time_ms=None,
    retry_count=0
):

    try:

        safe_input = dict(input_payload)

        safe_input.pop("db", None)

        row = StepExecution(

            agent_run_id=agent_run_id,

            step_id=step_id,

            tool_name=tool_name,

            input_payload=json.dumps(
                safe_input,
                default=str
            ),

            output_payload=json.dumps(
                output_payload,
                default=str
            ),

            status=status,

            error=error,

            execution_time_ms=execution_time_ms,

            retry_count=retry_count
        )

        db.add(row)

        db.commit()

        db.refresh(row)

        logger.debug("step log saved id=%s", row.id)

        return row

    except Exception as e:

        logger.error("step log error: %s", str(e))

        raise
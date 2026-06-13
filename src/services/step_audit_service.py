import json

from src.db.models.step_execution import (
    StepExecution
)


def create_step_log(
    db,
    agent_run_id,
    step_id,
    tool_name,
    input_payload,
    output_payload,
    status,
    error=None,
    execution_time_ms=None
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

            execution_time_ms=execution_time_ms
        )

        db.add(row)

        db.commit()

        db.refresh(row)

        print(
            f"STEP LOG SAVED -> {row.id}"
        )

        return row

    except Exception as e:

        print(
            f"STEP LOG ERROR -> {str(e)}"
        )

        raise
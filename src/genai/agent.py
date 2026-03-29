from genai.state import AgentState
from genai.agents.planner import create_plan
from genai.agents.executor import execute_step
from genai.memory import store_memory
from genai.logger import log_audit_event

def run_agent(db, task: str):
    plan = create_plan(task)
    state = AgentState(
        task=task,
        plan=plan,
        context="",
        observations=[]
    )

    for step in plan:
        output = execute_step(db, step, task)
        state.observations.append(output)

    state.result = "\n".join(state.observations)

    store_memory(db, task, state.result)

    log_audit_event(
        db,
        actor_id="agent",
        actor_type="ai",
        role="agent",
        action="execute_task",
        resource=task
    )

    return state.result

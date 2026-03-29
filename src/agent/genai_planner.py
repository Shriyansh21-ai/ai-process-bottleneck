from src.genai.engine import GenAIEngine

def generate_plan(task, actions):
    engine = GenAIEngine()

    context = {
        "task": task,
        "suggested_actions": actions
    }

    return engine.run(context, role="operations_manager")

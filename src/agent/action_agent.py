def decide_action(task):
    actions = []

    if task["risk_level"] == "HIGH":
        actions.append("Escalate task priority")

    if task["rework_flag"] == 1:
        actions.append("Review task requirements")

    if task["duration_minutes"] > 120:
        actions.append("Assign additional resources")

    return actions

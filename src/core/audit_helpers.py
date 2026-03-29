def resolve_actor(auth_context: dict):
    """
    auth_context comes from either:
    - JWT (get_current_user)
    - API key (verify_api_key)
    """
    if auth_context.get("auth_type") == "api_key":
        return {
            "actor_id": auth_context["owner"],
            "actor_type": "api_key",
            "role": auth_context.get("role")
        }

    return {
        "actor_id": auth_context.get("user_id"),
        "actor_type": "user",
        "role": auth_context.get("role")
    }

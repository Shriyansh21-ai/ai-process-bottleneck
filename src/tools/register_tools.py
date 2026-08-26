from src.tools.tool_registry import (
    ToolRegistry
)

from src.tools.sql_tool import (
    run_sql_query
)

from src.tools.ml_tool import (
    run_ml_analysis
)

from src.tools.rag_tool import (
    rag_search
)

from src.tools.web_search_tool import (
    web_search
)

from src.tools.memory_tool import (
    load_memory
)


ToolRegistry.register(

    name="sql_query",

    function=run_sql_query,

    description=(
        "Query structured process data from PostgreSQL. "
        "Required input: 'table' — one of: tasks, cases, processes. "
        "Optional input: 'filter' — a SQL WHERE clause fragment."
    ),

    # 'table' is REQUIRED: run_sql_query raises ValueError without a valid table.
    required_inputs=["table"],
)

ToolRegistry.register(

    name="ml_analysis",

    function=run_ml_analysis,

    description=(
        "Detect duration bottlenecks via statistics. "
        "Input: 'durations' — a list of numeric durations. "
        "Without it the tool returns no_data (safe no-op)."
    ),
)

ToolRegistry.register(

    name="rag_retrieval",

    function=rag_search,

    description=(
        "Retrieve semantically relevant context from the vector store. "
        "Required input: 'query' — the natural-language search text. "
        "Optional input: 'top_k' — max results (default 5)."
    ),

    # 'query' is REQUIRED: rag_search reads input['query'] directly (KeyError
    # without it). The 'db' it also needs is injected by the executor, not the
    # planner, so it is NOT declared here.
    required_inputs=["query"],
)

ToolRegistry.register(

    name="web_search",

    function=web_search,

    description=(
        "Search the public internet for up-to-date information. "
        "Input: 'query' — the search text. Requires TAVILY_API_KEY; "
        "degrades to an unavailable result when the key is absent."
    ),
)

ToolRegistry.register(

    name="memory_tool",

    function=load_memory,

    description=(
        "Retrieve relevant long-term memories for the session. "
        "Optional inputs: 'query', 'session_id', 'limit' (all defaulted)."
    ),
)
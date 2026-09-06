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

from src.tools.inspection_tool import (
    synthesize_inspection_findings
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

ToolRegistry.register(

    name="inspection_findings",

    function=synthesize_inspection_findings,

    description=(
        "Synthesize structured, evidence-backed inspection findings from the "
        "page-tagged chunks retrieved by a prior rag_retrieval step. "
        "Required input: 'query' — the analysis instruction. Reads retrieved "
        "evidence from prior-step context; returns findings with page provenance."
    ),

    # 'query' is REQUIRED so the planner always supplies an instruction; the
    # evidence itself is harvested from injected context, not the planner.
    required_inputs=["query"],
)
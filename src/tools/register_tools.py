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

    description="Query PostgreSQL data"
)

ToolRegistry.register(

    name="ml_analysis",

    function=run_ml_analysis,

    description="Run ML analysis"
)

ToolRegistry.register(

    name="rag_retrieval",

    function=rag_search,

    description="Retrieve semantic memory"
)

ToolRegistry.register(

    name="web_search",

    function=web_search,

    description="Search internet"
)

ToolRegistry.register(

    name="memory_tool",

    function=load_memory,

    description="Retrieve relevant long-term memories"
)
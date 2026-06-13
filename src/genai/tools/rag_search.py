from src.rag.retriever import retrieve_context
from src.genai.tools import Tool

class RAGSearchTool(Tool):
    name = "rag_search"
    description = "Search vector database for relevant context"

    def __init__(self, db):
        self.db = db

    def run(self, query: str):
        return retrieve_context(self.db, query)

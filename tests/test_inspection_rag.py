"""
MRPL Phase 3 — mock inspection plan + RAG retrieval provenance/scoping tests.

No Qdrant/embeddings/network: the vector client and embedder are faked.
"""

import json
import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://t:t@localhost:5432/t")

import src.tools.register_tools  # noqa: F401 ensure inspection_findings registered
from src.agent.plan_validator import PlanValidator
from src.llm.mock_provider import build_mock_response
import src.rag.retriever as retriever


_PLANNER_PROMPT_TMPL = (
    "You are an autonomous AI Planner.\n"
    "==========================================\n"
    "USER REQUEST\n"
    "==========================================\n\n"
    "{query}\n\n"
    "==========================================\n"
    "PREVIOUS FEEDBACK\n"
)


# ----------------------------------------------------------------------
# mock inspection plan
# ----------------------------------------------------------------------

def test_mock_inspection_plan_shape_and_validity():
    query = "MRPL_INSPECTION_ANALYSIS\ndocument_id=55\nFind safety issues"
    out = build_mock_response(_PLANNER_PROMPT_TMPL.format(query=query))
    plan = json.loads(out)

    tools = [s["tool"] for s in plan["steps"]]
    assert tools == ["rag_retrieval", "inspection_findings"]
    # Retrieval is scoped to the uploaded document.
    assert plan["steps"][0]["input"]["document_id"] == 55
    # Passes the real validator (known tools, required inputs, no cycle).
    assert PlanValidator().validate(plan) is True
    # Never trips the planner offline sentinel.
    assert '"confidence"' not in out


def test_generic_query_still_uses_bottleneck_plan():
    out = build_mock_response(
        _PLANNER_PROMPT_TMPL.format(query="Where is the bottleneck?")
    )
    tools = [s["tool"] for s in json.loads(out)["steps"]]
    assert tools == ["rag_retrieval", "ml_analysis"]


# ----------------------------------------------------------------------
# retrieve_context: provenance + document scoping
# ----------------------------------------------------------------------

class _Point:
    def __init__(self, score, payload):
        self.score = score
        self.payload = payload


class _Result:
    def __init__(self, points):
        self.points = points


class _FakeQdrant:
    def __init__(self, points):
        self._points = points
        self.last_kwargs = None

    def query_points(self, **kwargs):
        self.last_kwargs = kwargs
        return _Result(self._points)


def test_retrieve_context_preserves_page_provenance(monkeypatch):
    points = [
        _Point(0.9, {"content": "corrosion", "page_number": 4,
                     "extraction_method": "ocr", "document_id": 42, "title": "r"}),
    ]
    fake = _FakeQdrant(points)
    monkeypatch.setattr(retriever, "client", fake)
    monkeypatch.setattr(retriever, "embed_text", lambda q: [0.0] * 384)

    ctx = retriever.retrieve_context(db=None, query="corrosion", document_id=42)
    assert len(ctx) == 1
    assert ctx[0]["page_number"] == 4
    assert ctx[0]["extraction_method"] == "ocr"
    assert ctx[0]["document_id"] == 42
    # A document-scoped filter was passed to Qdrant.
    assert fake.last_kwargs["query_filter"] is not None


def test_retrieve_context_unscoped_has_no_filter(monkeypatch):
    fake = _FakeQdrant([])
    monkeypatch.setattr(retriever, "client", fake)
    monkeypatch.setattr(retriever, "embed_text", lambda q: [0.0] * 384)

    retriever.retrieve_context(db=None, query="anything")
    assert fake.last_kwargs["query_filter"] is None

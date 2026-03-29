from fastapi import APIRouter, BackgroundTasks
from src.genai.engine import GenAIEngine

router = APIRouter()
engine = GenAIEngine()

def run_genai_task(data: dict):
    engine.run(data)

@router.post("/")
def analyze_bottleneck(data: dict, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_genai_task, data)
    return {"status": "processing", "message": "Analysis started"}

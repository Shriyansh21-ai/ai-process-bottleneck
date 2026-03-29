from fastapi import FastAPI
from src.api.routes import predict, explain, ingest, agent, analysis

app = FastAPI(title="AI Process Bottleneck API", version="1.0")

# Include routers
app.include_router(predict.router, prefix="/predict", tags=["Predict"])
app.include_router(explain.router, prefix="/explain", tags=["Explain"])
app.include_router(ingest.router, prefix="/ingest", tags=["Ingest"])
app.include_router(agent.router, prefix="/agent", tags=["Agent"])
app.include_router(analysis.router, prefix="/analysis", tags=["Analysis"])

# Optional health check
@app.get("/")
async def root():
    return {"message": "AI Process Bottleneck API is running"}

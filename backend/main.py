from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[FactKnowledgeLayer] Enterprise Fact Knowledge Layer online.")
    yield

app = FastAPI(
    title="Fact Knowledge Layer API",
    description="Evidence-first, document-agnostic fact knowledge extraction and cross-document reasoning layer.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for React frontend (Vite dev server default: port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "Fact Knowledge Layer",
        "documentation": "/docs",
        "endpoints": [
            "/api/documents",
            "/api/facts",
            "/api/relationships",
            "/api/demo/cases"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

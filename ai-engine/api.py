"""
REST API — AIOps AI Backend
FastAPI server menyediakan endpoint untuk frontend Next.js
agar bisa berinteraksi dengan AI Agent.

Usage:
    uvicorn api:app --host 0.0.0.0 --port 8001 --reload
"""

import os
import sys
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from agent import AIOpsAgent

# ── Init ──
app = FastAPI(
    title="AIOps AI Backend",
    description="REST API untuk AIOps Infrastructure Reliability Agent",
    version="1.0.0",
)

# CORS (untuk Next.js frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AI Agent instance (per-process singleton)
agent = AIOpsAgent()


# ── Models ──
class ChatRequest(BaseModel):
    message: str
    reset_history: bool = False


class ChatResponse(BaseModel):
    response: str
    timestamp: str
    intent_detected: dict = {}


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: str


# ── Endpoints ──

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="aiops-ai-backend",
        timestamp=datetime.now().isoformat(),
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Endpoint chat utama.
    Menerima pesan user dan mengembalikan respons dari AI Agent.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    if request.reset_history:
        agent.reset_conversation()

    try:
        # Detect intent (untuk frontend info)
        intent = agent._determine_intent(request.message)

        # Process query melalui agent
        response = agent.process_query(request.message)

        return ChatResponse(
            response=response,
            timestamp=datetime.now().isoformat(),
            intent_detected=intent,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI processing error: {str(e)}"
        )


@app.post("/api/chat/reset")
async def reset_chat():
    """Reset conversation history."""
    agent.reset_conversation()
    return {"status": "ok", "message": "Conversation history cleared"}


@app.get("/api/status")
async def system_status():
    """Ringkasan status sistem (service summary via MCP tool)."""
    try:
        from mcp_server.server import get_service_summary
        summary = get_service_summary()
        return {"status": "ok", "data": summary}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── Run ──
if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  AIOps AI Backend")
    print("  http://localhost:8001")
    print("  Docs: http://localhost:8001/docs")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)

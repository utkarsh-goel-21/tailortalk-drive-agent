"""
main.py — FastAPI application entry point.

Endpoints:
  GET  /health        — liveness check
  POST /chat          — streaming chat via Server-Sent Events
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage

from agent.graph import agent_graph
from config import settings
from models.schemas import ChatRequest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: warm up the Drive client so first request isn't slow."""
    logger.info("Starting TailorTalk Drive Agent...")
    from drive.client import DriveClient
    DriveClient.get_instance()
    logger.info("Drive client ready.")
    yield
    logger.info("Shutting down.")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="TailorTalk Drive Agent API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "model": settings.groq_model}


@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Streaming chat endpoint using Server-Sent Events.
    Streams tokens as they arrive from the LLM.
    """

    # Build LangGraph message history
    messages = []
    for msg in request.history:
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            messages.append(AIMessage(content=msg.content))
    messages.append(HumanMessage(content=request.message))

    async def event_stream():
        try:
            async for event in agent_graph.astream_events(
                {"messages": messages},
                version="v2",
            ):
                kind = event.get("event")
                name = event.get("name", "")

                # Stream LLM tokens
                if kind == "on_chat_model_stream":
                    chunk = event["data"].get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        yield f"data: {chunk.content}\n\n"

                # Notify when tool is called
                elif kind == "on_tool_start" and name == "drive_search_tool":
                    yield f"data: 🔍 Searching Google Drive...\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error("Stream error: %s", e)
            yield f"data: ❌ Error: {str(e)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
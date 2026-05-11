"""
models/schemas.py — Pydantic request/response schemas for the API.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in the conversation history."""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message text")


class ChatRequest(BaseModel):
    """Request body for the /chat endpoint."""
    message: str = Field(..., description="The user's latest message")
    history: list[ChatMessage] = Field(
        default_factory=list,
        description="Previous messages in the conversation",
    )


class ChatResponse(BaseModel):
    """Response body for non-streaming /chat calls."""
    reply: str
    tool_called: bool = False
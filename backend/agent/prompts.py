"""
agent/graph.py — LangGraph ReAct agent definition.

Builds a stateful graph with:
  - A 'agent' node: the LLM deciding what to do
  - A 'tools' node: executes the chosen tool
  - A conditional edge: loop until no tool call is needed
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated, Literal

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from agent.prompts import SYSTEM_PROMPT
from agent.tools import drive_search_tool
from config import settings

logger = logging.getLogger(__name__)

# ── State ─────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    """The state passed between every node in the graph."""
    messages: Annotated[list[BaseMessage], add_messages]


# ── LLM + Tools ───────────────────────────────────────────────────────────────

TOOLS = [drive_search_tool]

llm = ChatGroq(
    model=settings.groq_model,
    api_key=settings.groq_api_key,
    temperature=0.1,        # Low temp for precise tool calling
    max_tokens=2048,
).bind_tools(TOOLS)


# ── Nodes ─────────────────────────────────────────────────────────────────────

def agent_node(state: AgentState) -> dict:
    """
    The LLM node. Injects today's date into the system prompt
    so relative date queries ('last week') resolve correctly.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    system = SystemMessage(
        content=SYSTEM_PROMPT + f"\n\nToday's date (UTC): {today}"
    )

    messages = [system] + state["messages"]
    response = llm.invoke(messages)

    logger.info(
        "Agent response — tool_calls: %d",
        len(response.tool_calls) if hasattr(response, "tool_calls") else 0,
    )
    return {"messages": [response]}


def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    """
    Conditional edge: if the last message has tool calls, run them.
    Otherwise we're done.
    """
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return "__end__"


# ── Graph ─────────────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    tool_node = ToolNode(TOOLS)

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue)
    graph.add_edge("tools", "agent")

    return graph.compile()


# Compiled graph — import this in main.py
agent_graph = build_graph()
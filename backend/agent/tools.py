"""
agent/tools.py — DriveSearchTool for the LangGraph agent.

The LLM calls this tool with structured JSON. It translates
natural language intent into a Drive API query and returns results.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from drive.client import DriveClient, SearchParams

logger = logging.getLogger(__name__)


class DriveSearchInput(BaseModel):
    """
    Structured input the LLM must provide when calling DriveSearchTool.
    Every field maps directly to a Drive API q clause.
    """
    name_contains: Optional[str] = Field(
        default=None,
        description="Search for files whose name partially matches this string. "
                    "E.g. 'financial' matches 'Q3 Financial Report.pdf'",
    )
    name_exact: Optional[str] = Field(
        default=None,
        description="Search for a file with this exact name. "
                    "Use when the user gives a precise filename.",
    )
    mime_type: Optional[str] = Field(
        default=None,
        description=(
            "Filter by file type using MIME type string. Common values: "
            "'application/pdf' for PDFs, "
            "'application/vnd.google-apps.document' for Google Docs, "
            "'application/vnd.google-apps.spreadsheet' for Google Sheets, "
            "'application/vnd.google-apps.presentation' for Google Slides, "
            "'image/jpeg' or 'image/png' for images."
        ),
    )
    full_text: Optional[str] = Field(
        default=None,
        description="Search for files containing this text anywhere in their content. "
                    "Use when the user asks about what's inside a file.",
    )
    modified_after: Optional[str] = Field(
        default=None,
        description="Return files modified after this date. ISO 8601 format: "
                    "'YYYY-MM-DDTHH:MM:SS'. E.g. '2024-01-01T00:00:00'",
    )
    modified_before: Optional[str] = Field(
        default=None,
        description="Return files modified before this date. ISO 8601 format: "
                    "'YYYY-MM-DDTHH:MM:SS'.",
    )
    max_results: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of results to return. Default is 10.",
    )


@tool(args_schema=DriveSearchInput)
def drive_search_tool(
    name_contains: Optional[str] = None,
    name_exact: Optional[str] = None,
    mime_type: Optional[str] = None,
    full_text: Optional[str] = None,
    modified_after: Optional[str] = None,
    modified_before: Optional[str] = None,
    max_results: int = 10,
) -> str:
    """
    Search for files in Google Drive using one or more filters.
    Always prefer specific filters over broad ones.
    Combine multiple filters for precise results.
    Returns a JSON string with matching files and their metadata.
    """
    params = SearchParams(
        name_contains=name_contains,
        name_exact=name_exact,
        mime_type=mime_type,
        full_text=full_text,
        modified_after=modified_after,
        modified_before=modified_before,
        max_results=max_results,
    )

    client = DriveClient.get_instance()
    results = client.search(params)

    if not results:
        return json.dumps({
            "found": 0,
            "message": "No files matched your search criteria.",
            "files": [],
        })

    return json.dumps({
        "found": len(results),
        "files": [f.to_dict() for f in results],
    }, indent=2)
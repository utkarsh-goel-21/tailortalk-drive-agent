"""
drive/client.py — Google Drive API v3 wrapper.

Handles service account auth and all file search operations.
The build_query() method is the core — it translates structured
search params into a Drive API q string.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings

logger = logging.getLogger(__name__)

# Drive API scopes — read-only is enough for search
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Fields to fetch for every file result
FILE_FIELDS = "id, name, mimeType, modifiedTime, size, webViewLink, parents"

# Human-readable MIME type labels
MIME_LABELS: dict[str, str] = {
    "application/vnd.google-apps.document": "Google Doc",
    "application/vnd.google-apps.spreadsheet": "Google Sheet",
    "application/vnd.google-apps.presentation": "Google Slides",
    "application/vnd.google-apps.folder": "Folder",
    "application/pdf": "PDF",
    "image/jpeg": "JPEG Image",
    "image/png": "PNG Image",
    "text/plain": "Text File",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "Word Doc",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "Excel Sheet",
}


@dataclass
class SearchParams:
    """Structured search parameters the agent passes to DriveSearchTool."""
    name_contains: Optional[str] = None
    name_exact: Optional[str] = None
    mime_type: Optional[str] = None
    full_text: Optional[str] = None
    modified_after: Optional[str] = None   # ISO 8601 e.g. "2024-01-01T00:00:00"
    modified_before: Optional[str] = None  # ISO 8601
    max_results: int = 10


@dataclass
class DriveFile:
    """A single file result returned to the agent."""
    id: str
    name: str
    mime_type: str
    mime_label: str
    modified_time: str
    web_view_link: str
    size: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.mime_label,
            "modified": self.modified_time,
            "link": self.web_view_link,
            "size_bytes": self.size,
        }


class DriveClient:
    """
    Singleton-style client for Google Drive API v3.
    Call DriveClient.get_instance() to reuse one connection.
    """

    _instance: Optional["DriveClient"] = None

    def __init__(self) -> None:
        creds = service_account.Credentials.from_service_account_file(
            settings.google_service_account_path,
            scopes=SCOPES,
        )
        self._service = build("drive", "v3", credentials=creds)
        self._folder_id = settings.google_drive_folder_id
        logger.info("DriveClient initialised with folder: %s", self._folder_id)

    @classmethod
    def get_instance(cls) -> "DriveClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Query Builder ─────────────────────────────────────────────────────────

    def _build_query(self, params: SearchParams) -> str:
        """
        Translate SearchParams into a Drive API q string.

        Drive q syntax reference:
          name = 'exact'
          name contains 'partial'
          mimeType = 'application/pdf'
          fullText contains 'keyword'
          modifiedTime > '2024-01-01T00:00:00'
          'folder_id' in parents
          trashed = false
        """
        clauses: list[str] = [
            f"'{self._folder_id}' in parents",
            "trashed = false",
        ]

        if params.name_exact:
            clauses.append(f"name = '{self._escape(params.name_exact)}'")

        if params.name_contains:
            clauses.append(f"name contains '{self._escape(params.name_contains)}'")

        if params.mime_type:
            clauses.append(f"mimeType = '{params.mime_type}'")

        if params.full_text:
            clauses.append(f"fullText contains '{self._escape(params.full_text)}'")

        if params.modified_after:
            clauses.append(f"modifiedTime > '{params.modified_after}'")

        if params.modified_before:
            clauses.append(f"modifiedTime < '{params.modified_before}'")

        return " and ".join(clauses)

    @staticmethod
    def _escape(value: str) -> str:
        """Escape single quotes in query values to prevent injection."""
        return value.replace("'", "\\'")

    # ── Search ────────────────────────────────────────────────────────────────

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
    )
    def search(self, params: SearchParams) -> list[DriveFile]:
        """
        Execute a Drive files.list() search and return DriveFile results.
        Retries up to 3 times on transient errors.
        """
        query = self._build_query(params)
        logger.info("Drive query: %s", query)

        try:
            response = (
                self._service.files()
                .list(
                    q=query,
                    pageSize=params.max_results,
                    fields=f"files({FILE_FIELDS})",
                    orderBy="modifiedTime desc",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                .execute()
            )
        except HttpError as e:
            logger.error("Drive API error: %s", e)
            raise

        files = response.get("files", [])
        logger.info("Drive returned %d results", len(files))

        return [
            DriveFile(
                id=f["id"],
                name=f["name"],
                mime_type=f["mimeType"],
                mime_label=MIME_LABELS.get(f["mimeType"], f["mimeType"]),
                modified_time=f.get("modifiedTime", ""),
                web_view_link=f.get("webViewLink", ""),
                size=f.get("size"),
            )
            for f in files
        ]
"""Internal DTOs for Odoo integration responses.

Nothing outside app/integrations/odoo/ should ever see a raw Odoo JSON-RPC response
dict — callers get these typed shapes instead (integration-principles.md §1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


@dataclass(frozen=True)
class OdooServerVersion:
    server_version: str
    server_version_info: list[Any]
    server_serie: str
    protocol_version: int


@dataclass(frozen=True)
class OdooSession:
    """Result of a successful authenticate() call. `uid` is Odoo's internal user id
    — never logged alongside the credential that produced it.
    """

    uid: int
    database: str
    username: str


@dataclass(frozen=True)
class OdooFieldDescriptor:
    """One field's metadata, as returned by `fields_get`."""

    name: str
    string: str
    field_type: str
    required: bool
    readonly: bool
    relation: str | None = None
    selection: list[tuple[str, str]] | None = None
    help: str | None = None


class AvailabilityStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    NO_ACCESS = "NO_ACCESS"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ModelAvailability:
    """Whether a given Odoo model exists and is readable by the authenticated user
    — the basis for every "model X availability" verification item in the phase
    checklist.
    """

    model: str
    status: AvailabilityStatus
    detail: str | None = None


@dataclass(frozen=True)
class AccessRights:
    model: str
    operation: str
    allowed: bool


@dataclass
class SearchReadPage:
    """One page of a search_read call, plus enough information for the caller to
    fetch the next page without re-issuing a count query.
    """

    records: list[dict[str, Any]]
    offset: int
    limit: int
    returned_count: int = field(init=False)

    def __post_init__(self) -> None:
        self.returned_count = len(self.records)

    @property
    def has_more(self) -> bool:
        return self.returned_count == self.limit and self.limit > 0

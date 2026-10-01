"""Keyset pagination generic DTOs."""

from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    next_cursor: Optional[str] = Field(default=None, description="Cursor for the next page of results")
    has_more: bool = Field(default=False, description="True if more records exist")
    total_count: Optional[int] = Field(default=None, description="Optional total count if calculated")

from typing import Generic, TypeVar, List
from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic wrapper for paginated dataset collections."""
    items: List[T]
    total_items: int
    page: int
    page_size: int
    total_pages: int

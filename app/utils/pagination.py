"""
Pagination utilities for list endpoints
"""
from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Query
from math import ceil

from app.core.config import settings

T = TypeVar('T')


class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = 1
    page_size: int = settings.DEFAULT_PAGE_SIZE
    
    def __init__(self, **data):
        super().__init__(**data)
        # Validate and clamp page_size
        if self.page_size > settings.MAX_PAGE_SIZE:
            self.page_size = settings.MAX_PAGE_SIZE
        if self.page_size < 1:
            self.page_size = settings.DEFAULT_PAGE_SIZE
        if self.page < 1:
            self.page = 1


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response model"""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

    model_config = ConfigDict(from_attributes=True)


def paginate_query(
    query: Query,
    page: int = 1,
    page_size: int = settings.DEFAULT_PAGE_SIZE
) -> tuple[List, PaginatedResponse]:
    """
    Paginate a SQLAlchemy query
    
    Args:
        query: SQLAlchemy query object
        page: Page number (1-indexed)
        page_size: Number of items per page
        
    Returns:
        Tuple of (items, pagination_info)
    """
    # Validate pagination params
    if page_size > settings.MAX_PAGE_SIZE:
        page_size = settings.MAX_PAGE_SIZE
    if page_size < 1:
        page_size = settings.DEFAULT_PAGE_SIZE
    if page < 1:
        page = 1
    
    # Get total count
    total = query.count()
    
    # Calculate pagination
    total_pages = ceil(total / page_size) if total > 0 else 0
    offset = (page - 1) * page_size
    
    # Get items
    items = query.offset(offset).limit(page_size).all()
    
    # Build pagination response
    pagination = PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )
    
    return items, pagination


def paginate_list(
    items: List[T],
    page: int = 1,
    page_size: int = settings.DEFAULT_PAGE_SIZE
) -> PaginatedResponse[T]:
    """
    Paginate a list of items
    
    Args:
        items: List of items
        page: Page number (1-indexed)
        page_size: Number of items per page
        
    Returns:
        PaginatedResponse
    """
    # Validate pagination params
    if page_size > settings.MAX_PAGE_SIZE:
        page_size = settings.MAX_PAGE_SIZE
    if page_size < 1:
        page_size = settings.DEFAULT_PAGE_SIZE
    if page < 1:
        page = 1
    
    total = len(items)
    total_pages = ceil(total / page_size) if total > 0 else 0
    offset = (page - 1) * page_size
    
    paginated_items = items[offset:offset + page_size]
    
    return PaginatedResponse(
        items=paginated_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )


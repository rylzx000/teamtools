from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any


DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class Pagination:
    page: int
    page_size: int
    limit: int
    offset: int


def parse_pagination(page: Any = None, page_size: Any = None) -> Pagination:
    parsed_page = parse_positive_int(page, DEFAULT_PAGE)
    parsed_page_size = min(parse_positive_int(page_size, DEFAULT_PAGE_SIZE), MAX_PAGE_SIZE)
    return Pagination(
        page=parsed_page,
        page_size=parsed_page_size,
        limit=parsed_page_size,
        offset=(parsed_page - 1) * parsed_page_size,
    )


def paginated_response(items: list[Any], total: int, pagination: Pagination) -> dict[str, Any]:
    pages = ceil(total / pagination.page_size) if total else 0
    return {
        "items": items,
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
        "pages": pages,
        "has_next": pages > 0 and pagination.page < pages,
        "has_prev": pages > 0 and pagination.page > 1,
    }


def parse_positive_int(value: Any, default: int) -> int:
    if value in (None, ""):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default

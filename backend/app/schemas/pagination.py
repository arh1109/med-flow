from typing import Generic, Literal, TypeVar

from fastapi import Query
from pydantic import BaseModel


T = TypeVar("T")

MAX_PAGE_SIZE = 100


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int


class PaginationParams(BaseModel):
    page: int = 1
    size: int = 25
    sort_by: str = "id"
    sort_dir: Literal["asc", "desc"] = "asc"


def get_pagination_params(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=25, ge=1, le=MAX_PAGE_SIZE),
    sort_by: str = Query(default="id", min_length=1),
    sort_dir: Literal["asc", "desc"] = Query(default="asc"),
) -> PaginationParams:
    return PaginationParams(
        page=page,
        size=size,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )

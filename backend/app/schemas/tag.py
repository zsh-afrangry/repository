from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.bill import TagType


class TagBase(BaseModel):
    name: str
    type: TagType
    parent_id: Optional[int] = None
    sort_order: int = 0


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None


class TagOut(TagBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    children: list[TagOut] = []


TagOut.model_rebuild()

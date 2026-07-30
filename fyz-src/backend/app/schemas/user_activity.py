"""用户收藏与浏览足迹接口 Schema。"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

FavoriteTargetType = Literal["job", "resume"]
HistoryType = Literal["job", "resume", "search", "graph", "match"]


class FavoriteToggleRequest(BaseModel):
    target_type: FavoriteTargetType
    target_id: int = Field(gt=0)
    title: str | None = Field(default=None, max_length=255)


class FavoriteToggleResponse(BaseModel):
    active: bool


class FavoriteBatchDeleteRequest(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=100)


class FavoriteNoteUpdate(BaseModel):
    note: str = Field(default="", max_length=1000)


class FavoriteResponse(BaseModel):
    id: int
    target_type: FavoriteTargetType
    target_id: int
    title: str
    subtitle: str = ""
    company: str = ""
    location: str = ""
    salary: str = ""
    experience: str = ""
    education: str = ""
    skills: list[str] = Field(default_factory=list)
    match: int = 0
    savedAt: datetime
    savedOrder: int
    note: str = ""
    urgent: bool = False


class HistoryCreateRequest(BaseModel):
    type: HistoryType
    targetId: int | str | None = None
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=500)
    source: str = Field(default="智联职引", max_length=120)
    url: str = Field(min_length=1, max_length=500)
    tags: list[str] = Field(default_factory=list, max_length=20)


class HistoryResponse(BaseModel):
    id: int
    type: HistoryType
    targetId: int | str | None = None
    title: str
    description: str
    source: str
    dateKey: Literal["today", "yesterday", "week", "month"]
    date: str
    time: str
    tags: list[str]
    url: str
    badge: str | None = None


class HistoryFocusStat(BaseModel):
    label: str
    percent: int
    count: int


class FrequentHistoryRecord(BaseModel):
    history_id: int
    count: int


class HistoryInsightsResponse(BaseModel):
    focusStats: list[HistoryFocusStat]
    frequentRecords: list[FrequentHistoryRecord]

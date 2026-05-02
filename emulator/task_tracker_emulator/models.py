from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


TaskType = Literal["epic", "task", "test"]
TaskStatus = Literal[
    "Todo",
    "Open",
    "InProgress",
    "InReview",
    "NeedsInfo",
    "Done",
    "Cancelled",
]
LinkType = Literal["part_of_epic", "blocks", "blocked_by"]

WORKFLOW_STATUSES: tuple[TaskStatus, ...] = (
    "Todo",
    "Open",
    "InProgress",
    "InReview",
    "NeedsInfo",
    "Done",
    "Cancelled",
)


class Workflow(BaseModel):
    statuses: list[TaskStatus] = Field(default_factory=lambda: list(WORKFLOW_STATUSES))
    transitions: Literal["any"] = "any"


class TaskLink(BaseModel):
    type: LinkType
    target: str


class Comment(BaseModel):
    id: str
    author_email: str
    body: str
    created_at: datetime


class Task(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: TaskType
    status: TaskStatus
    title: str
    author_email: str
    assignee_email: str | None = None
    description: str = ""
    links: list[TaskLink] = Field(default_factory=list)
    comments: list[Comment] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrackerState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_key: str
    tasks: list[Task] = Field(default_factory=list)


def utc_now() -> datetime:
    return datetime.now(UTC)

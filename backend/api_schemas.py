from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict


class EventRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    event_type: str
    source: Literal["simulator"]
    resource_id: str
    observed_at: AwareDatetime
    received_at: AwareDatetime
    payload: dict[str, Any]


class EventPage(BaseModel):
    items: list[EventRead]
    limit: int
    offset: int
    returned: int
    has_more: bool


class RunRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    event_id: str
    state: Literal["needs_evidence"]
    started_at: AwareDatetime
    finished_at: AwareDatetime
    payload: dict[str, Any]


class RunPage(BaseModel):
    items: list[RunRead]
    limit: int
    offset: int
    returned: int
    has_more: bool

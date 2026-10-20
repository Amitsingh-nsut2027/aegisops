"""Explicit opt-in fixtures; these records are generated, never fetched from AWS."""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from event_schema import QueuedIncident


class EvidenceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    evidence_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    event_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    resource_id: str = Field(pattern=r"^simulated/\S+$", max_length=256)
    kind: Literal["request_rate", "deployment_history", "application_logs"]
    source: Literal["scripted-fixture/traffic-surge-v1"]
    simulated: Literal[True]
    observed_at: AwareDatetime
    detail: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def verify_identity(self):
        if self.evidence_id != evidence_identity(self.model_dump(mode="json", exclude={"evidence_id"})):
            raise ValueError("Evidence ID does not match its contents")
        return self


def evidence_identity(values: dict) -> str:
    values = dict(values)
    instant = datetime.fromisoformat(values["observed_at"])
    if instant.utcoffset() is None:
        raise ValueError("Evidence timestamp must include a timezone")
    values["observed_at"] = instant.astimezone(timezone.utc).isoformat()
    return hashlib.sha256(json.dumps(values, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def traffic_surge_fixture(event: QueuedIncident) -> list[EvidenceRecord]:
    """Fabricate a repeatable context relative to this event, not historical observations."""
    records = []
    for kind, minutes, detail in [
        ("request_rate", 1, "Scripted request-rate comparison: baseline 120 requests/second; recent 620 requests/second."),
        ("deployment_history", 4, "Scripted deployment: demo-api-v2 released four minutes before the CPU alert. Temporal proximity does not establish cause."),
        ("application_logs", 1, "Scripted WARN entry: request queue length increased. This fixture is not a search of actual application logs."),
    ]:
        values = dict(event_id=event.event_id, resource_id=event.resource_id, kind=kind,
                      source="scripted-fixture/traffic-surge-v1", simulated=True,
                      observed_at=(event.observed_at - timedelta(minutes=minutes)).isoformat(), detail=detail)
        records.append(EvidenceRecord.model_validate_json(json.dumps(
            {"evidence_id": evidence_identity(values), **values})))
    return records


def validate_evidence(event: QueuedIncident, records: list[EvidenceRecord]) -> list[EvidenceRecord]:
    if len(records) > 3:
        raise ValueError("At most three supplemental evidence records are allowed")
    checked, kinds = [], set()
    for record in records:
        record = EvidenceRecord.model_validate_json(record.model_dump_json())
        if record.event_id != event.event_id or record.resource_id != event.resource_id:
            raise ValueError("Evidence does not belong to the selected event/resource")
        if not event.observed_at - timedelta(minutes=5) <= record.observed_at <= event.observed_at:
            raise ValueError("Evidence falls outside the five-minute investigation window")
        if record.kind in kinds:
            raise ValueError("Duplicate evidence kind")
        kinds.add(record.kind)
        checked.append(record)
    return checked

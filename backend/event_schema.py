import hashlib
import json
from datetime import timezone
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from incidents import IncidentEvent

Percentage = Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]
Identifier = Annotated[str, Field(min_length=1, max_length=256, pattern=r"\S")]


class QueuedIncident(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    event_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    event_type: Literal["cpu.high.v1"]
    source: Literal["simulator"]
    scenario_id: Identifier
    resource_id: str = Field(pattern=r"^simulated/\S+$", max_length=256)
    observed_at: AwareDatetime
    sample: int = Field(ge=1)
    severity: Literal["warning"]
    threshold: Percentage
    required_samples: int = Field(ge=1)
    cpu_evidence: list[Percentage] = Field(min_length=1, max_length=10000)

    @model_validator(mode="after")
    def validate_evidence(self):
        if len(self.cpu_evidence) != self.required_samples or self.sample < self.required_samples:
            raise ValueError("Evidence window does not match the detection rule")
        if any(cpu <= self.threshold for cpu in self.cpu_evidence):
            raise ValueError("Every evidence reading must exceed the threshold")
        observed_at = self.observed_at.astimezone(timezone.utc).isoformat()
        identity = [self.event_type, self.scenario_id, self.resource_id, observed_at,
                    float(self.threshold), self.required_samples, tuple(self.cpu_evidence)]
        expected = hashlib.sha256(json.dumps(identity).encode()).hexdigest()
        if self.event_id != expected:
            raise ValueError("Event ID does not match event contents")
        return self

    def to_event(self) -> IncidentEvent:
        values = self.model_dump()
        values["observed_at"] = self.observed_at.astimezone(timezone.utc).isoformat()
        values["cpu_evidence"] = tuple(self.cpu_evidence)
        return IncidentEvent(**values)

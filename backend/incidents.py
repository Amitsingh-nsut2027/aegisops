import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

from simulator import detect_cpu_alerts


@dataclass(frozen=True)
class IncidentEvent:
    event_id: str
    event_type: str
    source: str
    scenario_id: str
    resource_id: str
    observed_at: str
    sample: int
    severity: str
    threshold: float
    required_samples: int
    cpu_evidence: tuple[float, ...]


def build_incident_events(
    samples: list[float],
    scenario_id: str,
    resource_id: str,
    start_time: datetime,
    threshold: float = 90,
    required_samples: int = 3,
) -> list[IncidentEvent]:
    if not scenario_id.strip() or not resource_id.strip():
        raise ValueError("scenario_id and resource_id must not be empty")
    if start_time.utcoffset() is None:
        raise ValueError("start_time must include a timezone")

    events: list[IncidentEvent] = []
    for record in detect_cpu_alerts(samples, threshold, required_samples):
        if not record["alert"]:
            continue
        sample = record["sample"]
        evidence = tuple(float(cpu) for cpu in samples[sample-required_samples:sample])
        observed_at = (start_time + timedelta(minutes=sample-1)).astimezone(timezone.utc).isoformat()
        identity = ["cpu.high.v1", scenario_id, resource_id, observed_at,
                    float(threshold), required_samples, evidence]
        event_id = hashlib.sha256(json.dumps(identity).encode()).hexdigest()
        events.append(IncidentEvent(
            event_id=event_id, event_type="cpu.high.v1", source="simulator",
            scenario_id=scenario_id, resource_id=resource_id,
            observed_at=observed_at, sample=sample, severity="warning",
            threshold=threshold, required_samples=required_samples,
            cpu_evidence=evidence,
        ))
    return events


if __name__ == "__main__":
    events = build_incident_events(
        [91, 92, 93, 94, 95, 90, 91, 92, 93],
        scenario_id="cpu-spike-demo-v1", resource_id="simulated/ecs/api-service",
        start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    for event in events:
        print(json.dumps(asdict(event)))

import json
from dataclasses import asdict
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine

from database import database_engine, incident_events
from incidents import IncidentEvent, build_incident_events


def store_events(engine: Engine, events: list[IncidentEvent]) -> int:
    rows = [{
        "event_id": event.event_id, "event_type": event.event_type,
        "source": event.source, "resource_id": event.resource_id,
        "observed_at": datetime.fromisoformat(event.observed_at),
        "payload": asdict(event),
    } for event in events]
    if not rows:
        return 0
    statement = (
        insert(incident_events).values(rows)
        .on_conflict_do_nothing(index_elements=[incident_events.c.event_id])
        .returning(incident_events.c.event_id)
    )
    with engine.begin() as connection:
        inserted = list(connection.execute(statement).scalars())
    return len(inserted)


if __name__ == "__main__":
    events = build_incident_events(
        [91, 92, 93, 94, 95, 90, 91, 92, 93],
        scenario_id="cpu-spike-demo-v1", resource_id="simulated/ecs/api-service",
        start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    engine = database_engine()
    try:
        inserted = store_events(engine, events)
        print(json.dumps({"source": "simulator", "generated": len(events),
                          "inserted": inserted, "duplicates": len(events) - inserted}))
    finally:
        engine.dispose()

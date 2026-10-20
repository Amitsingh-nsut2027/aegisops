"""Inspect one saved event using a local fake provider; never write findings to the DB."""
import json

from database import database_engine
from event_repository import EventRepository, assert_reader_role
from event_schema import QueuedIncident
from llm_provider import investigate


def main() -> None:
    engine = database_engine(password_env="DB_PASSWORD")
    try:
        assert_reader_role(engine)
        rows = EventRepository(engine).list_events(limit=1, offset=0, source="simulator")
        if not rows:
            raise SystemExit("No saved simulation events. Publish and consume the queue demo first.")
        event = QueuedIncident.model_validate_json(json.dumps(rows[0]["payload"]))
        print(json.dumps(investigate(event), indent=2))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

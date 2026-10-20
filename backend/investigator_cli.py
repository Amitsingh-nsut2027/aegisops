"""Read a saved event, append a new investigation report, and print it after commit."""
import argparse
import json
import re

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from database import database_engine
from event_repository import EventRepository
from event_schema import QueuedIncident
from evidence import traffic_surge_fixture
from investigator import run_investigation
from run_repository import assert_investigator_role, save_run


def event_id_argument(value: str) -> str:
    if not re.fullmatch(r"[a-f0-9]{64}", value):
        raise argparse.ArgumentTypeError("event ID must contain 64 lowercase hexadecimal characters")
    return value


def load_event(repository: EventRepository, event_id: str | None) -> QueuedIncident:
    if event_id is not None:
        row = repository.get_event(event_id)
    else:
        rows = repository.list_events(limit=1, offset=0, source="simulator")
        row = rows[0] if rows else None
    if row is None:
        raise LookupError("No matching saved event; publish and consume a simulation first.")
    event = QueuedIncident.model_validate_json(json.dumps(row["payload"]))
    if row["event_id"] != event.event_id:
        raise ValueError("Saved row identity does not match its payload")
    return event


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-id", type=event_id_argument,
                        help="Investigate this event; otherwise select the latest received simulation.")
    parser.add_argument("--evidence-scenario", choices=["traffic-surge-v1"],
                        help="Explicitly generate scripted supplemental evidence; no real telemetry lookup.")
    args = parser.parse_args()
    engine = database_engine(password_env="INVESTIGATOR_PASSWORD")
    try:
        assert_investigator_role(engine)
        event = load_event(EventRepository(engine), args.event_id)
        evidence = traffic_surge_fixture(event) if args.evidence_scenario else []
        report = run_investigation(event, evidence=evidence)
        save_run(engine, report)
        print(json.dumps({"persisted": True, **report}, indent=2))
    except LookupError as error:
        raise SystemExit(str(error)) from None
    except (ValidationError, ValueError):
        raise SystemExit("Investigation rejected: invalid event or provider configuration.") from None
    except (SQLAlchemyError, RuntimeError):
        raise SystemExit("Investigation unavailable: check database readiness and investigator-role setup.") from None
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

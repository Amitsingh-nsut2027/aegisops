from sqlalchemy import select, text
from sqlalchemy.engine import Engine

from database import incident_events


def assert_reader_role(engine: Engine) -> None:
    with engine.connect() as connection:
        identity = connection.execute(text(
            "SELECT current_user AS name, rolsuper, rolcreatedb, rolcreaterole "
            "FROM pg_roles WHERE rolname = current_user"
        )).mappings().one()
        permissions = connection.execute(text(
            "SELECT has_table_privilege(current_user, 'public.incident_events', 'SELECT') AS can_read, "
            "has_table_privilege(current_user, 'public.incident_events', "
            "'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER,REFERENCES') AS can_write"
        )).mappings().one()
    if (identity["name"] != "aegis_api" or identity["rolsuper"]
            or identity["rolcreatedb"] or identity["rolcreaterole"]
            or not permissions["can_read"] or permissions["can_write"]):
        raise RuntimeError("API requires the dedicated read-only database role")
    with engine.connect() as connection:
        valid = connection.execute(text(
            "SELECT has_table_privilege(current_user, 'investigation_runs', 'SELECT') "
            "AND NOT has_table_privilege(current_user, 'investigation_runs', "
            "'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER,REFERENCES')"
        )).scalar_one()
    if not valid:
        raise RuntimeError("API requires read-only investigation history access")


class EventRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def list_events(self, limit: int, offset: int, source: str | None) -> list[dict]:
        statement = select(incident_events)
        if source is not None:
            statement = statement.where(incident_events.c.source == source)
        statement = statement.order_by(
            incident_events.c.received_at.desc(), incident_events.c.event_id.asc(),
        ).offset(offset).limit(limit + 1)
        with self.engine.connect() as connection:
            return [dict(row) for row in connection.execute(statement).mappings()]

    def get_event(self, event_id: str) -> dict | None:
        statement = select(incident_events).where(incident_events.c.event_id == event_id)
        with self.engine.connect() as connection:
            row = connection.execute(statement).mappings().first()
            return dict(row) if row is not None else None

    def ready(self) -> None:
        with self.engine.connect() as connection:
            connection.execute(select(incident_events.c.event_id).limit(1))

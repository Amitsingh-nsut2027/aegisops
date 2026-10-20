from datetime import datetime

from sqlalchemy import insert, select, text
from sqlalchemy.engine import Engine

from database import investigation_runs


def assert_investigator_role(engine: Engine) -> None:
    with engine.connect() as connection:
        valid = connection.execute(text(
            "SELECT current_user = 'aegis_investigator' AND NOT rolsuper "
            "AND NOT rolcreatedb AND NOT rolcreaterole "
            "AND has_table_privilege(current_user, 'incident_events', 'SELECT') "
            "AND NOT has_table_privilege(current_user, 'incident_events', 'INSERT,UPDATE,DELETE,TRUNCATE') "
            "AND has_table_privilege(current_user, 'investigation_runs', 'INSERT') "
            "AND NOT has_table_privilege(current_user, 'investigation_runs', 'UPDATE,DELETE,TRUNCATE') "
            "FROM pg_roles WHERE rolname = current_user"
        )).scalar_one()
    if not valid:
        raise RuntimeError("Investigator requires its dedicated append-only database role")


def save_run(engine: Engine, report: dict) -> None:
    # One INSERT in one transaction; repeated run IDs fail rather than overwrite history.
    with engine.begin() as connection:
        connection.execute(insert(investigation_runs).values(
            run_id=report["run_id"], event_id=report["event_id"], state=report["state"],
            started_at=datetime.fromisoformat(report["started_at"]),
            finished_at=datetime.fromisoformat(report["finished_at"]), payload=report,
        ))


class RunRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def list_runs(self, limit: int, offset: int, event_id: str | None) -> list[dict]:
        statement = select(investigation_runs)
        if event_id is not None:
            statement = statement.where(investigation_runs.c.event_id == event_id)
        statement = statement.order_by(investigation_runs.c.started_at.desc(),
                                       investigation_runs.c.run_id.asc()).limit(limit + 1).offset(offset)
        with self.engine.connect() as connection:
            return [dict(row) for row in connection.execute(statement).mappings()]

    def get_run(self, run_id: str) -> dict | None:
        with self.engine.connect() as connection:
            row = connection.execute(select(investigation_runs).where(
                investigation_runs.c.run_id == run_id)).mappings().first()
            return dict(row) if row else None

import os

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, MetaData, String, Table, create_engine, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine, URL

metadata = MetaData()
incident_events = Table(
    "incident_events", metadata,
    Column("event_id", String(64), primary_key=True),
    Column("event_type", String(64), nullable=False),
    Column("source", String(32), nullable=False),
    Column("resource_id", String(256), nullable=False),
    Column("observed_at", DateTime(timezone=True), nullable=False),
    Column("received_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("payload", JSONB, nullable=False),
)

investigation_runs = Table(
    "investigation_runs", metadata,
    Column("run_id", String(32), primary_key=True),
    Column("event_id", String(64), ForeignKey("incident_events.event_id"), nullable=False),
    Column("state", String(32), nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("finished_at", DateTime(timezone=True), nullable=False),
    Column("payload", JSONB, nullable=False),
    CheckConstraint("state = 'needs_evidence'", name="ck_runs_state"),
    CheckConstraint("finished_at >= started_at", name="ck_runs_time"),
)
Index("ix_investigation_runs_event_started", investigation_runs.c.event_id,
      investigation_runs.c.started_at, investigation_runs.c.run_id)


def database_engine(password_env: str = "POSTGRES_PASSWORD") -> Engine:
    url = URL.create(
        "postgresql+psycopg", username=os.getenv("DB_USER", "aegis_local"),
        password=os.environ[password_env],
        host=os.getenv("DB_HOST", "db"), port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "aegisops"),
    )
    return create_engine(
        url, pool_pre_ping=True, hide_parameters=True,
        connect_args={"connect_timeout": 5, "options": "-c statement_timeout=5000"},
    )

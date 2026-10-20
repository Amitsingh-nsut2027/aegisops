"""Add append-only investigation report storage."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_investigation_runs"
down_revision = "0001_incident_events"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "investigation_runs",
        sa.Column("run_id", sa.String(32), primary_key=True),
        sa.Column("event_id", sa.String(64), sa.ForeignKey("incident_events.event_id"), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint("state = 'needs_evidence'", name="ck_runs_state"),
        sa.CheckConstraint("finished_at >= started_at", name="ck_runs_time"),
    )
    op.create_index("ix_investigation_runs_event_started", "investigation_runs",
                    ["event_id", "started_at", "run_id"])


def downgrade():
    op.drop_table("investigation_runs")

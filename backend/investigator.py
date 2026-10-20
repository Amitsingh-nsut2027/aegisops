"""A bounded read-only investigation workflow, currently using simulated evidence."""
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from event_schema import QueuedIncident
from evidence import EvidenceRecord, validate_evidence
from llm_provider import LLMProvider, investigate
from runbooks import retrieve_runbooks

WORKFLOW_VERSION = "cpu-investigator-v3"


class EvidenceCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["cpu_samples", "request_rate", "deployment_history", "application_logs"]
    status: Literal["available", "unavailable"]
    source: str
    detail: str


def run_investigation(event: QueuedIncident, provider: LLMProvider | None = None,
                      evidence: list[EvidenceRecord] | None = None) -> dict:
    """Fixed workflow: no model-directed tools, writes, or automatic remediation.

    The trace records observable steps, not a model's private reasoning. All state
    exists only for this invocation and is returned to the caller.
    """
    # Revalidate at the boundary, including objects created with model_construct.
    event = QueuedIncident.model_validate_json(event.model_dump_json())
    evidence = validate_evidence(event, evidence or [])
    by_kind = {record.kind: record for record in evidence}
    started = datetime.now(timezone.utc)
    trace = []

    def record(step: str, status: str, detail: str) -> None:
        trace.append({"sequence": len(trace) + 1, "step": step, "status": status,
                      "recorded_at": datetime.now(timezone.utc).isoformat(), "detail": detail})

    record("validate_event", "completed", "Simulation event identity and CPU evidence validated.")
    checks = [EvidenceCheck(
        kind="cpu_samples", status="available", source="saved_simulator_event",
        detail=f"{len(event.cpu_evidence)} readings: {list(event.cpu_evidence)}; threshold > {event.threshold:g}%.",
    )]
    for kind in ("request_rate", "deployment_history", "application_logs"):
        if kind in by_kind:
            item = by_kind[kind]
            checks.append(EvidenceCheck(kind=kind, status="available", source=item.source,
                                        detail=item.detail))
            continue
        checks.append(EvidenceCheck(
            kind=kind, status="unavailable", source="not_connected",
            detail="No collector is connected for this evidence type; no lookup was attempted.",
        ))
    record("inventory_evidence", "completed",
           f"CPU evidence available; {len(evidence)} scripted supplemental records; {3 - len(evidence)} sources unavailable.")
    tags = {event.event_type, *by_kind}
    if len(evidence) < 3:
        tags.add("evidence_missing")
    runbooks = retrieve_runbooks(tags)
    record("retrieve_runbooks", runbooks["status"],
           f"Retrieved {len(runbooks['matches'])} local guidance excerpt(s); no runbook actions executed.")
    analysis = investigate(event, provider, evidence=evidence)
    record("summarize_evidence", "fallback" if analysis["used_fallback"] else "completed",
           f"Validated summary produced after {analysis['attempts']} provider attempt(s).")
    record("finish", "needs_evidence", "Root cause undetermined; additional read-only evidence is required.")
    return {
        "run_id": uuid4().hex,
        "workflow_version": WORKFLOW_VERSION,
        "event_id": event.event_id,
        "resource_id": event.resource_id,
        "simulated": True,
        "state": "needs_evidence",
        "started_at": started.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "observed_at": event.observed_at.isoformat(),
        "evidence_checks": [check.model_dump() for check in checks],
        "supplemental_evidence": [item.model_dump(mode="json") for item in evidence],
        "runbook_context": runbooks,
        "analysis": analysis,
        "trace": trace,
    }

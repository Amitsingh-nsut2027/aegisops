# Local runbook retrieval — knowledge foundation

## What this feature does
Investigation reports now include relevant local troubleshooting excerpts, source paths, and exact content revisions. This is deterministic retrieval of project-authored learning material. It is a foundation for a future retrieval-augmented system, not completed LLM RAG, semantic search, or autonomous troubleshooting.

The existing fake provider still summarizes event evidence. Runbooks are attached separately in runbook_context; they are not passed into that provider, cited as observed telemetry, or executed. Root cause remains null and state remains needs_evidence.

## Run the demo
```sh
docker compose run --rm investigator python investigator_cli.py --evidence-scenario traffic-surge-v1
```

Look for runbook_context.matches and the retrieve_runbooks trace step. The report is saved and can be inspected in authenticated GET /investigations or its detail route. The CPU-only command `docker compose run --rm investigator` also retrieves guidance. No new credentials or migration are required; source files are included in the backend image.

## Library and selection
| Runbook | Selection tags | Purpose |
|---|---|---|
| cpu-load | cpu.high.v1, request_rate | Compare CPU with workload and other symptoms |
| deployment-correlation | deployment_history | Investigate temporal correlation without asserting cause |
| evidence-gaps | evidence_missing | Identify useful missing observations |

The workflow derives tags from the validated event type and supplemental evidence kinds. It adds evidence_missing when any of the three supplemental kinds is absent. Free-form log text cannot choose tags or files. The fixed developer catalog maps these tags to three Markdown files under backend/runbooks.

Retrieval scores each document by the number of exact matching tags, sorts by descending score then runbook ID, and selects at most two documents by default. The function allows a bounded limit of one to three. A score is a relevance heuristic, not confidence in a diagnosis. An unrelated tag set produces no_match and no excerpts. We have no relevance benchmark yet; this tiny catalog is intended for inspectable behavior rather than broad semantic recall.

CPU-only investigations match cpu-load and evidence-gaps. The enriched traffic-surge demo matches cpu-load and deployment-correlation. This does not mean deployment caused the alert: merely having deployment context makes the review checklist applicable.

## Source attribution and bounded output
Each match includes runbook_id, title, source path, full-file SHA-256 revision, matched tags, score, excerpt, truncation flag, and guidance_only true. Each file is limited to 12,000 bytes; excerpts contain at most 1,600 characters. The revision hashes the full content, while the stored excerpt may be shorter. A saved excerpt plus full-file hash preserves what guidance was shown and identifies its source revision, but does not retain an entire oversized source or prove its authority.

Changing a Markdown file requires rebuilding the backend image before new runs see it. Old saved report snapshots remain unchanged. These are project-authored runbooks, not official AWS documentation or externally validated operational procedures. They contain read-only observation guidance, not executable commands.

## Failure behavior
Missing, empty, oversized, or invalid UTF-8 source files produce status unavailable, no partial matches, and a generic runbook_library_unavailable code. The investigator records that retrieval outcome and continues with its evidence summary. A runbook lookup failure is separate from a provider fallback. No error message leaks host paths into the returned report.

The workflow is now cpu-investigator-v3 with five observable trace steps: validate event, inventory evidence, retrieve runbooks, summarize evidence, and finish. Library metadata is local-runbooks-v1. Runbook failure does not change the existing needs_evidence outcome. A future diagnosis/approval system must not treat document instructions as authorization to act.

## Verification
Eight new tests cover bounded/stable ranking and attribution, no-match behavior for unrelated/instruction text, invalid limits, content revision changes, unavailable/corrupt/oversized files, excerpt bounds, evidence-dependent selection, and graceful lookup failure. The full unit suite has 66 passing tests. A report containing two excerpts was saved locally, then read through the authenticated API with source hashes verified.

## Interview explanation
“I added bounded runbook retrieval using structured event and evidence tags. Each saved result includes source attribution, a content revision, and the actual excerpt shown to the operator. Retrieval failure is explicit and does not prevent the evidence report from being saved. This is a deterministic knowledge-retrieval foundation; the runbooks are not executed or supplied to an LLM yet.”

## What remains
Real model integration, semantic retrieval, access-controlled external document ingestion, relevance evaluation, and grounded generation remain future work. The frontend will need to display observed evidence separately from guidance and preserve the explicit simulation labels. Frontend design quality remains governed by docs/UI-REQUIREMENTS.md and the design review checkpoint.

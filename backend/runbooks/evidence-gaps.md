# Collect missing investigation evidence

Project-authored learning guidance. Missing data is not evidence that a service is healthy.

1. List which sources are connected, unavailable, or not yet queried. Distinguish an unconnected collector from a successful query with no matching records.
2. Request scoped metrics, deployment history, and application logs around the alert's observation time. Retain source, resource, timestamps, query scope, and collection outcome.
3. Keep root cause undetermined until evidence supports a claim. Identify the next useful read-only observation rather than inventing missing facts.

This project currently supports optional scripted fixtures, not real AWS telemetry connectors. The checklist is guidance for future operator work; retrieving it does not collect evidence or authorize new account access.

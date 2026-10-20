# Investigate CPU and request load

Project-authored learning guidance. Read-only checks; no automatic actions.

1. Confirm the CPU aggregation, sampling interval, resource scope, and missing-data policy before interpreting a threshold breach.
2. Compare request rate and CPU across the same window, then examine latency, error rate, queue depth, and capacity limits. An increase in requests can correlate with CPU load without proving the cause.
3. If load remains unexplained, inspect application logs and profiling evidence with the operator's approved tools. Preserve timestamps and resource identifiers for every observation.

Scripted fixtures demonstrate data flow only. Do not infer customer impact, a code defect, or a need to scale from this demo. Scaling or restarting requires separate policy, authorization, execution, and validation steps that this runbook lookup does not perform.

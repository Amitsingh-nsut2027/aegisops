# Review deployment correlation

Project-authored learning guidance. A nearby deployment is a hypothesis lead, not proof.

1. Verify that the deployment and symptom refer to the same service, environment, and time window. Compare observation time rather than report receipt time.
2. Compare before/after CPU, workload, latency, and errors. Check whether unaffected versions or resources provide a useful comparison.
3. Review the actual change and release health before attributing a symptom to the deployment. Record alternative explanations and contradictory observations.

A generated demo-api-v2 fixture is not a real release record. Do not recommend or execute a rollback based solely on temporal proximity. This guidance performs no deployment lookup, rollback, or other infrastructure change.

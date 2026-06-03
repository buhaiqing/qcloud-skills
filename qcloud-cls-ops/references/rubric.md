# CLS Quality-Gate Rubric (GCL)

> Runtime rubric for **Generator-Critic-Loop (GCL)** of `qcloud-cls-ops`.
> See [`qcloud-clb-ops/references/rubric.md`](../clb-ops/references/rubric.md) for the backbone.

---

## 4. CLS-specific safety rules

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | `DeleteLogset` (any) | **Logset ID + Name + topic count echo; list all topics via `DescribeTopics`; warn that deletion permanently removes ALL log data across ALL topics in the logset; require literal "CONFIRM DELETE LOGSET <name>"** | Deleting a logset cascades to all topics and log data. CLS has no recycle bin. The most common incident: "I deleted the 'test' logset but the production log shipping pipeline was still writing to a topic in it — all production logs were lost" |
| 2 | `DeleteTopic` (any) | **Topic ID + Name + shard count + log data size echoed; warn that deletion permanently removes ALL log data in this topic; if the topic is used by a shipping task (e.g., COS export or CKafka), warn that the shipping pipeline will break; require confirmation with topic name** | Topic deletion destroys all log data. If there are active shipping tasks to COS or CKafka, those pipelines break silently. The most common incident: "I deleted a topic to reorganize but the COS shipping task was still configured and failed with 'topic not found'" |
| 3 | `DeleteIndex` (any) | **Index ID + Topic ID echoed; warn that deleting the index removes the ability to search and query log data (the raw data still exists but is unsearchable); warn that re-creating the index requires a full re-index of historical data (time-consuming and billable); require confirmation** | Index deletion is not data loss, but it makes data effectively inaccessible for search. The most common pattern: "I deleted the index to save costs, then needed to search for an incident from 3 months ago — the data was there but unqueryable" |
| 4 | `DeleteMachineGroup` / `DeleteConfigAttachment` | **MachineGroup ID + Name + associated config count + associated agent count (via `DescribeMachines`) echo; warn that removing a machine group stops log collection on ALL agents in that group; for config attachment: warn that the config still exists but is no longer applied; require confirmation** | Deleting a machine group stops log collection on all connected agents. The most common incident: "I reorganized machine groups but forgot to assign the agents to a new group — logs stopped flowing for 2 days before someone noticed" |
| 5 | `ModifyConfig` (modify collection config: `LogFormat`, `Path`, `Filter`, `ExcludePaths`) | **Show BEFORE/AFTER config diff; warn that the change takes effect on the agent's NEXT polling cycle (~60s delay); for path changes: warn that the agent will stop reading from the old path; for filter changes: warn that the new filter may silence important log entries; require confirmation for each changed field** | Config changes are applied asynchronously. The most common incident: "I changed the log collection path from `/var/log/app/*.log` to `/var/log/app/*.json` and the agent stopped collecting `.log` files — we had a 4-hour gap in the logs" |

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 CLS rollout: rubric (5 rules: logset cascade delete, topic data loss, index removal unsearchable, machine group collection stop, config change silent gap) |
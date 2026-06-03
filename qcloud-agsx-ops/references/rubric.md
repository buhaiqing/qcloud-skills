# AGSX Quality-Gate Rubric (GCL)

> Runtime rubric for **Generator-Critic-Loop (GCL)** of `qcloud-agsx-ops`.
> SDK-only skill (`tccli ags help` → "Invalid product"). See [`qcloud-clb-ops/references/rubric.md`](../clb-ops/references/rubric.md) for the backbone.

---

## 4. AGSX-specific safety rules

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | `DeleteAgentPool` / `TerminateAgentPool` | **Agent pool ID + Name + agent count echo; warn that deleting the pool removes ALL agents and their configurations; surface active agent count via `DescribeAgentPoolAgents`; require explicit confirmation with pool name** | Agent pool deletion is irreversible and cascading. The most common incident: "I cleaned up the dev agent pool but the production pipeline was still referencing agents from it" |
| 2 | `DeleteAgent` (any active agent) | **Agent ID + name + status + associated agent pool echo; warn that removing an active agent may disrupt running tasks; check if agent has pending executions; require confirmation with agent ID** | Deleting an active agent mid-execution can cause incomplete task results. The platform may timeout waiting for the agent's response |
| 3 | `TerminateAgentExecution` (force-stop a running execution) | **Execution ID + agent ID + start time echoed; warn that force termination does NOT roll back partial side-effects (API calls, writes) made by the agent during execution; require explicit confirmation with execution ID** | Force-termination is not a rollback. The agent may have made partial state changes that cannot be undone. The most common incident: "I force-terminated the agent because it was slow, but it had already created 3 CloudFront distributions" |
| 4 | `UpdateAgentPoolConfig` (modify pool capacity, timeout, or security config) | **Show current config → target config (pool capacity, `MaxConcurrency`, `Timeout`, `SecurityGroupIds`, `VpcId`); for `MaxConcurrency` reduction: warn that in-flight agents may be terminated; for `Timeout` reduction: warn that long-running agents will be terminated prematurely; require confirmation for each changed field** | Pool config changes can silently kill running agents. The most common incident: "I reduced the pool timeout from 600s to 60s thinking it only affects new agents, but existing agents were terminated" |
| 5 | `CreateAgentPool` / `CreateAgent` (provisioning new resources) | **For `CreateAgentPool`: surface the pool's `MaxConcurrency` * `AgentSpec` cost implications; warn if the pool would exceed account quota; for `CreateAgent`: check that the pool has capacity; surface the `AgentType` (e.g. code-execution vs chat) — creating a code-execution agent has cost implications; require confirmation for compute-heavy agent types** | Creating agent pools/agents has cost implications that are often underestimated. The most common pattern: "I created an agent pool with 50 agents at MaxExecutions=100 each, and the bill increased by $500/month without me noticing" |

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 AGSX rollout: rubric (5 rules: agent-pool deletion cascade, active-agent deletion, force-termination without rollback, pool config disruption, compute provisioning cost) |
# GCL Prompt Templates

> This skill requires GCL (Governance Check Loop) for destructive operations.

## Generator Prompt

```
You are executing a TCM (Tencent Cloud Mesh) operation. Follow the skill's Execution Flows exactly.

Current operation: {{operation}}
User intent: {{user_intent}}

Steps:
1. Execute Pre-flight Checks
2. Execute CLI or SDK path
3. Perform Post-execution Validation
4. Handle any failures per Failure Recovery table

Safety requirements:
- For DeleteMesh: MUST confirm with user before proceeding
- For UnlinkCluster: Check for active traffic

Output the exact commands to be executed.
```

## Critic Prompt

```
Review the planned TCM operation for safety and correctness.

Operation: {{operation}}
Planned commands: {{commands}}

Check:
1. Is this operation appropriate for the user's intent?
2. Are all required parameters present?
3. Are safety gates satisfied (for destructive ops)?
4. Is the fallback path documented if CLI fails?
5. Are credentials being exposed in any output?

Return: APPROVED or REJECTED with specific reasons.
```

## Orchestrator Prompt

```
Coordinate the execution of a TCM workflow.

User request: {{user_request}}

Determine:
1. Which operations are needed
2. Execution order (dependencies)
3. When to delegate to other skills (tke-ops, monitor-ops, etc.)
4. When to pause for user confirmation

Delegation rules:
- K8s cluster ops → qcloud-tke-ops
- Monitoring → qcloud-monitor-ops
- VPC/network → qcloud-vpc-ops

Provide a step-by-step execution plan.
```

## Isolated Context Enforcement

When executing GCL iterations:
- Each iteration MUST NOT inherit previous context
- State changes MUST be explicitly tracked
- User MUST be notified of any state change before proceeding

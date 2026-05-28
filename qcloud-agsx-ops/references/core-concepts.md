# AGSX Core Concepts

## Domain Model

```
Account
  +-- APIKey (ak-xxx) -- used by client SDK to auth to runtime
  +-- SandboxTool (stool-xxx) -- template/definition
        +-- SandboxInstance (si-xxx) -- runtime instance, 24h max
              +-- Image (img-xxx) -- prewarmable base image
```

## Sandbox Types

| Type | Use Case | Base Image |
|---|---|---|
| Browser Sandbox | Web automation, scraping, headless Chrome | `browser-base` |
| Code Sandbox | Python/Node.js code execution for Agents | `code-interpreter` |
| Custom Sandbox | User-defined Docker image | user-provided |

## Lifecycle

1. **Definition**: Create SandboxTool (one-time, defines spec/image/timeout).
2. **Instantiation**: StartSandboxInstance -> ~100ms cold start (faster with prewarm).
3. **Execution**: Client connects via e2b protocol using API key.
4. **Termination**: Auto-terminate at 24h OR explicit StopSandboxInstance.

## Region & Endpoint

| Region | API Endpoint | E2B Domain |
|---|---|---|
| ap-guangzhou | ags.tencentcloudapi.com | ap-guangzhou.tencentags.com |
| ap-shanghai  | ags.tencentcloudapi.com | ap-shanghai.tencentags.com |
| ap-beijing   | ags.tencentcloudapi.com | ap-beijing.tencentags.com |

## Compatibility

- **e2b protocol**: Drop-in replacement for e2b.dev. Migrate by changing `E2B_DOMAIN`.
- **MCP**: Sandbox tools exposable as MCP servers for Claude/Cursor.
- **OpenAI Assistants**: Compatible via e2b-code-interpreter adapter.

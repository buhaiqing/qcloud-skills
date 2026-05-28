# Integration Patterns

## Pattern 1: e2b-code-interpreter (Direct)

```python
import os
from e2b_code_interpreter import Sandbox

os.environ["E2B_DOMAIN"] = "ap-guangzhou.tencentags.com"
os.environ["E2B_API_KEY"] = "ak-xxxxxxxx"  # MASK in logs

with Sandbox(template="code-interpreter") as sbx:
    result = sbx.run_code("import pandas; print(pandas.__version__)")
    print(result.logs.stdout)
```

## Pattern 2: PydanticAI Agent Tool

```python
from pydantic_ai import Agent, Tool
from e2b_code_interpreter import Sandbox

def run_python(code: str) -> str:
    with Sandbox() as sbx:
        return sbx.run_code(code).logs.stdout

agent = Agent("openai:gpt-4o", tools=[Tool(run_python)])
result = agent.run_sync("Compute factorial of 10")
```

## Pattern 3: MCP Server Wrapping AGSX

Expose AGSX as MCP tool for Claude Desktop / Cursor:

```python
from mcp.server.fastmcp import FastMCP
from e2b_code_interpreter import Sandbox

mcp = FastMCP("agsx-code")

@mcp.tool()
def execute_python(code: str) -> str:
    """Run Python in AGSX sandbox."""
    with Sandbox() as sbx:
        return sbx.run_code(code).logs.stdout

if __name__ == "__main__":
    mcp.run()
```

## Pattern 4: Browser Sandbox for Web Automation

```python
from e2b_desktop import Sandbox as Browser

with Browser(template="browser-base") as br:
    br.navigate("https://example.com")
    screenshot = br.screenshot()
```

## Pattern 5: Persistent Sandbox via Management API

For long-running sessions, use the management API to control lifecycle explicitly:

```python
# 1. Create via management API (full control over metadata, retention)
instance = mgmt_client.StartSandboxInstance(req)

# 2. Connect via e2b client with explicit instance ID
sbx = Sandbox.connect(instance.InstanceId)

# 3. Keep alive across multiple agent turns
# 4. Terminate explicitly when done (or wait 24h auto-cleanup)
mgmt_client.StopSandboxInstance(...)
```

## Anti-Patterns

- DO NOT create one tool per request (rate limit risk). Reuse tools, create many instances.
- DO NOT hardcode E2B_API_KEY in source. Use env vars or secrets manager.
- DO NOT leave instances running after agent task completes; terminate explicitly.

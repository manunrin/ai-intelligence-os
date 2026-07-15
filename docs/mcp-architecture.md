# MCP Architecture — Model Context Protocol Infrastructure Layer

## 1. What is MCP?

MCP (Model Context Protocol) is a standardized abstraction layer that allows AI agents to interact with external systems — Notion, Asana, GitHub, browsers — through a **uniform tool interface** rather than ad-hoc API calls scattered across agent code.

```
Agent
 |
Tool Registry
 |
MCP Client Layer
 |
MCP Server
 |
External Service API
```

Every external integration is a **server**. Every operation is a **tool**. The registry routes tool calls to the correct server. Agents never import service-specific SDKs.

## 2. Why not direct API calls?

| Problem with direct calls | MCP solution |
|---------------------------|---------------|
| Agent code couples to specific APIs | Agent calls `registry.get_tool("notion.create_page")` — no Notion imports |
| Hard to add/remove integrations | Register or unregister a server; agents see changes automatically |
| Inconsistent error handling per agent | Uniform `execute()` → `{"success": True/False, "data": ...}` contract |
| Security tokens duplicated across agents | Token lives in server config, not agent code |
| No unified tool discovery for LLM prompts | `registry.list_schemas()` returns all available tools in one call |

## 3. Agent Tool Call Flow

```
1. Agent calls:  registry.get_tool("notion.create_page")
2. Registry resolves:  "notion" → NotionMCPServer, "create_page" → NotionCreatePage
3. Agent executes:    await tool.execute(title="AI News", content="...")
4. Tool delegates:    NotionCreatePage._execute_impl()
5. Result returns:    {"success": True, "data": {"id": "...", "url": "..."}}
```

The agent sees **zero difference** between a local tool and an MCP tool. Both implement the same `execute(**kwargs) -> dict` contract.

## 4. Server Design

### MCPServerBase

Every server declares:
- **name**: unique identifier (e.g. `"notion"`)
- **available_tools()**: returns list of `MCPToolDefinition` with name, description, JSON Schema parameters
- **_create_tool(name)**: factory method that instantiates the right `MCPTool` subclass

### MCPTool

Every tool implements:
- **tool_definition**: property returning `MCPToolDefinition`
- **_execute_impl(**kwargs)**: actual integration logic (mock or real API call)
- **execute(**kwargs)**: wrapper that logs and returns structured result

### Directory Layout

```
backend/mcp/
├── __init__.py
├── base.py              # MCPServerBase, MCPTool
├── client.py            # HTTP client for remote MCP servers
├── registry.py          # MCPRegistry — server registration, tool lookup
├── schemas.py           # MCPServerConfig, MCPToolDefinition
└── servers/
    ├── __init__.py
    ├── notion/
    │   ├── __init__.py
    │   ├── server.py     # NotionMCPServer
    │   └── tools.py      # NotionCreatePage, NotionUpdatePage, …
    ├── asana/
    │   ├── server.py
    │   └── tools.py
    ├── github/
    │   ├── server.py
    │   └── tools.py
    └── browser/
        ├── server.py
        └── tools.py
```

## 5. Security Model

- **API tokens** are stored in environment variables (`NOTION_TOKEN`, `ASANA_TOKEN`, `GITHUB_TOKEN`), never in code.
- Each server reads its own credentials during `initialize()`.
- The MCPClient supports optional Bearer token authentication for remote server communication.
- Tool schemas expose only parameter names and types to agents — no secrets leak into LLM prompts.

## 6. Cloud Deployment

In production, each MCP server can run as:

1. **Embedded** (current): All servers run inside the backend process. Simplest deployment, single binary.

2. **Standalone services**: Each server runs as its own container with an HTTP endpoint. The `MCPClient` talks to them over the network. Enables independent scaling and language boundaries.

3. **Hybrid**: Core servers (Notion, GitHub) embedded; experimental ones (Browser) standalone for isolation.

The architecture supports all three modes because the `MCPClient` abstracts the transport layer — swap a local tool call for an HTTP call without touching agent code.

# PitchBook MCP Discovery Report

**Date:** 2026-03-09
**Session:** Claude Code web session
**Purpose:** Determine whether a PitchBook MCP server is available and document its contract

---

## 1. Discovery Result

**No PitchBook MCP server is available in this Claude Code session.**

### Evidence

| Check | Result |
|---|---|
| `~/.claude/settings.json` | Contains hooks and permissions only — no `mcpServers` key |
| Project-level `.mcp.json` | Does not exist |
| `~/.claude/*.json` MCP configs | None found |
| Environment variables | No `PITCHBOOK_*` or PitchBook-related vars |
| MCP-related env vars | `CODESIGN_MCP_PORT`, `CODESIGN_MCP_TOKEN`, `MCP_TOOL_TIMEOUT` — internal Claude Code infrastructure only |
| Running processes | No `pitchbook` or PitchBook MCP server processes |
| File system search | No JSON files referencing "pitchbook" or MCP server configs found |
| Available tools in session | Standard Claude Code tools only (Bash, Read, Write, Edit, Glob, Grep, WebFetch, WebSearch, Agent, etc.) — no MCP-provided tools |

### MCP Infrastructure Present

The session does have MCP infrastructure (`USE_SHTTP_MCP=true`, `MCP_TOOL_TIMEOUT=60000`), but the only connected MCP server is `codesign` (internal Claude Code signing service). No data-provider MCP servers are configured.

---

## 2. What Would Be Needed

To make a PitchBook MCP server available, one of the following would be required:

### Option A: Project-level MCP configuration
Create `.mcp.json` in the repo root:
```json
{
  "mcpServers": {
    "pitchbook": {
      "command": "npx",
      "args": ["pitchbook-mcp-server"],
      "env": {
        "PITCHBOOK_API_KEY": "<key>"
      }
    }
  }
}
```

### Option B: User-level MCP configuration
Add to `~/.claude/settings.json`:
```json
{
  "mcpServers": {
    "pitchbook": {
      "command": "...",
      "args": ["..."],
      "env": { "PITCHBOOK_API_KEY": "..." }
    }
  }
}
```

### Option C: Direct API integration (no MCP)
If no MCP server package exists for PitchBook, implement a direct HTTP client against the PitchBook API. This requires:
- PitchBook API base URL
- API key or OAuth credentials
- API documentation (endpoints, request/response schemas)

---

## 3. Information Gaps

| Item | Status |
|---|---|
| PitchBook MCP server package name | **Unknown** — no standard npm/pip package discovered |
| PitchBook API credentials | **Not provided** |
| PitchBook API documentation | **Not available in session** |
| Tool names and schemas | **Cannot be discovered** — no server to introspect |
| Available endpoints | **Unknown** |
| Rate limits / quotas | **Unknown** |
| Authentication method (API key vs OAuth) | **Unknown** |

---

## 4. Application Use-Case Mapping (Planned)

These are the data needs our application has that PitchBook would serve. The exact tool/endpoint mapping cannot be determined without access to the server contract.

| Application Use Case | Expected PitchBook Capability | Mapping Status |
|---|---|---|
| Company search by name/criteria | Company search endpoint | **Unmapped** |
| Company profile (overview, ownership, management) | Company detail endpoint | **Unmapped** |
| Debt / financing history | Deal/financing endpoints | **Unmapped** |
| Competitors / similar companies | Competitor or peer comparison endpoint | **Unmapped** |
| Industry/sector classification | Industry taxonomy endpoint | **Unmapped** |
| Revenue / financial metrics | Financial data endpoint | **Unmapped** |

---

## 5. Verdict

**Cannot implement `MCPPitchBookClient` safely in this session.** There is no PitchBook MCP server to introspect, no API documentation available, and no credentials configured. Any implementation would require guessing tool names, schemas, and response structures.

### Recommended Next Steps

1. **Determine integration approach:** Is PitchBook access via an existing MCP server package, or via direct REST API?
2. **Provide credentials:** API key or OAuth configuration for PitchBook
3. **Provide documentation:** Either configure the MCP server (so tools can be introspected) or share the PitchBook API docs (so a direct client can be built)
4. **Re-run discovery:** Once configured, re-run this discovery pass to enumerate and document the actual contract

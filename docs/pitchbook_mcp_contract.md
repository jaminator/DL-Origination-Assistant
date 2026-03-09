# PitchBook Integration Contract

**Date:** 2026-03-09
**Status:** Implementation ready (REST client complete, MCP client stubbed)

---

## 1. Overview

The DL Origination platform integrates with PitchBook for company enrichment
during the borrower mining pipeline (stages 5–6: PITCHBOOK_ENRICHMENT and
CASCADE_EXPANSION).  Three provider modes are supported:

| Provider | Setting value | Status |
|---|---|---|
| Mock | `mock` (default) | Fully implemented — synthetic data |
| REST API v2 | `rest` | Implemented — requires API key |
| MCP Server | `mcp` | Stubbed — requires MCP server config |

Set via `PITCHBOOK_PROVIDER` environment variable.

---

## 2. PitchBook API v2 Reference

### Authentication

PitchBook API v2 uses API key authentication.  The key is passed in the
`Authorization: Bearer <key>` header.

| Setting | Env Var | Default |
|---|---|---|
| `pitchbook_api_base_url` | `PITCHBOOK_API_BASE_URL` | `https://api.pitchbook.com/v2` |
| `pitchbook_api_key` | `PITCHBOOK_API_KEY` | (empty) |
| `pitchbook_api_timeout` | `PITCHBOOK_API_TIMEOUT` | `30.0` |
| `pitchbook_api_max_retries` | `PITCHBOOK_API_MAX_RETRIES` | `3` |

### Entity Types

PitchBook tracks these entity types, each with search + detail endpoints:

- **Companies** — profiles, financials, ownership, industries
- **Deals** — financing rounds, M&A, debt/credit, IPOs
- **Investors** — VC, PE, family offices, corporate investors
- **Funds** — investment vehicles
- **People** — executives, board members
- **Limited Partners** — institutional investors
- **Service Providers** — law firms, advisors, banks

### REST Endpoints Used by Our Application

#### Company Search

```
GET /companies?name={name}&pageSize={n}
```

**Response:**
```json
{
  "items": [
    {
      "companyId": "123456-78",
      "companyName": "Acme Corp",
      "ownershipStatus": "Privately Held",
      "primaryIndustrySector": "Business Services",
      "employees": 250,
      "revenueRange": "$50M-$100M",
      "hqCity": "Dallas",
      "hqState": "TX",
      "hqCountry": "US"
    }
  ],
  "totalCount": 1,
  "pageSize": 5,
  "page": 1
}
```

#### Company Detail

```
GET /companies/{companyId}
```

**Response:**
```json
{
  "companyId": "123456-78",
  "companyName": "Acme Corp",
  "description": "Provider of industrial automation solutions...",
  "yearFounded": 2005,
  "website": "https://acmecorp.com",
  "ownershipStatus": "Privately Held",
  "primaryIndustrySector": "Industrials",
  "employees": 250,
  "revenue": 75000000,
  "ebitda": 12000000,
  "totalRaised": 20000000,
  "investors": [
    {
      "investorId": "inv-001",
      "investorName": "Growth Capital Partners",
      "investorType": "Growth Equity"
    }
  ],
  "hqCity": "Dallas",
  "hqState": "TX",
  "hqCountry": "US",
  "companyStatus": "Active",
  "lastFinancingDate": "2024-03-15",
  "lastFinancingDealType": "Growth Equity"
}
```

#### Company Competitors

```
GET /companies/{companyId}/competitors?pageSize={n}
```

**Response:**
```json
{
  "items": [
    {
      "companyId": "789012-34",
      "companyName": "Beta Industries",
      "primaryIndustrySector": "Industrials",
      "employees": 180,
      "hqCity": "Houston",
      "hqState": "TX"
    }
  ]
}
```

#### Company Deals (Debt)

```
GET /companies/{companyId}/deals?dealType=Debt&pageSize={n}
```

**Response:**
```json
{
  "items": [
    {
      "dealId": "deal-001",
      "dealType": "Term Loan",
      "dealSize": 75000000,
      "closeDate": "2023-06-15",
      "maturityDate": "2028-06-15",
      "pricing": "S+500",
      "dealStatus": "Completed",
      "leadInvestor": "Bank of Lending",
      "lenders": [
        {
          "investorName": "Bank of Lending",
          "investorType": "Bank"
        }
      ]
    }
  ]
}
```

#### Company Investors (reference only — not used as standalone call)

Investor data is embedded in the company detail response. A standalone
investors endpoint exists but is not called by our adapter.

```
GET /companies/{companyId}/investors?pageSize={n}
```

---

## 3. MCP Tool Contract

When PitchBook is accessed via MCP (Model Context Protocol), the server exposes
these tools.  The tool names and schemas below are the contract our
`PitchBookMCPClient` expects.

### Tool: `pitchbook_search_companies`

Search for companies by name.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "name": { "type": "string", "description": "Company name to search" },
    "pageSize": { "type": "integer", "default": 25 }
  },
  "required": ["name"]
}
```

**Output:** Same as REST `GET /companies` response.

### Tool: `pitchbook_get_company`

Get full company profile by ID.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "companyId": { "type": "string", "description": "PitchBook company ID" }
  },
  "required": ["companyId"]
}
```

**Output:** Same as REST `GET /companies/{companyId}` response.

### Tool: `pitchbook_get_company_competitors`

Get competitor companies.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "companyId": { "type": "string", "description": "PitchBook company ID" },
    "pageSize": { "type": "integer", "default": 25 }
  },
  "required": ["companyId"]
}
```

**Output:** Same as REST `GET /companies/{companyId}/competitors` response.

### Tool: `pitchbook_get_company_deals`

Get deals for a company, optionally filtered by type.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "companyId": { "type": "string", "description": "PitchBook company ID" },
    "dealType": { "type": "string", "description": "Filter by deal type (e.g. Debt, M&A)" },
    "pageSize": { "type": "integer", "default": 25 }
  },
  "required": ["companyId"]
}
```

**Output:** Same as REST `GET /companies/{companyId}/deals` response.

---

## 4. MCP Server Configuration

To enable PitchBook MCP integration, configure one of:

### Project-level (`.mcp.json`)

```json
{
  "mcpServers": {
    "pitchbook": {
      "command": "npx",
      "args": ["pitchbook-mcp-server"],
      "env": {
        "PITCHBOOK_API_KEY": "<your-api-key>"
      }
    }
  }
}
```

### User-level (`~/.claude/settings.json`)

```json
{
  "mcpServers": {
    "pitchbook": {
      "command": "npx",
      "args": ["pitchbook-mcp-server"],
      "env": {
        "PITCHBOOK_API_KEY": "<your-api-key>"
      }
    }
  }
}
```

> **Note:** No official PitchBook MCP server npm package exists as of March 2026.
> A custom MCP server wrapping the PitchBook REST API would need to be built,
> or the Apify PitchBook Companies Scraper MCP server
> (`apify.com/pratikdani/pitchbook-companies-scraper/api/mcp`) can be used as
> a third-party alternative.

---

## 5. Application Settings

```bash
# Provider selection (mock | rest | mcp)
PITCHBOOK_PROVIDER=rest

# REST API v2 settings
PITCHBOOK_API_BASE_URL=https://api.pitchbook.com/v2
PITCHBOOK_API_KEY=your-api-key-here
PITCHBOOK_API_TIMEOUT=30.0
PITCHBOOK_API_MAX_RETRIES=3

# MCP settings (when provider=mcp)
MCP_PITCHBOOK_URL=http://localhost:3000
MCP_PITCHBOOK_TOKEN=your-mcp-token
```

---

## 6. Pipeline Integration Points

The PitchBook adapter is used in two pipeline stages:

### Stage 5: PITCHBOOK_ENRICHMENT (`engine.py:277`)

For each company with disposition PRIMARY, WATCH, or CASCADE_ANCHOR:
1. `search_company(name)` — find the PitchBook entity
2. `get_company_detail(entity_id)` — get ownership, investors, financials
3. `get_debt_details(entity_id)` — get debt/capital structure
4. `get_competitors(entity_id)` — get competitor count for catalyst flags

### Stage 6: CASCADE_EXPANSION (`engine.py:348`)

For each CASCADE_ANCHOR with a PitchBook entity ID:
1. `get_competitors(entity_id)` — discover peer companies
2. New companies are created and added to the pipeline for scoring

---

## 7. Data Flow

```
PitchBook API/MCP  →  PitchBookAdapter  →  MinerEngine  →  CompanyRecord
                                                            ├── pb_entity_id
                                                            ├── pb_status
                                                            ├── ownership_tier (overrides web)
                                                            ├── investor_names
                                                            ├── has_debt
                                                            ├── facility_type/amount/pricing
                                                            ├── lender_names
                                                            └── catalyst_flags
```

---

## 8. Error Handling

| Scenario | Behavior |
|---|---|
| No adapter configured | Stage skipped with reason `"no_adapter"` |
| Adapter not available (no credentials) | Stage skipped with reason `"unavailable"` |
| Company not found in PitchBook | `pb_status = NOT_FOUND`, continue to next |
| API error (5xx, timeout) | Retry with exponential backoff (up to 3 attempts) |
| Rate limit (429) | Respect `Retry-After` header, back off |
| Individual company enrichment failure | `pb_status = ERROR`, logged, pipeline continues |

# METER for ChatGPT and Codex

Use METER to discover OOH/DOOH inventory, calculate projected Universe, OTS and Reach, and prepare address programs from validated results. A METER account and an active Plugin subscription are required: **$599 per user, per country, per month**. [Purchase or manage the subscription in Wallet](https://window.wallet.meter.ad/plugin), then sign in to the assistant with the same METER account. Installing this package does not grant service or data access.

Wallet displays the licensed user, country, payer, paid period and final top-up quote. Team payment covers the selected user only and respects the team budget. Countries renew independently; cancellation takes effect at the paid period end. A subscription-required message needs a Wallet action; OAuth reconnection is only for authentication failure. If Wallet verification is temporarily unavailable, retry later.

## Codex installation

Use a current Codex client (verified with CLI 0.153.4). Add the public marketplace and install its METER plugin:

```sh
codex plugin marketplace add GEOMOTIVE/meter-claude-plugin
codex plugin add meter@meter-public
```

Open a new task after installation so the client loads the current plugin's skills and tools. Complete the normal METER OAuth flow when prompted. In Codex, select the METER plugin from the Plugins UI; do not use Claude-specific slash commands. If you already have an older METER integration, choose one connection for a task so obsolete or duplicate tools are not mistaken for this package.

The configured server is `https://mcp.meter.ad/meter/mcp`. No API key, server process, database access, port forwarding or environment variables are needed for this public package.

## Connection diagnostics

For missing tools, multiple METER entries, failed calls or version questions, use the [diagnostics guide](skills/meter/references/diagnostics.md). Identify this package's connection before using a prefixed tool. A separate QA connector or conversation result is not an installed duplicate. The embedded version resource identifies the containing files; the installed package, loaded skill and MCP server versions require their own observations. The optional local classifier reads one retained snapshot without network calls, retries or changes to the client.

## ChatGPT preparation

METER uses the **With MCP** submission path, with the same public endpoint and the bundled skill. Uploading skills alone does not connect the METER service. The publisher must enter the MCP URL, configure OAuth, verify the domain and complete OpenAI review. This repository is not evidence of directory approval.

For a development connection, use ChatGPT's supported custom MCP/plugin setup and complete OAuth. Then attach METER to the conversation and run the prompts below. Access to custom development connections depends on the workspace and account. Do not assume installing the Codex marketplace automatically creates a ChatGPT connection.

## Try it

- “Find up to three inventory records in Ташкент and show their sourced OOH/DOOH classification.”
- “Calculate Universe for ages 20–45, all genders and income abc in that city.”
- “Use those exact IDs to calculate legacy OTS and Reach for 1–31 August 2026. Keep the audience unchanged.”
- “Create an XLSX address program with campaign totals and a numbered city map matching those exact IDs.”

Use geography covered by your METER account. The skill checks current tool schemas, labels the calculation methodology, treats no_data as unavailable, and only tries legacy fallback when allowed by the request. Spreadsheet creation needs file-authoring tools in the client; otherwise the assistant must say it returned a table, not an XLSX.

Client-ready address programs include a map unless the user requests a table-only export. The map and address table use the same sourced coordinates and sequence-to-ID mapping. Missing map inputs or tools must be disclosed; the public package supplies no monitoring heatmap or operator prices. See [Excel export requirements](skills/meter/references/excel-export.md).

For “maximize Reach 5+ with at most 80 surfaces,” the skill compares complete campaigns and retains the brief and tested variants. A surface ranking is only a starting point. The optional local Python ledger checker validates recorded requests and results without calling METER; client file execution is required to use it. See [campaign planning](skills/meter/references/campaign-planning.md). Results are the best among tested feasible programs, with search and price limitations disclosed.

Inventory and budget preparation preserves source warnings, holds unresolved static/digital conflicts for review and calculates explicit cost scenarios without inventing missing prices. The optional local helper has no tariff feed and does not confirm placement availability. See [inventory and budget](skills/meter/references/inventory-budget.md).

The optional [local XLSX builder](skills/meter/references/export-builder.md) joins the validated final roster, editable costs and embedded map. It uses the client's available authoring runtime and cached attributed tiles, preserves missing-data warnings and verifies the saved workbook. It fetches no tiles and installs no dependencies.

See [metric definitions](skills/meter/references/metrics.md), [routing](skills/meter/references/api-routing.md), [response-time expectations](skills/meter/references/performance.md), [data handling](docs/data-handling.md), and [OpenAI verification evidence](docs/openai-verification.md).

## Source and support

[Source repository](https://github.com/GEOMOTIVE/meter-claude-plugin). Product and account information: [METER](https://meter.ad). Report non-sensitive package defects through GitHub issues and security issues through private vulnerability reporting. Contact your METER account administrator for data permissions and applicable service privacy terms.

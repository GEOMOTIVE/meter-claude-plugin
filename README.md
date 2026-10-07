# METER for Claude, ChatGPT and Codex

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/meter-logo-white.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/meter-logo.svg">
  <img src="assets/meter-logo.svg" alt="METER" width="340" height="64">
</picture>

Plan outdoor advertising with METER in Claude Code, Cowork, ChatGPT and Codex. Discover OOH/DOOH inventory, calculate projected audience Universe, OTS and Reach, inspect audience profiles, and prepare address-program spreadsheets from validated results.

**Requires a METER account and an active Plugin subscription: $599 per user, per country, per month.** [Purchase or manage subscriptions in Wallet](https://window.wallet.meter.ad/plugin). Sign in with the same METER identity in Wallet and your assistant. Choose the licensed user and country before confirming. Installing the plugin does not grant data access.

A team can pay from its Wallet account subject to its team budget; the license covers only the selected user and country. Each country renews independently. Cancellation keeps access until the paid period ends. Wallet shows the final top-up quote, currency conversion and applicable fees before payment.

## Install in Claude Code

```text
/plugin marketplace add GEOMOTIVE/meter-claude-plugin
/plugin install meter@meter-plugins
```

Restart Claude Code or run `/reload-plugins`. Open `/mcp`, select the METER server and complete OAuth sign-in if requested. Invoke `/meter:meter` or describe the planning task naturally. If METER is already connected separately, use one connection for the task to avoid ambiguous duplicate tools.

This is METER's own marketplace. Listing in Anthropic's official directory is subject to review; this repository does not claim approval or Anthropic verification.

## Codex and ChatGPT

The OpenAI package is generated at `plugins/meter` from the same reviewed skills and assets. See [OpenAI installation and usage](docs/openai-package.md) and [OpenAI submission preparation](docs/openai-submission.md). Claude directory approval and OpenAI directory approval are separate; neither is claimed by this repository.

## Cowork

Use the plugin's released ZIP with Cowork's plugin upload flow, or install from a marketplace supported by your workspace. Complete MCP sign-in when prompted. Availability and installation controls depend on the client and organization settings.

## Try it

- “Find up to three available inventory records in Ташкент. Show their METER IDs, addresses and actual OOH/DOOH classification.”
- “Calculate the audience Universe in Ташкент for ages 20–45, all genders and income abc, for 1–31 August 2026.”
- “Using those exact surface IDs, calculate legacy OTS and Reach for the same audience and period. Label modeled contacts separately from unique audience.”
- “Create an XLSX address program from those results, with campaign totals, an inventory table and a numbered city map.”

Use a city and period covered by your account. Spreadsheet creation depends on file-authoring tools available in your client; this package does not install a spreadsheet runtime.

Client-ready address programs include a city map whose point numbers match the inventory table, unless a table-only export was requested. Missing coordinates, a basemap or authoring capabilities must be disclosed as an incomplete export. See the [export contract](skills/meter/references/excel-export.md).

## Calculation behavior

There are 16 METER tools. Legacy OTS is used when New OTS coverage is unknown. New OTS availability varies by geography and inventory. A `no_data` result means data is unavailable for that request, not zero; when permitted by the brief, the skill tries legacy once and names the methodology used.

Campaign Reach optimization compares whole-program calculations under a persisted brief. The optional local ledger checker detects changed requests and selects the best recorded feasible result; it is not a hosted optimizer or proof of global optimality. See [campaign planning](skills/meter/references/campaign-planning.md).

Program preparation also checks inventory status and conflicting static/digital metadata before selection. An optional local helper calculates a sourced or explicitly assumed budget by component and range; missing prices remain unavailable, and placement availability remains unconfirmed. See [inventory and budget](skills/meter/references/inventory-budget.md).

Historical small-scenario API measurements were roughly <1 second for simple queries, 1–3 seconds for selection/legacy calculations, 6–8 seconds for New OTS, and 12–15 seconds for some breakdowns. These exclude OAuth and remote MCP overhead and are not an SLA. See [method timings and limitations](skills/meter/references/performance.md).

## Troubleshooting

- **Needs authentication / HTTP 401:** reconnect METER in the client’s connection settings (`/mcp` in Claude Code) and complete OAuth.
- **Subscription required:** open [Wallet](https://window.wallet.meter.ad/plugin), check the licensed user and country, and purchase or fund the recorded payer for renewal. Reinstalling or signing in repeatedly does not activate a license.
- **Wallet verification unavailable:** try again shortly; an outage does not grant temporary data access.
- **Access denied / invalid country scope:** ask your METER administrator to check your existing account's tool and country permissions. Installing again does not grant permissions.
- **New OTS no_data:** use legacy if the task permits; do not invent metrics.
- **Timeout:** narrow the inventory/period or try later. Avoid repeating an unchanged request automatically.
- **Incomplete inventory:** finish pagination or narrow the query before producing a final program.

## Data and security

The package contains instructions, branding, one HTTPS MCP configuration and optional Python helpers for checking local campaign ledgers and inventory/budget models. The helpers use no network or credentials. The package installs no executable hooks, local MCP server or database connector. Calculation inputs and results pass between your assistant client and METER. Authentication is handled through OAuth; never put passwords or tokens in prompts or GitHub issues. See [data handling](docs/data-handling.md) and [security reporting](SECURITY.md).

## Development and review

```sh
claude plugin validate .claude-plugin/plugin.json
claude plugin validate .claude-plugin/marketplace.json
python3 scripts/validate-package.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

See [reviewer scenarios](docs/reviewer-guide.md) and [verification evidence](docs/verification.md). This repository contains only the client plugin; hosted METER services and datasets are separate.

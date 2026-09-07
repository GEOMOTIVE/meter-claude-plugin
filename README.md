# METER for Claude

<img src="assets/meter-logo-square.png" alt="METER" width="96">

Plan outdoor advertising with METER in Claude Code and Cowork. Discover OOH/DOOH inventory, calculate projected audience Universe, OTS and Reach, inspect audience profiles, and prepare address-program spreadsheets from validated results.

**Requires an existing METER account with access to the requested tools and countries.** Installing the plugin does not create an account or grant data access. Contact your METER account administrator for access; product information is at [meter.ad](https://meter.ad).

## Install in Claude Code

```text
/plugin marketplace add GEOMOTIVE/meter-claude-plugin
/plugin install meter@meter-plugins
```

Restart Claude Code or run `/reload-plugins`. Open `/mcp`, select the METER server and complete OAuth sign-in if requested. Invoke `/meter:meter` or describe the planning task naturally. If METER is already connected separately, use one connection for the task to avoid ambiguous duplicate tools.

This is METER's own marketplace. Listing in Anthropic's official directory is subject to review; this repository does not claim approval or Anthropic verification.

## Cowork

Use the plugin's released ZIP with Cowork's plugin upload flow, or install from a marketplace supported by your workspace. Complete MCP sign-in when prompted. Availability and installation controls depend on the client and organization settings.

## Try it

- “Find up to three available inventory records in Ташкент. Show their METER IDs, addresses and actual OOH/DOOH classification.”
- “Calculate the audience Universe in Ташкент for ages 20–45, all genders and income abc, for 1–31 August 2026.”
- “Using those exact surface IDs, calculate legacy OTS and Reach for the same audience and period. Label modeled contacts separately from unique audience.”
- “Create an XLSX address program from those results, with a summary and an inventory table.”

Use a city and period covered by your account. Spreadsheet creation depends on file-authoring tools available in your Claude environment; this package does not install a spreadsheet runtime.

## Calculation behavior

There are 16 METER tools. Legacy OTS is used when New OTS coverage is unknown. New OTS availability varies by geography and inventory. A `no_data` result means data is unavailable for that request, not zero; when permitted by the brief, the skill tries legacy once and names the methodology used.

Historical small-scenario API measurements were roughly <1 second for simple queries, 1–3 seconds for selection/legacy calculations, 6–8 seconds for New OTS, and 12–15 seconds for some breakdowns. These exclude OAuth and remote MCP overhead and are not an SLA. See [method timings and limitations](skills/meter/references/performance.md).

## Troubleshooting

- **Needs authentication / HTTP 401:** reconnect METER through `/mcp` and complete OAuth.
- **Access denied / invalid country scope:** ask your METER administrator to check your existing account's tool and country permissions. Installing again does not grant permissions.
- **New OTS no_data:** use legacy if the task permits; do not invent metrics.
- **Timeout:** narrow the inventory/period or try later. Avoid repeating an unchanged request automatically.
- **Incomplete inventory:** finish pagination or narrow the query before producing a final program.

## Data and security

The package contains instructions, branding and one HTTPS MCP configuration. It installs no executable hooks, local MCP server or database connector. Calculation inputs and results pass between Claude and METER. Authentication is handled through OAuth; never put passwords or tokens in prompts or GitHub issues. See [data handling](docs/data-handling.md) and [security reporting](SECURITY.md).

## Development and review

```sh
claude plugin validate .claude-plugin/plugin.json
claude plugin validate .claude-plugin/marketplace.json
python3 scripts/validate-package.py
```

See [reviewer scenarios](docs/reviewer-guide.md) and [verification evidence](docs/verification.md). This repository contains only the client plugin; hosted METER services and datasets are separate.

# Reviewer guide

## Package

Name: METER. Publisher: METER / GEOMOTIVE. Purpose: OOH/DOOH inventory discovery and projected audience calculations. Website: https://meter.ad. Source: https://github.com/GEOMOTIVE/meter-claude-plugin. MCP: https://mcp.meter.ad/meter/mcp (Streamable HTTP, OAuth).

Install following the README and authenticate in the client. A METER account with permission for the selected geography and tools is required. Reviewer account access must be arranged privately with the publisher; this repository intentionally contains no test credentials. Tashkent and the period below are example benchmark conditions, not a guarantee of access for every account.

## Positive cases

1. Ask for up to three inventory records in Ташкент. Expect `meter_query_surfaces`, actual existing IDs/addresses and sourced OOH/DOOH classification. Do not require a particular ID or output count when inventory changes.
2. Request Universe in that city for ages 20–45, all genders, income abc, 1–31 August 2026. Expect `meter_universe` with the requested filters and a clearly labeled projected audience result, or an explicit coverage/access error.
3. Request legacy OTS and Reach using exactly the IDs from case 1 and the audience/period from case 2. Expect `meter_ots_reach`; disclose actual modeled metrics, preserve surface list/period, never sum individual Reach.
4. Request New OTS for an authorized geography. If the server returns `no_data`, expect one equivalent legacy retry with methodology disclosure unless New OTS only was requested. Errors must remain visible.
5. Request an XLSX address program from successful calculations. Expect a real file when authoring tools are available, matching inventory counts, IDs and calculation metadata. Otherwise expect a table and an explicit file-generation limitation.

## Negative cases

- Ask to access an unauthorized country/account. Expect access controls to hold and no identity/country substitution to bypass them.
- Ask to treat 230,400 scheduled plays as measured OTS or unique Reach. Expect the distinction to be explained and a real calculation requested/run.
- Explicitly require New OTS only when coverage is absent. Expect unavailable results; no silent legacy substitution or invented estimate.

## Review boundaries

No ad buying/booking, personal tracking, permit-owner matching or direct database access is shipped. Historical timings are API-only observations, not client performance guarantees. See verification.md for which release checks were actually completed.

## Claude directory submission fields

Prepared on 8 September 2026 for the [official submission form](https://platform.claude.com/plugins/submit). Submission has not been completed.

| Field | Prepared value |
| --- | --- |
| Plugin link | https://github.com/GEOMOTIVE/meter-claude-plugin |
| Path within repository | Leave empty: the Claude plugin is at the repository root |
| Homepage | https://meter.ad |
| Name | METER |
| Tested surface | Claude Code; Claude Cowork has not been tested |
| Privacy policy | https://meter.ad/privacy-policy |
| Contact email | hello@meter.ad, as published on the official website |
| License | Leave the optional field empty; this package has no assigned open-source license |

Suggested description: Plan outdoor advertising with METER: discover OOH/DOOH inventory, calculate projected audience Universe, OTS and Reach, inspect audience profiles, and prepare address programs from validated results. Connects through OAuth and requires a METER account with access to the requested tools and countries. New OTS coverage varies; unavailable results are disclosed, and legacy calculations are used only when the task permits. Spreadsheet export depends on the file-authoring tools available in the client.

Use the five positive cases above as example use cases. Publisher acceptance of Anthropic's Software Directory Terms and privately arranged reviewer access remain required. A validated package is not a submitted or approved listing.

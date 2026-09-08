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

Submitted on 8 September 2026 through the [official submission form](https://platform.claude.com/plugins/submit), after the publisher accepted Anthropic's Software Directory Terms. The [submission list](https://platform.claude.com/plugins/submissions) shows **METER — Submitted and pending review**. This is an application for review, not directory approval or publication.

| Field or reference | Value |
| --- | --- |
| Plugin link | https://github.com/GEOMOTIVE/meter-claude-plugin |
| Path within repository | Leave empty: the Claude plugin is at the repository root |
| Homepage | https://meter.ad |
| Name | METER |
| Submitted platform | Claude Code only; Claude Cowork has not been tested or selected |
| Privacy policy | https://meter.ad/privacy-policy |
| Service terms | https://meter.ad/terms-of-service?lang=en — GEOMOTIVE LTD, verified published on 8 September 2026 |
| Contact email | hello@meter.ad, as published on the official website |
| License | Leave the optional field empty; this package has no assigned open-source license |

Submitted description: Plan outdoor advertising with METER: discover OOH/DOOH inventory, calculate projected audience Universe, OTS and Reach, inspect audience profiles, and prepare address programs from validated results. Connects through OAuth and requires a METER account with access to the requested tools and countries. New OTS coverage varies; unavailable results are disclosed, and legacy calculations are used only when the task permits. Spreadsheet export depends on the file-authoring tools available in the client.

Five example use cases covering inventory, Universe, legacy OTS/Reach, New OTS coverage handling and spreadsheet output were included. The form displayed **Plugin submitted for review** and confirmed receipt. Reviewer correspondence is directed to hello@meter.ad.

The initial form has no field for reviewer credentials. A dedicated testing account with sample data still needs to be arranged privately for functional review, and service-specific privacy coverage needs confirmation. These remain review dependencies under sections 3.A and 3.D of the [Anthropic Software Directory Policy](https://support.claude.com/en/articles/13145358-anthropic-software-directory-policy); sending the initial application does not establish that they are complete. The Terms of Service URL in the table is a verified public reference, not a separate field in the current Claude form.

## Dedicated-account verification

Use the [reviewer test and demo runbook](reviewer-test-runbook.md) for the exact eight prepared OpenAI cases and the recording sequence. These instructions do not establish that a reviewer account has been provisioned or that its tests have passed.

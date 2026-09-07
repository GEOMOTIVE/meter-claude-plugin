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

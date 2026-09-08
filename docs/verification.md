# Release verification

Package checks were performed on 7 September 2026 with Claude Code 2.1.212. A fresh native-plugin OAuth and calculation test passed on 8 September 2026 with Claude Code 2.1.263 and METER 0.2.0.

| Check | Observed result |
| --- | --- |
| Official plugin manifest validation | Passed |
| Official marketplace manifest validation | Passed without warnings |
| Package integrity script | Passed: MCP config, skill frontmatter, component boundaries and Markdown links |
| Independent package review | Passed after restoring benchmark error/accuracy caveats |
| TruffleHog filesystem scan | Zero verified or unverified secrets |
| Clean installation from public GitHub | Passed in an isolated Claude configuration directory |
| Installed package contents | Skill, references, logo and HTTP MCP configuration all present |
| GitHub Actions | Passed on initial publication |
| Private vulnerability reporting | Enabled and verified through GitHub API |
| Public endpoint without credentials | HTTP 401, access remains protected |
| Existing authenticated Claude Code METER connection | Five successful tool responses, HTTP 200 and ok=true |
| Fresh native plugin OAuth | Completed successfully using the public endpoint |
| Fresh native plugin calculations | Four successful responses; positive Universe, OTS and Reach |

## Fresh native plugin test

Claude Code loaded this package through its native plugin mechanism and completed a new OAuth login for `plugin:meter:meter`. Its automatic import of existing Claude account connectors was disabled for the test process using the documented `ENABLE_CLAUDEAI_MCP_SERVERS=false` option. No account settings were changed.

Exactly four calls used the native plugin transport: `meter-meter_status`, `meter-meter_query_surfaces`, `meter-meter_universe` and `meter-meter_ots_reach`. Each returned HTTP 200 and `ok=true`. The inventory query returned three Tashkent surfaces; the calculation used those same IDs, explicitly requested demographic filters, the period 1–31 August 2026 and the legacy method. Universe, OTS and Reach were present and positive. Credentials, account details, surface IDs and metric payloads remain outside this repository.

This establishes the native Claude Code plugin workflow. It does not establish Claude Cowork compatibility, all 16 methods, independent audience-model accuracy or execution of the separately prepared OpenAI reviewer scenarios.

The same native workflow was repeated after the hosted-server release on 8 September. All four responses succeeded. The submitted inputs, returned metric values and five legacy date fields matched the earlier run; echoed service identifiers and top-level response timestamps were removed. The deployed service was healthy before the repeat test.

## Earlier service check

The authenticated test used the existing Claude account's METER connector. Calls completed: `meter_status`, `meter_query_surfaces`, `meter_universe`, `meter_ots_reach` and `meter_ots_reach_by_surface`. A three-surface Tashkent query was followed by audience and legacy calculations with explicitly submitted filters. Universe and legacy calculations returned nonzero values. These are service response checks, not an independent audit of the audience methodology or all 16 tools.

The first non-interactive test exited while the METER connector was still loading. A second test used Claude's tool discovery and completed successfully. Therefore a pending connection must not be reported as a permanent absence of tools.

The legacy response can contain an empty echoed request and calculation-date statistic rows. The test assistant inferred dropped filters from those fields, but that inference is not established by these responses. The routing guide explains this known response limitation; calculation correctness should be checked using controlled input comparisons, not an empty echo alone.

## Remaining review prerequisites

- The fresh Claude Code sign-in and four-call calculation path are verified. Test Claude Cowork separately before listing it as a tested surface.
- Arrange reviewer access privately; no credentials or customer records are published here.
- The official website publishes [privacy information](https://meter.ad/privacy-policy) and the contact hello@meter.ad. Confirm that service policies cover the MCP integration and review any additional directory requirements. No open-source license has been assigned to this package.
- Submit through Anthropic's authenticated submission form. A public repository and passing CI do not constitute directory submission or approval.

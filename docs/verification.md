# Release verification

Checks performed on 7 September 2026 with Claude Code 2.1.212.

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

The authenticated test used the existing Claude account's METER connector. Calls completed: `meter_status`, `meter_query_surfaces`, `meter_universe`, `meter_ots_reach` and `meter_ots_reach_by_surface`. A three-surface Tashkent query was followed by audience and legacy calculations with explicitly submitted filters. Universe and legacy calculations returned nonzero values. These are service response checks, not an independent audit of the audience methodology or all 16 tools.

The first non-interactive test exited while the METER connector was still loading. A second test used Claude's tool discovery and completed successfully. Therefore a pending connection must not be reported as a permanent absence of tools.

The legacy response can contain an empty echoed request and calculation-date statistic rows. The test assistant inferred dropped filters from those fields, but that inference is not established by these responses. The routing guide explains this known response limitation; calculation correctness should be checked using controlled input comparisons, not an empty echo alone.

## Remaining review prerequisites

- Complete a fresh OAuth sign-in for the newly installed plugin and run the reviewer scenarios in that installation. The existing-connector test above does not prove this step.
- Arrange reviewer access privately; no credentials or customer records are published here.
- Finalize the public package license and publisher-approved service privacy/support details.
- Submit through Anthropic's authenticated submission form. A public repository and passing CI do not constitute directory submission or approval.

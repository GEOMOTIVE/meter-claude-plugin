# OpenAI verification

Verified on 7 September 2026 for package 0.2.0. These checks establish package integrity and the tested Codex workflow; they do not establish official directory approval.

## Package and listing

- Codex marketplace registration and installation succeeded with the public HTTPS configuration. CLI 0.153.4 was used for authenticated testing.
- The Codex plugin validator and skill frontmatter validator passed. Generated files match the reviewed public source.
- The submission import validates against OpenAI's current canonical plugins v1 JSON schema. It contains 16 exact public MCP action names, five positive and three negative cases.
- The public endpoint's authenticated tools/list returned 16 methods, all with explicit read-only, non-destructive and closed-world hints and an output schema. Public names use the `meter-meter_` prefix. The retired export and footfall methods are absent.
- Claude and OpenAI manifests, package boundaries and Markdown references are checked by repository scripts. Three ZIP archives are checked for integrity, safe paths, standalone references and reproducible SHA256 hashes.
- A local secret scan found no credentials in the public package. Hosted server code and datasets are not included.

## Authenticated Codex calculation

An installed plugin was exercised in a new ephemeral Codex task using the public MCP endpoint and a legitimately authorized METER account. The older local METER integration was disabled for that task. OAuth credentials and raw result logs were kept outside this repository.

| Public action | Observed result |
| --- | --- |
| meter-meter_status | HTTP 200, successful response |
| meter-meter_query_surfaces | HTTP 200, returned inventory records for the test city |
| meter-meter_universe | HTTP 200, numeric projected Universe |
| meter-meter_ots_reach | HTTP 200, numeric OTS and Reach for returned surface IDs |

The test used a small Tashkent inventory selection, August 2026 dates and demographic filters. It verifies connectivity and returned metrics, not the independent statistical accuracy of the audience model. Some responses do not echo all submitted filters; an absent echo does not establish that the model ignored them. Raw IDs, account details and metric payloads are deliberately not published.

## OAuth and remaining checks

Path-scoped resource discovery and authorization-server discovery return HTTP 200 and advertise PKCE S256. Anonymous MCP initialization returns HTTP 401. The latest tested CLI completed login and reports OAuth authentication. The 401 response currently lacks a WWW-Authenticate discovery challenge; improve this for broader interoperability. Token expiry/refresh and workspace-domain restrictions have not been validated by this run.

ChatGPT's new package connection and the eight reviewer scenarios still need an end-to-end run in the submission/development environment. Existing client integrations and successful Codex calls do not prove that separate ChatGPT setup. Publisher identity, domain verification, public service policies and reviewer access remain required before submission.

A separately reviewed hosted-server patch minimizes discovery fields and successful-response identifiers; 140 source tests pass. It is prepared for review, not deployed. Rescan the hosted descriptors after it is released. No server behavior is changed by installing this client package.

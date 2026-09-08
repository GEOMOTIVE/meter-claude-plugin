# OpenAI verification

Verified on 7 September 2026 for package 0.2.0, with deployment, native client and OpenAI portal checks repeated on 8 September. These checks establish package integrity and the tested workflows; they do not establish official directory approval.

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

On 8 September a draft was created in the OpenAI organization using its verified business identity. The portal completed its own OAuth flow, Scan Tools returned all 16 public methods with their explicit annotations, and the domain challenge completed with **Domain verified**. Listing fields, annotation justifications, starter prompts and all eight reviewer test cases were saved. This verifies portal authentication, discovery and domain ownership, not execution of the eight ChatGPT reviewer scenarios. The directory and composer icons were uploaded and persisted after a page reload. The portal accepted the skill ZIP with SKILL.md at its root and started security scanning; the scan result remains pending. The published service Terms URL was verified and saved. Privacy-policy coverage, dedicated reviewer access, a real demo video and execution of those scenarios with the reviewer account remain outstanding before submission.

The reviewed hosted-server patch was deployed on 8 September after 140 source tests and release validation. Fresh public discovery confirmed all 16 methods, their output schemas and safety annotations, closed input objects, and removal of server-owned selectors and unsupported selection filters. A fresh native Codex session completed status and inventory requests; the documented Cyrillic city name returned an inventory record. A Latin spelling returned an empty selection, so callers should use the catalog's actual city names.

A subsequent release added the optional public domain-verification response and passed all 148 source tests. Independent live checks verified the exact challenge response, rejected neighboring paths and unsupported methods, and confirmed that anonymous MCP initialization still returns HTTP 401. The OpenAI portal then accepted the challenge.

The native Claude plugin repeated the same four-call calculation path after deployment. Inputs, all returned metric values and five legacy date fields matched the pre-release baseline. Echoed internal identifiers and top-level response timestamps were absent. These are controlled compatibility checks, not an independent audit of model accuracy. No server behavior is changed by installing this client package.

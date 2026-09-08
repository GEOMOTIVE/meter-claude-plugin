# OpenAI review findings

## Descriptor review

The reviewed METER MCP wrapper advertises 16 tools. All set explicit readOnlyHint=true, openWorldHint=false and destructiveHint=false. Every tool declares an outputSchema; the shared envelope has a broadly typed data payload, so this is not a complete method-specific result schema.

The exposed operations retrieve inventory and compute audience/media metrics. No placement booking, advertising purchase, external messaging, segment export or permission changes are exposed. Normal operational auditing occurs; readOnly is interpreted here as no user-requested business-state mutation. The reviewer should reconcile that interpretation with OpenAI's wording about logging. Neither destructive nor public-write annotations should be inferred from incidental auditing alone.

The hosted analytics implementation is separate from this wrapper; this preparation is not an audit of every upstream calculation.

## Server preparation

Review identified model-facing fields that are server-owned, a fallback default inconsistent with enforced behavior, and potentially echoed internal identifiers in successful responses. A focused backend patch was deployed on 8 September 2026 to minimize those surfaces while preserving existing authentication, country checks and returned metric values. It also clarifies reporting descriptions and respects requests that require New OTS. Independent review and 140 source tests passed. Fresh public discovery and native-client calls verified the deployed change; controlled before/after calculations retained their metric values and date fields. The package itself does not modify hosted server behavior.

There is no embedded UI in the plugin, so widget CSP is not applicable. The package requests no credentials in tool prompts and carries no account secrets. Service data handling, retention and reviewer account access still need the publisher's confirmation and applicable public policies.

The subsequent domain-verification release passed 148 source tests and independent live checks. The public proof is served only at the exact verification path; the MCP endpoint retains its existing authentication. OpenAI accepted the domain challenge on 8 September 2026.

## OAuth interoperability

Path-scoped resource and authorization-server discovery return valid metadata and advertise PKCE S256. Anonymous MCP calls remain rejected. The public gateway currently returns its 401 without a WWW-Authenticate discovery challenge; current clients can use path discovery, but the header should be improved for compatibility. Do not disable authentication or direct users to an internal service as a workaround.

The OpenAI portal reports enterprise domain restrictions as unavailable: the integration must advertise the required identity scopes and a UserInfo endpoint returning a verified email before claiming this capability. Its ordinary OAuth flow and tool scan succeeded; enterprise restrictions are a separate requirement.

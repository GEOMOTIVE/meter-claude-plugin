# METER for ChatGPT and Codex

Use METER to discover OOH/DOOH inventory, calculate projected Universe, OTS and Reach, and prepare address programs from validated results. A METER account with access to the requested tools and countries is required. Installing this package does not grant service or data access.

## Codex installation

Use a current Codex client (verified with CLI 0.153.4). Add the public marketplace and install its METER plugin:

```sh
codex plugin marketplace add GEOMOTIVE/meter-claude-plugin
codex plugin add meter@meter-public
```

Open a new task after installation so the client loads the current plugin's skills and tools. Complete the normal METER OAuth flow when prompted. In Codex, select the METER plugin from the Plugins UI; do not use Claude-specific slash commands. If you already have an older METER integration, choose one connection for a task so obsolete or duplicate tools are not mistaken for this package.

The configured server is `https://mcp.meter.ad/meter/mcp`. No API key, server process, database access, port forwarding or environment variables are needed for this public package.

## ChatGPT preparation

METER uses the **With MCP** submission path, with the same public endpoint and the bundled skill. Uploading skills alone does not connect the METER service. The publisher must enter the MCP URL, configure OAuth, verify the domain and complete OpenAI review. This repository is not evidence of directory approval.

For a development connection, use ChatGPT's supported custom MCP/plugin setup and complete OAuth. Then attach METER to the conversation and run the prompts below. Access to custom development connections depends on the workspace and account. Do not assume installing the Codex marketplace automatically creates a ChatGPT connection.

## Try it

- “Find up to three inventory records in Ташкент and show their sourced OOH/DOOH classification.”
- “Calculate Universe for ages 20–45, all genders and income abc in that city.”
- “Use those exact IDs to calculate legacy OTS and Reach for 1–31 August 2026. Keep the audience unchanged.”

Use geography covered by your METER account. The skill checks current tool schemas, labels the calculation methodology, treats no_data as unavailable, and only tries legacy fallback when allowed by the request. Spreadsheet creation needs file-authoring tools in the client; otherwise the assistant must say it returned a table, not an XLSX.

See [metric definitions](../skills/meter/references/metrics.md), [routing](../skills/meter/references/api-routing.md), [response-time expectations](../skills/meter/references/performance.md), [data handling](../docs/data-handling.md), and [OpenAI verification evidence](../docs/openai-verification.md).

## Source and support

[Source repository](https://github.com/GEOMOTIVE/meter-claude-plugin). Product and account information: [METER](https://meter.ad). Report non-sensitive package defects through GitHub issues and security issues through private vulnerability reporting. Contact your METER account administrator for data permissions and applicable service privacy terms.

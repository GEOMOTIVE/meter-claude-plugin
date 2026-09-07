# OpenAI submission preparation

METER uses one **With MCP** submission for the shared ChatGPT/Codex directory. The public endpoint is `https://mcp.meter.ad/meter/mcp`; choose **Universal**. Include the METER skill with its references and assets. Do not use an existing connector identifier in place of the server URL.

## Prepared files

- [Submission import JSON](../chatgpt-app-submission.json): proposed listing, actual safety annotations with explanations, five positive and three negative scenarios. Use the portal's import if available, otherwise copy the corresponding fields. The JSON is a preparation artifact, not a submitted application.
- [OpenAI package](../plugins/meter/README.md): installable Codex package and shared instructions.
- [Technical verification](openai-verification.md): observed checks and limits.
- [Review findings](openai-review-findings.md): server metadata and privacy review notes.

Build from reviewed source using `python3 scripts/build-openai-package.py`. Check reproducibility with `python3 scripts/build-openai-package.py --check`. Generate ZIP archives using `python3 scripts/package-releases.py`; upload the skills archive in the **Skills** section of the same **With MCP** draft. The skills archive omits the MCP configuration; enter the endpoint and OAuth settings separately in the portal.

## Portal field guide

| Field | Prepared value or next action |
| --- | --- |
| Name | METER |
| Category | Business / Data & Analytics, according to the portal taxonomy |
| Subtitle | OOH audience and planning |
| Website | https://meter.ad |
| Logo | assets/meter-logo-square.png |
| MCP server URL | https://mcp.meter.ad/meter/mcp |
| Authentication | OAuth authorization code with PKCE S256; discovery metadata under the MCP URL's path |
| Starter prompts | Inventory lookup; Universe calculation; OTS and Reach for selected surfaces |
| Publisher | Select the publisher's verified identity in the owning OpenAI organization |
| Support / Privacy / Terms | Supply publisher-approved public URLs; the technical data-handling note is not a substitute for service policy |
| Availability | Select only supported business regions; inventory geography and listing availability are distinct |
| Reviewer account | Arrange privately, with relevant tool/country access and usable without private-network access or interactive second-factor dependencies |

The submitter needs Apps Management write access. Complete the portal's domain challenge at the exact generated `/.well-known/openai-apps-challenge` URL. Do not invent a challenge token or replace an existing token used by another listing. Then Scan Tools, reconcile the discovered names/annotations with the import JSON and rerun reviewer cases in ChatGPT.

Submit only after server review findings and client tests are resolved. A package validation pass does not establish reviewer account readiness, OAuth interoperability on every client, legal readiness, submission or approval. After approval, publication is a separate action in the portal.

## Current scope

This preparation does not submit the application, select/attest publisher terms, create reviewer credentials, change account permissions, or claim official directory approval. The service remains protected by OAuth and existing METER access controls.

## Official references

- [Submit plugins](https://developers.openai.com/plugins/deploy/submission)
- [Migrate a Claude plugin](https://developers.openai.com/plugins/guides/submit-claude-plugin)
- [Authentication requirements](https://developers.openai.com/plugins/build/auth)
- [MCP review requirements](https://developers.openai.com/plugins/deploy/app-review)

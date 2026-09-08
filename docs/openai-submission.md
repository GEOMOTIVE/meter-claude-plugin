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
| Starter prompts | Inventory lookup; OTS and Reach for selected surfaces; address programs from validated results |
| Publisher | Verified business identity GEOMOTIVE selected in the owning OpenAI organization |
| Support | https://meter.ad, which publishes hello@meter.ad |
| Privacy | https://meter.ad/privacy-policy; confirm that the policy covers the MCP integration |
| Terms | Supply the publisher-approved service terms URL; no public service terms URL has been verified |
| Availability | Select only supported business regions; inventory geography and listing availability are distinct |
| Reviewer account | Arrange privately, with relevant tool/country access and usable without private-network access or interactive second-factor dependencies |

The submitter needs Apps Management write access. Complete the portal's domain challenge at the exact generated `/.well-known/openai-apps-challenge` URL. Do not invent a challenge token or replace an existing token used by another listing. Then Scan Tools, reconcile the discovered names/annotations with the import JSON and rerun reviewer cases in ChatGPT.

Submit only after server review findings and client tests are resolved. A package validation pass does not establish reviewer account readiness, OAuth interoperability on every client, legal readiness, submission or approval. After approval, publication is a separate action in the portal.

## Current scope

On 8 September 2026 a draft was created in the publisher's OpenAI organization using its verified business identity. The portal completed OAuth, discovered all 16 public methods and confirmed **Domain verified** for the public MCP host. Listing text, all 48 annotation justifications, three starter prompts, five positive test cases, three negative test cases and release notes were saved.

The skills archive and listing icons still need uploading. Publisher-approved service terms, confirmation of privacy-policy coverage, dedicated reviewer access with sample data, and execution of the eight ChatGPT reviewer scenarios remain outstanding. Prepared test cases are not evidence that those cases ran in ChatGPT. Directory policy declarations remain unchecked until the publisher confirms them.

The public privacy page identifies METER IT LLC as controller and describes website, contact and service data. It does not explicitly describe the MCP integration's OAuth account information, tool inputs/results or their exchange with the selected AI client. Confirm the applicable coverage and publish accurate service-specific information before review; this repository does not make retention or data-use commitments on the publisher's behalf.

No official OpenAI application has been submitted. Reviewer credentials and permissions have not been changed. The service remains protected by OAuth and existing METER access controls.

## Official references

- [Submit plugins](https://developers.openai.com/plugins/deploy/submission)
- [Migrate a Claude plugin](https://developers.openai.com/plugins/guides/submit-claude-plugin)
- [Authentication requirements](https://developers.openai.com/plugins/build/auth)
- [MCP review requirements](https://developers.openai.com/plugins/deploy/app-review)

# OpenAI submission preparation

METER uses one **With MCP** submission for the shared ChatGPT/Codex directory. The public endpoint is `https://mcp.meter.ad/meter/mcp`; choose **Universal**. Include the METER skill with its references and assets. Do not use an existing connector identifier in place of the server URL.

## Prepared files

- [Submission import JSON](../chatgpt-app-submission.json): proposed listing, actual safety annotations with explanations, five positive and three negative scenarios. Use the portal's import if available, otherwise copy the corresponding fields. The JSON is a preparation artifact, not a submitted application.
- [OpenAI package](../plugins/meter/README.md): installable Codex package and shared instructions.
- [Technical verification](openai-verification.md): observed checks and limits.
- [Reviewer test and demo runbook](reviewer-test-runbook.md): the eight submission prompts, acceptance criteria and recording sequence; dedicated-account execution is still pending.
- [Review findings](openai-review-findings.md): server metadata and privacy review notes.

Build from reviewed source using `python3 scripts/build-openai-package.py`. Check reproducibility with `python3 scripts/build-openai-package.py --check`. Generate ZIP archives using `python3 scripts/package-releases.py`; upload the skills archive in the **Skills** section of the same **With MCP** draft. The skills archive contains `SKILL.md` at its root and the skill’s unchanged `references/` directory. The portal did not attach the previous archive with a Codex plugin wrapper. Enter the endpoint and OAuth settings separately in the portal; use the Codex archive for local plugin installation.

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
| Terms | https://meter.ad/terms-of-service?lang=en — published, verified against the approved English text and saved in the draft on 8 September 2026 |
| Availability | Select only supported business regions; inventory geography and listing availability are distinct |
| Reviewer account | Dedicated demo account with sample data only; include login URL, tenant/workspace, username, password and steps in the private portal field. No real user account, production customer data, MFA, email/SMS verification or private-network dependency. |
| Demo recording | Required by the current form; provide a reviewer-accessible video of the plugin functioning in Developer Mode |

The submitter needs Apps Management write access. Complete the portal's domain challenge at the exact generated `/.well-known/openai-apps-challenge` URL. Do not invent a challenge token or replace an existing token used by another listing. Then Scan Tools, reconcile the discovered names/annotations with the import JSON and rerun reviewer cases in ChatGPT.

Submit only after server review findings and client tests are resolved. A package validation pass does not establish reviewer account readiness, OAuth interoperability on every client, legal readiness, submission or approval. After approval, publication is a separate action in the portal.

## Current scope

On 8 September 2026 a draft was created in the publisher's OpenAI organization using its verified business identity. The portal completed OAuth, discovered all 16 public methods and confirmed **Domain verified** for the public MCP host. Listing text, all 48 annotation justifications, three starter prompts, five positive test cases, three negative test cases and release notes were saved.

The publisher approved and published the GEOMOTIVE LTD service terms on 8 September 2026. The public English text was checked against the approved edition: all 59 clauses match. The terms URL above was saved in the OpenAI draft and remained present after reloading the form.

The directory and composer icons were uploaded, and their light/dark previews persisted after reloading the form. The portal accepted the corrected skill archive with `SKILL.md` at the root and started its safety/security scan. It reports that scanning may take up to two hours; acceptance of the upload is not a passed scan. The uploaded archive SHA-256 is `1da3ac3a4689595fed1cbf0b0d5d0fdcbe52db14705891ff6d117667a2da0b9e`. Its instructions are unchanged; the performance reference now links to the public verification report by HTTPS so the skill remains standalone. The archive is byte-identical to the generated skill source, and all relative links are checked inside each archive.

On the latest visit, the Submit page showed all policy declarations already checked; this continuation did not change them. The form explicitly blocks **Submit for Review** because **Demo recording URL is required** and **Test credentials is required**. These form checks do not establish that all substantive review requirements are met. Approval of METER's service terms is separate from agreement with directory terms.

Confirmation of privacy-policy coverage, dedicated reviewer access with sample data, a demo recording, and execution of the reviewer scenarios on the supported ChatGPT/Codex surfaces remain outstanding. All supplied cases must also be run with the dedicated reviewer account. Prepared test cases and native-client checks using the owner's account are not evidence of reviewer readiness.

The public privacy page was rechecked on 8 September: it still identifies METER IT LLC as controller and describes website, contact and service data. It does not explicitly describe the MCP integration's OAuth account information, tool inputs/results or their exchange with the selected AI client. Explain the applicable roles of METER IT LLC and GEOMOTIVE LTD and publish accurate service-specific information before review; this repository does not infer controller roles or make retention or data-use commitments on the publisher's behalf.

No official OpenAI application has been submitted. Reviewer credentials and permissions have not been changed. The service remains protected by OAuth and existing METER access controls.

## Official references

- [Submit plugins](https://developers.openai.com/plugins/deploy/submission)
- [Migrate a Claude plugin](https://developers.openai.com/plugins/guides/submit-claude-plugin)
- [Authentication requirements](https://developers.openai.com/plugins/build/auth)
- [MCP review requirements](https://developers.openai.com/plugins/deploy/app-review)

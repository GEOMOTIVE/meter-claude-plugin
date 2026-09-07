# Data handling for the METER plugin

The public package includes Markdown instructions, images, and the MCP endpoint configuration. It contains no credentials and runs no install/startup hooks. It adds no separate telemetry or local database.

When the assistant calls METER, the tool arguments can include city/country, campaign dates, surface IDs, audience filters and broadcast parameters. METER returns inventory information and modeled aggregate media metrics to the assistant. The OAuth flow connects the user to their METER account and its existing permissions. Do not include individual-level sensitive data or credentials in prompts or tool arguments.

Conversation data is handled according to your client provider's applicable policies and your plan/settings (Anthropic for Claude; OpenAI for ChatGPT and Codex). METER service processing is governed by your METER service agreement and applicable service privacy terms. This package does not establish or change those terms, promise a retention period, or claim that hosted systems do not log requests. Ask your METER account administrator for the applicable service privacy policy and data-processing terms before use.

Local exports are created by the client tools the user chooses. The skill does not instruct automatic upload to third-party services. Public GitHub issues are suitable only for non-sensitive package defects. Use the private security reporting channel for security issues.

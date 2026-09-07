#!/usr/bin/env python3
"""Validate distribution integrity without credentials or network access."""
from pathlib import Path
import json
import re

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / ".claude-plugin/plugin.json").read_text())
marketplace = json.loads((root / ".claude-plugin/marketplace.json").read_text())
mcp = json.loads((root / ".mcp.json").read_text())
assert manifest["name"] == "meter"
assert re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"])
assert marketplace["plugins"][0]["source"] == "./"
assert marketplace["plugins"][0]["name"] == manifest["name"]
assert mcp == {"mcpServers": {"meter": {"type": "http", "url": "https://mcp.meter.ad/meter/mcp"}}}
assert not any((root / name).exists() for name in ["hooks", "node_modules", "src", ".env"])
for path in root.rglob("*.md"):
    if ".git" in path.parts:
        continue
    text = path.read_text()
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
        if "://" in target or target.startswith("#"):
            continue
        linked = (path.parent / target.split("#")[0]).resolve()
        assert linked.is_relative_to(root), (path, target, "outside package")
        assert linked.exists(), (path, target, "missing reference")
    assert not re.search(r"localhost|userKey|user_key|\b[a-z0-9]+(?:-[a-z0-9]+)*-cluster\b|ClickHouse|OpenFGA|LiteLLM", text), path
openai_market = json.loads((root / ".agents/plugins/marketplace.json").read_text())
assert openai_market["name"] == "meter-public"
entry = openai_market["plugins"][0]
assert entry["source"] == {"source": "local", "path": "./plugins/meter"}
assert entry["policy"] == {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}
openai_manifest = json.loads((root / "plugins/meter/.codex-plugin/plugin.json").read_text())
assert openai_manifest["version"] == manifest["version"]
assert openai_manifest["interface"]["capabilities"] == ["Read"]
assert openai_manifest["mcpServers"] == "./.mcp.json"
submission = json.loads((root / "chatgpt-app-submission.json").read_text())
assert len(submission["tools"]) == 16
assert len(submission["test_cases"]) == 5
assert len(submission["negative_test_cases"]) == 3
assert len(submission["app_info"]["subtitle"]) <= 30
for tool in submission["tools"].values():
    assert set(tool["annotations"]) == {"readOnlyHint", "openWorldHint", "destructiveHint"}
    assert all(type(v) is bool for v in tool["annotations"].values())
    assert set(tool["justifications"]) == {"read_only_justification", "open_world_justification", "destructive_justification"}
for case in submission["test_cases"]:
    assert all(name.strip() in submission["tools"] for name in case["tools_triggered"].split(","))
skill = (root / "skills/meter/SKILL.md").read_text()
assert skill.startswith("---\nname: meter\n")
assert "description:" in skill.split("---", 2)[1]
print("PASS: manifests, HTTPS-only MCP configuration, component boundaries, skill frontmatter and all Markdown references")

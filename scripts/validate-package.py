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
    assert not re.search(r"localhost|userKey|user_key|new-geom-cluster|ClickHouse|OpenFGA|LiteLLM", text), path
skill = (root / "skills/meter/SKILL.md").read_text()
assert skill.startswith("---\nname: meter\n")
assert "description:" in skill.split("---", 2)[1]
print("PASS: manifests, HTTPS-only MCP configuration, component boundaries, skill frontmatter and all Markdown references")

#!/usr/bin/env python3
"""Verify the files installed by the Codex CLI against the generated package."""
from pathlib import Path
import argparse
import json
import os

root = Path(__file__).resolve().parents[1]
source = root / "plugins/meter"
version = json.loads((source / ".codex-plugin/plugin.json").read_text())["version"]
parser = argparse.ArgumentParser()
parser.add_argument("--installed-root", type=Path, help="Override the installed package directory for a fixture")
args = parser.parse_args()
codex_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
installed = args.installed_root or codex_home / "plugins/cache/meter-public/meter" / version
assert installed.is_dir(), f"Installed METER {version} package not found: {installed}"
expected = {str(p.relative_to(source)): p.read_bytes() for p in source.rglob("*") if p.is_file()}
for name, content in expected.items():
    actual = installed / name
    assert actual.is_file(), (name, "missing installed file")
    assert actual.read_bytes() == content, (name, "installed content differs from generated package")
for directory in ("skills", "assets"):
    expected_names = {name for name in expected if name.startswith(directory + "/")}
    actual_names = {str(p.relative_to(installed)) for p in (installed / directory).rglob("*") if p.is_file()}
    assert actual_names == expected_names, (directory, "missing or stale installed resources")
manifest = json.loads((installed / ".codex-plugin/plugin.json").read_text())
assert manifest["skills"] == "./skills/"
assert (installed / manifest["mcpServers"]).read_bytes() == (source / ".mcp.json").read_bytes()
print(f"PASS: installed METER {version}, {len(expected)} files, skill routing and MCP configuration match the generated package")

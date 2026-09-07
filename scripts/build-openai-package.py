#!/usr/bin/env python3
"""Build the OpenAI package from the reviewed public client files only."""
from pathlib import Path
import argparse
import json
import shutil

root = Path(__file__).resolve().parents[1]
target = root / "plugins/meter"
args = argparse.ArgumentParser()
args.add_argument("--check", action="store_true", help="Fail when committed generated files differ")
check = args.parse_args().check
source_manifest = json.loads((root / ".claude-plugin/plugin.json").read_text())
manifest = {k: source_manifest[k] for k in ("name", "version", "description", "author", "homepage", "repository", "keywords")}
manifest.update({
    "skills": "./skills/",
    "mcpServers": "./.mcp.json",
    "interface": {
        "displayName": "METER",
        "shortDescription": "OOH audience and planning",
        "longDescription": "Discover outdoor advertising inventory and calculate projected Universe, OTS and Reach with METER. Requires an authorized METER account. Create address-program files when the client supports file authoring.",
        "developerName": "METER",
        "category": "Data & Analytics",
        "capabilities": ["Read"],
        "websiteURL": "https://meter.ad",
        "defaultPrompt": [
            "Find OOH/DOOH inventory in my campaign city.",
            "Calculate OTS and Reach for my selected surfaces.",
            "Prepare an address program from validated METER results."
        ],
        "brandColor": "#390050",
        "composerIcon": "./assets/meter-logo-square.png",
        "logo": "./assets/meter-logo-square.png"
    }
})
# Only include publisher-approved optional fields when supplied in the source.
if "license" in source_manifest:
    manifest["license"] = source_manifest["license"]
expected = {
    ".codex-plugin/plugin.json": (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode(),
    ".mcp.json": (root / ".mcp.json").read_bytes(),
}
for directory in ("skills", "assets"):
    for path in sorted((root / directory).rglob("*")):
        if path.is_symlink():
            raise ValueError("Symlinks are not accepted in the distribution source")
        if path.is_file():
            expected[str(path.relative_to(root))] = path.read_bytes()
for name in ("NOTICE", "SECURITY.md", "docs/data-handling.md", "docs/verification.md", "docs/openai-verification.md"):
    expected[name] = (root / name).read_bytes()
expected["README.md"] = (root / "docs/openai-package.md").read_text().replace("(../", "(").encode()
if (root / "LICENSE").exists():
    expected["LICENSE"] = (root / "LICENSE").read_bytes()
actual = {str(p.relative_to(target)): p.read_bytes() for p in target.rglob("*") if p.is_file()} if target.exists() else {}
if check:
    changed = sorted(k for k in set(expected) | set(actual) if expected.get(k) != actual.get(k))
    if changed:
        raise SystemExit("Generated OpenAI package differs: " + ", ".join(changed))
    print("PASS: generated OpenAI package matches the reviewed source")
else:
    if target.exists():
        shutil.rmtree(target)
    for name, content in expected.items():
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    print(f"Built OpenAI package: {len(expected)} files")

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
submission = json.loads((root / "chatgpt-app-submission.json").read_text())
version_file = root / "skills/meter/references/package-version.json"
version_bytes = (json.dumps({"schema_version": 1, "package": "meter@meter-public", "version": source_manifest["version"]}, indent=2) + "\n").encode()
if check:
    if not version_file.is_file() or version_file.read_bytes() != version_bytes:
        raise SystemExit("Skill package-version.json differs from the source manifest")
else:
    version_file.write_bytes(version_bytes)
manifest = {k: source_manifest[k] for k in ("name", "version", "description", "author", "homepage", "repository", "keywords")}
manifest["description"] = "Plan outdoor advertising with METER: discover OOH/DOOH inventory, calculate projected audience, OTS and Reach, and prepare address programs."
manifest.update({
    "skills": "./skills/",
    "mcpServers": "./.mcp.json",
    "interface": {
        "displayName": "METER",
        "shortDescription": "OOH audience and planning",
        "longDescription": "METER helps media planners discover OOH/DOOH inventory, calculate projected audience Universe, OTS and Reach, and prepare address programs from validated results. A connected METER account with access to the requested country is required. New OTS coverage varies; unavailable results are disclosed and legacy is used only when the task permits. Spreadsheet exports require file-authoring tools in the client. METER does not book or purchase advertising placements.",
        "developerName": "GEOMOTIVE",
        "category": "Data & Analytics",
        "capabilities": ["Read"],
        "websiteURL": "https://meter.ad",
        "supportURL": "https://meter.ad",
        "privacyPolicyURL": "https://meter.ad/privacy-policy",
        "termsOfServiceURL": "https://meter.ad/terms-of-service?lang=en",
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
# Review scenarios are public instructions, not evidence of a passed replay.
# Credentials and the demo recording URL remain in the secure publisher portal.
def review_case(case):
    result = {"description": case["description"], "prompt": case["user_prompt"],
              "expected_behavior": case["expected_output"]}
    if case.get("tools_triggered"):
        result["tools_triggered"] = case["tools_triggered"]
    return result

manifest["extensions"] = {"com.openai": {"review": {"test_cases": {
    "positive": [review_case(case) for case in submission["test_cases"]],
    "negative": [review_case(case) for case in submission["negative_test_cases"]],
}}}}
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

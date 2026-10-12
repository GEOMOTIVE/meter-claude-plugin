#!/usr/bin/env python3
"""Create bounded archives from reviewed public files; never archive the checkout wholesale."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import sys
import zipfile

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output-dir", type=Path, default=root / "dist")
parser.add_argument("--chatgpt-name", default="meter", help="Existing publisher plugin name; keep its identity on updates")
args = parser.parse_args()
if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", args.chatgpt_name):
    parser.error("--chatgpt-name must be a lowercase plugin slug")
subprocess.run([sys.executable, str(root / "scripts/build-openai-package.py"), "--check"], check=True)
subprocess.run([sys.executable, str(root / "scripts/validate-package.py")], check=True)
version = json.loads((root / ".claude-plugin/plugin.json").read_text())["version"]
out = args.output_dir.resolve()
out.mkdir(parents=True, exist_ok=True)
openai = root / "plugins/meter"
codex_files = {str(p.relative_to(openai)): p for p in openai.rglob("*") if p.is_file()}
# Keep the standalone skill archive for clients that accept skills only.
# The current OpenAI publisher portal accepts the complete Codex archive.
skill_root = openai / "skills/meter"
skills_files = {str(p.relative_to(skill_root)): p for p in skill_root.rglob("*") if p.is_file()}
claude_files = {}
for directory in ("skills", "assets", "docs"):
    for p in (root / directory).rglob("*"):
        if p.is_file():
            claude_files[str(p.relative_to(root))] = p
for name in (".claude-plugin/plugin.json", ".mcp.json", "README.md", "NOTICE", "SECURITY.md", "chatgpt-app-submission.json"):
    claude_files[name] = root / name
# Root README links to the generated package; include that public package, never .git or private files.
for name, p in codex_files.items():
    claude_files["plugins/meter/" + name] = p
hashes = {}
for label, files in (("codex", codex_files), ("chatgpt", codex_files), ("openai-skills", skills_files), ("claude", claude_files)):
    archive = out / f"meter-{label}-{version}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, p in sorted(files.items()):
            content = p.read_bytes()
            if label == "chatgpt" and name == ".codex-plugin/plugin.json":
                manifest = json.loads(content)
                manifest["name"] = args.chatgpt_name
                content = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
            info = zipfile.ZipInfo(name, (2026, 9, 7, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, content)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        if label == "openai-skills":
            assert "SKILL.md" in z.namelist(), "Portal upload requires a skill at the archive root"
            assert set(z.namelist()) == set(skills_files)
            for name, source in skills_files.items():
                assert z.read(name) == source.read_bytes(), (name, "skill content changed during packaging")
    hashes[archive.name] = hashlib.sha256(archive.read_bytes()).hexdigest()
(out / "SHA256SUMS").write_text("".join(f"{digest}  {name}\n" for name, digest in hashes.items()))
print(json.dumps(hashes, indent=2))

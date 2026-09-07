#!/usr/bin/env python3
"""Check standalone archives, their references, and reproducible builds."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import posixpath
import re
import subprocess
import sys
import zipfile

root = Path(__file__).resolve().parents[1]
version = json.loads((root / ".claude-plugin/plugin.json").read_text())["version"]
archives = [root / "dist" / f"meter-{kind}-{version}.zip" for kind in ("codex", "openai-skills", "claude")]
hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in archives}
for archive in archives:
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        assert len(names) == len(set(names)), "duplicate archive entries"
        assert z.testzip() is None
        for name in names:
            assert not name.startswith("/") and ".." not in PurePosixPath(name).parts
            assert not any(part in (".git", ".env", "node_modules", "src", "hooks") for part in PurePosixPath(name).parts)
            if name.endswith(".md"):
                for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", z.read(name).decode()):
                    if "://" in link or link.startswith("#"):
                        continue
                    target = posixpath.normpath(posixpath.join(posixpath.dirname(name), link.split("#")[0]))
                    assert target in names, (archive.name, name, link)
        if "openai-skills" in archive.name:
            assert ".mcp.json" not in names
            assert "mcpServers" not in json.loads(z.read(".codex-plugin/plugin.json"))
        else:
            assert json.loads(z.read(".mcp.json"))["mcpServers"]["meter"]["url"] == "https://mcp.meter.ad/meter/mcp"
subprocess.run([sys.executable, str(root / "scripts/package-releases.py")], check=True, stdout=subprocess.DEVNULL)
assert hashes == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in archives}
print("PASS: 3 standalone archives, safe paths, complete references and reproducible SHA256 hashes")

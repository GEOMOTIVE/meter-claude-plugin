#!/usr/bin/env python3
"""Probe public OAuth discovery without credentials or calculation requests."""
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

origin = "https://mcp.meter.ad"
resource = origin + "/meter/mcp"
issuer = origin + "/meter"

def fetch(url, body=None):
    request = Request(url, data=None if body is None else json.dumps(body).encode(), headers={
        "Accept": "application/json, text/event-stream", "Content-Type": "application/json",
    })
    try:
        response = urlopen(request, timeout=30)
    except HTTPError as error:
        response = error
    with response:
        return response.status, response.headers, response.read()

status, headers, _ = fetch(resource, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
    "protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "meter-public-preflight", "version": "0.2.0"},
}})
assert status == 401, f"Anonymous MCP initialization must require authentication; got {status}"
status, _, body = fetch(origin + "/.well-known/oauth-protected-resource/meter/mcp")
assert status == 200
metadata = json.loads(body)
assert metadata["resource"] == resource
assert issuer in metadata["authorization_servers"]
status, _, body = fetch(origin + "/.well-known/oauth-authorization-server/meter")
assert status == 200
metadata = json.loads(body)
assert metadata["issuer"] == issuer
assert "S256" in metadata["code_challenge_methods_supported"]
for field in ("authorization_endpoint", "token_endpoint", "registration_endpoint"):
    assert metadata[field].startswith(issuer + "/"), field
print("PASS: anonymous calls rejected; path-scoped OAuth discovery and PKCE S256 available")
if not headers.get("WWW-Authenticate"):
    print("FOLLOW-UP: the 401 response lacks a WWW-Authenticate discovery challenge; path discovery works")
print("This probe does not verify login, token refresh, tool access or calculation results.")

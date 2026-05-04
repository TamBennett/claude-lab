# MCP Research Notes

- MCP = Model Context Protocol, open standard from Anthropic
- Two transports: stdio (local) and SSE (remote/shared)
- Filesystem MCP is the canonical first example
- Enterprise use case: scope Claude's access to specific directories only
- Gotcha: full binary path required on macOS with Homebrew

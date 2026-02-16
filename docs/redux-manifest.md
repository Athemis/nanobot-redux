# Nanobot Redux Manifest

## What This Is

`nanobot redux` is my personal fork of nanobot. I maintain it in my free time and tune it to my own needs and workflows. It's not a professional product—just a hobby project that works the way I want it to.

## Contributions

Contributions are welcome! However, I'll only integrate features that I can personally use or at least test myself. For example, I won't add support for obscure chat platforms I can't validate. If you need something I can't test, feel free to maintain your own fork.

## What Stays Stable

I try to keep these compatible so I don't break my own setup:

- CLI stays `nanobot`
- Python package stays `nanobot.*`
- Config lives in `~/.nanobot/*`

## Current Priorities

These drive what I work on and maintain, but they're not set in stone:

- Keep channels stable, debuggable, and easy to self-host
- Make sure providers work in real-world scenarios (local, VPN, corporate networks)
- Treat web search as configurable plumbing—local and federated options matter
- Only build tools I actually use regularly and want to support
- Add safety guards on anything that touches sensitive files or runs commands

## What I've Pulled from Upstream

Features I've adopted because they solved real problems for me:

- `HKUDS#420` Matrix channel
- `HKUDS#151` OpenAI Codex OAuth
- `HKUDS#398` Multi-provider web search including SearXNG
- `HKUDS#564` `delete_file` tool with symlink protection
- `HKUDS#555` shell security hardening

## How I Decide What to Adopt

When looking at upstream changes, I ask:

- Does it improve something I care about?
- Is the security risk acceptable?
- Am I willing to maintain it?
- Does it break my existing setup?

## Versioning

- Separate version line from upstream (PEP 440 compliant)
- Started at `0.2.0`
- I release when things feel stable, no fixed schedule
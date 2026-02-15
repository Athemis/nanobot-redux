<div align="center">
  <img src="squidbot_logo.webp" alt="squidbot" width="500">
  <h1>squidbot: Ultra-Lightweight Personal AI Assistant</h1>
  <p>
    <a href="https://pypi.org/project/squidbot-ai/"><img src="https://img.shields.io/pypi/v/squidbot-ai" alt="PyPI"></a>
    <a href="https://pepy.tech/project/squidbot-ai"><img src="https://static.pepy.tech/badge/squidbot-ai" alt="Downloads"></a>
    <img src="https://img.shields.io/badge/python-≥3.11-blue" alt="Python">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
    <a href="./COMMUNICATION.md"><img src="https://img.shields.io/badge/WeChat-Group-C5EAB4?style=flat&logo=wechat&logoColor=white" alt="WeChat"></a>
  </p>
</div>

🦑 **squidbot** is an **ultra-lightweight** personal AI assistant inspired by [OpenClaw](https://github.com/openclaw/openclaw) and based on [nanobot](https://github.com/HKUDS/nanobot).

⚡️ Delivers core agent functionality in just **~4,000** lines of code — **99% smaller** than Clawdbot's 430k+ lines.

📏 Real-time line count: **4,133 lines** (run `bash core_agent_lines.sh` to verify anytime)

## 📢 News

- **2026-02-14** 🔌 squidbot now supports MCP! See [MCP section](#mcp-model-context-protocol) for details.
- **2026-02-13** 🎉 Released v0.1.3.post7 — includes security hardening and multiple improvements. All users are recommended to upgrade to the latest version. See [release notes](https://github.com/HKUDS/squidbot/releases/tag/v0.1.3.post7) for more details.
- **2026-02-12** 🧠 Redesigned memory system — Less code, more reliable. Join the [discussion](https://github.com/HKUDS/squidbot/discussions/566) about it!
- **2026-02-11** ✨ Enhanced CLI experience and added MiniMax support!
- **2026-02-10** 🎉 Released v0.1.3.post6 with improvements! Check the updates [notes](https://github.com/HKUDS/squidbot/releases/tag/v0.1.3.post6) and our [roadmap](https://github.com/HKUDS/squidbot/discussions/431).
- **2026-02-08** 🔧 Refactored Providers—adding a new LLM provider now takes just 2 simple steps! Check [here](#providers).
- **2026-02-07** 🚀 Released v0.1.3.post5 with Qwen support & several key improvements! Check [here](https://github.com/HKUDS/squidbot/releases/tag/v0.1.3.post5) for details.
- **2026-02-04** 🚀 Released v0.1.3.post4 with multi-provider & Docker support! Check [here](https://github.com/HKUDS/squidbot/releases/tag/v0.1.3.post4) for details.
- **2026-02-03** ⚡ Integrated vLLM for local LLM support and improved natural language task scheduling!
- **2026-02-02** 🎉 squidbot officially launched! Welcome to try 🦑 squidbot!

## Key Features of squidbot:

🪶 **Ultra-Lightweight**: Just ~4,000 lines of core agent code — 99% smaller than Clawdbot.

🔬 **Research-Ready**: Clean, readable code that's easy to understand, modify, and extend for research.

⚡️ **Lightning Fast**: Minimal footprint means faster startup, lower resource usage, and quicker iterations.

💎 **Easy-to-Use**: One-click to deploy and you're ready to go.

## 🏗️ Architecture

```mermaid
flowchart LR
    subgraph channels["Channels"]
        cli["CLI (direct)"]
        matrix["Matrix (Element)"]
        email["Email (IMAP/SMTP)"]
    end

    subgraph runtime["Runtime"]
        bus["Message Bus"]
        cm["ChannelManager\n(outbound dispatcher)"]
        loop["Agent Loop"]
        llm["LLM"]
        tools["Tool Registry"]
    end

    subgraph ctx["Context"]
        mem["Memory"]
        skills["Skills"]
    end

    subgraph toolsrc["Tool Sources"]
        builtin["Built-in Tools\nfile, shell, web, cron, message, spawn"]
        mcp["MCP Servers\nstdio / HTTP"]
    end

    matrix --> bus
    email --> bus
    bus <--> loop
    bus --> cm
    cm --> matrix
    cm --> email

    cli <--> loop

    loop <--> llm
    loop <-->|tool calls/results| tools

    builtin --> tools
    mcp --> tools

    mem <--> loop
    skills --> loop
```

### Runtime Flow

```mermaid
sequenceDiagram
    participant U as User
    participant CLI as CLI Command
    participant C as Channel (Matrix/Email)
    participant CM as ChannelManager
    participant B as Message Bus
    participant A as Agent Loop
    participant L as LLM
    participant T as Tool Registry
    participant M as MCP Server

    opt CLI direct mode
        U->>CLI: squidbot agent -m "..."
        CLI->>A: process_direct(...)
    end

    opt Gateway channel mode
        U->>C: message
        C->>B: InboundMessage
        B->>A: consume_inbound()
    end

    A->>A: build context (history + memory + skills)
    A->>L: chat(context + tools)
    L-->>A: response / tool calls

    loop tool-call loop
        A->>T: execute(tool, args)
        alt built-in tool
            T-->>A: result
        else MCP-provided tool
            T->>M: call_tool(...)
            M-->>T: result
            T-->>A: result
        end
        opt message tool used
            T->>B: publish_outbound(...)
            CM->>B: consume_outbound()
            CM->>C: channel.send(...)
            C-->>U: intermediate message
        end
        A->>L: continue with tool result
        L-->>A: next step / final answer
    end

    opt Gateway channel mode
        A->>B: OutboundMessage
        CM->>B: consume_outbound()
        CM->>C: channel.send(...)
        C-->>U: response
    end

    opt CLI direct mode
        A-->>CLI: final response
        CLI-->>U: print response
    end
```

## 📦 Install

**Install from source** (latest features, recommended for development)

```bash
git clone https://github.com/Athemis/squidbot.git
cd squidbot
pip install -e .
```

**Install with [uv](https://github.com/astral-sh/uv)** (stable, fast)

```bash
uv tool install squidbot-ai
```

**Install from PyPI** (stable)

```bash
pip install squidbot-ai
```

## 🚀 Quick Start

> [!TIP]
> Set your API key in `~/.squidbot/config.json`.
> Get API keys: [OpenRouter](https://openrouter.ai/keys) (Global) · [DashScope](https://dashscope.console.aliyun.com) (Qwen) · [Brave Search](https://brave.com/search/api/) or [Tavily](https://tavily.com/) (optional, for web search). SearXNG is supported via a base URL.

**1. Initialize**

```bash
squidbot onboard
```

**2. Configure** (`~/.squidbot/config.json`)

Add or merge these **two parts** into your config (other options have defaults).

*Set your API key* (e.g. OpenRouter, recommended for global users):
```json
{
  "providers": {
    "openrouter": {
      "apiKey": "sk-or-v1-xxx"
    }
  }
}
```

*Set your model*:
```json
{
  "agents": {
    "defaults": {
      "model": "anthropic/claude-opus-4-5"
    }
  }
}
```

`squidbot onboard` seeds OpenRouter attribution headers by default; set `providers.openrouter.extraHeaders` to `{}` to opt out.
**Optional: Web search provider** — set `tools.web.search.provider` to `brave` (default), `duckduckgo`, `tavily`, or `searxng`. See [docs/web-search.md](docs/web-search.md) for full configuration.

```json
{
  "tools": {
    "web": {
      "search": {
        "provider": "tavily",
        "apiKey": "tvly-..."
      }
    }
  }
}
```

**3. Chat**

```bash
squidbot agent
```

That's it! You have a working AI assistant in 2 minutes.

## 💬 Chat Apps

Talk to your squidbot through Matrix (Element) or Email — anytime, anywhere.

| Channel              | Setup                              |
| -------------------- | ---------------------------------- |
| **Matrix (Element)** | Medium (homeserver + access token) |
| **Email**            | Medium (IMAP/SMTP credentials)     |

<details>
<summary><b>Matrix (Element)</b></summary>

Uses Matrix sync via `matrix-nio` (inbound media + outbound file attachments).

**1. Create/choose a Matrix account**

- Create or reuse a Matrix account on your homeserver (for example `matrix.org`).
- Confirm you can log in with Element.

**2. Get credentials**

- You need:
  - `userId` (example: `@squidbot:matrix.org`)
  - `accessToken`
  - `deviceId` (recommended so sync tokens can be restored across restarts)
- You can obtain these from your homeserver login API (`/_matrix/client/v3/login`) or from your client's advanced session settings.

**3. Configure**

```json
{
  "channels": {
    "matrix": {
      "enabled": true,
      "homeserver": "https://matrix.org",
      "userId": "@squidbot:matrix.org",
      "accessToken": "syt_xxx",
      "deviceId": "SQUIDBOT01",
      "e2eeEnabled": true,
      "allowFrom": [],
      "groupPolicy": "open",
      "groupAllowFrom": [],
      "allowRoomMentions": false,
      "maxMediaBytes": 20971520
    }
  }
}
```

> `allowFrom`: Empty allows all senders; set user IDs to restrict access.
> `groupPolicy`: `open`, `mention`, or `allowlist`.
> `groupAllowFrom`: Room allowlist used when `groupPolicy` is `allowlist`.
> `allowRoomMentions`: If `true`, accepts `@room` (`m.mentions.room`) in mention mode.
> `e2eeEnabled`: Enables Matrix E2EE support (default `true`); set `false` only for plaintext-only setups.
> `maxMediaBytes`: Max attachment size in bytes (default `20MB`) for inbound and outbound media handling; set to `0` to block all inbound and outbound attachment uploads.

> [!NOTE]
> Matrix E2EE implications:
>
> - Keep a persistent `matrix-store` and stable `deviceId`; otherwise encrypted session state can be lost after restart.
> - In newly joined encrypted rooms, initial messages may fail until Olm/Megolm sessions are established.
> - With `e2eeEnabled=false`, encrypted room messages may be undecryptable and E2EE send safeguards are not applied.
> - With `e2eeEnabled=true`, the bot sends with `ignore_unverified_devices=true` (more compatible, less strict than verified-only sending).
> - Changing `accessToken`/`deviceId` effectively creates a new device and may require session re-establishment.
> - Outbound attachments are sent from `OutboundMessage.media`.
> - Effective media limit (inbound + outbound) uses the stricter value of local `maxMediaBytes` and homeserver `m.upload.size` (if advertised).
> - If `tools.restrictToWorkspace=true`, Matrix outbound attachments are limited to files inside the workspace.

**4. Run**

```bash
squidbot gateway
```

</details>

<details>
<summary><b>Email</b></summary>

Give squidbot its own email account. It polls **IMAP** for incoming mail and replies via **SMTP** — like a personal email assistant.

**1. Get credentials (Gmail example)**
- Create a dedicated Gmail account for your bot (e.g. `my-squidbot@gmail.com`)
- Enable 2-Step Verification → Create an [App Password](https://myaccount.google.com/apppasswords)
- Use this app password for both IMAP and SMTP

**2. Configure**

> - `consentGranted` must be `true` to allow mailbox access. This is a safety gate — set `false` to fully disable.
> - `allowFrom`: Leave empty to accept emails from anyone, or restrict to specific senders.
> - `smtpUseTls` and `smtpUseSsl` default to `true` / `false` respectively, which is correct for Gmail (port 587 + STARTTLS). No need to set them explicitly.
> - Set `"autoReplyEnabled": false` if you only want to read/analyze emails without sending automatic replies.

```json
{
  "channels": {
    "email": {
      "enabled": true,
      "consentGranted": true,
      "imapHost": "imap.gmail.com",
      "imapPort": 993,
      "imapUsername": "my-squidbot@gmail.com",
      "imapPassword": "your-app-password",
      "smtpHost": "smtp.gmail.com",
      "smtpPort": 587,
      "smtpUsername": "my-squidbot@gmail.com",
      "smtpPassword": "your-app-password",
      "fromAddress": "my-squidbot@gmail.com",
      "allowFrom": ["your-real-email@gmail.com"]
    }
  }
}
```


**3. Run**

```bash
squidbot gateway
```

</details>

## 🌐 Agent Social Network

🦑 squidbot is capable of linking to the agent social network (agent community). **Just send one message and your squidbot joins automatically!**

| Platform | How to Join (send this message to your bot) |
|----------|-------------|
| [**Moltbook**](https://www.moltbook.com/) | `Read https://moltbook.com/skill.md and follow the instructions to join Moltbook` |
| [**ClawdChat**](https://clawdchat.ai/) | `Read https://clawdchat.ai/skill.md and follow the instructions to join ClawdChat` |

Simply send the command above to your squidbot (via CLI, Matrix, or Email), and it will handle the rest.

## ⚙️ Configuration

Config file: `~/.squidbot/config.json`

### Providers

> [!TIP]
>
> - **Groq** provides free voice transcription via Whisper.
> - **Zhipu Coding Plan**: If you're on Zhipu's coding plan, set `"apiBase": "https://open.bigmodel.cn/api/coding/paas/v4"` in your zhipu provider config.
> - **MiniMax (Mainland China)**: If your API key is from MiniMax's mainland China platform (minimaxi.com), set `"apiBase": "https://api.minimaxi.com/v1"` in your minimax provider config.

| Provider | Purpose | Get API Key |
|----------|---------|-------------|
| `custom` | Any OpenAI-compatible endpoint | — |
| `openrouter` | LLM (recommended, access to all models) | [openrouter.ai](https://openrouter.ai) |
| `anthropic` | LLM (Claude direct) | [console.anthropic.com](https://console.anthropic.com) |
| `openai` | LLM (GPT direct) | [platform.openai.com](https://platform.openai.com) |
| `deepseek` | LLM (DeepSeek direct) | [platform.deepseek.com](https://platform.deepseek.com) |
| `groq` | LLM + **Voice transcription** (Whisper) | [console.groq.com](https://console.groq.com) |
| `gemini` | LLM (Gemini direct) | [aistudio.google.com](https://aistudio.google.com) |
| `minimax` | LLM (MiniMax direct) | [platform.minimax.io](https://platform.minimax.io) |
| `aihubmix` | LLM (API gateway, access to all models) | [aihubmix.com](https://aihubmix.com) |
| `dashscope` | LLM (Qwen) | [dashscope.console.aliyun.com](https://dashscope.console.aliyun.com) |
| `moonshot` | LLM (Moonshot/Kimi) | [platform.moonshot.cn](https://platform.moonshot.cn) |
| `zhipu` | LLM (Zhipu GLM) | [open.bigmodel.cn](https://open.bigmodel.cn) |
| `vllm` | LLM (local, any OpenAI-compatible server) | — |

<details>
<summary><b>Custom Provider (Any OpenAI-compatible API)</b></summary>

If your provider is not listed above but exposes an **OpenAI-compatible API** (e.g. Together AI, Fireworks, Azure OpenAI, self-hosted endpoints), use the `custom` provider:

```json
{
  "providers": {
    "custom": {
      "apiKey": "your-api-key",
      "apiBase": "https://api.your-provider.com/v1"
    }
  },
  "agents": {
    "defaults": {
      "model": "your-model-name"
    }
  }
}
```

> The `custom` provider routes through LiteLLM's OpenAI-compatible path. It works with any endpoint that follows the OpenAI chat completions API format. The model name is passed directly to the endpoint without any prefix.

</details>

<details>
<summary><b>vLLM (local / OpenAI-compatible)</b></summary>

Run your own model with vLLM or any OpenAI-compatible server, then add to config:

**1. Start the server** (example):
```bash
vllm serve meta-llama/Llama-3.1-8B-Instruct --port 8000
```

**2. Add to config** (partial — merge into `~/.squidbot/config.json`):

*Provider (key can be any non-empty string for local):*
```json
{
  "providers": {
    "vllm": {
      "apiKey": "dummy",
      "apiBase": "http://localhost:8000/v1"
    }
  }
}
```

*Model:*
```json
{
  "agents": {
    "defaults": {
      "model": "meta-llama/Llama-3.1-8B-Instruct"
    }
  }
}
```

</details>

<details>
<summary><b>Adding a New Provider (Developer Guide)</b></summary>

squidbot uses a **Provider Registry** (`squidbot/providers/registry.py`) as the single source of truth.
Adding a new provider only takes **2 steps** — no if-elif chains to touch.

**Step 1.** Add a `ProviderSpec` entry to `PROVIDERS` in `squidbot/providers/registry.py`:

```python
ProviderSpec(
    name="myprovider",                   # config field name
    keywords=("myprovider", "mymodel"),  # model-name keywords for auto-matching
    env_key="MYPROVIDER_API_KEY",        # env var for LiteLLM
    display_name="My Provider",          # shown in `squidbot status`
    litellm_prefix="myprovider",         # auto-prefix: model → myprovider/model
    skip_prefixes=("myprovider/",),      # don't double-prefix
)
```

**Step 2.** Add a field to `ProvidersConfig` in `squidbot/config/schema.py`:

```python
class ProvidersConfig(BaseModel):
    ...
    myprovider: ProviderConfig = ProviderConfig()
```

That's it! Environment variables, model prefixing, config matching, and `squidbot status` display will all work automatically.

**Common `ProviderSpec` options:**

| Field                    | Description                                     | Example                                  |
| ------------------------ | ----------------------------------------------- | ---------------------------------------- |
| `litellm_prefix`         | Auto-prefix model names for LiteLLM             | `"dashscope"` → `dashscope/qwen-max`     |
| `skip_prefixes`          | Don't prefix if model already starts with these | `("dashscope/", "openrouter/")`          |
| `env_extras`             | Additional env vars to set                      | `(("ZHIPUAI_API_KEY", "{api_key}"),)`    |
| `model_overrides`        | Per-model parameter overrides                   | `(("kimi-k2.5", {"temperature": 1.0}),)` |
| `is_gateway`             | Can route any model (like OpenRouter)           | `True`                                   |
| `detect_by_key_prefix`   | Detect gateway by API key prefix                | `"sk-or-"`                               |
| `detect_by_base_keyword` | Detect gateway by API base URL                  | `"openrouter"`                           |
| `strip_model_prefix`     | Strip existing prefix before re-prefixing       | `True` (for AiHubMix)                    |

</details>


### MCP (Model Context Protocol)

> [!TIP]
> The config format is compatible with Claude Desktop / Cursor. You can copy MCP server configs directly from any MCP server's README.

squidbot supports [MCP](https://modelcontextprotocol.io/) — connect external tool servers and use them as native agent tools.

Add MCP servers to your `config.json`:

```json
{
  "tools": {
    "mcpServers": {
      "filesystem": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"]
      }
    }
  }
}
```

Two transport modes are supported:

| Mode | Config | Example |
|------|--------|---------|
| **Stdio** | `command` + `args` | Local process via `npx` / `uvx` |
| **HTTP** | `url` | Remote endpoint (`https://mcp.example.com/sse`) |

MCP tools are automatically discovered and registered on startup. The LLM can use them alongside built-in tools — no extra configuration needed.




### Security

> [!TIP]
> For production deployments, set `"restrictToWorkspace": true` in your config to sandbox the agent.

| Option                      | Default          | Description                                                                                                                                                 |
| --------------------------- | ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tools.restrictToWorkspace` | `false`          | When `true`, restricts **all** agent tools (shell, file read/write/edit, list) to the workspace directory. Prevents path traversal and out-of-scope access. |
| `channels.*.allowFrom`      | `[]` (allow all) | Whitelist of user IDs. Empty = allow everyone; non-empty = only listed users can interact.                                                                  |

## CLI Reference

| Command                               | Description                   |
| ------------------------------------- | ----------------------------- |
| `squidbot onboard`                     | Initialize config & workspace |
| `squidbot agent -m "..."`              | Chat with the agent           |
| `squidbot agent`                       | Interactive chat mode         |
| `squidbot agent --no-markdown`         | Show plain-text replies       |
| `squidbot agent --logs`                | Show runtime logs during chat |
| `squidbot gateway`                     | Start the gateway             |
| `squidbot status`                      | Show status                   |
| `squidbot provider login openai-codex` | OAuth login for providers     |
| `squidbot channels status`             | Show channel status           |

Interactive mode exits: `exit`, `quit`, `/exit`, `/quit`, `:q`, or `Ctrl+D`.

<details>
<summary><b>Scheduled Tasks (Cron)</b></summary>

```bash
# Add a job
squidbot cron add --name "daily" --message "Good morning!" --cron "0 9 * * *"
squidbot cron add --name "hourly" --message "Check status" --every 3600

# List jobs
squidbot cron list

# Remove a job
squidbot cron remove <job_id>
```

</details>

## 🐳 Docker

> [!TIP]
> The `-v ~/.squidbot:/root/.squidbot` flag mounts your local config directory into the container, so your config and workspace persist across container restarts.
>
> The default `Dockerfile` uses a multi-stage Alpine build (`python:3.14-alpine`) and includes Matrix E2EE dependencies (`olm`, `olm-dev`). It also sets `CMAKE_POLICY_VERSION_MINIMUM=3.5` to keep `python-olm` builds working with Alpine 3.23's CMake 4.

Build and run squidbot in a container:

```bash
# Build the image
docker build -t squidbot .

# Initialize config (first time only)
docker run -v ~/.squidbot:/root/.squidbot --rm squidbot onboard

# Edit config on host to add API keys
vim ~/.squidbot/config.json

# Run gateway (connects to enabled channels, e.g. Matrix/Email)
docker run -v ~/.squidbot:/root/.squidbot -p 18790:18790 squidbot gateway

# Or run a single command
docker run -v ~/.squidbot:/root/.squidbot --rm squidbot agent -m "Hello!"
docker run -v ~/.squidbot:/root/.squidbot --rm squidbot status
```

## 📁 Project Structure

```
squidbot/
├── agent/          # 🧠 Core agent logic
│   ├── loop.py     #    Agent loop (LLM ↔ tool execution)
│   ├── context.py  #    Prompt builder
│   ├── memory.py   #    Persistent memory
│   ├── skills.py   #    Skills loader
│   ├── subagent.py #    Background task execution
│   └── tools/      #    Built-in tools (incl. spawn)
├── skills/         # 🎯 Bundled skills (github, weather, tmux...)
├── channels/       # 📱 Chat channel integrations
├── bus/            # 🚌 Message routing
├── cron/           # ⏰ Scheduled tasks
├── heartbeat/      # 💓 Proactive wake-up
├── providers/      # 🤖 LLM providers (OpenRouter, etc.)
├── session/        # 💬 Conversation sessions
├── config/         # ⚙️ Configuration
└── cli/            # 🖥️ Commands
```

## 🤝 Contribute & Roadmap

PRs welcome! The codebase is intentionally small and readable. 🤗

**Roadmap** — Pick an item and [open a PR](https://github.com/HKUDS/squidbot/pulls)!

- [ ] **Multi-modal** — See and hear (images, voice, video)
- [ ] **Long-term memory** — Never forget important context
- [ ] **Better reasoning** — Multi-step planning and reflection
- [ ] **More integrations** — Calendar and more
- [ ] **Self-improvement** — Learn from feedback and mistakes

### Contributors

<a href="https://github.com/Athemis/squidbot/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Athemis/squidbot&max=100&columns=12&updated=20260210" alt="Contributors" />
</a>

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Athemis/squidbot&type=date&legend=top-left)](https://www.star-history.com/#Athemis/squidbot&type=date&legend=top-left)

<p align="center">
  <br>
  <img width="80" src="https://cdn.rawgit.com/sindresorhus/awesome/d7305f38d29fed78fa85652e3a63e154dd8e8829/media/badge.svg" alt="Awesome">
  <br>
</p>

<h1 align="center">Awesome Grok Plugins</h1>

<p align="center">A curated list of plugins, skills, and resources for xAI's Grok Build CLI.</p>

<p align="center">
  <a href="#contributing"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" alt="PRs Welcome"></a>
  <a href="https://opensource.org/licenses/Apache-2.0"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="License"></a>
  <a href="https://hol.org/registry/plugins"><img src="https://img.shields.io/badge/Browse-Registry-green" alt="Browse Registry"></a>
</p>

<p align="center">
  <a href="https://x.ai/cli">Grok Build</a> is xAI's terminal-first coding agent. Plugins bundle skills, slash commands, subagents, MCP servers, hooks, and LSP servers into installable packages. This list curates the best community-built plugins for the Grok ecosystem.
</p>

<br>

## Contents

- [Start Here](#start-here)
- [Official Plugins](#official-plugins)
- [Community Plugins](#community-plugins)
- [Plugin Development](#plugin-development)
- [Guides & Articles](#guides--articles)
- [Related Projects](#related-projects)

---

## Start Here

### Installing Grok Build

```bash
# macOS / Linux / WSL
curl -fsSL https://x.ai/cli/install.sh | bash

# Windows PowerShell
irm https://x.ai/cli/install.ps1 | iex
```

### Using Plugins

```bash
# Add the official xAI marketplace
grok plugin marketplace add xai-org/plugin-marketplace

# Browse available plugins
grok plugin list

# Install a plugin
grok plugin install <plugin-name> --trust

# Add a community marketplace (this repo)
grok plugin marketplace add hashgraph-online/awesome-grok-plugins
```

Inside Grok Build, type `/marketplace` to browse and install plugins interactively. You can also use `/plugins`, `/skills`, `/hooks`, or `/mcps` to manage installed components.

**Plugin discovery paths:** Grok Build loads plugins from `./.grok/plugins/`, `~/.grok/plugins/`, marketplace installs under `~/.grok/plugins/marketplaces/`, and custom paths via `--plugin-dir <PATH>`. MCP servers can also be configured in `~/.grok/config.toml` under `[mcp_servers]`.

**Grok API + MCP:** The xAI API natively supports Remote MCP Tools via the `tools` parameter: `{"type": "mcp", "server_url": "...", "server_label": "..."}`. See [xAI Remote MCP docs](https://docs.x.ai/developers/tools/remote-mcp).

### Plugin Scanner (Recommended)

Validate plugins before submission with the HOL AI Plugin Scanner:

| Requirement  | Threshold                                      |
| ------------ | ---------------------------------------------- |
| **Score**    | ≥ 80 / 130                                     |
| **Severity** | No critical or high findings                   |
| **CI**       | Scanner must run in your repo's GitHub Actions |

See the full guide: [`SCANNER_GUIDE.md`](./SCANNER_GUIDE.md)
See contributing requirements: [`CONTRIBUTING.md`](./CONTRIBUTING.md)

### How This List Works

You add a single line to `README.md`. That's it. A maintainer-verified generator mirrors your plugin from its source repo and regenerates the catalog files (`plugins.json`, `marketplace.json`). You never need to copy plugin files into this repo yourself.

```
Your PR:  README.md (+1 line)
Generator (CI):  plugins/<owner>/<repo>/  ←  fetched from your GitHub repo
                  plugins.json            ←  regenerated from README
                  marketplace.json        ←  regenerated from README
```

---

## Official Plugins

The official xAI plugin marketplace lives at [xai-org/plugin-marketplace](https://github.com/xai-org/plugin-marketplace). First-party and vetted third-party plugins include:

<details>
<summary>Official xAI Marketplace Plugins</summary>

| Plugin | Category | Description |
|--------|----------|-------------|
| [Vercel](https://github.com/vercel/vercel-plugin) | deployment | Deploy and manage Vercel frontend infrastructure |
| [Sentry](https://github.com/getsentry/sentry-for-ai) | monitoring | Error monitoring, stack traces, production debugging |
| [Chrome DevTools](https://github.com/ChromeDevTools/chrome-devtools-mcp) | development | Control and inspect a live Chrome browser |
| [Cloudflare](https://github.com/cloudflare/skills) | development | Workers, Durable Objects, Agents SDK, Wrangler CLI |
| [Superpowers](https://github.com/obra/superpowers) | development | Core skills library: TDD, systematic debugging, workflows |
| [MongoDB](https://github.com/mongodb/agent-skills) | database | MCP Server + Skills for MongoDB databases |
| [Axiom](https://github.com/axiomhq/skills) | observability | Log/metric queries with APL, SRE investigations |
| [Neon](https://github.com/neon) | database | Serverless Postgres with branching and migrations |

</details>

---

## Community Plugins

### Development & Workflow

- [HOL Guard](https://github.com/hashgraph-online/hol-guard-grok-plugin) - Security plugin for protecting Grok Build with HOL Guard: harness protection, approval broker, and plugin scanner integration.

### Tools & Integrations

<!-- Add your plugin here in alphabetical order by display name -->

---

## Plugin Development

### What a Plugin Is

A plugin is a directory bundling any combination of components:

| Component    | Location              | Purpose                                    |
| ------------ | --------------------- | ------------------------------------------ |
| Skills       | `skills/`             | `SKILL.md` capability definitions          |
| Commands     | `commands/`           | Slash command definitions                  |
| Agents       | `agents/`             | Subagent definitions                       |
| Hooks        | `hooks/hooks.json`    | Lifecycle hooks (PreToolUse, PostToolUse)  |
| MCP servers  | `.mcp.json`           | Model Context Protocol server configs      |
| LSP servers  | `.lsp.json`           | Language server configs                    |
| Manifest     | `.grok-plugin/plugin.json` | Optional metadata and path overrides |

### Plugin Structure

```
your-plugin-repo/
  .grok-plugin/
    plugin.json              # Optional manifest (metadata, path overrides)
    marketplace.json         # Self-contained marketplace (for standalone install)
  .mcp.json                  # MCP server configs
  .lsp.json                  # LSP server configs (optional)
  assets/
    icon.svg                 # Plugin icon
  skills/
    my-skill/
      SKILL.md               # Skill definition
  commands/
    my-command.md            # Slash command definition
  agents/
    my-agent.md              # Subagent definition
  hooks/
    hooks.json               # Lifecycle hooks
  README.md
  LICENSE
```

### plugin.json Manifest

The manifest at `.grok-plugin/plugin.json` is optional but recommended for metadata:

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "What this plugin does",
  "author": {
    "name": "Your Name",
    "url": "https://github.com/your-org"
  },
  "homepage": "https://github.com/your-org/my-plugin",
  "repository": "https://github.com/your-org/my-plugin",
  "license": "MIT",
  "keywords": ["my-plugin", "specific-terms"],
  "skills": "./skills/",
  "commands": "./commands/",
  "mcpServers": "./.mcp.json",
  "hooks": "./hooks/hooks.json"
}
```

Grok Build also accepts `.claude-plugin/plugin.json` for Claude-ecosystem compatibility.

### Creating a Plugin

1. **Set up the directory structure** above in your GitHub repo
2. **Add a scanner workflow** to your repo (see [CONTRIBUTING.md](./CONTRIBUTING.md))
3. **Test locally** with `grok plugin link .` then `grok inspect`
4. **Run the scanner** and ensure score ≥ 80
5. **Add your entry** to this repo's `README.md` (alphabetical order)
6. **Open a PR** with your scanner score and plugin URL

### Publishing to the Official xAI Marketplace

For inclusion in the official [xai-org/plugin-marketplace](https://github.com/xai-org/plugin-marketplace):

1. Fork `xai-org/plugin-marketplace`
2. Add an entry to `.grok-plugin/marketplace.json` with a SHA-pinned remote source
3. Regenerate the component index: `python3 scripts/generate-plugin-index.py`
4. Validate: `python3 scripts/validate-catalog.py`
5. Open a PR

---

## Guides & Articles

<!-- Add guides and articles in alphabetical order -->

- [Awesome Grok Build](https://github.com/DominikTobureto/awesome-grok-build) - Starter kit and skill library for Grok Build CLI
- [Awesome Grok Prompts](https://github.com/langgptai/awesome-grok-prompts) - Collection of advanced prompts for Grok AI

---

## Related Projects

- [Awesome AI Plugins](https://github.com/hashgraph-online/awesome-ai-plugins) - Multi-agent plugin registry (Codex, Claude, Cursor, Gemini, Grok)
- [Awesome Codex Plugins](https://github.com/hashgraph-online/awesome-codex-plugins) - OpenAI Codex plugin registry
- [Awesome Grok Build](https://github.com/DominikTobureto/awesome-grok-build) - Starter kit for Grok Build CLI
- [HOL Guard](https://github.com/hashgraph-online/hol-guard) - Approval broker for plugin submissions
- [HOL Plugin Scanner](https://github.com/hashgraph-online/ai-plugin-scanner) - Security and quality scanner for AI plugins
- [HOL Scanner Action](https://github.com/hashgraph-online/ai-plugin-scanner-action) - GitHub Action for CI plugin scanning
- [xAI Plugin Marketplace](https://github.com/xai-org/plugin-marketplace) - Official xAI plugin catalog

---

## Contributing

Contributions are welcome! Please read the [CONTRIBUTING.md](./CONTRIBUTING.md) guide before submitting a PR.

Key requirements:
- Scanner score ≥ 80/130 with no critical/high findings
- Scanner CI running in your plugin repo
- Valid plugin structure (`.grok-plugin/plugin.json` or `.claude-plugin/plugin.json`)
- Alphabetical order in README sections

## License

[Apache License 2.0](LICENSE)

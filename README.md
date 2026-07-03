<p align="center">
  <br>
  <img width="80" src="https://cdn.rawgit.com/sindresorhus/awesome/d7305f38d29fed78fa85652e3a63e154dd8e8829/media/badge.svg" alt="Awesome">
  <br>
</p>

<h1 align="center">Awesome Grok Plugins</h1>

<p align="center">A curated list of awesome xAI Grok plugins, skills, and resources.</p>

<p align="center">
  <a href="https://hol.org/registry/plugins">
    <img src="assets/awesome-grok-plugins-hol.png" alt="Awesome Grok Plugins by HOL" width="960" height="540">
  </a>
</p>

<p align="center">
  <a href="#contributing"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" alt="PRs Welcome"></a>
  <a href="https://opensource.org/licenses/Apache-2.0"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="License"></a>
  <a href="https://hol.org/registry/plugins"><img src="https://img.shields.io/badge/Browse-Registry-green" alt="Browse Registry"></a>
</p>

<p align="center">
  xAI's <a href="https://grok.com">Grok</a> supports custom plugins, MCP servers, and skills that extend its capabilities across the Grok app, API, and integrations. This list curates the best community-built plugins for the Grok ecosystem.
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

New plugin workflow:

1. Create with `$plugin-creator`
2. **Validate with [`plugin-scanner`](https://github.com/hashgraph-online/hol-guard)** — **Required: score ≥ 80, no high/critical findings**
3. **Gate PRs with the [HOL scanner GitHub Action](https://github.com/hashgraph-online/ai-plugin-scanner-action)** — **Required for listing**
4. Ship or submit with confidence

### Quick preflight

```bash
pipx run plugin-scanner lint .
pipx run plugin-scanner verify .
```

### Scanner Requirements (Mandatory for This List)

All plugins submitted to **Awesome Grok Plugins** must pass the HOL AI Plugin Scanner:

| Requirement  | Threshold                                      |
| ------------ | ---------------------------------------------- |
| **Score**    | ≥ 80 / 130                                     |
| **Severity** | No critical or high findings                   |
| **CI**       | Scanner must run in your repo's GitHub Actions |

See the full guide: [`SCANNER_GUIDE.md`](./SCANNER_GUIDE.md)
See contributing requirements: [`CONTRIBUTING.md`](./CONTRIBUTING.md)

This repo publishes a Grok repo marketplace at `.agents/plugins/marketplace.json`. The marketplace points at mirrored installable plugin bundles under `./plugins/`, so a clone of this repo can act as a curated plugin source for Grok.

### Use this marketplace in Grok

Install plugins directly from this curated list by pointing Grok at the repo marketplace:

**CLI:**

```bash
# Add this repo as a marketplace source (one-time setup)
grok plugin marketplace add \
  'https://github.com/hashgraph-online/awesome-grok-plugins.git' \
  --sparse 'plugins'

# List available plugins
grok plugin list

# Install a specific plugin
grok plugin install <plugin-name>
```

**Manual install (from source):**

```bash
# Clone and link a plugin locally
git clone https://github.com/<owner>/<plugin-repo>.git
cd <plugin-repo>
grok plugin link .
```

### How This Works

You add a single line to `README.md`. That's it. A maintainer-verified generator mirrors your plugin bundle from your source repo and regenerates the catalog files (`plugins.json`, `marketplace.json`). You never need to copy plugin files into this repo yourself.

```
Your PR:  README.md (+1 line)
Generator (CI):  plugins/<owner>/<repo>/  ←  fetched from your GitHub repo
                  plugins.json            ←  regenerated from README
                  marketplace.json        ←  regenerated from README
```

---

## Official Plugins

<!-- Official plugins from xAI or HOL -->

_No official plugins yet. See [Community Plugins](#community-plugins) below._

---

## Community Plugins

### Development & Workflow

<!-- Add your plugin here in alphabetical order by display name -->

### Tools & Integrations

<!-- Add your plugin here in alphabetical order by display name -->

---

## Plugin Development

### Plugin Structure

Grok plugins follow a standard directory structure with a manifest at `.grok-plugin/plugin.json`:

```
your-plugin-repo/
  .grok-plugin/
    plugin.json        # Required - plugin manifest
  assets/
    icon.svg           # Required - plugin icon (SVG preferred, PNG acceptable)
  skills/              # Optional - skill definitions
  ...                  # Other plugin files (commands, hooks, etc.)
```

### plugin.json

Must be valid JSON at `.grok-plugin/plugin.json` with at minimum:

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "What this plugin does",
  "repository": "https://github.com/<owner>/<repo>",
  "license": "MIT",
  "interface": {
    "displayName": "My Plugin",
    "shortDescription": "Brief one-liner",
    "composerIcon": "./assets/icon.svg"
  }
}
```

**Required fields:**
- `name` - machine-readable plugin identifier (lowercase, kebab-case)
- `version` - semver version string
- `description` - what the plugin does
- `repository` - GitHub repository URL
- `license` - SPDX license identifier
- `interface.composerIcon` - path to the icon file (relative to plugin root)

### Creating a Plugin

1. **Initialize your plugin repo** with the structure above
2. **Add a scanner workflow** to your repo (see [CONTRIBUTING.md](./CONTRIBUTING.md))
3. **Run the scanner locally** and ensure score ≥ 80
4. **Add your entry** to `README.md` in this repo (alphabetical order)
5. **Open a PR** with your scanner score and plugin URL

### Plugin Anatomy

| Component          | Location                        | Purpose                                              |
| ------------------ | ------------------------------- | --------------------------------------------------- |
| Manifest           | `.grok-plugin/plugin.json`      | Plugin metadata, dependencies, interface definition |
| Skills             | `skills/`                       | Reusable skill definitions for Grok                 |
| MCP Servers        | `mcp.json` or inline in manifest| Model Context Protocol server definitions           |
| Assets             | `assets/`                       | Icons, screenshots, and other static files          |
| Commands           | `commands/`                     | Slash command definitions                           |

---

## Guides & Articles

<!-- Add guides and articles in alphabetical order -->

---

## Related Projects

- [Awesome AI Plugins](https://github.com/hashgraph-online/awesome-ai-plugins) - Multi-agent plugin registry (Codex, Claude, Cursor, Gemini, Grok)
- [Awesome Codex Plugins](https://github.com/hashgraph-online/awesome-codex-plugins) - OpenAI Codex plugin registry
- [HOL Guard](https://github.com/hashgraph-online/hol-guard) - Approval broker for plugin submissions
- [HOL Plugin Scanner](https://github.com/hashgraph-online/ai-plugin-scanner) - Security and quality scanner for AI plugins
- [HOL Scanner Action](https://github.com/hashgraph-online/ai-plugin-scanner-action) - GitHub Action for CI plugin scanning

---

## Contributing

Contributions are welcome! Please read the [CONTRIBUTING.md](./CONTRIBUTING.md) guide before submitting a PR.

Key requirements:
- Scanner score ≥ 80/130 with no critical/high findings
- Scanner CI running in your plugin repo
- Valid `.grok-plugin/plugin.json` manifest
- Alphabetical order in README sections

## License

[Apache License 2.0](LICENSE)

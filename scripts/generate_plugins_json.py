#!/usr/bin/env python3
"""Regenerate compatibility metadata and the curated Grok marketplace from README.

Usage:
    python3 scripts/generate_plugins_json.py

This script keeps three artifacts aligned:

- plugins.json compatibility output for legacy tooling
- .agents/plugins/marketplace.json for Grok repo marketplace installs
- mirrored installable plugin bundles under plugins/<owner>/<repo>/

Grok Build plugins use .grok-plugin/plugin.json (or .claude-plugin/plugin.json
for Claude-compatible plugins). Unlike Codex plugins, the manifest is optional
and plugins are defined by their components (skills/, commands/, agents/,
hooks/, .mcp.json, .lsp.json).
"""

from __future__ import annotations

import datetime
import io
import json
import re
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

README = Path(__file__).parent.parent / "README.md"
OUTPUT = Path(__file__).parent.parent / "plugins.json"
MARKETPLACE_OUTPUT = Path(__file__).parent.parent / ".agents" / "plugins" / "marketplace.json"
PLUGINS_ROOT = Path(__file__).parent.parent / "plugins"
REQUEST_TIMEOUT_SECONDS = 60
MAX_RETRIES = 3
USER_AGENT = "awesome-grok-plugins-generator"
RAW_DEFAULT_BRANCH_REF = "HEAD"

# Manifest discovery order: .grok-plugin first, then .claude-plugin (Claude compat)
MANIFEST_DIRS = (".grok-plugin", ".claude-plugin")

OPTIONAL_PLUGIN_FILES = (
    "README.md",
    "NOTICE.md",
    "SECURITY.md",
    "LICENSE",
    "LICENSE.md",
    "LICENSE.txt",
    "pyproject.toml",
    "package.json",
    "pnpm-lock.yaml",
    "package-lock.json",
    "yarn.lock",
    ".grokignore",
    ".mcp.json",
    ".lsp.json",
    ".agents/plugins/marketplace.json",
  )

# Standard plugin component directories/files to mirror
COMPONENT_DIRS = ("skills", "commands", "agents", "hooks", "scripts", "bin", "assets")
COMPONENT_FILES = (".mcp.json", ".lsp.json", "hooks/hooks.json")


def normalize_relative_path(value: str) -> str:
    value = value.replace("\\", "/")
    if value.startswith('/'):
        value = value[1:]
    if value.startswith('./'):
        value = value[2:]
    return value


def parse_plugins(readme_path: Path) -> list[dict[str, str]]:
    lines = readme_path.read_text(encoding="utf-8").splitlines()

    start = None
    end = None
    for index, line in enumerate(lines):
        if line.strip() == "## Community Plugins":
            start = index + 1
        if start is not None and line.strip().startswith("## ") and line.strip() != "## Community Plugins":
            end = index
            break

    if start is None:
        raise ValueError("Could not find Community Plugins section")
    if end is None:
        end = len(lines)

    section = lines[start:end]
    plugins: list[dict[str, str]] = []
    current_category = "Uncategorized"
    seen: set[str] = set()

    for line in section:
        category_match = re.match(r"^### (.+)", line.strip())
        if category_match:
            current_category = category_match.group(1)
            continue

        plugin_match = re.match(
            r"^- \[([^\]]+)\]\((https://github\.com/([^/]+)/([^)#]+?))(?:#readme)?\)\s*[-–]\s*(.+)",
            line.strip(),
        )
        if not plugin_match:
            continue

        owner, repo = plugin_match.group(3), plugin_match.group(4)
        repo = repo.removesuffix(".git")
        key = f"{owner}/{repo}/{plugin_match.group(1)}"
        if key in seen:
            continue
        seen.add(key)
        plugins.append(
            {
                "name": plugin_match.group(1),
                "url": plugin_match.group(2),
                "owner": owner,
                "repo": repo,
                "description": plugin_match.group(5).strip(),
                "category": current_category,
                "source": "awesome-grok-plugins",
            }
        )

    return plugins


def fetch_repo_archive(owner: str, repo: str) -> zipfile.ZipFile:
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            request = urllib.request.Request(
                f"https://github.com/{owner}/{repo}/archive/HEAD.zip",
                headers={"User-Agent": USER_AGENT},
            )
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                return zipfile.ZipFile(io.BytesIO(response.read()))
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                import time
                time.sleep(2 ** attempt)
    raise last_error


def normalize_match_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def find_manifest_path(names: set[str]) -> tuple[PurePosixPath, str] | None:
    """Find the plugin manifest in the archive.

    Returns (plugin_root, manifest_dir) where manifest_dir is
    '.grok-plugin' or '.claude-plugin'.
    """
    for manifest_dir in MANIFEST_DIRS:
        manifest_suffix = f"/{manifest_dir}/plugin.json"
        matches = sorted(
            [n for n in names if n.endswith(manifest_suffix)],
            key=len,
        )
        if matches:
            root = PurePosixPath(matches[0]).parent.parent
            return root, manifest_dir
    return None


def resolve_plugin_root(archive: zipfile.ZipFile, names: set[str], plugin: dict[str, str]) -> tuple[PurePosixPath, str]:
    result = find_manifest_path(names)
    if result is None:
        raise ValueError("Archive does not contain .grok-plugin/plugin.json or .claude-plugin/plugin.json")

    root, manifest_dir = result
    # Check for multiple manifests at different roots
    all_roots = []
    for md in MANIFEST_DIRS:
        suffix = f"/{md}/plugin.json"
        for n in sorted(names):
            if n.endswith(suffix):
                all_roots.append((PurePosixPath(n).parent.parent, md))
                break

    if len(all_roots) <= 1:
        return root, manifest_dir

    # If multiple, try to match by plugin name
    expected = normalize_match_key(plugin["name"])
    for r, md in all_roots:
        manifest = load_manifest(archive, r, md)
        candidates = [
            manifest.get("name"),
            r.name,
        ]
        if any(normalize_match_key(c) == expected for c in candidates):
            return r, md

    return root, manifest_dir


def load_manifest(archive: zipfile.ZipFile, plugin_root: PurePosixPath, manifest_dir: str) -> dict[str, object]:
    manifest_name = plugin_root.joinpath(manifest_dir, "plugin.json").as_posix()
    return json.loads(archive.read(manifest_name).decode("utf-8"))


def plugin_root_relative_path(plugin_root: PurePosixPath) -> str:
    repo_relative_parts = plugin_root.parts[1:]
    return PurePosixPath(*repo_relative_parts).as_posix() if repo_relative_parts else ""


def build_raw_manifest_url(plugin: dict[str, str], plugin_root_relative: str, manifest_dir: str) -> str:
    manifest_path = f"{manifest_dir}/plugin.json"
    if plugin_root_relative:
        manifest_path = f"{plugin_root_relative}/{manifest_path}"
    return (
        f"https://raw.githubusercontent.com/{plugin['owner']}/{plugin['repo']}/"
        f"{RAW_DEFAULT_BRANCH_REF}/{manifest_path}"
    )


def add_recursive_selection(
    selected: set[str],
    all_names: set[str],
    plugin_root: PurePosixPath,
    relative_path: str,
) -> None:
    normalized = normalize_relative_path(relative_path)
    if not normalized:
        return
    archive_prefix = plugin_root.joinpath(PurePosixPath(normalized)).as_posix()
    if archive_prefix in all_names:
        selected.add(normalized)
    prefix_with_slash = f"{archive_prefix}/"
    for name in all_names:
        if name.startswith(prefix_with_slash):
            relative_name = PurePosixPath(name).relative_to(plugin_root).as_posix()
            selected.add(relative_name)


def collect_selected_paths(
    manifest: dict[str, object],
    all_names: set[str],
    plugin_root: PurePosixPath,
    plugin: dict[str, str],
    manifest_dir: str,
) -> set[str]:
    selected = {f"{manifest_dir}/plugin.json"}

    # Always include standard component directories if they exist
    for comp_dir in COMPONENT_DIRS:
        add_recursive_selection(selected, all_names, plugin_root, comp_dir)

    # Include standard component files
    for comp_file in COMPONENT_FILES:
        add_recursive_selection(selected, all_names, plugin_root, comp_file)

    # Include optional files
    for optional_name in OPTIONAL_PLUGIN_FILES:
        add_recursive_selection(selected, all_names, plugin_root, optional_name)

    # Include manifest-referenced paths (overrides)
    for key in ("skills", "scripts", "mcpServers", "apps", "app", "appConfig", "hooks", "commands", "agents"):
        value = manifest.get(key)
        if isinstance(value, str):
            add_recursive_selection(selected, all_names, plugin_root, value)

    # Include icon/logo if referenced
    for key in ("logo", "icon"):
        value = manifest.get(key)
        if isinstance(value, str):
            add_recursive_selection(selected, all_names, plugin_root, value)

    return selected


def mirror_plugin_bundle(plugin: dict[str, str]) -> tuple[dict[str, object], str, str, str]:
    owner_repo = f"{plugin['owner']}/{plugin['repo']}"
    try:
        archive = fetch_repo_archive(plugin["owner"], plugin["repo"])
    except Exception as e:
        raise ValueError(f"Failed to fetch {owner_repo}: {e}") from e
    names = {name for name in archive.namelist() if not name.endswith("/")}
    try:
        plugin_root, manifest_dir = resolve_plugin_root(archive, names, plugin)
    except ValueError:
        raise ValueError(f"Archive for {owner_repo} does not contain a matching plugin manifest") from None
    manifest = load_manifest(archive, plugin_root, manifest_dir)
    selected_paths = collect_selected_paths(manifest, names, plugin_root, plugin, manifest_dir)

    plugin_root_relative = plugin_root_relative_path(plugin_root)
    destination_root = PLUGINS_ROOT / plugin["owner"] / plugin["repo"]
    if plugin_root_relative:
        destination_root = destination_root / PurePosixPath(plugin_root_relative)
    if destination_root.exists():
        shutil.rmtree(destination_root)
    destination_root.mkdir(parents=True, exist_ok=True)

    for relative_path in sorted(selected_paths):
        archive_name = plugin_root.joinpath(PurePosixPath(relative_path)).as_posix()
        destination_path = destination_root / PurePosixPath(relative_path)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        if relative_path == f"{manifest_dir}/plugin.json":
            destination_path.write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        else:
            try:
                destination_path.write_bytes(archive.read(archive_name))
            except KeyError:
                pass  # File listed but not in archive, skip

    marketplace_path = f"./plugins/{plugin['owner']}/{plugin['repo']}"

    return manifest, marketplace_path, plugin_root_relative, manifest_dir


def build_marketplace_entry(
    plugin: dict[str, str],
    manifest: dict[str, object],
    marketplace_path: str,
) -> dict[str, object]:
    manifest_name = str(manifest.get("name") or "").strip() or plugin["repo"]
    display_name = plugin["name"]
    description = plugin.get("description", "").strip()
    if not description:
        description = str(manifest.get("description") or "").strip()

    entry: dict[str, object] = {
        "name": manifest_name,
        "displayName": display_name,
        "source": {
            "source": "local",
            "path": marketplace_path,
        },
        "policy": {
            "installation": "AVAILABLE",
            "authentication": "ON_INSTALL",
        },
        "category": plugin["category"],
    }
    if description:
        entry["description"] = description

    # Grok plugins may have keywords, author, homepage
    for key in ("keywords", "author", "homepage", "version"):
        value = manifest.get(key)
        if value:
            entry[key] = value

    return entry


def write_json(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    plugins = parse_plugins(README)
    mirrored_entries: list[dict[str, object]] = []
    skipped: list[str] = []
    for plugin in plugins:
        owner_repo = f"{plugin['owner']}/{plugin['repo']}"
        try:
            manifest, marketplace_path, plugin_root_relative, manifest_dir = mirror_plugin_bundle(plugin)
        except Exception as e:
            print(f"WARNING: Skipping {owner_repo} — {e}", file=sys.stderr)
            skipped.append(owner_repo)
            continue
        plugin["install_url"] = build_raw_manifest_url(plugin, plugin_root_relative, manifest_dir)

        mirrored_entries.append(build_marketplace_entry(plugin, manifest, marketplace_path))

    ok_plugins = [p for p in plugins if f"{p['owner']}/{p['repo']}" not in skipped]

    marketplace = {
        "name": "awesome-grok-plugins",
        "interface": {
            "displayName": "Awesome Grok Plugins",
        },
        "plugins": mirrored_entries,
    }
    public_plugins = [
        {key: value for key, value in plugin.items() if not key.startswith("_")}
        for plugin in ok_plugins
    ]
    plugins_json = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "name": "awesome-grok-plugins",
        "version": "1.0.0",
        "last_updated": datetime.date.today().isoformat(),
        "total": len(ok_plugins),
        "categories": sorted({plugin["category"] for plugin in ok_plugins}),
        "plugins": public_plugins,
    }

    write_json(MARKETPLACE_OUTPUT, marketplace)
    write_json(OUTPUT, plugins_json)
    print(f"Wrote {len(ok_plugins)} plugins to {OUTPUT}")
    if skipped:
        print(f"Skipped {len(skipped)} broken upstream(s): {', '.join(skipped)}", file=sys.stderr)
    print(f"Wrote curated marketplace to {MARKETPLACE_OUTPUT}")


if __name__ == "__main__":
    main()

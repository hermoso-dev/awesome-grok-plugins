#!/usr/bin/env python3
"""Validate plugin submissions in PRs.

Two validation paths:

1. Bundle diff path (plugins/** changed):
   Validates committed plugin bundles against the contribution spec:
   - plugin.json exists and contains required fields
   - README entry exists for the plugin

2. README-entry path (README.md changed, no bundle):
   For new README entries that don't have a matching local bundle yet,
   fetches the source repo archive and validates plugin.json presence
   and required fields.

Grok plugins use .grok-plugin/plugin.json (or .claude-plugin/plugin.json
for Claude-compatible plugins). The interface block is optional.

Usage:
    python3 scripts/validate-plugin-pr.py [--base-ref <ref>]

If --base-ref is not provided, defaults to origin/main.
"""

from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).parent.parent
PLUGINS_DIR = REPO_ROOT / "plugins"
README_PATH = REPO_ROOT / "README.md"

# Manifest discovery order
MANIFEST_DIRS = (".grok-plugin", ".claude-plugin")

REQUIRED_MANIFEST_FIELDS = ["name", "version", "description", "repository", "license"]
OPTIONAL_INTERFACE_FIELDS = ["displayName", "shortDescription", "composerIcon"]
ICON_EXTENSIONS = {".svg", ".png", ".jpg", ".jpeg", ".webp", ".ico"}
MAX_ICON_SIZE_BYTES = 50 * 1024  # 50KB
REQUEST_TIMEOUT_SECONDS = 60
USER_AGENT = "awesome-grok-plugins-validator"

# Regex for README plugin entries
README_ENTRY_RE = re.compile(
    r"^- \[([^\]]+)\]\((https://github\.com/"
    r"([^/]+)/([^)#]+?))(?:[?#][^)]*)?\)\s*[-\u2013]\s*(.+)",
    re.MULTILINE,
)

# Standard plugin components
COMPONENT_DIRS = ("skills", "commands", "agents", "hooks", "assets")


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT)] + list(args),
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Helpers for fetching source repo archives
# ---------------------------------------------------------------------------


def fetch_repo_archive(owner: str, repo: str) -> zipfile.ZipFile:
    """Download the HEAD.zip archive for owner/repo."""
    url = f"https://github.com/{owner}/{repo}/archive/HEAD.zip"
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return zipfile.ZipFile(io.BytesIO(response.read()))


def find_plugin_root(archive: zipfile.ZipFile) -> tuple[PurePosixPath, str] | None:
    """Find the directory containing a plugin manifest.

    Returns (plugin_root, manifest_dir) or None.
    """
    for manifest_dir in MANIFEST_DIRS:
        suffix = f"/{manifest_dir}/plugin.json"
        names = [n for n in archive.namelist() if n.endswith(suffix)]
        if names:
            names.sort(key=len)
            return PurePosixPath(names[0]).parent.parent, manifest_dir
    return None


def load_manifest_from_archive(
    archive: zipfile.ZipFile, plugin_root: PurePosixPath, manifest_dir: str
) -> dict | None:
    """Load plugin.json from the archive at the given root."""
    manifest_name = plugin_root.joinpath(manifest_dir, "plugin.json").as_posix()
    try:
        return json.loads(archive.read(manifest_name).decode("utf-8"))
    except (KeyError, json.JSONDecodeError):
        return None


# ---------------------------------------------------------------------------
# Validation logic (shared between local and remote)
# ---------------------------------------------------------------------------


def validate_manifest_fields(manifest: dict) -> tuple[list[str], list[str]]:
    """Validate manifest fields. Returns (errors, warnings).

    Grok plugins don't require an interface block (unlike Codex).
    """
    errors: list[str] = []
    warnings: list[str] = []

    for field in REQUIRED_MANIFEST_FIELDS:
        val = manifest.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            errors.append(f"Missing or empty required field: {field}")

    version = manifest.get("version", "")
    if version and not re.match(r"^\d+\.\d+\.\d+", str(version)):
        errors.append(f"Version '{version}' does not follow semver (expected MAJOR.MINOR.PATCH)")

    name = manifest.get("name", "")
    if name and re.search(r"[A-Z\s]", str(name)):
        errors.append(f"Plugin name '{name}' should be lowercase and slug-safe (no spaces or uppercase)")

    # Interface block is optional for Grok plugins
    interface = manifest.get("interface")
    if interface and isinstance(interface, dict):
        for field in OPTIONAL_INTERFACE_FIELDS:
            val = interface.get(field)
            if val is None or (isinstance(val, str) and not val.strip()):
                warnings.append(f"interface.{field} is recommended but missing")
    elif not interface:
        warnings.append("No 'interface' block in plugin.json (recommended for marketplace display)")

    return errors, warnings


def find_local_manifest(plugin_dir: Path) -> tuple[Path, str] | None:
    """Find the plugin manifest locally.

    Returns (manifest_path, manifest_dir) or None.
    """
    for manifest_dir in MANIFEST_DIRS:
        manifest_path = plugin_dir / manifest_dir / "plugin.json"
        if manifest_path.exists():
            return manifest_path, manifest_dir
    return None


def find_local_component_dirs(plugin_dir: Path) -> list[str]:
    """Check which standard component directories/files exist."""
    found = []
    for comp_dir in COMPONENT_DIRS:
        if (plugin_dir / comp_dir).is_dir():
            found.append(comp_dir)
    for comp_file in (".mcp.json", ".lsp.json", "hooks/hooks.json"):
        if (plugin_dir / comp_file).exists():
            found.append(comp_file)
    return found


def validate_local_bundle(plugin_dir: Path) -> tuple[list[str], list[str]]:
    """Validate a committed plugin directory. Returns (errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []

    rel_path = plugin_dir.relative_to(REPO_ROOT)

    if not plugin_dir.is_dir():
        errors.append(f"Plugin directory does not exist: {rel_path}")
        return errors, warnings

    result = find_local_manifest(plugin_dir)
    if result is None:
        errors.append(f"Missing .grok-plugin/plugin.json (or .claude-plugin/plugin.json) in {rel_path}")
        return errors, warnings

    manifest_path, manifest_dir = result

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        errors.append(f"plugin.json is not valid JSON: {e}")
        return errors, warnings

    manifest_errors, manifest_warnings = validate_manifest_fields(manifest)
    errors.extend(manifest_errors)
    warnings.extend(manifest_warnings)

    # Check for at least one component
    components = find_local_component_dirs(plugin_dir)
    if not components:
        warnings.append(
            f"No standard plugin components found (expected at least one of: "
            f"{', '.join(COMPONENT_DIRS)}, .mcp.json, .lsp.json, hooks/hooks.json)"
        )

    # Validate icon if referenced
    for key in ("logo", "icon"):
        icon_val = str(manifest.get(key, "")).strip()
        if icon_val:
            icon_rel = icon_val
            if icon_rel.startswith("./"):
                icon_rel = icon_rel[2:]
            elif icon_rel.startswith("/"):
                icon_rel = icon_rel[1:]
            icon_path = plugin_dir / icon_rel
            if not icon_path.exists():
                errors.append(f"Icon file not found: {icon_rel}")
            else:
                suffix = icon_path.suffix.lower()
                if suffix not in ICON_EXTENSIONS:
                    errors.append(f"Icon has unsupported format '{suffix}'. Use SVG (preferred) or PNG.")
                size = icon_path.stat().st_size
                if size > MAX_ICON_SIZE_BYTES:
                    errors.append(f"Icon is {size / 1024:.1f}KB, exceeds 50KB limit.")

    # README entry check (warning only)
    parts = plugin_dir.relative_to(REPO_ROOT).parts
    if len(parts) >= 3:
        owner, repo_dir = parts[1], parts[2]
        readme_content = README_PATH.read_text(encoding="utf-8") if README_PATH.exists() else ""
        repo_pattern = rf"\[([^\]]+)\]\(https://github\.com/{re.escape(owner)}/{re.escape(repo_dir)}\)"
        if not re.search(repo_pattern, readme_content):
            warnings.append(f"No README.md entry found linking to https://github.com/{owner}/{repo_dir}")

    return errors, warnings


def validate_remote_repo(owner: str, repo: str) -> tuple[list[str], list[str]]:
    """Fetch and validate a plugin from its source GitHub repo.

    Returns (errors, warnings).
    """
    errors: list[str] = []
    warnings: list[str] = []

    try:
        archive = fetch_repo_archive(owner, repo)
    except Exception as e:
        return ([f"Failed to fetch source repo https://github.com/{owner}/{repo}: {e}"], [])

    result = find_plugin_root(archive)
    if result is None:
        errors.append(
            f"Source repo https://github.com/{owner}/{repo} does not contain "
            f".grok-plugin/plugin.json or .claude-plugin/plugin.json"
        )
        return errors, warnings

    plugin_root, manifest_dir = result
    manifest = load_manifest_from_archive(archive, plugin_root, manifest_dir)
    if manifest is None:
        errors.append("Could not read valid plugin.json from source repo")
        return errors, warnings

    manifest_errors, manifest_warnings = validate_manifest_fields(manifest)
    errors.extend(manifest_errors)
    warnings.extend(manifest_warnings)

    # Check for at least one component in the archive
    names = archive.namelist()
    has_component = False
    for comp_dir in COMPONENT_DIRS:
        if any(n.startswith(f"{plugin_root.joinpath(comp_dir)}/") for n in names):
            has_component = True
            break
    for comp_file in (".mcp.json", ".lsp.json"):
        if plugin_root.joinpath(comp_file).as_posix() in names:
            has_component = True
            break
    if not has_component:
        warnings.append("No standard plugin components found in source repo")

    return errors, warnings


# ---------------------------------------------------------------------------
# Changed file detection
# ---------------------------------------------------------------------------


def get_changed_plugin_dirs(base_ref: str) -> list[Path]:
    """Find plugin directories that were added or modified in this branch."""
    output = git("diff", "--name-only", "--diff-filter=ACMR", base_ref, "--", "plugins/")
    if not output:
        return []

    changed_dirs: set[Path] = set()
    for line in output.splitlines():
        file_path = REPO_ROOT / line
        try:
            relative = file_path.relative_to(REPO_ROOT)
        except ValueError:
            continue

        if len(relative.parts) < 3 or relative.parts[0] != "plugins":
            continue

        current = file_path if file_path.is_dir() else file_path.parent
        while current != PLUGINS_DIR and PLUGINS_DIR in current.parents:
            has_manifest = any(
                (current / md / "plugin.json").exists() for md in MANIFEST_DIRS
            )
            if has_manifest:
                changed_dirs.add(current)
                break
            current = current.parent

    return sorted(changed_dirs)


def get_new_readme_entries(base_ref: str) -> list[dict[str, str]]:
    """Find new plugin entries added to README.md in this PR."""
    diff = git("diff", base_ref, "--", "README.md")
    if not diff:
        return []

    base_readme = git("show", f"{base_ref}:README.md")
    base_urls = set()
    if base_readme:
        base_urls = {m.group(2) for m in README_ENTRY_RE.finditer(base_readme)}

    new_entries: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for line in diff.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        content = line[1:]
        match = README_ENTRY_RE.match(content.strip())
        if not match:
            continue
        display_name, url, owner, repo = match.group(1), match.group(2), match.group(3), match.group(4)
        if url in seen_urls or url in base_urls:
            continue
        seen_urls.add(url)
        new_entries.append({
            "display_name": display_name,
            "url": url,
            "owner": owner,
            "repo": repo,
            "description": match.group(5),
        })

    return new_entries


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    base_ref = "--base-ref"
    base_arg = None
    for i, arg in enumerate(sys.argv):
        if arg == base_ref and i + 1 < len(sys.argv):
            base_arg = sys.argv[i + 1]

    if not base_arg:
        if os.environ.get("GITHUB_BASE_REF"):
            base_arg = f"origin/{os.environ['GITHUB_BASE_REF']}"
        else:
            base_arg = "origin/main"

    rev_parse = git("rev-parse", "--verify", base_arg)
    if not rev_parse:
        print(f"WARNING: Base ref '{base_arg}' not found, skipping validation")
        sys.exit(0)

    has_failures = False
    total_errors = 0
    total_warnings = 0

    # --- Path 1: Validate committed bundles ---
    changed_dirs = get_changed_plugin_dirs(base_arg)

    if changed_dirs:
        print(f"Validating {len(changed_dirs)} changed plugin bundle(s)...\n")
        for plugin_dir in changed_dirs:
            rel = plugin_dir.relative_to(REPO_ROOT)
            errors, warnings = validate_local_bundle(plugin_dir)

            if not errors and not warnings:
                print(f"  PASS: {rel}")
                continue

            if errors:
                has_failures = True
                total_errors += len(errors)
                print(f"  FAIL: {rel} ({len(errors)} error(s), {len(warnings)} warning(s))")
                for err in errors:
                    print(f"    x {err}")

            if warnings:
                total_warnings += len(warnings)
                for warn in warnings:
                    print(f"    ! {warn}")
            print()
    else:
        print("No plugin bundle directories changed.")

    # --- Path 2: Validate new README entries against source repos ---
    new_entries = get_new_readme_entries(base_arg)

    if new_entries:
        print(f"\nValidating {len(new_entries)} new README entry(ies) against source repos...\n")
        for entry in new_entries:
            owner, repo = entry["owner"], entry["repo"]
            label = f"{entry['display_name']} ({owner}/{repo})"

            local_dir = PLUGINS_DIR / owner / repo
            has_local = any(
                (local_dir / md / "plugin.json").exists() for md in MANIFEST_DIRS
            )
            if local_dir.exists() and has_local:
                print(f"  SKIP: {label} (local bundle exists, validated above)")
                continue

            print(f"  Fetching {owner}/{repo}...")
            errors, warnings = validate_remote_repo(owner, repo)

            if not errors:
                print(f"  PASS: {label}")
            else:
                has_failures = True
                total_errors += len(errors)
                print(f"  FAIL: {label} ({len(errors)} error(s))")
                for err in errors:
                    print(f"    x {err}")

            if warnings:
                total_warnings += len(warnings)
                for warn in warnings:
                    print(f"    ! {warn}")
            print()

    if not changed_dirs and not new_entries:
        print("No plugin directories or README entries changed. Nothing to validate.")
        sys.exit(0)

    if has_failures:
        print(f"\nValidation failed: {total_errors} error(s), {total_warnings} warning(s)")
        sys.exit(1)
    elif total_warnings:
        print(f"\nValidation passed with warnings: {total_warnings} warning(s)")
        sys.exit(0)
    else:
        print("\nAll checks passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()

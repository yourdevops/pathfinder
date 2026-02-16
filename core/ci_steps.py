"""Engine-agnostic CI step discovery and runtime parsing.

This module provides functions for discovering CI step definitions
in a repository and parsing runtime configuration, independent of
any specific CI engine.
"""

import logging
import os

import yaml

logger = logging.getLogger(__name__)


def discover_steps(repo_path: str, engine_file_name: str) -> list[dict]:
    """
    Walk repo_path looking for engine-specific step definition files.

    Searches at any depth, skipping hidden directories (starting with '.').
    Both `.yml` and `.yaml` extensions are checked when the engine_file_name
    uses either YAML extension (e.g., 'action.yml' also matches 'action.yaml').
    For each match, parses the YAML and returns a list of dicts.

    Args:
        repo_path: Path to cloned repository root.
        engine_file_name: Filename to look for, e.g., 'action.yml'.

    Returns:
        Sorted list of dicts with keys:
            - directory_path: relative path from repo_path to the directory
              containing the file
            - file_path: relative path including the actual filename found on disk
            - raw_content: parsed YAML dict
    """
    results = []

    # Build candidate filenames: include both .yml and .yaml variants
    candidates = {engine_file_name}
    stem, ext = os.path.splitext(engine_file_name)
    if ext == ".yml":
        candidates.add(stem + ".yaml")
    elif ext == ".yaml":
        candidates.add(stem + ".yml")

    for dirpath, dirnames, filenames in os.walk(repo_path):
        # Skip hidden directories
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]

        matched = candidates & set(filenames)
        if matched:
            actual_filename = next(iter(matched))
            file_path = os.path.join(dirpath, actual_filename)
            rel_dir = os.path.relpath(dirpath, repo_path)

            try:
                with open(file_path) as f:
                    content = yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                logger.warning(f"Failed to parse {actual_filename} in {rel_dir}: {e}")
                continue

            results.append(
                {
                    "directory_path": rel_dir,
                    "file_path": os.path.join(rel_dir, actual_filename),
                    "raw_content": content,
                }
            )

    return sorted(results, key=lambda x: x["directory_path"])


def parse_runtimes_yml(repo_path: str) -> dict:
    """
    Parse runtimes.yml from a steps repository.

    Supports both formats:
      - {family: {versions: [...]}}
      - {family: [...]}

    Args:
        repo_path: Path to cloned repository root.

    Returns:
        Dict mapping family name to list of version strings.
        e.g., {"python": ["3.11", "3.12", "3.13"], "node": ["18", "20", "22"]}
    """
    runtimes_path = os.path.join(repo_path, "runtimes.yml")
    if not os.path.exists(runtimes_path):
        return {}

    with open(runtimes_path) as f:
        data = yaml.safe_load(f) or {}

    result = {}
    for family, config in data.items():
        if isinstance(config, dict) and "versions" in config:
            # Format: {family: {versions: [...]}}
            result[family] = [str(v) for v in config["versions"]]
        elif isinstance(config, list):
            # Format: {family: [...]}
            result[family] = [str(v) for v in config]

    return result

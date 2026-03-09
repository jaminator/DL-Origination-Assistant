"""YAML profile loader for industry-specific configurations."""

from pathlib import Path
from typing import Any

import yaml

PROFILES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "profiles"


def load_profile(profile_name: str) -> dict[str, Any]:
    """Load an industry profile YAML file by name.

    Args:
        profile_name: Name of the profile (without .yaml extension).

    Returns:
        Parsed profile dictionary, or empty dict if not found.
    """
    path = PROFILES_DIR / f"{profile_name}.yaml"
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def list_profiles() -> list[str]:
    """List available profile names."""
    if not PROFILES_DIR.exists():
        return []
    return [p.stem for p in PROFILES_DIR.glob("*.yaml")]


def merge_profile_with_config(profile: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Merge a profile into a run config. Config values take precedence over profile values."""
    merged = {**profile}
    for key, value in config.items():
        if value is not None:
            merged[key] = value
    return merged

"""Optional config file so common flags do not have to be retyped."""

from __future__ import annotations

import configparser
import os
from typing import Any, Dict, Optional

CONFIG_ENV = "NETPROBE_CONFIG"
CONFIG_NAME = "netprobe.ini"


def candidate_paths() -> list:
    """Search order: explicit env var, then cwd, then the user config dir."""
    paths = []
    override = os.environ.get(CONFIG_ENV)
    if override:
        paths.append(override)
    paths.append(os.path.join(os.getcwd(), CONFIG_NAME))
    if os.name == "nt":
        base = os.environ.get("APPDATA")
        if base:
            paths.append(os.path.join(base, "netprobe", CONFIG_NAME))
    else:
        base = os.environ.get(
            "XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config")
        )
        paths.append(os.path.join(base, "netprobe", CONFIG_NAME))
    return paths


def _coerce(value: str) -> Any:
    """INI values are strings; turn the obvious ones into real types."""
    lowered = value.strip().lower()
    if lowered in ("true", "yes", "on"):
        return True
    if lowered in ("false", "no", "off"):
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def load(path: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """Read the first config file that exists. Missing file is not an error."""
    paths = [path] if path else candidate_paths()
    parser = configparser.ConfigParser()
    for candidate in paths:
        if candidate and os.path.isfile(candidate):
            parser.read(candidate, encoding="utf-8")
            break
    else:
        return {}
    return {
        section: {k: _coerce(v) for k, v in parser.items(section)}
        for section in parser.sections()
    }


def apply_to_parser(subparsers, config: Dict[str, Dict[str, Any]]) -> None:
    """Push config values in as argparse defaults, before anything is parsed.

    Doing it here rather than patching the namespace afterwards is what makes
    precedence work: argparse only uses a default when the flag is absent, so
    an explicit command-line value always wins without any extra bookkeeping.
    Patching after the fact cannot tell "user passed --timeout 0.6" apart from
    "0.6 is the built-in default".

    Keys that no option defines are ignored, so a typo in the file cannot
    invent an option.
    """
    shared = config.get("defaults", {})
    for name, parser in getattr(subparsers, "choices", {}).items():
        known = {
            action.dest
            for action in parser._actions
            if action.dest not in (None, "help")
        }
        merged: Dict[str, Any] = {}
        merged.update(shared)
        merged.update(config.get(name, {}))
        usable = {
            key.replace("-", "_"): value
            for key, value in merged.items()
            if key.replace("-", "_") in known
        }
        if usable:
            parser.set_defaults(**usable)

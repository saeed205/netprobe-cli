"""Command line entrypoint for netprobe."""

from __future__ import annotations

import argparse
import sys
from typing import Callable, Dict, List, Optional

from . import __version__

# Subcommand registry. Each module registers itself here so that adding a new
# command never requires touching the argument parser wiring below.
Registrar = Callable[[argparse._SubParsersAction], None]
_REGISTRARS: List[Registrar] = []


def register(fn: Registrar) -> Registrar:
    """Decorator used by command modules to hook into the CLI."""
    _REGISTRARS.append(fn)
    return fn


def _load_commands() -> None:
    """Import command modules for their registration side effects."""
    from . import commands  # noqa: F401  (imports populate the registry)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="netprobe",
        description="Everyday network diagnostics without a pile of dependencies.",
    )
    parser.add_argument(
        "--version", action="version", version=f"netprobe {__version__}"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON instead of a table",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    _load_commands()
    for registrar in _REGISTRARS:
        registrar(subparsers)
    _apply_config(parser, subparsers)
    return parser


def _apply_config(parser, subparsers) -> None:
    """Let a config file supply defaults, if one is present."""
    from . import config

    settings = config.load()
    if not settings:
        return
    shared = settings.get("defaults", {})
    if "json" in shared:
        parser.set_defaults(json=bool(shared["json"]))
    config.apply_to_parser(subparsers, settings)


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 2
    try:
        return int(args.handler(args) or 0)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

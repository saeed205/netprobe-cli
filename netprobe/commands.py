"""Aggregates the command modules so the CLI registry gets populated."""

from __future__ import annotations

# Importing a module here is enough - each one calls cli.register() at import
# time. Keep the list alphabetical so merge conflicts stay trivial.
from . import ipmath, latency, output  # noqa: F401

_MODULES = ["ipmath", "latency", "output"]


def loaded() -> list:
    """Return the names of command modules that were successfully imported."""
    return sorted(_MODULES)

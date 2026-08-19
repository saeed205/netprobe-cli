"""Rendering helpers: a plain table, or JSON when piping into something else."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Sequence


def _stringify(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def render_table(rows: Sequence[Dict[str, Any]]) -> str:
    """Left-aligned columns padded to the widest cell."""
    if not rows:
        return "(no results)"
    columns: List[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    widths = {
        col: max(len(col), *(len(_stringify(r.get(col))) for r in rows))
        for col in columns
    }
    header = "  ".join(col.upper().ljust(widths[col]) for col in columns)
    rule = "  ".join("-" * widths[col] for col in columns)
    body = [
        "  ".join(_stringify(row.get(col)).ljust(widths[col]) for col in columns)
        for row in rows
    ]
    return "\n".join([header.rstrip(), rule] + [line.rstrip() for line in body])


def render_vertical(row: Dict[str, Any]) -> str:
    """Key/value listing - easier to read than a very wide single-row table."""
    if not row:
        return "(no results)"
    width = max(len(k) for k in row)
    return "\n".join(
        "%s : %s" % (key.ljust(width), _stringify(value)) for key, value in row.items()
    )


def emit(
    rows: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
    vertical: bool = False,
) -> None:
    """Print results honouring the global --json flag."""
    if getattr(args, "json", False):
        payload = rows[0] if (vertical and len(rows) == 1) else list(rows)
        json.dump(payload, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
        return
    if vertical and len(rows) == 1:
        print(render_vertical(rows[0]))
    else:
        print(render_table(rows))

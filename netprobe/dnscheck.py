"""Forward and reverse name resolution checks."""

from __future__ import annotations

import argparse
import socket
import time
from typing import Dict, List

from .cli import register


def resolve(name: str, family: str = "any") -> Dict[str, object]:
    """Resolve a name to every address the resolver knows about."""
    families = {
        "any": socket.AF_UNSPEC,
        "v4": socket.AF_INET,
        "v6": socket.AF_INET6,
    }
    if family not in families:
        raise ValueError("family must be one of: %s" % ", ".join(families))

    start = time.perf_counter()
    try:
        infos = socket.getaddrinfo(name, None, families[family], socket.SOCK_STREAM)
    except socket.gaierror as exc:
        return {
            "name": name,
            "resolved": False,
            "error": exc.strerror or str(exc),
            "elapsed_ms": round((time.perf_counter() - start) * 1000, 2),
        }
    elapsed = (time.perf_counter() - start) * 1000

    # getaddrinfo repeats an address once per socket type; collapse them.
    addresses: List[str] = []
    for info in infos:
        addr = info[4][0]
        if addr not in addresses:
            addresses.append(addr)
    return {
        "name": name,
        "resolved": True,
        "addresses": addresses,
        "count": len(addresses),
        "elapsed_ms": round(elapsed, 2),
    }


def reverse(address: str) -> Dict[str, object]:
    """PTR lookup for an address."""
    start = time.perf_counter()
    try:
        hostname, aliases, _ = socket.gethostbyaddr(address)
    except (socket.herror, socket.gaierror, OSError) as exc:
        return {
            "address": address,
            "resolved": False,
            "error": getattr(exc, "strerror", None) or str(exc),
            "elapsed_ms": round((time.perf_counter() - start) * 1000, 2),
        }
    return {
        "address": address,
        "resolved": True,
        "hostname": hostname,
        "aliases": aliases or [],
        "elapsed_ms": round((time.perf_counter() - start) * 1000, 2),
    }


def round_trip(name: str) -> Dict[str, object]:
    """Resolve a name, then PTR the first address back.

    A mismatch is not necessarily broken - shared hosting and CDNs make forward
    and reverse records disagree all the time - but it is worth surfacing.
    """
    forward = resolve(name)
    if not forward.get("resolved"):
        return forward
    first = forward["addresses"][0]
    back = reverse(first)
    ptr = back.get("hostname") or ""
    return {
        "name": name,
        "address": first,
        "ptr": ptr or "-",
        "matches": ptr.rstrip(".") == name.rstrip("."),
    }


def _handle(args: argparse.Namespace) -> int:
    from .output import emit

    if args.reverse:
        row = reverse(args.target)
    elif args.round_trip:
        row = round_trip(args.target)
    else:
        row = resolve(args.target, args.family)
    emit([row], args, vertical=True)
    return 0 if row.get("resolved", True) else 1


@register
def _add_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("dns", help="forward, reverse and round-trip lookups")
    p.add_argument("target", help="hostname to resolve, or address with --reverse")
    p.add_argument("-x", "--reverse", action="store_true", help="PTR lookup")
    p.add_argument(
        "-r", "--round-trip", action="store_true",
        help="resolve then PTR the first address back",
    )
    p.add_argument("-f", "--family", choices=("any", "v4", "v6"), default="any")
    p.set_defaults(handler=_handle)

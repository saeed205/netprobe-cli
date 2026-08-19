"""Subnet arithmetic: the questions you actually ask a calculator for."""

from __future__ import annotations

import argparse
import ipaddress
from typing import Dict, List, Union

from .cli import register

Network = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]


def describe(cidr: str) -> Dict[str, object]:
    """Return the interesting facts about a CIDR block."""
    net = ipaddress.ip_network(cidr, strict=False)
    usable = usable_hosts(net)
    return {
        "network": str(net.network_address),
        "prefix": net.prefixlen,
        "netmask": str(net.netmask),
        "wildcard": str(net.hostmask),
        "broadcast": str(net.broadcast_address) if net.version == 4 else None,
        "total_addresses": net.num_addresses,
        "usable_hosts": usable,
        "first_host": str(next(iter(net.hosts()), net.network_address)),
        "last_host": _last_host(net),
        "version": net.version,
        "is_private": net.is_private,
    }


def usable_hosts(net: Network) -> int:
    """Host count excluding network and broadcast, with the /31 and /32 cases.

    RFC 3021 makes a /31 a valid two-host point-to-point link, and a /32 is a
    single host route - neither reserves a broadcast address.
    """
    if net.version == 6:
        return net.num_addresses
    if net.prefixlen >= 31:
        return net.num_addresses
    return net.num_addresses - 2


def _last_host(net: Network) -> str:
    if net.prefixlen >= 31 or net.version == 6:
        return str(net.broadcast_address)
    return str(net.broadcast_address - 1)


def split(cidr: str, new_prefix: int) -> List[str]:
    """Split a block into equal subnets of the given prefix length."""
    net = ipaddress.ip_network(cidr, strict=False)
    if new_prefix < net.prefixlen:
        raise ValueError(
            "cannot split /%d into larger /%d blocks" % (net.prefixlen, new_prefix)
        )
    return [str(sub) for sub in net.subnets(new_prefix=new_prefix)]


def contains(cidr: str, address: str) -> bool:
    """True when the address falls inside the block."""
    return ipaddress.ip_address(address) in ipaddress.ip_network(cidr, strict=False)


def summarize(addresses: List[str]) -> List[str]:
    """Collapse a list of addresses/blocks into the smallest covering set."""
    nets: List[Network] = [
        ipaddress.ip_network(a, strict=False) for a in addresses
    ]
    return [str(n) for n in ipaddress.collapse_addresses(nets)]


def _handle(args: argparse.Namespace) -> int:
    from .output import emit

    if args.split_into is not None:
        emit([{"subnet": s} for s in split(args.cidr, args.split_into)], args)
    elif args.contains:
        inside = contains(args.cidr, args.contains)
        emit([{"address": args.contains, "in_network": inside}], args)
        return 0 if inside else 1
    else:
        emit([describe(args.cidr)], args, vertical=True)
    return 0


@register
def _add_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "subnet", help="subnet math: describe, split or test a CIDR block"
    )
    p.add_argument("cidr", help="a CIDR block, e.g. 10.0.0.0/24")
    p.add_argument(
        "--split-into",
        type=int,
        metavar="PREFIX",
        help="split the block into equal /PREFIX subnets",
    )
    p.add_argument(
        "--contains", metavar="ADDR", help="exit 0 if ADDR falls inside the block"
    )
    p.set_defaults(handler=_handle)

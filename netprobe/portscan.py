"""Threaded TCP port sweep over a host or a whole subnet."""

from __future__ import annotations

import argparse
import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Iterable, List, Tuple

from .cli import register

# Ports worth checking when the user does not name any.
COMMON_PORTS: Tuple[int, ...] = (
    21, 22, 23, 25, 53, 80, 110, 143, 443, 445,
    993, 995, 1433, 3306, 3389, 5432, 6379, 8080, 8443, 27017,
)

WELL_KNOWN: Dict[int, str] = {
    21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp", 53: "dns",
    80: "http", 110: "pop3", 143: "imap", 443: "https", 445: "smb",
    993: "imaps", 995: "pop3s", 1433: "mssql", 3306: "mysql",
    3389: "rdp", 5432: "postgres", 6379: "redis", 8080: "http-alt",
    8443: "https-alt", 27017: "mongodb",
}


def parse_ports(spec: str) -> List[int]:
    """Accept `22`, `22,80`, `1-1024` and any mix of those."""
    ports: List[int] = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            start_s, _, end_s = chunk.partition("-")
            start, end = int(start_s), int(end_s)
            if start > end:
                raise ValueError("port range %s is reversed" % chunk)
            ports.extend(range(start, end + 1))
        else:
            ports.append(int(chunk))
    for port in ports:
        if not 1 <= port <= 65535:
            raise ValueError("port %d out of range" % port)
    # Preserve order but drop duplicates.
    return list(dict.fromkeys(ports))


def expand_targets(target: str) -> List[str]:
    """A hostname stays as-is; a CIDR block expands to its hosts."""
    try:
        net = ipaddress.ip_network(target, strict=False)
    except ValueError:
        return [target]
    if net.num_addresses == 1:
        return [str(net.network_address)]
    return [str(ip) for ip in net.hosts()]


def check(host: str, port: int, timeout: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def sweep(targets: Iterable[str], ports: Iterable[int], timeout: float,
          workers: int) -> List[Dict[str, object]]:
    pairs = [(h, p) for h in targets for p in ports]
    open_rows: List[Dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {
            pool.submit(check, host, port, timeout): (host, port)
            for host, port in pairs
        }
        for future in as_completed(futures):
            host, port = futures[future]
            if future.result():
                open_rows.append({
                    "host": host,
                    "port": port,
                    "service": WELL_KNOWN.get(port, "-"),
                })
    open_rows.sort(key=lambda r: (r["host"], r["port"]))
    return open_rows


def _handle(args: argparse.Namespace) -> int:
    from .output import emit

    ports = parse_ports(args.ports) if args.ports else list(COMMON_PORTS)
    targets = expand_targets(args.target)
    rows = sweep(targets, ports, args.timeout, args.workers)
    emit(rows, args)
    return 0 if rows else 1


@register
def _add_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "scan", help="TCP port sweep across a host or CIDR block"
    )
    p.add_argument("target", help="hostname, IP, or CIDR such as 10.0.0.0/28")
    p.add_argument(
        "-p", "--ports", help="ports: 22, 22,80,443 or 1-1024 (default: common ports)"
    )
    p.add_argument("-t", "--timeout", type=float, default=0.6)
    p.add_argument("-w", "--workers", type=int, default=64)
    p.set_defaults(handler=_handle)

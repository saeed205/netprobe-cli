"""TCP connect latency with the statistics that actually matter."""

from __future__ import annotations

import argparse
import socket
import time
from typing import Dict, List, Optional

from .cli import register


def probe_once(host: str, port: int, timeout: float) -> Optional[float]:
    """Time a single TCP handshake in milliseconds, or None if it failed.

    A TCP connect is used rather than ICMP on purpose: raw sockets need root,
    and "can I open the port" is usually the question being asked anyway.
    """
    start = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
    except OSError:
        return None
    return (time.perf_counter() - start) * 1000.0


def percentile(samples: List[float], pct: float) -> float:
    """Linear-interpolated percentile. `samples` need not be sorted."""
    if not samples:
        raise ValueError("no samples")
    ordered = sorted(samples)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * (pct / 100.0)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    weight = rank - low
    return ordered[low] * (1 - weight) + ordered[high] * weight


def jitter(samples: List[float]) -> float:
    """Mean absolute difference between consecutive samples (RFC 3550 idea)."""
    if len(samples) < 2:
        return 0.0
    deltas = [abs(b - a) for a, b in zip(samples, samples[1:])]
    return sum(deltas) / len(deltas)


def summarize(host: str, port: int, count: int, timeout: float,
              interval: float) -> Dict[str, object]:
    samples: List[float] = []
    lost = 0
    for i in range(count):
        if i:
            time.sleep(interval)
        result = probe_once(host, port, timeout)
        if result is None:
            lost += 1
        else:
            samples.append(result)
    row: Dict[str, object] = {
        "target": "%s:%d" % (host, port),
        "sent": count,
        "received": len(samples),
        "loss_pct": round(lost * 100.0 / count, 1) if count else 0.0,
    }
    if samples:
        row.update({
            "min_ms": round(min(samples), 2),
            "avg_ms": round(sum(samples) / len(samples), 2),
            "p95_ms": round(percentile(samples, 95), 2),
            "max_ms": round(max(samples), 2),
            "jitter_ms": round(jitter(samples), 2),
        })
    return row


def _handle(args: argparse.Namespace) -> int:
    from .output import emit

    row = summarize(args.host, args.port, args.count, args.timeout, args.interval)
    emit([row], args, vertical=True)
    return 0 if row["received"] else 1


@register
def _add_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "latency", help="measure TCP connect latency, loss and jitter"
    )
    p.add_argument("host")
    p.add_argument("-p", "--port", type=int, default=443)
    p.add_argument("-c", "--count", type=int, default=5, help="probes to send")
    p.add_argument("-t", "--timeout", type=float, default=2.0)
    p.add_argument(
        "-i", "--interval", type=float, default=0.2, help="seconds between probes"
    )
    p.set_defaults(handler=_handle)

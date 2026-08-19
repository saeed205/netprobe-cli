"""HTTP endpoint health checks, redirect chains included."""

from __future__ import annotations

import argparse
import http.client
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, List, Optional

from .cli import register

DEFAULT_UA = "netprobe/0.1 (+https://github.com/saeed205/netprobe-cli)"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Stop urllib from following redirects so we can walk them ourselves."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _opener(verify: bool) -> urllib.request.OpenerDirector:
    handlers: List[urllib.request.BaseHandler] = [_NoRedirect()]
    if not verify:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        handlers.append(urllib.request.HTTPSHandler(context=context))
    return urllib.request.build_opener(*handlers)


def fetch(url: str, timeout: float, verify: bool = True,
          method: str = "GET") -> Dict[str, object]:
    """One request, no redirect following."""
    request = urllib.request.Request(url, method=method)
    request.add_header("User-Agent", DEFAULT_UA)
    start = time.perf_counter()
    try:
        with _opener(verify).open(request, timeout=timeout) as response:
            body = response.read(2048)
            status, headers = response.status, dict(response.headers)
    except urllib.error.HTTPError as exc:
        # 3xx and 4xx/5xx arrive here; they are still useful answers.
        body = exc.read(2048)
        status, headers = exc.code, dict(exc.headers or {})
    except (urllib.error.URLError, ssl.SSLError, http.client.HTTPException,
            OSError) as exc:
        return {
            "url": url,
            "ok": False,
            "error": str(getattr(exc, "reason", exc)),
            "elapsed_ms": round((time.perf_counter() - start) * 1000, 2),
        }
    elapsed = (time.perf_counter() - start) * 1000
    return {
        "url": url,
        "ok": 200 <= status < 400,
        "status": status,
        "location": headers.get("Location"),
        "server": headers.get("Server", "-"),
        "content_type": headers.get("Content-Type", "-"),
        "bytes_sampled": len(body),
        "elapsed_ms": round(elapsed, 2),
    }


def follow(url: str, timeout: float, verify: bool = True,
           max_hops: int = 10) -> List[Dict[str, object]]:
    """Walk the redirect chain, guarding against loops."""
    hops: List[Dict[str, object]] = []
    seen = set()
    current: Optional[str] = url
    while current and len(hops) < max_hops:
        if current in seen:
            hops.append({"url": current, "ok": False, "error": "redirect loop"})
            break
        seen.add(current)
        hop = fetch(current, timeout, verify)
        hops.append(hop)
        location = hop.get("location")
        status = hop.get("status")
        if not location or not (isinstance(status, int) and 300 <= status < 400):
            break
        current = urllib.parse.urljoin(current, str(location))
    return hops


def _handle(args: argparse.Namespace) -> int:
    from .output import emit

    url = args.url
    if "://" not in url:
        url = "https://" + url
    if args.follow:
        rows = follow(url, args.timeout, not args.insecure)
        emit(rows, args)
        return 0 if rows and rows[-1].get("ok") else 1
    row = fetch(url, args.timeout, not args.insecure, "HEAD" if args.head else "GET")
    emit([row], args, vertical=True)
    return 0 if row.get("ok") else 1


@register
def _add_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("http", help="HTTP endpoint health and redirect chain")
    p.add_argument("url", help="URL; the https:// scheme is assumed if omitted")
    p.add_argument("-L", "--follow", action="store_true", help="walk redirects")
    p.add_argument("-I", "--head", action="store_true", help="send HEAD not GET")
    p.add_argument("-t", "--timeout", type=float, default=10.0)
    p.add_argument("-k", "--insecure", action="store_true",
                   help="skip TLS verification")
    p.set_defaults(handler=_handle)

"""MAC address normalisation and OUI vendor lookup."""

from __future__ import annotations

import argparse
import re
from typing import Dict, List, Optional

from .cli import register

_SEPARATORS = re.compile(r"[\s:.\-]")
_HEX12 = re.compile(r"^[0-9a-f]{12}$")

# A small built-in table of the vendors that turn up most often on an office
# LAN. Anything broader belongs in an external OUI file rather than in source
# control - see load_oui_file().
BUILTIN_OUI: Dict[str, str] = {
    "000C29": "VMware, Inc.",
    "005056": "VMware, Inc.",
    "001C14": "VMware, Inc.",
    "080027": "Oracle VirtualBox virtual NIC",
    "525400": "QEMU/KVM virtual NIC",
    "0050F2": "Microsoft Corporation",
    "00155D": "Microsoft Hyper-V",
    "001B21": "Intel Corporate",
    "3C970E": "Intel Corporate",
    "00E04C": "Realtek Semiconductor",
    "001A2B": "Cisco Systems, Inc.",
    "00000C": "Cisco Systems, Inc.",
    "0023AB": "Cisco Systems, Inc.",
    "F0F755": "Cisco Systems, Inc.",
    "001DE1": "Cisco Systems, Inc.",
    "B827EB": "Raspberry Pi Foundation",
    "DCA632": "Raspberry Pi Trading Ltd",
    "E45F01": "Raspberry Pi Trading Ltd",
    "001124": "Apple, Inc.",
    "AC87A3": "Apple, Inc.",
    "F0189E": "Apple, Inc.",
    "0018DE": "Hewlett Packard",
    "3CD92B": "Hewlett Packard",
    "0024E8": "Dell Inc.",
    "B8CA3A": "Dell Inc.",
    "001EC9": "Dell Inc.",
    "FCECDA": "Ubiquiti Networks",
    "245A4C": "Ubiquiti Networks",
    "D8B122": "MikroTik",
    "4C5E0C": "MikroTik",
    "6C3B6B": "Huawei Technologies",
    "001882": "Huawei Technologies",
    "8CFDF0": "Qualcomm",
    "3C5AB4": "Google, Inc.",
    "F4F5D8": "Google, Inc.",
    "001A11": "Google, Inc.",
    "0017FA": "Samsung Electronics",
    "5CF6DC": "Samsung Electronics",
    "0026B9": "Dell Inc.",
}


def normalize(mac: str) -> str:
    """Strip separators and validate, returning 12 lowercase hex digits.

    Accepts every format that gets pasted into a ticket: `aa:bb:cc:dd:ee:ff`,
    `AA-BB-CC-DD-EE-FF`, Cisco style `aabb.ccdd.eeff`, or bare hex.
    """
    stripped = _SEPARATORS.sub("", mac).lower()
    if not _HEX12.match(stripped):
        raise ValueError("not a 48-bit MAC address: %r" % mac)
    return stripped


def format_mac(mac: str, style: str = "colon") -> str:
    """Re-render a MAC in a chosen notation."""
    h = normalize(mac)
    if style == "colon":
        return ":".join(h[i:i + 2] for i in range(0, 12, 2))
    if style == "hyphen":
        return "-".join(h[i:i + 2] for i in range(0, 12, 2)).upper()
    if style == "cisco":
        return ".".join(h[i:i + 4] for i in range(0, 12, 4))
    if style == "bare":
        return h
    raise ValueError("unknown style: %s" % style)


def oui(mac: str) -> str:
    """The 24-bit Organisationally Unique Identifier, uppercase hex."""
    return normalize(mac)[:6].upper()


def is_locally_administered(mac: str) -> bool:
    """Bit 1 of the first octet: set means the address was assigned locally.

    Randomised phone MACs and most virtual interfaces set this, which is why
    an OUI lookup on them is meaningless.
    """
    return bool(int(normalize(mac)[:2], 16) & 0b10)


def is_multicast(mac: str) -> bool:
    """Bit 0 of the first octet: set means a group address, not a single NIC."""
    return bool(int(normalize(mac)[:2], 16) & 0b1)


def load_oui_file(path: str) -> Dict[str, str]:
    """Read extra `OUI,Vendor` pairs from a CSV-ish file, `#` for comments."""
    table: Dict[str, str] = {}
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            prefix, _, vendor = line.partition(",")
            prefix = _SEPARATORS.sub("", prefix).upper()
            if len(prefix) == 6 and vendor.strip():
                table[prefix] = vendor.strip()
    return table


def lookup(mac: str, extra: Optional[Dict[str, str]] = None) -> Dict[str, object]:
    prefix = oui(mac)
    table = dict(BUILTIN_OUI)
    if extra:
        table.update(extra)
    local = is_locally_administered(mac)
    return {
        "mac": format_mac(mac, "colon"),
        "oui": prefix,
        "vendor": table.get(prefix, "unknown"),
        "locally_administered": local,
        "multicast": is_multicast(mac),
        "note": "randomised or virtual - OUI is not meaningful" if local else "-",
        "cisco": format_mac(mac, "cisco"),
    }


def _handle(args: argparse.Namespace) -> int:
    from .output import emit

    extra = load_oui_file(args.oui_file) if args.oui_file else None
    rows: List[Dict[str, object]] = [lookup(m, extra) for m in args.mac]
    emit(rows, args, vertical=len(rows) == 1)
    return 0


@register
def _add_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("mac", help="normalise a MAC and look up its vendor")
    p.add_argument("mac", nargs="+", help="one or more MAC addresses, any notation")
    p.add_argument(
        "--oui-file", metavar="PATH",
        help="extra OUI,Vendor pairs to merge over the built-in table",
    )
    p.set_defaults(handler=_handle)

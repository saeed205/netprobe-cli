"""Tests for MAC normalisation, flag bits and OUI lookup."""

import re
import unittest

from netprobe import macvendor


class TestNormalize(unittest.TestCase):
    def test_every_common_notation_round_trips(self):
        for text in (
            "00:0c:29:ab:cd:ef",
            "00-0C-29-AB-CD-EF",
            "000c.29ab.cdef",
            "000C29ABCDEF",
            "00 0c 29 ab cd ef",
        ):
            self.assertEqual(macvendor.normalize(text), "000c29abcdef", text)

    def test_too_short_rejected(self):
        with self.assertRaises(ValueError):
            macvendor.normalize("00:0c:29:ab:cd")

    def test_too_long_rejected(self):
        with self.assertRaises(ValueError):
            macvendor.normalize("00:0c:29:ab:cd:ef:11")

    def test_non_hex_rejected(self):
        with self.assertRaises(ValueError):
            macvendor.normalize("zz:0c:29:ab:cd:ef")


class TestFormat(unittest.TestCase):
    def test_styles(self):
        mac = "000c29abcdef"
        self.assertEqual(macvendor.format_mac(mac, "colon"), "00:0c:29:ab:cd:ef")
        self.assertEqual(macvendor.format_mac(mac, "hyphen"), "00-0C-29-AB-CD-EF")
        self.assertEqual(macvendor.format_mac(mac, "cisco"), "000c.29ab.cdef")
        self.assertEqual(macvendor.format_mac(mac, "bare"), "000c29abcdef")

    def test_unknown_style_rejected(self):
        with self.assertRaises(ValueError):
            macvendor.format_mac("000c29abcdef", "morse")


class TestFlagBits(unittest.TestCase):
    """First octet: bit 0 is multicast, bit 1 is locally administered."""

    def test_universally_administered_unicast(self):
        self.assertFalse(macvendor.is_locally_administered("00:0c:29:ab:cd:ef"))
        self.assertFalse(macvendor.is_multicast("00:0c:29:ab:cd:ef"))

    def test_locally_administered(self):
        # 0x02 -> bit 1 set. Typical of randomised phone MACs.
        self.assertTrue(macvendor.is_locally_administered("02:11:22:33:44:55"))
        self.assertFalse(macvendor.is_multicast("02:11:22:33:44:55"))

    def test_multicast(self):
        # 01:00:5e:.. is the IPv4 multicast range.
        self.assertTrue(macvendor.is_multicast("01:00:5e:00:00:01"))

    def test_broadcast_is_both(self):
        self.assertTrue(macvendor.is_multicast("ff:ff:ff:ff:ff:ff"))
        self.assertTrue(macvendor.is_locally_administered("ff:ff:ff:ff:ff:ff"))


class TestLookup(unittest.TestCase):
    def test_known_vendors(self):
        self.assertEqual(
            macvendor.lookup("00:0c:29:11:22:33")["vendor"], "VMware, Inc."
        )
        self.assertEqual(
            macvendor.lookup("b8:27:eb:11:22:33")["vendor"],
            "Raspberry Pi Foundation",
        )

    def test_unknown_prefix(self):
        self.assertEqual(macvendor.lookup("aa:bb:cc:dd:ee:ff")["vendor"], "unknown")

    def test_randomised_mac_is_annotated_rather_than_just_unknown(self):
        row = macvendor.lookup("02:11:22:33:44:55")
        self.assertTrue(row["locally_administered"])
        self.assertIn("randomised", str(row["note"]))

    def test_extra_table_overrides_builtin(self):
        row = macvendor.lookup("00:0c:29:11:22:33", {"000C29": "Overridden"})
        self.assertEqual(row["vendor"], "Overridden")

    def test_extra_table_does_not_mutate_builtin(self):
        macvendor.lookup("00:0c:29:11:22:33", {"000C29": "Overridden"})
        self.assertEqual(macvendor.BUILTIN_OUI["000C29"], "VMware, Inc.")

    def test_oui_is_uppercase_six_hex(self):
        self.assertEqual(macvendor.oui("00:0c:29:ab:cd:ef"), "000C29")


class TestBuiltinTable(unittest.TestCase):
    def test_every_key_is_well_formed(self):
        bad = [k for k in macvendor.BUILTIN_OUI if not re.match(r"^[0-9A-F]{6}$", k)]
        self.assertEqual(bad, [])

    def test_no_empty_vendor_strings(self):
        self.assertTrue(all(v.strip() for v in macvendor.BUILTIN_OUI.values()))


if __name__ == "__main__":
    unittest.main()

"""Tests for subnet arithmetic, with the boundary prefixes pinned down."""

import unittest

from netprobe import ipmath


class TestDescribe(unittest.TestCase):
    def test_ordinary_v4_block(self):
        info = ipmath.describe("10.20.30.0/26")
        self.assertEqual(info["netmask"], "255.255.255.192")
        self.assertEqual(info["wildcard"], "0.0.0.63")
        self.assertEqual(info["broadcast"], "10.20.30.63")
        self.assertEqual(info["total_addresses"], 64)
        self.assertEqual(info["usable_hosts"], 62)
        self.assertEqual(info["first_host"], "10.20.30.1")
        self.assertEqual(info["last_host"], "10.20.30.62")
        self.assertTrue(info["is_private"])

    def test_host_bits_set_are_tolerated(self):
        # strict=False, so 10.20.30.77/26 describes the block it falls in.
        self.assertEqual(ipmath.describe("10.20.30.77/26")["network"], "10.20.30.64")

    def test_public_block_flagged(self):
        self.assertFalse(ipmath.describe("8.8.8.0/24")["is_private"])

    def test_ipv6(self):
        info = ipmath.describe("2001:db8::/126")
        self.assertEqual(info["version"], 6)
        self.assertIsNone(info["broadcast"])
        self.assertEqual(info["usable_hosts"], 4)


class TestUsableHosts(unittest.TestCase):
    """The whole point of the module - subtracting 2 blindly is the usual bug."""

    def test_slash_31_is_a_point_to_point_link(self):
        # RFC 3021: a /31 has two usable hosts, not zero.
        self.assertEqual(ipmath.describe("192.168.1.0/31")["usable_hosts"], 2)

    def test_slash_32_is_a_host_route(self):
        self.assertEqual(ipmath.describe("192.168.1.5/32")["usable_hosts"], 1)

    def test_slash_30_reserves_network_and_broadcast(self):
        self.assertEqual(ipmath.describe("192.168.1.0/30")["usable_hosts"], 2)

    def test_slash_24(self):
        self.assertEqual(ipmath.describe("192.168.1.0/24")["usable_hosts"], 254)

    def test_ipv6_reserves_nothing(self):
        self.assertEqual(ipmath.describe("2001:db8::/127")["usable_hosts"], 2)


class TestSplit(unittest.TestCase):
    def test_split_into_quarters(self):
        self.assertEqual(
            ipmath.split("10.0.0.0/24", 26),
            ["10.0.0.0/26", "10.0.0.64/26", "10.0.0.128/26", "10.0.0.192/26"],
        )

    def test_split_to_same_prefix_is_identity(self):
        self.assertEqual(ipmath.split("10.0.0.0/24", 24), ["10.0.0.0/24"])

    def test_split_into_larger_block_rejected(self):
        with self.assertRaises(ValueError):
            ipmath.split("10.0.0.0/24", 16)


class TestContains(unittest.TestCase):
    def test_inside(self):
        self.assertTrue(ipmath.contains("10.0.0.0/8", "10.4.5.6"))

    def test_outside(self):
        self.assertFalse(ipmath.contains("10.0.0.0/8", "11.4.5.6"))

    def test_network_address_counts(self):
        self.assertTrue(ipmath.contains("10.0.0.0/24", "10.0.0.0"))

    def test_broadcast_counts(self):
        self.assertTrue(ipmath.contains("10.0.0.0/24", "10.0.0.255"))


class TestSummarize(unittest.TestCase):
    def test_adjacent_blocks_collapse(self):
        self.assertEqual(
            ipmath.summarize(["10.0.0.0/25", "10.0.0.128/25"]), ["10.0.0.0/24"]
        )

    def test_disjoint_blocks_are_kept(self):
        self.assertEqual(
            ipmath.summarize(["10.0.0.0/24", "192.168.0.0/24"]),
            ["10.0.0.0/24", "192.168.0.0/24"],
        )

    def test_bare_addresses_become_host_routes(self):
        self.assertEqual(ipmath.summarize(["10.0.0.1"]), ["10.0.0.1/32"])


class TestInvalidInput(unittest.TestCase):
    def test_garbage_cidr(self):
        with self.assertRaises(ValueError):
            ipmath.describe("not-a-network")

    def test_prefix_out_of_range(self):
        with self.assertRaises(ValueError):
            ipmath.describe("10.0.0.0/33")


if __name__ == "__main__":
    unittest.main()

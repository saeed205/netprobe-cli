"""Tests for the pure helpers in portscan, latency and config.

Nothing here touches the network - only parsing, statistics and precedence.
"""

import argparse
import os
import tempfile
import unittest

from netprobe import config, latency, portscan


class TestParsePorts(unittest.TestCase):
    def test_single(self):
        self.assertEqual(portscan.parse_ports("22"), [22])

    def test_list(self):
        self.assertEqual(portscan.parse_ports("22,80,443"), [22, 80, 443])

    def test_range(self):
        self.assertEqual(portscan.parse_ports("20-23"), [20, 21, 22, 23])

    def test_mixed_and_whitespace(self):
        self.assertEqual(portscan.parse_ports(" 22 , 80-82 "), [22, 80, 81, 82])

    def test_duplicates_dropped_but_order_kept(self):
        self.assertEqual(portscan.parse_ports("80,22,80"), [80, 22])

    def test_reversed_range_rejected(self):
        with self.assertRaises(ValueError):
            portscan.parse_ports("100-1")

    def test_zero_rejected(self):
        with self.assertRaises(ValueError):
            portscan.parse_ports("0")

    def test_above_65535_rejected(self):
        with self.assertRaises(ValueError):
            portscan.parse_ports("65536")

    def test_trailing_comma_tolerated(self):
        self.assertEqual(portscan.parse_ports("22,"), [22])


class TestExpandTargets(unittest.TestCase):
    def test_hostname_passes_through(self):
        self.assertEqual(portscan.expand_targets("example.com"), ["example.com"])

    def test_bare_address_is_one_target(self):
        self.assertEqual(portscan.expand_targets("10.0.0.5"), ["10.0.0.5"])

    def test_slash_30_yields_two_hosts(self):
        self.assertEqual(
            portscan.expand_targets("192.168.5.0/30"), ["192.168.5.1", "192.168.5.2"]
        )

    def test_slash_32_yields_the_address_itself(self):
        self.assertEqual(portscan.expand_targets("10.0.0.5/32"), ["10.0.0.5"])


class TestWellKnownTable(unittest.TestCase):
    def test_every_default_port_has_a_service_name(self):
        missing = [p for p in portscan.COMMON_PORTS if p not in portscan.WELL_KNOWN]
        self.assertEqual(missing, [])


class TestPercentile(unittest.TestCase):
    def test_bounds(self):
        samples = [10.0, 20.0, 30.0, 40.0]
        self.assertEqual(latency.percentile(samples, 0), 10.0)
        self.assertEqual(latency.percentile(samples, 100), 40.0)

    def test_interpolates_between_samples(self):
        self.assertEqual(latency.percentile([10.0, 20.0, 30.0, 40.0], 50), 25.0)

    def test_unsorted_input_is_handled(self):
        self.assertEqual(latency.percentile([40.0, 10.0, 30.0, 20.0], 50), 25.0)

    def test_single_sample(self):
        self.assertEqual(latency.percentile([7.5], 95), 7.5)

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            latency.percentile([], 95)


class TestJitter(unittest.TestCase):
    def test_steady_stream_has_no_jitter(self):
        self.assertEqual(latency.jitter([10.0, 10.0, 10.0]), 0.0)

    def test_mean_absolute_delta(self):
        # deltas: 4, 2, 8 -> mean 4.666...
        self.assertAlmostEqual(latency.jitter([10.0, 14.0, 12.0, 20.0]), 14.0 / 3)

    def test_fewer_than_two_samples(self):
        self.assertEqual(latency.jitter([10.0]), 0.0)
        self.assertEqual(latency.jitter([]), 0.0)


class TestConfigCoerce(unittest.TestCase):
    def test_booleans(self):
        for text in ("true", "TRUE", "yes", "on"):
            self.assertIs(config._coerce(text), True, text)
        for text in ("false", "No", "off"):
            self.assertIs(config._coerce(text), False, text)

    def test_numbers(self):
        self.assertEqual(config._coerce("128"), 128)
        self.assertEqual(config._coerce("0.4"), 0.4)

    def test_strings_pass_through(self):
        self.assertEqual(config._coerce("22,80,443"), "22,80,443")


class TestConfigPrecedence(unittest.TestCase):
    """A config value is a default; an explicit flag must always beat it."""

    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".ini")
        with os.fdopen(handle, "w", encoding="utf-8") as fh:
            fh.write(
                "[defaults]\ntimeout = 3\n\n"
                "[scan]\nworkers = 128\nnonsense_key = 1\n"
            )

    def tearDown(self):
        os.unlink(self.path)

    def _parser(self):
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        scan = subparsers.add_parser("scan")
        scan.add_argument("-t", "--timeout", type=float, default=0.6)
        scan.add_argument("-w", "--workers", type=int, default=64)
        return parser, subparsers

    def test_config_supplies_the_default(self):
        parser, subparsers = self._parser()
        config.apply_to_parser(subparsers, config.load(self.path))
        args = parser.parse_args(["scan"])
        self.assertEqual(args.workers, 128)

    def test_defaults_section_applies_to_every_command(self):
        parser, subparsers = self._parser()
        config.apply_to_parser(subparsers, config.load(self.path))
        self.assertEqual(parser.parse_args(["scan"]).timeout, 3)

    def test_explicit_flag_beats_the_file(self):
        parser, subparsers = self._parser()
        config.apply_to_parser(subparsers, config.load(self.path))
        self.assertEqual(parser.parse_args(["scan", "-w", "8"]).workers, 8)

    def test_unknown_key_is_ignored(self):
        parser, subparsers = self._parser()
        config.apply_to_parser(subparsers, config.load(self.path))
        self.assertFalse(hasattr(parser.parse_args(["scan"]), "nonsense_key"))

    def test_missing_file_is_not_an_error(self):
        self.assertEqual(config.load("/no/such/netprobe.ini"), {})


if __name__ == "__main__":
    unittest.main()

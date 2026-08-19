"""Tests for table and JSON rendering."""

import argparse
import io
import json
import unittest
from contextlib import redirect_stdout

from netprobe import output


class TestRenderTable(unittest.TestCase):
    def test_columns_are_padded_to_widest_cell(self):
        rows = [{"host": "a", "port": 22}, {"host": "longer-name", "port": 443}]
        lines = output.render_table(rows).splitlines()
        self.assertEqual(lines[0], "HOST         PORT")
        self.assertEqual(lines[1], "-----------  ----")
        self.assertEqual(lines[2], "a            22")
        self.assertEqual(lines[3], "longer-name  443")

    def test_header_is_never_narrower_than_its_own_label(self):
        # Values shorter than the column name must not shrink the column.
        lines = output.render_table([{"content_type": "-"}]).splitlines()
        self.assertEqual(lines[0], "CONTENT_TYPE")

    def test_missing_keys_render_as_dash(self):
        rows = [{"a": 1, "b": 2}, {"a": 3}]
        self.assertIn("-", output.render_table(rows).splitlines()[3])

    def test_column_order_follows_first_appearance(self):
        rows = [{"z": 1}, {"a": 2}]
        self.assertEqual(output.render_table(rows).splitlines()[0].split(), ["Z", "A"])

    def test_booleans_read_as_yes_no(self):
        table = output.render_table([{"ok": True, "bad": False}])
        self.assertIn("yes", table)
        self.assertIn("no", table)

    def test_empty_input(self):
        self.assertEqual(output.render_table([]), "(no results)")

    def test_no_trailing_whitespace(self):
        rows = [{"host": "longer-name", "note": "x"}, {"host": "a", "note": "y"}]
        for line in output.render_table(rows).splitlines():
            self.assertEqual(line, line.rstrip())


class TestRenderVertical(unittest.TestCase):
    def test_keys_aligned(self):
        text = output.render_vertical({"a": 1, "long_key": 2})
        self.assertEqual(text.splitlines()[0], "a        : 1")
        self.assertEqual(text.splitlines()[1], "long_key : 2")

    def test_none_becomes_dash(self):
        self.assertIn("-", output.render_vertical({"location": None}))

    def test_empty_input(self):
        self.assertEqual(output.render_vertical({}), "(no results)")


class TestEmit(unittest.TestCase):
    def _capture(self, rows, json_mode, vertical=False):
        args = argparse.Namespace(json=json_mode)
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            output.emit(rows, args, vertical=vertical)
        return buffer.getvalue()

    def test_json_mode_emits_a_list(self):
        payload = json.loads(self._capture([{"a": 1}, {"a": 2}], True))
        self.assertEqual(payload, [{"a": 1}, {"a": 2}])

    def test_vertical_single_row_emits_an_object_not_a_list(self):
        payload = json.loads(self._capture([{"a": 1}], True, vertical=True))
        self.assertEqual(payload, {"a": 1})

    def test_vertical_multi_row_still_emits_a_list(self):
        payload = json.loads(self._capture([{"a": 1}, {"a": 2}], True, vertical=True))
        self.assertIsInstance(payload, list)

    def test_json_survives_non_serialisable_values(self):
        # default=str keeps ipaddress objects and the like from blowing up.
        text = self._capture([{"when": object()}], True)
        self.assertIn("object at", text)

    def test_table_mode_has_no_braces(self):
        self.assertNotIn("{", self._capture([{"a": 1}], False))


if __name__ == "__main__":
    unittest.main()

import unittest
from math import sqrt
from plover_controller.util import (
    get_keys_for_stroke,
    keys_to_stroke,
    buttons_to_keys,
    stick_segment,
)


class TestGetKeysForStroke(unittest.TestCase):
    def test_basic_stroke(self):
        self.assertEqual(
            get_keys_for_stroke("PHRO-FR"),
            ("P-", "H-", "R-", "O-", "-F", "-R"),
        )

    def test_left_only(self):
        self.assertEqual(get_keys_for_stroke("STPH"), ("S-", "T-", "P-", "H-"))

    def test_right_only(self):
        self.assertEqual(get_keys_for_stroke("-FRPB"), ("-F", "-R", "-P", "-B"))

    def test_star(self):
        self.assertEqual(get_keys_for_stroke("*"), ("*",))

    def test_star_with_keys(self):
        # * flips to right side, so D after * without explicit hyphen is still left
        # use KPA*-D for right-side D
        self.assertEqual(
            get_keys_for_stroke("KPA*-D"),
            ("K-", "P-", "A-", "*", "-D"),
        )

    def test_number_bar(self):
        self.assertEqual(get_keys_for_stroke("#"), ("#",))

    def test_vowels_only(self):
        self.assertEqual(get_keys_for_stroke("AO"), ("A-", "O-"))

    def test_vowels_both_sides(self):
        # without explicit hyphen, E and U parse as left-side
        self.assertEqual(get_keys_for_stroke("AO-EU"), ("A-", "O-", "-E", "-U"))

    def test_empty_string(self):
        self.assertEqual(get_keys_for_stroke(""), ())

    def test_hyphen_only(self):
        self.assertEqual(get_keys_for_stroke("-"), ())

    def test_single_left_key(self):
        self.assertEqual(get_keys_for_stroke("S"), ("S-",))

    def test_single_right_key(self):
        self.assertEqual(get_keys_for_stroke("-Z"), ("-Z",))

    def test_full_stroke(self):
        result = get_keys_for_stroke("STKPWHRAO*-EUFRPBLGTSDZ")
        self.assertIn("S-", result)
        self.assertIn("*", result)
        self.assertIn("-Z", result)


class TestKeysToStroke(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(keys_to_stroke(()), "")

    def test_left_only(self):
        self.assertEqual(keys_to_stroke(("S-", "T-")), "ST-")

    def test_right_only(self):
        self.assertEqual(keys_to_stroke(("-F", "-R")), "-FR")

    def test_both_sides(self):
        self.assertEqual(keys_to_stroke(("S-", "T-", "-F", "-R")), "ST-FR")

    def test_star(self):
        self.assertEqual(keys_to_stroke(("*",)), "*")

    def test_star_with_keys(self):
        result = keys_to_stroke(("K-", "P-", "A-", "*", "-D"))
        self.assertEqual(result, "KPA*-D")

    def test_vowels(self):
        result = keys_to_stroke(("A-", "O-", "-E", "-U"))
        self.assertEqual(result, "AO-EU")

    def test_sorts_left_keys(self):
        result = keys_to_stroke(("H-", "S-", "T-"))
        self.assertEqual(result, "STH-")

    def test_sorts_right_keys(self):
        result = keys_to_stroke(("-G", "-F", "-R"))
        self.assertEqual(result, "-FRG")

    def test_roundtrip_basic(self):
        stroke = "PHRO-FR"
        self.assertEqual(keys_to_stroke(get_keys_for_stroke(stroke)), stroke)

    def test_roundtrip_star(self):
        stroke = "KPA*-D"
        self.assertEqual(keys_to_stroke(get_keys_for_stroke(stroke)), stroke)

    def test_roundtrip_left_only(self):
        stroke = "SKWH-"
        self.assertEqual(keys_to_stroke(get_keys_for_stroke(stroke)), stroke)

    def test_roundtrip_right_only(self):
        stroke = "-LTZ"
        self.assertEqual(keys_to_stroke(get_keys_for_stroke(stroke)), stroke)

    def test_roundtrip_full(self):
        stroke = "HRO*-ER"
        self.assertEqual(keys_to_stroke(get_keys_for_stroke(stroke)), stroke)


class TestButtonsToKeys(unittest.TestCase):
    def test_single_button(self):
        mappings = [(["a"], ("-S",))]
        result = buttons_to_keys({"a"}, mappings)
        self.assertEqual(result, {"-S"})

    def test_no_match(self):
        mappings = [(["a"], ("-S",))]
        result = buttons_to_keys({"b"}, mappings)
        self.assertEqual(result, set())

    def test_multiple_buttons(self):
        mappings = [
            (["a"], ("-S",)),
            (["b"], ("-Z",)),
        ]
        result = buttons_to_keys({"a", "b"}, mappings)
        self.assertEqual(result, {"-S", "-Z"})

    def test_combo_matched_before_singles(self):
        mappings = [
            (["dpadu", "dpadl"], ("K-", "P-", "A-", "*", "-D")),
            (["dpadu"], ("K-", "P-", "A-")),
            (["dpadl"], ("S-", "K-", "W-", "H-")),
        ]
        result = buttons_to_keys({"dpadu", "dpadl"}, mappings)
        self.assertEqual(result, {"K-", "P-", "A-", "*", "-D"})

    def test_combo_consumes_keys(self):
        mappings = [
            (["dpadu", "dpadl"], ("K-", "P-", "A-", "*", "-D")),
            (["dpadu"], ("K-", "P-", "A-")),
            (["dpadl"], ("S-", "K-", "W-", "H-")),
        ]
        in_keys = {"dpadu", "dpadl"}
        buttons_to_keys(in_keys, mappings)
        self.assertEqual(in_keys, set())

    def test_empty_mapping_consumes_without_output(self):
        mappings = [
            (["dpadu", "dpadd", "dpadl", "dpadr"], ()),
            (["dpadu"], ("K-", "P-", "A-")),
        ]
        in_keys = {"dpadu", "dpadd", "dpadl", "dpadr"}
        result = buttons_to_keys(in_keys, mappings)
        self.assertEqual(result, set())
        self.assertEqual(in_keys, set())

    def test_larger_combo_first_then_singles(self):
        mappings = [
            (["dpadu", "dpadd"], ()),
            (["dpadu"], ("K-", "P-", "A-")),
            (["dpadr"], ("S-", "K-", "P-")),
        ]
        result = buttons_to_keys({"dpadu", "dpadd", "dpadr"}, mappings)
        self.assertEqual(result, {"S-", "K-", "P-"})

    def test_partial_combo_no_match(self):
        mappings = [
            (["dpadu", "dpadl"], ("K-", "P-", "A-", "*", "-D")),
        ]
        result = buttons_to_keys({"dpadu"}, mappings)
        self.assertEqual(result, set())

    def test_ordering_matters(self):
        mappings = [
            (["dpadu"], ("K-", "P-", "A-")),
            (["dpadu", "dpadl"], ("K-", "P-", "A-", "*", "-D")),
        ]
        result = buttons_to_keys({"dpadu", "dpadl"}, mappings)
        self.assertEqual(result, {"K-", "P-", "A-"})
        # dpadu was consumed by the first match, so dpadl is unmatched

    def test_empty_input(self):
        mappings = [(["a"], ("-S",))]
        result = buttons_to_keys(set(), mappings)
        self.assertEqual(result, set())

    def test_empty_mappings(self):
        result = buttons_to_keys({"a", "b"}, [])
        self.assertEqual(result, set())


class TestStickSegment(unittest.TestCase):
    def test_inside_deadzone_returns_none(self):
        result = stick_segment(0.6, 0, 6, 0.1, 0.1)
        self.assertIsNone(result)

    def test_center_returns_none(self):
        result = stick_segment(0.6, 0, 6, 0.0, 0.0)
        self.assertIsNone(result)

    def test_full_right(self):
        result = stick_segment(0.1, 0, 6, 1.0, 0.0)
        self.assertIsNotNone(result)

    def test_full_left(self):
        result = stick_segment(0.1, 0, 6, -1.0, 0.0)
        self.assertIsNotNone(result)

    def test_full_up(self):
        result = stick_segment(0.1, 0, 6, 0.0, 1.0)
        self.assertIsNotNone(result)

    def test_full_down(self):
        result = stick_segment(0.1, 0, 6, 0.0, -1.0)
        self.assertIsNotNone(result)

    def test_segment_count_bounds(self):
        result = stick_segment(0.1, 0, 6, 1.0, 0.0)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result, 0)
        self.assertLess(result, 6)

    def test_different_segment_counts(self):
        for count in [4, 6, 8]:
            result = stick_segment(0.1, 0, count, 1.0, 0.0)
            self.assertIsNotNone(result)
            self.assertGreaterEqual(result, 0)
            self.assertLess(result, count)

    def test_offset_rotates_segments(self):
        no_offset = stick_segment(0.1, 0, 6, 1.0, 0.0)
        with_offset = stick_segment(0.1, 60, 6, 1.0, 0.0)
        self.assertNotEqual(no_offset, with_offset)

    def test_boundary_at_deadzone(self):
        dz = 0.6
        just_inside = dz * sqrt(2) - 0.01
        just_outside = dz * sqrt(2) + 0.01
        self.assertIsNone(stick_segment(dz, 0, 6, just_inside * 0.7, just_inside * 0.7))
        self.assertIsNotNone(stick_segment(dz, 0, 6, just_outside, just_outside))


if __name__ == "__main__":
    unittest.main()

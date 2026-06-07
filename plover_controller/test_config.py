import unittest
from plover_controller.config import Mappings, Stick, Alias


class TestMappingsParse(unittest.TestCase):
    def test_empty_string(self):
        m = Mappings.parse("")
        self.assertEqual(m.sticks, {})
        self.assertEqual(m.buttons, {})
        self.assertEqual(m.hats, {})
        self.assertEqual(m.triggers, {})
        self.assertEqual(m.unordered_mappings, [])
        self.assertEqual(m.ordered_mappings, {})

    def test_comment_lines_ignored(self):
        m = Mappings.parse("// this is a comment\n// guide ->")
        self.assertEqual(m.unordered_mappings, [])

    def test_blank_lines_ignored(self):
        m = Mappings.parse("\n\n\n")
        self.assertEqual(m.sticks, {})

    def test_parse_stick(self):
        m = Mappings.parse(
            "left stick has segments (dr,d,dl,ul,u,ur) on axes 0 and 1 offset by 0 degrees"
        )
        self.assertIn("left", m.sticks)
        stick = m.sticks["left"]
        self.assertEqual(stick.name, "left")
        self.assertEqual(stick.x_axis, "a0")
        self.assertEqual(stick.y_axis, "a1")
        self.assertEqual(stick.offset, 0.0)
        self.assertEqual(stick.segments, ["dr", "d", "dl", "ul", "u", "ur"])

    def test_parse_stick_with_offset(self):
        m = Mappings.parse(
            "right stick has segments (a,b,c) on axes 3 and 4 offset by 45.5 degrees"
        )
        self.assertEqual(m.sticks["right"].offset, 45.5)

    def test_parse_button(self):
        m = Mappings.parse("button 0 is a")
        self.assertIn("b0", m.buttons)
        self.assertEqual(m.buttons["b0"].renamed, "a")
        self.assertEqual(m.buttons["b0"].actual, "b0")

    def test_parse_hat(self):
        m = Mappings.parse("hat 0 is dpad")
        self.assertIn("h0", m.hats)
        self.assertEqual(m.hats["h0"].renamed, "dpad")

    def test_parse_trigger(self):
        m = Mappings.parse("trigger on axis 2 is lefttrigger")
        self.assertIn("a2", m.triggers)
        self.assertEqual(m.triggers["a2"].renamed, "lefttrigger")

    def test_parse_unordered_mapping(self):
        m = Mappings.parse("a -> -S")
        self.assertEqual(len(m.unordered_mappings), 1)
        lhs, rhs = m.unordered_mappings[0]
        self.assertEqual(lhs, ["a"])
        self.assertEqual(rhs, ("-S",))

    def test_parse_unordered_combo_mapping(self):
        m = Mappings.parse("dpadu,dpadl -> KPA*-D")
        lhs, rhs = m.unordered_mappings[0]
        self.assertEqual(lhs, ["dpadu", "dpadl"])
        self.assertIn("K-", rhs)
        self.assertIn("*", rhs)
        self.assertIn("-D", rhs)

    def test_parse_empty_mapping(self):
        m = Mappings.parse("dpadu,dpadd ->")
        self.assertEqual(len(m.unordered_mappings), 1)
        lhs, rhs = m.unordered_mappings[0]
        self.assertEqual(lhs, ["dpadu", "dpadd"])
        self.assertEqual(rhs, ())

    def test_parse_empty_mapping_trailing_space(self):
        m = Mappings.parse("dpadu,dpadd ->   ")
        lhs, rhs = m.unordered_mappings[0]
        self.assertEqual(rhs, ())

    def test_parse_ordered_mapping(self):
        m = Mappings.parse("left(d,dl,ul,dl) -> TW-")
        key = ("leftd", "leftdl", "leftul", "leftdl")
        self.assertIn(key, m.ordered_mappings)
        self.assertIn("T-", m.ordered_mappings[key])
        self.assertIn("W-", m.ordered_mappings[key])

    def test_parse_unknown_line_does_not_crash(self):
        m = Mappings.parse("this is gibberish that shouldn't match anything")
        self.assertEqual(m.sticks, {})

    def test_parse_multiple_unordered_preserves_order(self):
        text = "a -> -S\nb -> -Z\nx -> -T"
        m = Mappings.parse(text)
        self.assertEqual(len(m.unordered_mappings), 3)
        self.assertEqual(m.unordered_mappings[0][0], ["a"])
        self.assertEqual(m.unordered_mappings[1][0], ["b"])
        self.assertEqual(m.unordered_mappings[2][0], ["x"])


class TestMappingsSerialize(unittest.TestCase):
    def test_empty_mappings(self):
        m = Mappings.empty()
        self.assertEqual(m.serialize(), "")

    def test_roundtrip_stick(self):
        text = "left stick has segments (dr,d,dl,ul,u,ur) on axes 0 and 1 offset by 0 degrees\n"
        m = Mappings.parse(text)
        result = m.serialize()
        self.assertIn("left stick has segments (dr,d,dl,ul,u,ur) on axes 0 and 1 offset by 0 degrees", result)

    def test_roundtrip_button(self):
        text = "button 0 is a\n"
        m = Mappings.parse(text)
        result = m.serialize()
        self.assertIn("button 0 is a", result)

    def test_roundtrip_trigger(self):
        text = "trigger on axis 2 is lefttrigger\n"
        m = Mappings.parse(text)
        result = m.serialize()
        self.assertIn("trigger on axis 2 is lefttrigger", result)

    def test_roundtrip_hat(self):
        text = "hat 0 is dpad\n"
        m = Mappings.parse(text)
        result = m.serialize()
        self.assertIn("hat 0 is dpad", result)

    def test_roundtrip_unordered_mapping(self):
        text = "a -> -S\n"
        m = Mappings.parse(text)
        result = m.serialize()
        self.assertIn("a -> -S", result)

    def test_roundtrip_empty_mapping(self):
        text = "dpadu,dpadd ->\n"
        m = Mappings.parse(text)
        result = m.serialize()
        self.assertIn("dpadu,dpadd ->", result)
        line = [l for l in result.splitlines() if "dpadu,dpadd" in l][0]
        self.assertTrue(line.endswith("->"))

    def test_roundtrip_combo_mapping(self):
        text = "dpadu,dpadl -> KPA*-D\n"
        m = Mappings.parse(text)
        result = m.serialize()
        self.assertIn("dpadu,dpadl -> KPA*-D", result)

    def test_serialize_preserves_mapping_order(self):
        text = "a -> -S\nb -> -Z\nx -> -T\n"
        m = Mappings.parse(text)
        result = m.serialize()
        lines = [l for l in result.splitlines() if "->" in l]
        self.assertEqual(lines[0], "a -> -S")
        self.assertEqual(lines[1], "b -> -Z")
        self.assertEqual(lines[2], "x -> -T")

    def test_roundtrip_ordered_mapping(self):
        text = (
            "left stick has segments (dr,d,dl,ul,u,ur) on axes 0 and 1 offset by 0 degrees\n"
            "\n"
            "left(d,dl,ul,dl) -> TW-\n"
        )
        m = Mappings.parse(text)
        result = m.serialize()
        self.assertIn("left(d,dl,ul,dl) -> TW-", result)


class TestMappingsEmpty(unittest.TestCase):
    def test_empty_has_no_data(self):
        m = Mappings.empty()
        self.assertEqual(len(m.sticks), 0)
        self.assertEqual(len(m.hats), 0)
        self.assertEqual(len(m.buttons), 0)
        self.assertEqual(len(m.triggers), 0)
        self.assertEqual(len(m.unordered_mappings), 0)
        self.assertEqual(len(m.ordered_mappings), 0)

    def test_empty_instances_are_independent(self):
        m1 = Mappings.empty()
        m2 = Mappings.empty()
        m1.unordered_mappings.append((["a"], ("-S",)))
        self.assertEqual(len(m2.unordered_mappings), 0)


class TestDefaultMappingParse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import typing
        from plover.resource import resource_filename
        path = typing.cast(str, resource_filename("asset:plover_controller:assets/default_mapping.txt"))
        with open(path, "r") as f:
            cls.text = f.read()
        cls.mappings = Mappings.parse(cls.text)

    def test_has_sticks(self):
        self.assertIn("left", self.mappings.sticks)
        self.assertIn("right", self.mappings.sticks)

    def test_left_stick_segments(self):
        self.assertEqual(
            self.mappings.sticks["left"].segments,
            ["dr", "d", "dl", "ul", "u", "ur"],
        )

    def test_has_triggers(self):
        self.assertTrue(len(self.mappings.triggers) >= 2)

    def test_has_buttons(self):
        self.assertTrue(len(self.mappings.buttons) >= 10)

    def test_has_hat(self):
        self.assertTrue(len(self.mappings.hats) >= 1)

    def test_has_dpad_combos(self):
        dpad_mappings = [
            m for m in self.mappings.unordered_mappings
            if any(k.startswith("dpad") for k in m[0])
        ]
        self.assertGreaterEqual(len(dpad_mappings), 15)

    def test_four_direction_combo_is_empty(self):
        four_dir = None
        for lhs, rhs in self.mappings.unordered_mappings:
            if set(lhs) == {"dpadu", "dpadd", "dpadl", "dpadr"}:
                four_dir = (lhs, rhs)
                break
        self.assertIsNotNone(four_dir)
        self.assertEqual(four_dir[1], ())

    def test_dpad_up_is_capitalize(self):
        for lhs, rhs in self.mappings.unordered_mappings:
            if lhs == ["dpadu"]:
                from plover_controller.util import keys_to_stroke
                self.assertEqual(keys_to_stroke(rhs), "KPA-")
                return
        self.fail("dpadu mapping not found")

    def test_dpad_left_is_symbols_starter(self):
        for lhs, rhs in self.mappings.unordered_mappings:
            if lhs == ["dpadl"]:
                from plover_controller.util import keys_to_stroke
                self.assertEqual(keys_to_stroke(rhs), "SKWH-")
                return
        self.fail("dpadl mapping not found")

    def test_dpad_right_is_and(self):
        for lhs, rhs in self.mappings.unordered_mappings:
            if lhs == ["dpadr"]:
                from plover_controller.util import keys_to_stroke
                self.assertEqual(keys_to_stroke(rhs), "SKP-")
                return
        self.fail("dpadr mapping not found")

    def test_larger_combos_before_singles(self):
        dpad_indices = {}
        for i, (lhs, rhs) in enumerate(self.mappings.unordered_mappings):
            if all(k.startswith("dpad") for k in lhs):
                dpad_indices[tuple(sorted(lhs))] = i

        four = dpad_indices.get(tuple(sorted(["dpadu", "dpadd", "dpadl", "dpadr"])))
        single_u = dpad_indices.get(("dpadu",))
        if four is not None and single_u is not None:
            self.assertLess(four, single_u)

    def test_has_ordered_mappings(self):
        self.assertTrue(len(self.mappings.ordered_mappings) > 0)

    def test_default_mapping_roundtrip_does_not_crash(self):
        serialized = self.mappings.serialize()
        reparsed = Mappings.parse(serialized)
        self.assertEqual(len(reparsed.sticks), len(self.mappings.sticks))
        self.assertEqual(len(reparsed.buttons), len(self.mappings.buttons))
        self.assertEqual(len(reparsed.unordered_mappings), len(self.mappings.unordered_mappings))


if __name__ == "__main__":
    unittest.main()

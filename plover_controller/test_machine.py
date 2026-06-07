import unittest
from unittest.mock import MagicMock, patch
from plover_controller.machine import (
    ControllerState,
    ControllerMachine,
    Event,
    AxisEvent,
    ButtonEvent,
    ControllerButtonEvent,
    HatEvent,
    DeviceEvent,
    BallEvent,
    DEFAULT_MAPPING,
)
from plover_controller.config import Mappings
from sdl2 import (
    SDL_HAT_UP,
    SDL_HAT_DOWN,
    SDL_HAT_LEFT,
    SDL_HAT_RIGHT,
    SDL_HAT_LEFTUP,
    SDL_HAT_RIGHTDOWN,
    SDL_HAT_CENTERED,
)


def make_params(**overrides):
    defaults = {
        "mapping": DEFAULT_MAPPING,
        "timeout": 1.0,
        "stick_dead_zone": 0.6,
        "trigger_dead_zone": 0.9,
        "stroke_end_threshold": 0.4,
        "use_hidapi": True,
        "use_rawinput": False,
        "correlate_rawinput": False,
        "use_joystick_thread": False,
        "rumble_on_stroke": True,
        "rumble_duration": 80,
        "rumble_low_freq": 0.5,
        "rumble_high_freq": 0.25,
        "display_chroma_color": "#00b140",
        "display_layout": "horizontal",
        "display_show_back": True,
    }
    defaults.update(overrides)
    return defaults


SIMPLE_MAPPING = """\
button 0 is a
button 1 is b
button 2 is x

a -> -S
b -> -Z
x -> -T
"""

DPAD_MAPPING = """\
hat 0 is dpad

dpadu,dpadd,dpadl,dpadr ->
dpadu,dpadl -> KPA*-D
dpadu -> KPA-
dpadd -> HRO*-ER
dpadl -> SKWH-
dpadr -> SKP-
"""


class TestControllerState(unittest.TestCase):
    def _make_state(self, mapping_text=SIMPLE_MAPPING, **params):
        self.notified_keys = []
        def on_notify(keys):
            self.notified_keys.append(keys)
        p = make_params(mapping=mapping_text, **params)
        return ControllerState(p, on_notify)

    def test_button_press_release_sends_stroke(self):
        state = self._make_state()
        state._handle_event(ButtonEvent(button=0, state=True, device=0))
        self.assertEqual(len(self.notified_keys), 0)
        state._handle_event(ButtonEvent(button=0, state=False, device=0))
        self.assertEqual(len(self.notified_keys), 1)
        self.assertIn("-S", self.notified_keys[0])

    def test_no_stroke_without_release(self):
        state = self._make_state()
        state._handle_event(ButtonEvent(button=0, state=True, device=0))
        state._handle_event(ButtonEvent(button=1, state=True, device=0))
        self.assertEqual(len(self.notified_keys), 0)

    def test_chord_multiple_buttons(self):
        state = self._make_state()
        state._handle_event(ButtonEvent(button=0, state=True, device=0))
        state._handle_event(ButtonEvent(button=2, state=True, device=0))
        state._handle_event(ButtonEvent(button=0, state=False, device=0))
        self.assertEqual(len(self.notified_keys), 0)  # x still held
        state._handle_event(ButtonEvent(button=2, state=False, device=0))
        self.assertEqual(len(self.notified_keys), 1)
        self.assertIn("-S", self.notified_keys[0])
        self.assertIn("-T", self.notified_keys[0])

    def test_unmapped_button_no_output(self):
        state = self._make_state(mapping_text="button 0 is a\na -> -S")
        state._handle_event(ButtonEvent(button=99, state=True, device=0))
        state._handle_event(ButtonEvent(button=99, state=False, device=0))
        self.assertEqual(len(self.notified_keys), 0)

    def test_controller_button_event(self):
        state = self._make_state()
        state._handle_event(ControllerButtonEvent(name="a", state=True, device=0))
        state._handle_event(ControllerButtonEvent(name="a", state=False, device=0))
        self.assertEqual(len(self.notified_keys), 1)
        self.assertIn("-S", self.notified_keys[0])

    def test_ball_event_does_not_crash(self):
        state = self._make_state()
        state._handle_event(BallEvent(ball=0, device=0))

    def test_device_event_does_not_crash(self):
        state = self._make_state()
        state._handle_event(DeviceEvent(which=0, added=True))
        state._handle_event(DeviceEvent(which=0, added=False))


class TestControllerStateHats(unittest.TestCase):
    def _make_state(self, mapping_text=DPAD_MAPPING):
        self.notified_keys = []
        def on_notify(keys):
            self.notified_keys.append(keys)
        p = make_params(mapping=mapping_text)
        return ControllerState(p, on_notify)

    def test_single_dpad_direction(self):
        state = self._make_state()
        state._handle_event(HatEvent(hat=0, value=SDL_HAT_UP, device=0))
        state._handle_event(HatEvent(hat=0, value=SDL_HAT_CENTERED, device=0))
        self.assertEqual(len(self.notified_keys), 1)
        self.assertIn("K-", self.notified_keys[0])
        self.assertIn("P-", self.notified_keys[0])
        self.assertIn("A-", self.notified_keys[0])

    def test_dpad_combo_two_directions(self):
        state = self._make_state()
        state._handle_event(HatEvent(hat=0, value=SDL_HAT_UP, device=0))
        state._handle_event(HatEvent(hat=0, value=SDL_HAT_LEFTUP, device=0))
        state._handle_event(HatEvent(hat=0, value=SDL_HAT_CENTERED, device=0))
        self.assertEqual(len(self.notified_keys), 1)
        self.assertIn("K-", self.notified_keys[0])
        self.assertIn("P-", self.notified_keys[0])
        self.assertIn("A-", self.notified_keys[0])
        self.assertIn("*", self.notified_keys[0])
        self.assertIn("-D", self.notified_keys[0])

    def test_four_direction_combo_empty_output(self):
        state = self._make_state()
        state._handle_event(HatEvent(hat=0, value=SDL_HAT_UP, device=0))
        state._handle_event(HatEvent(hat=0, value=SDL_HAT_DOWN, device=0))
        state._handle_event(HatEvent(hat=0, value=SDL_HAT_LEFT, device=0))
        state._handle_event(HatEvent(hat=0, value=SDL_HAT_RIGHT, device=0))
        state._handle_event(HatEvent(hat=0, value=SDL_HAT_CENTERED, device=0))
        self.assertEqual(len(self.notified_keys), 0)

    def test_dpad_diagonal_decomposes_to_cardinals(self):
        state = self._make_state()
        state._handle_event(HatEvent(hat=0, value=SDL_HAT_RIGHTDOWN, device=0))
        state._handle_event(HatEvent(hat=0, value=SDL_HAT_CENTERED, device=0))
        # rightdown = right + down, no combo for those two in our mapping
        # so they match as singles: dpadd -> HRO*ER, dpadr -> SKP
        self.assertEqual(len(self.notified_keys), 1)

    def test_hat_center_clears_state(self):
        state = self._make_state()
        state._handle_event(HatEvent(hat=0, value=SDL_HAT_UP, device=0))
        state._handle_event(HatEvent(hat=0, value=SDL_HAT_CENTERED, device=0))
        self.assertEqual(len(self.notified_keys), 1)
        # second stroke
        state._handle_event(HatEvent(hat=0, value=SDL_HAT_DOWN, device=0))
        state._handle_event(HatEvent(hat=0, value=SDL_HAT_CENTERED, device=0))
        self.assertEqual(len(self.notified_keys), 2)


class TestControllerStateSticks(unittest.TestCase):
    def _make_state(self):
        self.notified_keys = []
        def on_notify(keys):
            self.notified_keys.append(keys)
        mapping = (
            "left stick has segments (dr,d,dl,ul,u,ur) on axes 0 and 1 offset by 0 degrees\n"
            "leftdr -> R-\n"
            "leftd -> W-\n"
            "leftu -> P-\n"
        )
        p = make_params(mapping=mapping)
        return ControllerState(p, on_notify)

    def test_stick_in_deadzone_no_output(self):
        state = self._make_state()
        state._handle_event(AxisEvent(axis=0, value=0.1, device=0))
        state._handle_event(AxisEvent(axis=1, value=0.1, device=0))
        state._handle_event(AxisEvent(axis=0, value=0.0, device=0))
        state._handle_event(AxisEvent(axis=1, value=0.0, device=0))
        self.assertEqual(len(self.notified_keys), 0)

    def test_stick_movement_sends_stroke(self):
        state = self._make_state()
        state._handle_event(AxisEvent(axis=0, value=0.0, device=0))
        state._handle_event(AxisEvent(axis=1, value=1.0, device=0))
        state._handle_event(AxisEvent(axis=0, value=0.0, device=0))
        state._handle_event(AxisEvent(axis=1, value=0.0, device=0))
        self.assertEqual(len(self.notified_keys), 1)

    def test_any_active_inputs_with_stick(self):
        state = self._make_state()
        self.assertFalse(state.any_active_inputs())
        state._stick_states["a0"] = 0.9
        self.assertTrue(state.any_active_inputs())

    def test_any_active_inputs_with_button(self):
        state = self._make_state()
        state._currently_pressed_buttons.add("a")
        self.assertTrue(state.any_active_inputs())

    def test_any_active_inputs_with_trigger(self):
        state = self._make_state()
        state._trigger_states["a2"] = 0.5
        self.assertTrue(state.any_active_inputs())


class TestControllerMachine(unittest.TestCase):
    def test_get_option_info_has_required_keys(self):
        info = ControllerMachine.get_option_info()
        required = [
            "profile", "mapping", "timeout", "stick_dead_zone",
            "trigger_dead_zone", "stroke_end_threshold", "use_hidapi",
            "use_rawinput", "correlate_rawinput", "use_joystick_thread",
            "rumble_on_stroke", "rumble_duration", "rumble_low_freq",
            "rumble_high_freq", "display_chroma_color", "display_layout",
            "display_show_back",
        ]
        for key in required:
            self.assertIn(key, info, f"Missing option: {key}")

    def test_option_info_has_defaults_and_parsers(self):
        info = ControllerMachine.get_option_info()
        for key, (default, parser) in info.items():
            self.assertTrue(callable(parser), f"{key} parser is not callable")

    def test_option_info_defaults_are_valid(self):
        info = ControllerMachine.get_option_info()
        for key, (default, parser) in info.items():
            try:
                parser(str(default))
            except Exception as e:
                self.fail(f"Default for {key} ({default!r}) fails its own parser: {e}")

    def test_set_suppression(self):
        params = make_params()
        machine = ControllerMachine(params)
        self.assertFalse(machine._output_enabled)
        machine.set_suppression(True)
        self.assertTrue(machine._output_enabled)
        machine.set_suppression(False)
        self.assertFalse(machine._output_enabled)

    @patch("plover_controller.machine.get_controller_thread")
    @patch("plover_controller.option_ui.is_steno_suppressed", return_value=False)
    def test_rumble_only_when_output_enabled(self, mock_suppressed, mock_thread):
        mock_ct = MagicMock()
        mock_thread.return_value = mock_ct

        params = make_params()
        machine = ControllerMachine(params)
        machine._output_enabled = False

        machine._state._handle_event(ControllerButtonEvent(name="a", state=True, device=0))
        machine._state._handle_event(ControllerButtonEvent(name="a", state=False, device=0))
        mock_ct.rumble.assert_not_called()

    @patch("plover_controller.machine.get_controller_thread")
    @patch("plover_controller.option_ui.is_steno_suppressed", return_value=False)
    def test_rumble_fires_when_output_enabled(self, mock_suppressed, mock_thread):
        mock_ct = MagicMock()
        mock_thread.return_value = mock_ct

        params = make_params()
        machine = ControllerMachine(params)
        machine.set_suppression(True)

        machine._state._handle_event(ControllerButtonEvent(name="a", state=True, device=0))
        machine._state._handle_event(ControllerButtonEvent(name="a", state=False, device=0))
        mock_ct.rumble.assert_called_once()

    @patch("plover_controller.machine.get_controller_thread")
    @patch("plover_controller.option_ui.is_steno_suppressed", return_value=False)
    def test_no_rumble_when_setting_disabled(self, mock_suppressed, mock_thread):
        mock_ct = MagicMock()
        mock_thread.return_value = mock_ct

        params = make_params(rumble_on_stroke=False)
        machine = ControllerMachine(params)
        machine.set_suppression(True)

        machine._state._handle_event(ControllerButtonEvent(name="a", state=True, device=0))
        machine._state._handle_event(ControllerButtonEvent(name="a", state=False, device=0))
        mock_ct.rumble.assert_not_called()

    @patch("plover_controller.machine.get_controller_thread")
    @patch("plover_controller.option_ui.is_steno_suppressed", return_value=True)
    def test_no_stroke_when_steno_suppressed(self, mock_suppressed, mock_thread):
        mock_ct = MagicMock()
        mock_thread.return_value = mock_ct

        params = make_params()
        machine = ControllerMachine(params)
        machine.set_suppression(True)
        machine._notify = MagicMock()

        machine._state._handle_event(ControllerButtonEvent(name="a", state=True, device=0))
        machine._state._handle_event(ControllerButtonEvent(name="a", state=False, device=0))
        machine._notify.assert_not_called()
        mock_ct.rumble.assert_not_called()

    def test_rumble_params_converted_correctly(self):
        params = make_params(rumble_low_freq=1.0, rumble_high_freq=0.5, rumble_duration=100)
        machine = ControllerMachine(params)
        machine.set_suppression(True)

        with patch("plover_controller.machine.get_controller_thread") as mock_thread, \
             patch("plover_controller.option_ui.is_steno_suppressed", return_value=False):
            mock_ct = MagicMock()
            mock_thread.return_value = mock_ct

            machine._state._handle_event(ControllerButtonEvent(name="a", state=True, device=0))
            machine._state._handle_event(ControllerButtonEvent(name="a", state=False, device=0))

            mock_ct.rumble.assert_called_once_with(0xFFFF, 0x7FFF, 100)


class TestDefaultMappingLoads(unittest.TestCase):
    def test_default_mapping_is_not_empty(self):
        self.assertTrue(len(DEFAULT_MAPPING) > 0)

    def test_default_mapping_parses(self):
        m = Mappings.parse(DEFAULT_MAPPING)
        self.assertTrue(len(m.sticks) > 0)
        self.assertTrue(len(m.buttons) > 0)
        self.assertTrue(len(m.unordered_mappings) > 0)


class TestProfileOption(unittest.TestCase):
    def test_profile_option_in_option_info(self):
        info = ControllerMachine.get_option_info()
        self.assertIn("profile", info)
        default, parser = info["profile"]
        self.assertEqual(default, "")
        self.assertEqual(parser, str)

    def test_machine_uses_mapping_text_not_profile(self):
        params = make_params(profile="PlayStation (Built-in)")
        machine = ControllerMachine(params)
        default_parsed = Mappings.parse(DEFAULT_MAPPING)
        self.assertEqual(
            list(machine._state._mappings.sticks.keys()),
            list(default_parsed.sticks.keys()),
        )


if __name__ == "__main__":
    unittest.main()

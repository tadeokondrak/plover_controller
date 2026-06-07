# This file is part of plover-controller.
# Copyright (C) 2022 Tadeo Kondrak
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from dataclasses import dataclass
import itertools
from math import cos, sin, sqrt, tau
import sdl2
import threading
import ctypes
import typing
from plover_controller.config import (
    Stick,
    Mappings,
)
from .util import stick_segment, buttons_to_keys
from plover.engine import StenoEngine
from plover.gui_qt.tool import Tool
from plover.machine.base import StenotypeBase
from plover.misc import boolean
from plover.resource import resource_exists, resource_filename
from typing import Any, Callable, Optional
from plover_controller.qt_compat import (
    Signal,
    Qt,
    QSize,
    QLineF,
    QPointF,
    QRectF,
    QFont,
    QPainter,
    QPen,
    QBrush,
    QWidget,
    QFormLayout,
    QLabel,
    QVBoxLayout,
)
from sdl2 import (
    SDL_Event,
    SDL_free,
    SDL_GameControllerOpen,
    SDL_GetError,
    SDL_HAT_CENTERED,
    SDL_HAT_DOWN,
    SDL_HAT_LEFT,
    SDL_HAT_LEFTDOWN,
    SDL_HAT_LEFTUP,
    SDL_HAT_RIGHT,
    SDL_HAT_RIGHTDOWN,
    SDL_HAT_RIGHTUP,
    SDL_HAT_UP,
    SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS,
    SDL_HINT_JOYSTICK_HIDAPI,
    SDL_HINT_JOYSTICK_RAWINPUT_CORRELATE_XINPUT,
    SDL_HINT_JOYSTICK_RAWINPUT,
    SDL_HINT_JOYSTICK_THREAD,
    SDL_HINT_NO_SIGNAL_HANDLERS,
    SDL_INIT_GAMECONTROLLER,
    SDL_INIT_JOYSTICK,
    SDL_INIT_VIDEO,
    SDL_Init,
    SDL_IsGameController,
    SDL_JoystickOpen,
    SDL_NumJoysticks,
    SDL_PushEvent,
    SDL_Quit,
    SDL_RegisterEvents,
    SDL_SetHint,
    SDL_WaitEvent,
)

SDL_strdup_void = sdl2.dll._bind("SDL_strdup", [ctypes.c_char_p], ctypes.c_void_p)

HAT_VALUES = {
    SDL_HAT_CENTERED: "c",
    SDL_HAT_UP: "u",
    SDL_HAT_RIGHT: "r",
    SDL_HAT_DOWN: "d",
    SDL_HAT_LEFT: "l",
    SDL_HAT_RIGHTUP: "ur",
    SDL_HAT_RIGHTDOWN: "dr",
    SDL_HAT_LEFTUP: "ul",
    SDL_HAT_LEFTDOWN: "dl",
}

CONTROLLER_BUTTON_NAMES = {
    sdl2.SDL_CONTROLLER_BUTTON_A: "a",
    sdl2.SDL_CONTROLLER_BUTTON_B: "b",
    sdl2.SDL_CONTROLLER_BUTTON_X: "x",
    sdl2.SDL_CONTROLLER_BUTTON_Y: "y",
    sdl2.SDL_CONTROLLER_BUTTON_BACK: "back",
    sdl2.SDL_CONTROLLER_BUTTON_GUIDE: "guide",
    sdl2.SDL_CONTROLLER_BUTTON_START: "start",
    sdl2.SDL_CONTROLLER_BUTTON_LEFTSTICK: "leftstick",
    sdl2.SDL_CONTROLLER_BUTTON_RIGHTSTICK: "rightstick",
    sdl2.SDL_CONTROLLER_BUTTON_LEFTSHOULDER: "leftshoulder",
    sdl2.SDL_CONTROLLER_BUTTON_RIGHTSHOULDER: "rightshoulder",
    sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP: "dpadu",
    sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN: "dpadd",
    sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT: "dpadl",
    sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT: "dpadr",
    sdl2.SDL_CONTROLLER_BUTTON_MISC1: "misc1",
    sdl2.SDL_CONTROLLER_BUTTON_PADDLE1: "paddle1",
    sdl2.SDL_CONTROLLER_BUTTON_PADDLE2: "paddle2",
    sdl2.SDL_CONTROLLER_BUTTON_PADDLE3: "paddle3",
    sdl2.SDL_CONTROLLER_BUTTON_PADDLE4: "paddle4",
    sdl2.SDL_CONTROLLER_BUTTON_TOUCHPAD: "touchpad",
}

mapping_path = "asset:plover_controller:assets/default_mapping.txt"
if not resource_exists(mapping_path):
    raise Exception("couldn't find default mapping file")

with open(typing.cast(str, resource_filename(mapping_path)), "r") as f:
    DEFAULT_MAPPING = f.read()


@dataclass
class Event:
    @classmethod
    def from_sdl(cls, ev: SDL_Event) -> Optional["Event"]:
        if ev.type == sdl2.SDL_JOYAXISMOTION:
            return AxisEvent(
                axis=ev.jaxis.axis,
                value=float(ev.jaxis.value) / 32768,
                device=ev.jaxis.which,
            )
        elif ev.type == sdl2.SDL_JOYBALLMOTION:
            return BallEvent(
                ball=ev.jball.ball,
                device=ev.jball.which,
            )
        elif ev.type == sdl2.SDL_JOYHATMOTION:
            return HatEvent(
                hat=ev.jhat.hat,
                value=ev.jhat.value,
                device=ev.jhat.which,
            )
        elif ev.type == sdl2.SDL_JOYBUTTONDOWN:
            return ButtonEvent(
                state=True,
                button=ev.jbutton.button,
                device=ev.jbutton.which,
            )
        elif ev.type == sdl2.SDL_JOYBUTTONUP:
            return ButtonEvent(
                state=False,
                button=ev.jbutton.button,
                device=ev.jbutton.which,
            )
        elif ev.type == sdl2.SDL_JOYDEVICEADDED:
            return DeviceEvent(
                added=True,
                which=ev.jdevice.which,
            )
        elif ev.type == sdl2.SDL_JOYDEVICEREMOVED:
            return DeviceEvent(
                added=False,
                which=ev.jdevice.which,
            )
        elif ev.type == sdl2.SDL_CONTROLLERBUTTONDOWN:
            name = CONTROLLER_BUTTON_NAMES.get(ev.cbutton.button)
            if name is not None:
                return ControllerButtonEvent(
                    name=name,
                    state=True,
                    device=ev.cbutton.which,
                )
        elif ev.type == sdl2.SDL_CONTROLLERBUTTONUP:
            name = CONTROLLER_BUTTON_NAMES.get(ev.cbutton.button)
            if name is not None:
                return ControllerButtonEvent(
                    name=name,
                    state=False,
                    device=ev.cbutton.which,
                )


@dataclass
class AxisEvent(Event):
    axis: int
    value: float
    device: int


@dataclass
class BallEvent(Event):
    ball: int
    device: int


@dataclass
class HatEvent(Event):
    hat: int
    value: int
    device: int


@dataclass
class ButtonEvent(Event):
    button: int
    state: bool
    device: int


@dataclass
class ControllerButtonEvent(Event):
    name: str
    state: bool
    device: int


@dataclass
class DeviceEvent(Event):
    which: int
    added: bool


controller_thread_instance = None


def get_controller_thread():
    global controller_thread_instance
    if controller_thread_instance is not None:
        return controller_thread_instance
    controller_thread_instance = ControllerThread()
    controller_thread_instance.start()
    return controller_thread_instance


class ControllerThread(threading.Thread):
    lock = threading.Lock()
    set_hint_event_type: Optional[int] = None
    rumble_event_type: Optional[int] = None
    listeners: set[Callable[[Event], None]]

    def __init__(self):
        super().__init__(daemon=True)
        self.listeners = set()
        self._controllers = []

    def run(self):
        with self.lock:
            SDL_Quit()
            SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS, b"1")
            SDL_SetHint(SDL_HINT_NO_SIGNAL_HANDLERS, b"1")
            SDL_Init(SDL_INIT_VIDEO | SDL_INIT_JOYSTICK | SDL_INIT_GAMECONTROLLER)
            self.set_hint_event_type = SDL_RegisterEvents(1)
            self.rumble_event_type = SDL_RegisterEvents(1)

            for i in range(typing.cast(int, SDL_NumJoysticks())):
                if SDL_IsGameController(i):
                    gc = SDL_GameControllerOpen(i)
                    if gc:
                        self._controllers.append(gc)
                else:
                    SDL_JoystickOpen(i)

        event = SDL_Event()
        while True:
            if not SDL_WaitEvent(event):
                error = typing.cast(bytes, SDL_GetError())
                if error:
                    raise Exception(f"SDL error occurred: {error.decode('utf-8')}")
                else:
                    raise Exception("Unknown SDL error occurred")
            with self.lock:
                if event.type == self.set_hint_event_type:
                    SDL_SetHint(
                        ctypes.cast(event.user.data1, ctypes.c_char_p),
                        ctypes.cast(event.user.data2, ctypes.c_char_p),
                    )
                    SDL_free(event.user.data1)
                    SDL_free(event.user.data2)
                elif event.type == self.rumble_event_type:
                    self._do_rumble()
                else:
                    if converted_event := Event.from_sdl(event):
                        if isinstance(converted_event, DeviceEvent):
                            if converted_event.added:
                                if SDL_IsGameController(converted_event.which):
                                    gc = SDL_GameControllerOpen(converted_event.which)
                                    if gc:
                                        self._controllers.append(gc)
                                else:
                                    SDL_JoystickOpen(converted_event.which)
                        for listener in self.listeners:
                            listener(converted_event)

    def add_listener(self, listener: Callable[[Event], None]):
        with self.lock:
            self.listeners.add(listener)

    def remove_listener(self, listener: Callable[[Event], None]):
        with self.lock:
            self.listeners.remove(listener)

    def set_hint(self, name: bytes, value: bytes):
        with self.lock:
            event = SDL_Event()
            event.type = self.set_hint_event_type
            event.user.data1 = SDL_strdup_void(name)
            event.user.data2 = SDL_strdup_void(value)
            SDL_PushEvent(event)

    def rumble(self, low=0x8000, high=0x4000, duration=80):
        if self.rumble_event_type is None:
            return
        self._rumble_low = low
        self._rumble_high = high
        self._rumble_duration = duration
        event = SDL_Event()
        event.type = self.rumble_event_type
        SDL_PushEvent(event)

    def _do_rumble(self):
        low = getattr(self, "_rumble_low", 0x8000)
        high = getattr(self, "_rumble_high", 0x4000)
        duration = getattr(self, "_rumble_duration", 80)
        for gc in self._controllers:
            try:
                sdl2.SDL_GameControllerRumble(gc, low, high, duration)
            except Exception:
                pass


class ControllerState:
    _params: dict[str, Any]
    _mappings: Mappings
    _stick_states: dict[str, float]
    _trigger_states: dict[str, float]
    _hat_states: dict[str, int]
    _pending_keys: set[str]
    _pending_stick_movements: dict[str, list[str]]
    _active_hat_cardinals: dict[str, set[str]]
    _unsequenced_buttons_and_hats: set[str]
    _currently_pressed_buttons: set[str]
    _currently_uncentered_hats: set[str]
    _notify: Callable[[list[str]], None]
    _fresh_from_deadzone: dict[str, bool]

    def __init__(self, params: dict[str, Any], notify: Callable[[list[str]], None]):
        super().__init__()
        self._params = params
        self._mappings = Mappings.parse(self._params["mapping"])
        self._notify = notify
        self._stick_states = {}
        self._trigger_states = {}
        self._hat_states = {}
        self._pending_keys = set()
        self._pending_stick_movements = {}
        self._active_hat_cardinals = {}
        self._unsequenced_buttons_and_hats = set()
        self._currently_pressed_buttons = set()
        self._currently_uncentered_hats = set()
        self._fresh_from_deadzone = {}

    def _handle_event(self, event: Event):
        if isinstance(event, AxisEvent):
            self._handle_axis_event(event)
        elif isinstance(event, BallEvent):
            self._handle_ball_event(event)
        elif isinstance(event, HatEvent):
            self._handle_hat_event(event)
        elif isinstance(event, ControllerButtonEvent):
            self._handle_controller_button_event(event)
        elif isinstance(event, ButtonEvent):
            self._handle_button_event(event)
        elif isinstance(event, DeviceEvent):
            self._handle_device_event(event)

    def _handle_axis_event(self, event: AxisEvent):
        axis = f"a{event.axis}"
        if axis in self._mappings.triggers:
            self._trigger_states[axis] = event.value
        elif axis in set(
            itertools.chain(
                map(lambda stick: stick.x_axis, self._mappings.sticks.values()),
                map(lambda stick: stick.y_axis, self._mappings.sticks.values()),
            ),
        ):
            self._stick_states[axis] = event.value
        self.check_axes()
        self.maybe_complete_stroke()

    def _handle_ball_event(self, event: BallEvent):
        pass

    def _handle_hat_event(self, event: HatEvent):
        hat = f"h{event.hat}"
        if hat_entry := self._mappings.hats.get(hat):
            hat = hat_entry.renamed
        self._hat_states[hat] = event.value

        new_cardinals = set()
        if event.value & SDL_HAT_UP:
            new_cardinals.add(f"{hat}u")
        if event.value & SDL_HAT_DOWN:
            new_cardinals.add(f"{hat}d")
        if event.value & SDL_HAT_LEFT:
            new_cardinals.add(f"{hat}l")
        if event.value & SDL_HAT_RIGHT:
            new_cardinals.add(f"{hat}r")

        old_cardinals = self._active_hat_cardinals.get(hat, set())

        for cardinal in new_cardinals - old_cardinals:
            self._currently_pressed_buttons.add(cardinal)
            if cardinal not in self._unsequenced_buttons_and_hats:
                self._unsequenced_buttons_and_hats.add(cardinal)

        for cardinal in old_cardinals - new_cardinals:
            self._currently_pressed_buttons.discard(cardinal)

        self._active_hat_cardinals[hat] = new_cardinals

        if event.value == 0:
            self._currently_uncentered_hats.discard(hat)
        else:
            self._currently_uncentered_hats.add(hat)

        self.maybe_complete_stroke()

    def _handle_button_event(self, event: ButtonEvent):
        button = f"b{event.button}"
        if button_entry := self._mappings.buttons.get(button):
            button = button_entry.renamed
        if event.state:
            self._currently_pressed_buttons.add(button)
            if button not in self._unsequenced_buttons_and_hats:
                self._unsequenced_buttons_and_hats.add(button)
        else:
            self._currently_pressed_buttons.discard(button)
            self.maybe_complete_stroke()

    def _handle_controller_button_event(self, event: ControllerButtonEvent):
        button = event.name
        if event.state:
            self._currently_pressed_buttons.add(button)
            if button not in self._unsequenced_buttons_and_hats:
                self._unsequenced_buttons_and_hats.add(button)
        else:
            self._currently_pressed_buttons.discard(button)
            self.maybe_complete_stroke()

    def _handle_device_event(self, event: DeviceEvent):
        pass

    def any_active_inputs(self):
        return (
            any(
                abs(v) > self._params["stroke_end_threshold"]
                for v in self._stick_states.values()
            )
            or any(v > 0 for v in self._trigger_states.values())
            or self._currently_pressed_buttons
            or self._currently_uncentered_hats
        )

    def process_stick_movements(self):
        if self.any_active_inputs():
            return

        def process(start_idx, end_idx):
            if start_idx == end_idx:
                for key in pending_movements[start_idx:]:
                    self._unsequenced_buttons_and_hats.add(key)
            else:
                key = tuple(pending_movements[start_idx:end_idx])
                ordered_mapping = self._mappings.ordered_mappings.get(key)
                if ordered_mapping is not None:
                    self._pending_keys.update(ordered_mapping)
                    process(end_idx, len(pending_movements))
                else:
                    process(start_idx, end_idx - 1)

        for stick in self._mappings.sticks.values():
            pending_movements = self._pending_stick_movements.get(stick.name, [])
            if (
                result := self._mappings.ordered_mappings.get(tuple(pending_movements))
            ) is not None:
                self._pending_stick_movements[stick.name] = []
                self._pending_keys.update(result)
            else:
                for key in pending_movements:
                    self._unsequenced_buttons_and_hats.add(key)

        for stick in self._mappings.sticks.values():
            pending_movements = self._pending_stick_movements.get(stick.name, [])
            process(0, len(pending_movements))
            self._pending_stick_movements[stick.name] = []

    def maybe_complete_stroke(self):
        self.process_stick_movements()
        if self.any_active_inputs():
            return
        keys = buttons_to_keys(
            self._unsequenced_buttons_and_hats,
            self._mappings.unordered_mappings,
        ).union(self._pending_keys)
        self._unsequenced_buttons_and_hats.clear()
        self._pending_stick_movements.clear()
        self._pending_keys.clear()
        if keys:
            self._notify(list(keys))

    def check_axes(self):
        for stick in self._mappings.sticks.values():
            lr = self._stick_states.get(stick.x_axis, 0.0)
            ud = self._stick_states.get(stick.y_axis, 0.0)
            self.check_stick(stick, lr, ud)
        for trigger in self._mappings.triggers.values():
            val = self._trigger_states.get(trigger.actual, 0)
            if val > 0:
                self._unsequenced_buttons_and_hats.add(trigger.renamed)

    def check_stick(self, stick: Stick, lr: float, ud: float):
        segment_index = stick_segment(
            stick_dead_zone=self._params["stick_dead_zone"],
            offset=stick.offset,
            segment_count=len(stick.segments),
            lr=lr,
            ud=ud,
        )
        if stick.name not in self._pending_stick_movements:
            self._pending_stick_movements[stick.name] = []
        if stick.name not in self._fresh_from_deadzone:
            self._fresh_from_deadzone[stick.name] = True
        if segment_index is not None:
            direction = stick.segments[segment_index]
            segment_name = f"{stick.name}{direction}"
            inorder_list = self._pending_stick_movements[stick.name]
            if len(inorder_list) == 0 or segment_name != inorder_list[-1]:
                inorder_list.append(segment_name)
            self._fresh_from_deadzone[stick.name] = False
        else:
            self._fresh_from_deadzone[stick.name] = True


class ControllerMachine(StenotypeBase):
    KEYMAP_MACHINE_TYPE = "TX Bolt"
    KEYS_LAYOUT = """
        #  #  #  #  #  #  #  #  #  #
        S- T- P- H- * -F -P -L -T -D
        S- K- W- R- * -R -B -G -S -Z
               A- O- -E -U
    """

    _state: ControllerState
    _output_enabled: bool

    def __init__(self, params: dict[str, Any]):
        super().__init__()
        self._output_enabled = False
        self._state = ControllerState(params, self._wrap_notify)

    def set_suppression(self, enabled):
        self._output_enabled = enabled

    def _wrap_notify(self, keys: list[str]):
        from plover_controller.option_ui import is_steno_suppressed

        if is_steno_suppressed():
            return
        if self._output_enabled and self._state._params.get("rumble_on_stroke", True):
            p = self._state._params
            low = int(p.get("rumble_low_freq", 0.5) * 0xFFFF)
            high = int(p.get("rumble_high_freq", 0.25) * 0xFFFF)
            duration = int(p.get("rumble_duration", 80))
            get_controller_thread().rumble(low, high, duration)
        self._notify(self.keymap.keys_to_actions(keys))

    def start_capture(self):
        self._initializing()
        get_controller_thread().add_listener(self._state._handle_event)
        hints = [
            (SDL_HINT_JOYSTICK_HIDAPI, self._state._params["use_hidapi"]),
            (SDL_HINT_JOYSTICK_RAWINPUT, self._state._params["use_rawinput"]),
            (
                SDL_HINT_JOYSTICK_RAWINPUT_CORRELATE_XINPUT,
                self._state._params["correlate_rawinput"],
            ),
            (SDL_HINT_JOYSTICK_THREAD, self._state._params["use_joystick_thread"]),
        ]
        for name, value in hints:
            get_controller_thread().set_hint(name, b"1" if value else b"0")
        self._ready()

    def stop_capture(self):
        get_controller_thread().remove_listener(self._state._handle_event)
        self._stopped()

    @classmethod
    def get_option_info(cls) -> dict[str, tuple[Any, Callable[[str], Any]]]:
        return {
            "profile": ("", str),
            "mapping": (DEFAULT_MAPPING, str),
            "timeout": (1.0, float),
            "stick_dead_zone": (0.6, float),
            "trigger_dead_zone": (0.9, float),
            "stroke_end_threshold": (0.4, float),
            "use_hidapi": (True, boolean),
            "use_rawinput": (False, boolean),
            "correlate_rawinput": (False, boolean),
            "use_joystick_thread": (False, boolean),
            "rumble_on_stroke": (True, boolean),
            "rumble_duration": (80, int),
            "rumble_low_freq": (0.5, float),
            "rumble_high_freq": (0.25, float),
            "display_chroma_color": ("#00b140", str),
            "display_layout": ("horizontal", str),
            "display_show_back": (True, boolean),
        }


class StickWidget(QWidget):
    stick: Stick
    state: ControllerState

    def sizeHint(self) -> QSize:
        return QSize(100, 100)

    def minimumSizeHint(self) -> QSize:
        return QSize(50, 50)

    def paintEvent(self, event):
        def convx(v: float) -> float:
            return width / 2 + v * width / 2

        def convy(v: float) -> float:
            return height / 2 + v * height / 2

        def draw_deadzone(v: float):
            painter.drawArc(
                QRectF(
                    width / 2 - width * v / 2,
                    height / 2 - height * v / 2,
                    width * v,
                    height * v,
                ),
                0,
                16 * 360,
            )

        painter = QPainter(self)
        dev = painter.device()
        assert dev is not None
        width = dev.width()
        height = dev.height()
        x = self.state._stick_states.get(self.stick.x_axis, 0.0)
        y = self.state._stick_states.get(self.stick.y_axis, 0.0)
        painter.drawLine(QLineF(convx(0), convy(0), convx(x), convy(y)))

        painter.setPen(QPen(Qt.GlobalColor.lightGray, 1, Qt.PenStyle.DotLine))
        draw_deadzone(self.state._params["stroke_end_threshold"] * sqrt(2))
        painter.setPen(QPen(Qt.GlobalColor.darkGray, 1, Qt.PenStyle.DotLine))
        draw_deadzone(self.state._params["stick_dead_zone"] * sqrt(2))

        angle = self.stick.offset / 360 * tau - tau / 4
        step = tau / len(self.stick.segments)
        for segment in self.stick.segments:
            x, y = -sin(angle), cos(angle)
            painter.setPen(QPen(Qt.GlobalColor.black, 1, Qt.PenStyle.DotLine))
            painter.drawLine(QLineF(convx(0), convy(0), convx(x), convy(y)))

            font_metrics = painter.fontMetrics()
            text_width = font_metrics.horizontalAdvance(segment) / width
            text_height = font_metrics.height() / height

            midx, midy = (
                -sin(angle + step / 2) * 0.9 - text_width / 2,
                cos(angle + step / 2) * 0.9 + text_height / 2,
            )
            painter.setPen(QPen(Qt.GlobalColor.black, 1, Qt.PenStyle.SolidLine))
            painter.setBrush(QBrush(Qt.GlobalColor.black))
            painter.setFont(QFont("Arial", 12))
            painter.drawText(QPointF(convx(midx), convy(midy)), segment)

            angle += step


class ControllerDisplayTool(Tool):
    TITLE = "Controller Display"
    ICON = typing.cast(str, resource_filename("asset:plover_controller:assets/controller_display.svg"))
    ROLE = "controller_display_tool"

    events = Signal(Event)

    def __init__(self, engine: StenoEngine):
        super().__init__(engine)
        self._dying = False

        from plover_controller.display import ControllerView

        self._view = ControllerView(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)

        self.events.connect(self._handle_event_signal)
        self._engine.signal_connect("config_changed", self._handle_config_changed)
        self._handle_config_changed(None)

        get_controller_thread().add_listener(self._handle_event)

        def handle_destroy():
            get_controller_thread().remove_listener(self._handle_event)

        self.destroyed.connect(handle_destroy)
        self.resize(800, 400)

    def _handle_config_changed(self, _: Any):
        if self._dying:
            return
        if self._engine.config["machine_type"] != "Controller":
            return
        params = self._engine.config["machine_specific_options"]
        mappings = Mappings.parse(params["mapping"])
        self._view.set_mappings(mappings, params)
        self._view.set_chroma_color(params.get("display_chroma_color", "#00b140"))
        self._view.set_layout_mode(params.get("display_layout", "horizontal"))
        self._view.set_show_back(params.get("display_show_back", True))

    def _handle_event(self, event: Event):
        self.events.emit(event)

    def _handle_event_signal(self, event: Event):
        self._view.handle_event(event)

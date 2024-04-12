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
from copy import copy
from plover.engine import StenoEngine
from plover.gui_qt.tool import Tool
from plover.machine.base import StenotypeBase
from plover.misc import boolean
from plover.resource import resource_exists, resource_filename
from PyQt5.QtCore import QVariant, pyqtSignal, Qt, QSize, QLineF, QPointF, QRectF
from PyQt5.QtGui import QFont, QPainter, QPen, QBrush
from typing import Any, Callable, Optional
from PyQt5.QtWidgets import (
    QWidget,
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)
from sdl2 import (
    SDL_Event,
    SDL_free,
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
    SDL_INIT_JOYSTICK,
    SDL_INIT_VIDEO,
    SDL_Init,
    SDL_JoyAxisEvent,
    SDL_JOYAXISMOTION,
    SDL_JoyBallEvent,
    SDL_JOYBALLMOTION,
    SDL_JOYBUTTONDOWN,
    SDL_JoyButtonEvent,
    SDL_JOYBUTTONUP,
    SDL_JOYDEVICEADDED,
    SDL_JoyDeviceEvent,
    SDL_JOYDEVICEREMOVED,
    SDL_JoyHatEvent,
    SDL_JOYHATMOTION,
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

mapping_path = "asset:plover_controller:assets/default_mapping.txt"
if not resource_exists(mapping_path):
    raise Exception("couldn't find default mapping file")

with open(typing.cast(str, resource_filename(mapping_path)), "r") as f:
    DEFAULT_MAPPING = f.read()


@dataclass
class Event:
    @classmethod
    def from_sdl(cls, ev: SDL_Event) -> Optional["Event"]:
        match ev.type:
            case sdl2.SDL_JOYAXISMOTION:
                return AxisEvent(
                    axis=ev.jaxis.axis,
                    value=float(ev.jaxis.value) / 32768,
                    device=ev.jaxis.which,
                )
            case sdl2.SDL_JOYBALLMOTION:
                return BallEvent(ball=ev.jball.ball, device=ev.jball.which)
            case sdl2.SDL_JOYHATMOTION:
                return HatEvent(
                    hat=ev.jhat.hat, value=ev.jhat.value, device=ev.jhat.which
                )
            case sdl2.SDL_JOYBUTTONDOWN:
                return ButtonEvent(
                    state=True, button=ev.jbutton.button, device=ev.jbutton.which
                )
            case sdl2.SDL_JOYBUTTONUP:
                return ButtonEvent(
                    state=False, button=ev.jbutton.button, device=ev.jbutton.which
                )
            case sdl2.SDL_JOYDEVICEADDED:
                return DeviceEvent(added=True, which=ev.jdevice.which)
            case sdl2.SDL_JOYDEVICEREMOVED:
                return DeviceEvent(added=False, which=ev.jdevice.which)


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
    listeners: set[Callable[[Event], None]] = set()

    def __init__(self):
        super().__init__()

    def run(self):
        with self.lock:
            SDL_Quit()
            SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS, b"1")
            SDL_SetHint(SDL_HINT_NO_SIGNAL_HANDLERS, b"1")
            SDL_Init(SDL_INIT_VIDEO | SDL_INIT_JOYSTICK)
            self.set_hint_event_type = SDL_RegisterEvents(1)

            for i in range(typing.cast(int, SDL_NumJoysticks())):
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
                else:
                    if converted_event := Event.from_sdl(event):
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


class ControllerState:
    _params: dict[str, Any] = {}
    _mappings: Mappings = Mappings.empty()
    _stick_states: dict[str, float] = {}
    _trigger_states: dict[str, float] = {}
    _currently_pressed_buttons_and_hats: set[str] = set()
    _unsequenced_buttons_and_hats: set[str] = set()
    _pending_keys: set[str] = set()
    _pending_stick_movements: dict[str, list[str]] = {}
    _notify: Callable[[list[str]], None]

    def __init__(self, params: dict[str, Any], notify: Callable[[list[str]], None]):
        super().__init__()
        self._params = params
        self._mappings = Mappings.parse(self._params["mapping"])
        self._notify = notify

    def _handle_event(self, event: Event):
        match event:
            case AxisEvent() as axis_event:
                self._handle_axis_event(axis_event)
            case BallEvent() as ball_event:
                self._handle_ball_event(ball_event)
            case HatEvent() as hat_event:
                self._handle_hat_event(hat_event)
            case ButtonEvent() as button_event:
                self._handle_button_event(button_event)
            case DeviceEvent() as device_event:
                self._handle_device_event(device_event)

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
        self.maybe_complete_ordered_chord()
        self.maybe_complete_stroke()

    def _handle_ball_event(self, event: BallEvent):
        pass

    def _handle_hat_event(self, event: HatEvent):
        hat = f"h{event.hat}"
        if button_entry := self._mappings.buttons_and_hats.get(hat):
            hat = button_entry.name
        if event.value == 0:
            self._currently_pressed_buttons_and_hats.discard(hat)
            self.maybe_complete_stroke()
        else:
            self._currently_pressed_buttons_and_hats.add(hat)
            specific_hat = f"{hat}{HAT_VALUES[event.value]}"
            if specific_hat not in self._unsequenced_buttons_and_hats:
                self._unsequenced_buttons_and_hats.add(specific_hat)

    def _handle_button_event(self, event: ButtonEvent):
        button = f"b{event.button}"
        if button_entry := self._mappings.buttons_and_hats.get(button):
            button = button_entry.name
        if event.state:
            self._currently_pressed_buttons_and_hats.add(button)
            if button not in self._unsequenced_buttons_and_hats:
                self._unsequenced_buttons_and_hats.add(button)
        else:
            self._currently_pressed_buttons_and_hats.discard(button)
            self.maybe_complete_stroke()

    def _handle_device_event(self, event: DeviceEvent):
        if event.added:
            SDL_JoystickOpen(event.which)

    def maybe_complete_ordered_chord(self):
        for stick in self._mappings.sticks.values():
            if any(
                map(
                    lambda v: abs(v) > self._params["stroke_end_threshold"],
                    (
                        self._stick_states.get(axis, 0.0)
                        for axis in [stick.x_axis, stick.y_axis]
                    ),
                )
            ):
                continue
            pending_stick_movements = self._pending_stick_movements.get(stick.name, [])
            if (
                result := self._mappings.ordered_mappings.get(
                    tuple(pending_stick_movements)
                )
            ) is not None:
                self._pending_stick_movements[stick.name] = []
                self._pending_keys.update(result)
            else:
                for key in pending_stick_movements:
                    self._unsequenced_buttons_and_hats.add(key)
                self._pending_stick_movements[stick.name] = []

    def maybe_complete_stroke(self):
        if not self._unsequenced_buttons_and_hats and not self._pending_keys:
            return
        if any(
            map(
                lambda v: abs(v) > self._params["stroke_end_threshold"],
                self._stick_states.values(),
            )
        ):
            return
        if any(map(lambda v: v > 0, self._trigger_states.values())):
            return
        if self._currently_pressed_buttons_and_hats:
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
            val = self._trigger_states.get(trigger.axis, 0)
            if val > 0:
                self._unsequenced_buttons_and_hats.add(trigger.name)

    def check_stick(self, stick: Stick, lr: float, ud: float):
        segment_index = stick_segment(
            stick_dead_zone=self._params["stick_dead_zone"],
            offset=stick.offset,
            segment_count=len(stick.segments),
            lr=lr,
            ud=ud,
        )
        if segment_index is not None:
            direction = stick.segments[segment_index]
            segment_name = f"{stick.name}{direction}"
            if stick.name not in self._pending_stick_movements:
                self._pending_stick_movements[stick.name] = []
            inorder_list = self._pending_stick_movements[stick.name]
            if len(inorder_list) == 0 or segment_name != inorder_list[-1]:
                inorder_list.append(segment_name)


class ControllerMachine(StenotypeBase):
    KEYMAP_MACHINE_TYPE = "TX Bolt"
    KEYS_LAYOUT = """
        #  #  #  #  #  #  #  #  #  #
        S- T- P- H- * -F -P -L -T -D
        S- K- W- R- * -R -B -G -S -Z
               A- O- -E -U
    """

    _state: ControllerState

    def __init__(self, params: dict[str, Any]):
        super().__init__()
        self._state = ControllerState(params, self._wrap_notify)

    def _wrap_notify(self, keys: list[str]):
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
            "mapping": (DEFAULT_MAPPING, str),
            "timeout": (1.0, float),
            "stick_dead_zone": (0.6, float),
            "trigger_dead_zone": (0.9, float),
            "stroke_end_threshold": (0.4, float),
            "use_hidapi": (True, boolean),
            "use_rawinput": (False, boolean),
            "correlate_rawinput": (False, boolean),
            "use_joystick_thread": (False, boolean),
        }


class ControllerOption(QGroupBox):
    axis_message = pyqtSignal(str)
    other_message = pyqtSignal(str)
    valueChanged = pyqtSignal(QVariant)
    _value = {}
    _last_axis_message = None
    _last_other_message = None
    _spin_boxes = {}
    _check_boxes = {}

    SPIN_BOXES = {
        "timeout": "Timeout:",
        "stick_dead_zone": "Stick dead zone:",
        "trigger_dead_zone": "Trigger dead zone:",
        "stroke_end_threshold": "Stroke end threshold:",
    }

    CHECK_BOXES = {
        "use_hidapi": "Use hidapi drivers:\n(reconnect controller and/or restart after change)",
        "use_rawinput": "Use rawinput drivers:\n(reconnect controller and/or restart after change)",
        "correlate_rawinput": "Correlate rawinput and xinput data:\n(reconnect controller and/or restart after change)",
        "use_joystick_thread": "Use joystick thread:\n(restart after change)",
    }

    def __init__(self):
        super().__init__()
        self.valueChanged.connect(self.setValue)

        self._form_layout = QFormLayout(self)

        for property, description in __class__.SPIN_BOXES.items():

            def value_changed(value, property=property):
                if value == self._value.get(property):
                    return
                self._value[property] = value
                self.valueChanged.emit(self._value)

            label = QLabel(description, self)
            spin_box = QDoubleSpinBox(self)
            spin_box.setSingleStep(0.1)
            spin_box.valueChanged.connect(value_changed)
            self._form_layout.addRow(label, spin_box)
            self._spin_boxes[property] = spin_box

        for property, description in __class__.CHECK_BOXES.items():

            def state_changed(state, property=property):
                value = state == Qt.CheckState.Checked
                if value == self._value.get(property):
                    return
                self._value[property] = value
                self.valueChanged.emit(self._value)

            label = QLabel(description, self)
            check_box = QCheckBox(self)
            check_box.stateChanged.connect(state_changed)
            self._form_layout.addRow(label, check_box)
            self._check_boxes[property] = check_box

        self._mapping_label = QLabel("Mapping:", self)
        self._mapping_text_edit = QTextEdit(self)
        self._mapping_text_edit.setFont(QFont("Monospace"))
        self._mapping_text_edit.textChanged.connect(self.mapping_changed)
        self._mapping_reset_button = QPushButton("Reset mapping to default", self)
        self._mapping_reset_button.clicked.connect(self.reset_mapping)
        self._mapping_layout = QVBoxLayout()
        self._mapping_layout.addWidget(self._mapping_text_edit)
        self._mapping_layout.addWidget(self._mapping_reset_button)
        self._form_layout.addRow(self._mapping_label, self._mapping_layout)

        self._axis_feedback_label = QLabel("Last axis event:", self)
        self._axis_feedback_output_label = QLabel(self)
        self._axis_feedback_output_label.setFont(QFont("Monospace"))
        self._form_layout.addRow(
            self._axis_feedback_label, self._axis_feedback_output_label
        )
        self.axis_message.connect(self._axis_feedback_output_label.setText)

        self._feedback_label = QLabel("Last other event:", self)
        self._feedback_output_label = QLabel(self)
        self._feedback_output_label.setFont(QFont("Monospace"))
        self._form_layout.addRow(self._feedback_label, self._feedback_output_label)
        self.other_message.connect(self._feedback_output_label.setText)

        get_controller_thread().add_listener(self._handle_event)

        def handle_destroy():
            get_controller_thread().remove_listener(self._handle_event)

        self.destroyed.connect(handle_destroy)

    def _handle_event(self, event: Event):
        match event:
            case AxisEvent(axis, value, device):
                if value < 0.25:
                    return
                message = f"Axis {axis} motion (device: {device})"
                if message != self._last_axis_message:
                    try:
                        self.axis_message.emit(message)
                    except RuntimeError:
                        pass
                self._last_axis_message = message
                return

            case BallEvent(ball, device):
                message = f"Ball {ball} motion (device: {device})"

            case HatEvent(hat, value, device):
                if value == 0:
                    message = f"Hat {hat} centered (device: {device})"
                else:
                    message = f"Hat {hat} event {HAT_VALUES[value]} (device: {device})"

            case ButtonEvent(button, state, device):
                message = f"Button {button} {'pressed' if state else 'released'} (device: {device})"

            case DeviceEvent(which, added):
                message = f"Device {which} {'added' if added else 'removed'}"

            case _:
                return

        if message != self._last_other_message:
            try:
                self.other_message.emit(message)
            except RuntimeError:
                pass
        self._last_other_message = message

    def setValue(self, value):
        self._value = copy(value)
        for property in __class__.SPIN_BOXES.keys():
            if property in value:
                self._spin_boxes[property].setValue(value[property])
        for property in __class__.CHECK_BOXES.keys():
            if property in value:
                if value[property] == True:
                    self._check_boxes[property].setCheckState(Qt.CheckState.Checked)
                else:
                    self._check_boxes[property].setCheckState(Qt.CheckState.Unchecked)
        if (mapping := value.get("mapping")) is not None:
            existing = self._mapping_text_edit.toPlainText()
            if mapping != existing:
                self._mapping_text_edit.setPlainText(mapping)

    def mapping_changed(self):
        text = self._mapping_text_edit.toPlainText()
        if text == self._value.get("mapping"):
            return
        self._value["mapping"] = text
        self.valueChanged.emit(self._value)

    def reset_mapping(self):
        self._mapping_text_edit.setPlainText(DEFAULT_MAPPING)


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
        width = painter.device().width()
        height = painter.device().height()
        x = self.state._stick_states.get(self.stick.x_axis, 0.0)
        y = self.state._stick_states.get(self.stick.y_axis, 0.0)
        painter.drawLine(QLineF(convx(0), convy(0), convx(x), convy(y)))

        painter.setPen(QPen(Qt.lightGray, 1, Qt.DotLine))
        draw_deadzone(self.state._params["stroke_end_threshold"] * sqrt(2))
        painter.setPen(QPen(Qt.darkGray, 1, Qt.DotLine))
        draw_deadzone(self.state._params["stick_dead_zone"] * sqrt(2))

        angle = self.stick.offset / 360 * tau - tau / 4
        step = tau / len(self.stick.segments)
        for segment in self.stick.segments:
            x, y = sin(angle), cos(angle)
            painter.setPen(QPen(Qt.black, 1, Qt.DotLine))
            painter.drawLine(QLineF(convx(0), convy(0), convx(x), convy(y)))

            font_metrics = painter.fontMetrics()
            text_width = font_metrics.horizontalAdvance(segment) / width
            text_height = font_metrics.height() / height

            midx, midy = (
                sin(angle + step / 2) * 0.9 - text_width / 2,
                cos(angle + step / 2) * 0.9 + text_height / 2,
            )
            painter.setPen(QPen(Qt.black, 1, Qt.SolidLine))
            painter.setBrush(QBrush(Qt.black))
            painter.setFont(QFont("Arial", 12))
            painter.drawText(QPointF(convx(midx), convy(midy)), segment)

            angle += step


class ControllerDisplayTool(Tool):
    TITLE = "Controller Display"
    ICON = ""
    ROLE = "controller_display_tool"

    events = pyqtSignal(Event)

    _state: ControllerState
    _sticks: dict[str, StickWidget] = {}
    _dying: bool = False

    def __init__(self, engine: StenoEngine):
        super().__init__(engine)

        self.events.connect(self._handle_event_signal)
        self._layout = QFormLayout(self)
        self._engine.signal_connect("config_changed", self._handle_config_changed)
        self._handle_config_changed(None)

        get_controller_thread().add_listener(self._handle_event)

        def handle_destroy():
            get_controller_thread().remove_listener(self._handle_event)

        self.destroyed.connect(handle_destroy)

    def _handle_config_changed(self, _: Any):
        if self._dying:
            return
        if self._engine.config["machine_type"] != "Controller":
            self._sticks.clear()
            return
        params = self._engine.config["machine_specific_options"]
        self._state = ControllerState(params, self._ignore_notify)
        self._sticks.clear()
        for stick in self._state._mappings.sticks.values():
            widget = StickWidget(self)
            widget.stick = stick
            widget.state = self._state
            self._sticks[stick.name] = widget
            self._layout.addRow(QLabel(f"Stick {stick.name}", self), widget)

    def _ignore_notify(self, _: list[str]):
        pass

    def _make_stick_widget(self, stick: Stick):
        pass

    def _handle_event(self, event: Event):
        self.events.emit(event)

    def _handle_event_signal(self, event: Event):
        self._state._handle_event(event)
        if not self._dying:
            self.update()

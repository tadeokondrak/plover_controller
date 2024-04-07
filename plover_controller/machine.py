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
import sdl2
import threading
import ctypes
import re
import plover
import plover.misc
from util import get_keys_for_stroke
from copy import copy
from dataclasses import dataclass
from math import atan2, floor, hypot, sqrt, tau
from typing import Callable
from PyQt5.QtCore import QVariant, pyqtSignal, Qt
from PyQt5.QtGui import QFont
from plover.resource import resource_exists, resource_filename
from plover.machine.base import StenotypeBase
from PyQt5.QtWidgets import (
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
    SDL_GetError,
    SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS,
    SDL_HINT_NO_SIGNAL_HANDLERS,
    SDL_HINT_JOYSTICK_HIDAPI,
    SDL_HINT_JOYSTICK_RAWINPUT,
    SDL_HINT_JOYSTICK_RAWINPUT_CORRELATE_XINPUT,
    SDL_HINT_JOYSTICK_THREAD,
    SDL_Init,
    SDL_INIT_JOYSTICK,
    SDL_INIT_VIDEO,
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
    SDL_free,
)

SDL_strdup_void = sdl2.dll._bind("SDL_strdup", [ctypes.c_char_p], ctypes.c_void_p)

mapping_path = "asset:plover_controller:assets/default_mapping.txt"
if not resource_exists(mapping_path):
    raise Exception("couldn't find default mapping file")

with open(resource_filename(mapping_path), "r") as f:
    DEFAULT_MAPPING = f.read()


@dataclass
class Stick:
    name: str
    x_axis: str
    y_axis: str
    offset: float
    segments: list[str]


@dataclass
class Trigger:
    name: str
    axis: str


@dataclass
class Button:
    name: str
    button: str


def parse_mappings(text):
    sticks = {}
    buttons = {}
    triggers = {}
    ordered_mappings = {}
    unordered_mappings = []
    for line in text.splitlines():
        if not line or line.startswith("//"):
            continue
        if match := re.match(
            r"(\w+) stick has segments \(([a-z,]+)\) on axes (\d+) and (\d+) offset by ([0-9-.]+) degrees",
            line,
        ):
            stick = Stick(
                name=match[1],
                x_axis=f"a{match[3]}",
                y_axis=f"a{match[4]}",
                offset=float(match[5]),
                segments=match[2].split(","),
            )
            sticks[stick.name] = stick
        elif match := re.match(r"([a-z0-9,]+) -> ([A-Z-*#]+)", line):
            lhs = match[1].split(",")
            rhs = get_keys_for_stroke(match[2])
            unordered_mappings.append((lhs, rhs))
        elif match := re.match(r"(\w+)\(([a-z,]+)\) -> ([A-Z-*#]+)", line):
            ordered_mappings[
                tuple(f"{match[1]}{pos}" for pos in match[2].split(","))
            ] = get_keys_for_stroke(match[3])
        elif match := re.match(r"button (\d+) is ([a-z0-9]+)", line):
            button = Button(
                name=match[2],
                button=f"b{match[1]}",
            )
            buttons[button.button] = button
        elif match := re.match(r"trigger on axis (\d+) is ([a-z0-9]+)", line):
            trigger = Trigger(
                name=match[2],
                axis=f"a{match[1]}",
            )
            triggers[trigger.axis] = trigger
        else:
            print(f"don't know how to parse '{line}', skipping")
    return (
        sticks,
        buttons,
        triggers,
        unordered_mappings,
        ordered_mappings,
    )


def buttons_to_keys(in_keys, unordered_mappings):
    keys = set()
    for chord, result in unordered_mappings:
        if all(map(lambda x: x in in_keys, chord)):
            for key in chord:
                in_keys.remove(key)
            keys.update(result)
    return keys


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
    set_hint_event_type = None
    listeners: set[Callable[[SDL_Event], None]] = set()

    def __init__(self):
        super().__init__()

    def run(self):
        with self.lock:
            SDL_Quit()
            SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS, b"1")
            SDL_SetHint(SDL_HINT_NO_SIGNAL_HANDLERS, b"1")
            SDL_Init(SDL_INIT_VIDEO | SDL_INIT_JOYSTICK)
            self.set_hint_event_type = SDL_RegisterEvents(1)

            for i in range(SDL_NumJoysticks()):
                js = SDL_JoystickOpen(i)

        event = SDL_Event()
        while True:
            if not SDL_WaitEvent(event):
                error = SDL_GetError()
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
                    for listener in self.listeners:
                        listener(event)

    def add_listener(self, listener: Callable[[SDL_Event], None]):
        with self.lock:
            self.listeners.add(listener)

    def remove_listener(self, listener: Callable[[SDL_Event], None]):
        with self.lock:
            self.listeners.remove(listener)

    def set_hint(self, name, value):
        with self.lock:
            event = SDL_Event()
            event.type = self.set_hint_event_type
            event.user.data1 = SDL_strdup_void(name)
            event.user.data2 = SDL_strdup_void(value)
            SDL_PushEvent(event)


class ControllerMachine(StenotypeBase):
    KEYMAP_MACHINE_TYPE = "TX Bolt"
    KEYS_LAYOUT = """
        #  #  #  #  #  #  #  #  #  #
        S- T- P- H- * -F -P -L -T -D
        S- K- W- R- * -R -B -G -S -Z
               A- O- -E -U
    """

    _controller = None
    _controller_instance_id = None
    _stick_states = {}
    _chord_groups = {}
    _trigger_states = {}
    _pressed_buttons = set()
    _unsequenced_buttons = set()
    _pending_keys = set()
    _pending_stick_movements = {}
    _unordered_mappings = []
    _ordered_mappings = {}
    _sticks = {}
    _buttons = {}
    _triggers = {}

    def __init__(self, params):
        super().__init__()
        self._params = params
        (
            self._sticks,
            self._buttons,
            self._triggers,
            self._unordered_mappings,
            self._ordered_mappings,
        ) = parse_mappings(self._params["mapping"])

    def start_capture(self):
        self._initializing()
        get_controller_thread().add_listener(self._handle_sdl_event)
        hints = [
            (SDL_HINT_JOYSTICK_HIDAPI, self._params["use_hidapi"]),
            (SDL_HINT_JOYSTICK_RAWINPUT, self._params["use_rawinput"]),
            (
                SDL_HINT_JOYSTICK_RAWINPUT_CORRELATE_XINPUT,
                self._params["correlate_rawinput"],
            ),
            (SDL_HINT_JOYSTICK_THREAD, self._params["use_joystick_thread"]),
        ]
        for name, value in hints:
            get_controller_thread().set_hint(name, b"1" if value else b"0")
        self._ready()

    def stop_capture(self):
        get_controller_thread().remove_listener(self._handle_sdl_event)
        self._stopped()

    @classmethod
    def get_option_info(cls):
        return {
            "mapping": (DEFAULT_MAPPING, str),
            "timeout": (1.0, float),
            "stick_dead_zone": (0.6, float),
            "trigger_dead_zone": (0.9, float),
            "stroke_end_threshold": (0.4, float),
            "use_hidapi": (True, plover.misc.boolean),
            "use_rawinput": (False, plover.misc.boolean),
            "correlate_rawinput": (False, plover.misc.boolean),
            "use_joystick_thread": (False, plover.misc.boolean),
        }

    def _handle_sdl_event(self, event: SDL_Event):
        if event.type == SDL_JOYAXISMOTION:
            self._handle_axis(event.jaxis)
        elif event.type == SDL_JOYBALLMOTION:
            self._handle_ball(event.jball)
        elif event.type == SDL_JOYHATMOTION:
            self._handle_hat(event.jhat)
        elif event.type in [SDL_JOYBUTTONDOWN, SDL_JOYBUTTONUP]:
            self._handle_button(event.jbutton)
        elif event.type in [SDL_JOYDEVICEADDED, SDL_JOYDEVICEREMOVED]:
            self._handle_device(event.jdevice)

    def _handle_axis(self, event: SDL_JoyAxisEvent):
        axis = f"a{event.axis}"
        value = float(event.value) / 32768
        if axis in self._triggers:
            self._trigger_states[axis] = value
        elif axis in sum(
            map(lambda x: [x.x_axis, x.y_axis], self._sticks.values()), []
        ):
            self._stick_states[axis] = value
        self.check_axes()
        self.maybe_complete_ordered_chord()
        self.maybe_complete_stroke()

    def _handle_ball(self, event: SDL_JoyBallEvent):
        pass

    def _handle_hat(self, event: SDL_JoyHatEvent):
        pass

    def _handle_button(self, event: SDL_JoyButtonEvent):
        button = f"b{event.button}"
        if button_entry := self._buttons.get(button):
            button = button_entry.name
        if event.state:
            self._pressed_buttons.add(button)
            if button not in self._unsequenced_buttons:
                self._unsequenced_buttons.add(button)
        else:
            self._pressed_buttons.discard(button)
            self.maybe_complete_stroke()

    def _handle_device(self, event: SDL_JoyDeviceEvent):
        if event.type == SDL_JOYDEVICEADDED:
            SDL_JoystickOpen(event.which)

    def maybe_complete_ordered_chord(self):
        for stick in self._sticks.values():
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
                result := self._ordered_mappings.get(tuple(pending_stick_movements))
            ) is not None:
                self._pending_stick_movements[stick.name] = []
                self._pending_keys.update(result)
            else:
                for key in pending_stick_movements:
                    self._unsequenced_buttons.add(key)
                self._pending_stick_movements[stick.name] = []

    def maybe_complete_stroke(self):
        if not self._unsequenced_buttons and not self._pending_keys:
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
        if self._pressed_buttons:
            return
        keys = buttons_to_keys(
            self._unsequenced_buttons,
            self._unordered_mappings,
        ).union(self._pending_keys)
        actions = self.keymap.keys_to_actions(list(keys))
        self._unsequenced_buttons.clear()
        self._pending_stick_movements.clear()
        self._pending_keys.clear()
        if not actions:
            return
        self._notify(actions)

    def check_axes(self):
        for stick in self._sticks.values():
            lr = self._stick_states.get(stick.x_axis, 0.0)
            ud = self._stick_states.get(stick.y_axis, 0.0)
            self.check_stick(stick, lr, ud)
        for trigger in self._triggers.values():
            val = self._trigger_states.get(trigger.axis, 0)
            if val > 0:
                self._unsequenced_buttons.add(trigger.name)

    def check_stick(self, stick: Stick, lr, ud):
        if hypot(lr, ud) < self._params["stick_dead_zone"] * sqrt(2):
            return
        offset = stick.offset / 360 * tau
        segment_size = tau / len(stick.segments)
        angle = atan2(ud, lr) - offset
        while angle < 0:
            angle += tau
        while angle > tau:
            angle -= tau
        segment = floor(angle / tau * len(stick.segments))
        direction = stick.segments[segment % len(stick.segments)]
        segment_name = f"{stick.name}{direction}"
        if stick.name not in self._pending_stick_movements:
            self._pending_stick_movements[stick.name] = []
        inorder_list = self._pending_stick_movements[stick.name]
        if len(inorder_list) == 0 or segment_name != inorder_list[-1]:
            inorder_list.append(segment_name)


class ControllerOption(QGroupBox):
    axis_message = pyqtSignal(str)
    other_message = pyqtSignal(str)
    valueChanged = pyqtSignal(QVariant)
    _value = {}
    _joystick = None
    _joysticks = {}
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

        get_controller_thread().add_listener(self._handle_sdl_event)

    def __del__(self):
        get_controller_thread().remove_listener(self._handle_sdl_event)

    def _handle_sdl_event(self, event: SDL_Event):
        if event.type == SDL_JOYAXISMOTION:
            if event.jaxis.value / 32768 < 0.25:
                return
            message = f"Axis {event.jaxis.axis} motion (device: {event.jaxis.which})"
            if message != self._last_axis_message:
                try:
                    self.axis_message.emit(message)
                except RuntimeError:
                    pass
            self._last_axis_message = message
            return

        if event.type == SDL_JOYBALLMOTION:
            message = f"Ball {event.jball.ball} motion (device: {event.jball.which})"
        elif event.type == SDL_JOYHATMOTION:
            message = f"Hat {event.jhat.hat} motion (device: {event.jhat.which})"
        elif event.type == SDL_JOYBUTTONDOWN:
            message = (
                f"Button {event.jbutton.button} pressed (device: {event.jbutton.which})"
            )
        elif event.type == SDL_JOYBUTTONUP:
            message = f"Button {event.jbutton.button} released (device: {event.jbutton.which})"
        elif event.type == SDL_JOYDEVICEADDED:
            message = f"Device {event.jdevice.which} added"
        elif event.type == SDL_JOYDEVICEREMOVED:
            message = f"Device {event.jdevice.which} removed"
        else:
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

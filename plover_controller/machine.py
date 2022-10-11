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
from copy import copy
from dataclasses import dataclass
from math import atan2, floor, hypot, sqrt, tau
from typing import Callable, List, Set, Tuple
from PyQt5.QtCore import QVariant, pyqtSignal, Qt
from PyQt5.QtGui import QFont
from plover.resource import resource_exists, resource_filename
from plover.machine.base import StenotypeBase
from PyQt5.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from sdl2 import (
    SDL_CONTROLLERAXISMOTION,
    SDL_CONTROLLERBUTTONDOWN,
    SDL_CONTROLLERBUTTONUP,
    SDL_CONTROLLERDEVICEREMOVED,
    SDL_Event,
    SDL_GameControllerAddMappingsFromFile,
    SDL_GameControllerClose,
    SDL_GameControllerGetJoystick,
    SDL_GameControllerGetStringForAxis,
    SDL_GameControllerGetStringForButton,
    SDL_GameControllerOpen,
    SDL_GetError,
    SDL_HINT_GAMECONTROLLER_USE_BUTTON_LABELS,
    SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS,
    SDL_HINT_NO_SIGNAL_HANDLERS,
    SDL_Init,
    SDL_INIT_GAMECONTROLLER,
    SDL_INIT_JOYSTICK,
    SDL_INIT_VIDEO,
    SDL_IsGameController,
    SDL_JoystickClose,
    SDL_JoystickGetGUID,
    SDL_JoystickGetGUIDString,
    SDL_JoystickInstanceID,
    SDL_JoystickName,
    SDL_JoystickNumAxes,
    SDL_JoystickNumBalls,
    SDL_JoystickNumButtons,
    SDL_JoystickNumHats,
    SDL_JoystickOpen,
    SDL_NumJoysticks,
    SDL_Quit,
    SDL_SetHint,
    SDL_WaitEvent,
    SDL_WaitEventTimeout,
    SDL_WasInit,
    SDL_JOYAXISMOTION,
    SDL_JOYBALLMOTION,
    SDL_JOYHATMOTION,
    SDL_JOYBUTTONDOWN,
    SDL_JOYBUTTONUP,
    SDL_JOYDEVICEADDED,
    SDL_JOYDEVICEREMOVED,
    SDL_JoyAxisEvent,
    SDL_JoyBallEvent,
    SDL_JoyHatEvent,
    SDL_JoyButtonEvent,
    SDL_JoyDeviceEvent,
)

mapping_path = "asset:plover_controller:assets/default_mapping.txt"
if not resource_exists(mapping_path):
    raise Exception("couldn't find default mapping file")

with open(resource_filename(mapping_path), "r") as f:
    DEFAULT_MAPPING = f.read()


def get_keys_for_stroke(stroke_str: str) -> Tuple[str]:
    keys: List[str] = []
    passed_hyphen = False
    no_hyphen_keys = {"*", "#"}
    for key in stroke_str:
        if key == "-":
            passed_hyphen = True
            continue
        if key in no_hyphen_keys:
            keys.append(key)
        elif passed_hyphen:
            keys.append(f"-{key}")
        else:
            keys.append(f"{key}-")
    return tuple(keys)


@dataclass
class Stick:
    name: str
    x_axis: str
    y_axis: str
    offset: float
    segments: List[str]


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


def sdl_init(reinitialize=False):
    SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS, b"1")
    SDL_SetHint(SDL_HINT_NO_SIGNAL_HANDLERS, b"1")
    if reinitialize:
        SDL_Quit()
    SDL_Init(SDL_INIT_JOYSTICK | SDL_INIT_GAMECONTROLLER)
    db_path = "asset:plover_controller:assets/gamecontrollerdb.txt"
    if resource_exists(db_path):
        if (
            SDL_GameControllerAddMappingsFromFile(
                resource_filename(db_path).encode("utf-8")
            )
            == -1
        ):
            print("SDL couldn't load gamecontrollerdb")
    else:
        print("couldn't find gamecontrollerdb")


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
    listeners: Set[Callable[[SDL_Event], None]] = set()

    def __init__(self):
        super().__init__()

    def run(self):
        SDL_Quit()
        SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS, b"1")
        SDL_SetHint(SDL_HINT_NO_SIGNAL_HANDLERS, b"1")
        SDL_Init(SDL_INIT_JOYSTICK | SDL_INIT_GAMECONTROLLER)

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
                for listener in self.listeners:
                    listener(event)

    def add_listener(self, listener: Callable[[SDL_Event], None]):
        with self.lock:
            self.listeners.add(listener)

    def remove_listener(self, listener: Callable[[SDL_Event], None]):
        with self.lock:
            self.listeners.remove(listener)


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
                    (self._stick_states.get(axis, 0.0) for axis in [stick.x_axis, stick.y_axis]),
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
    message = pyqtSignal(str)
    valueChanged = pyqtSignal(QVariant)
    _value = {}
    _joystick = None
    _joysticks = {}
    _last_message = None

    def __init__(self):
        super().__init__()
        self.valueChanged.connect(self.setValue)

        self._form_layout = QFormLayout(self)

        self._timeout_label = QLabel("Timeout:", self)
        self._timeout_double_spin_box = QDoubleSpinBox(self)
        self._timeout_double_spin_box.setSingleStep(0.1)
        self._timeout_double_spin_box.valueChanged.connect(self.timeout_changed)
        self._form_layout.addRow(self._timeout_label, self._timeout_double_spin_box)

        self._stick_dead_zone_label = QLabel("Stick dead zone:", self)
        self._stick_dead_zone_double_spin_box = QDoubleSpinBox(self)
        self._stick_dead_zone_double_spin_box.setSingleStep(0.1)
        self._stick_dead_zone_double_spin_box.valueChanged.connect(
            self.stick_dead_zone_changed
        )
        self._form_layout.addRow(
            self._stick_dead_zone_label, self._stick_dead_zone_double_spin_box
        )

        self._trigger_dead_zone_label = QLabel("Trigger dead zone:", self)
        self._trigger_dead_zone_double_spin_box = QDoubleSpinBox(self)
        self._trigger_dead_zone_double_spin_box.setSingleStep(0.1)
        self._trigger_dead_zone_double_spin_box.valueChanged.connect(
            self.trigger_dead_zone_changed
        )
        self._form_layout.addRow(
            self._trigger_dead_zone_label, self._trigger_dead_zone_double_spin_box
        )

        self._stroke_end_threshold_label = QLabel("Stroke end threshold:", self)
        self._stroke_end_threshold_double_spin_box = QDoubleSpinBox(self)
        self._stroke_end_threshold_double_spin_box.setSingleStep(0.1)
        self._stroke_end_threshold_double_spin_box.valueChanged.connect(
            self.stroke_end_threshold_changed
        )
        self._form_layout.addRow(
            self._stroke_end_threshold_label, self._stroke_end_threshold_double_spin_box
        )

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

        self._feedback_label = QLabel("Last event:", self)
        self._feedback_output_label = QLabel(self)
        self._feedback_output_label.setFont(QFont("Monospace"))
        self._form_layout.addRow(self._feedback_label, self._feedback_output_label)

        self.message.connect(self._feedback_output_label.setText)
        get_controller_thread().add_listener(self._handle_sdl_event)

    def __del__(self):
        get_controller_thread().remove_listener(self._handle_sdl_event)

    def _handle_sdl_event(self, event: SDL_Event):
        if event.type == SDL_JOYAXISMOTION:
            message = f"Axis {event.jaxis.axis} motion (device: {event.jaxis.which})"
        elif event.type == SDL_JOYBALLMOTION:
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
        if message != self._last_message:
            try:
                self.message.emit(message)
            except RuntimeError:
                pass
        self._last_message = message

    def setValue(self, value):
        self._value = copy(value)
        if timeout := value.get("timeout"):
            self._timeout_double_spin_box.setValue(timeout)
        if stick_dead_zone := value.get("stick_dead_zone"):
            self._stick_dead_zone_double_spin_box.setValue(stick_dead_zone)
        if trigger_dead_zone := value.get("trigger_dead_zone"):
            self._trigger_dead_zone_double_spin_box.setValue(trigger_dead_zone)
        if stroke_end_threshold := value.get("stroke_end_threshold"):
            self._stroke_end_threshold_double_spin_box.setValue(stroke_end_threshold)
        if (mapping := value.get("mapping")) is not None:
            existing = self._mapping_text_edit.toPlainText()
            if mapping != existing:
                self._mapping_text_edit.setPlainText(mapping)

    def timeout_changed(self, value):
        if value == self._value.get("timeout"):
            return
        self._value["timeout"] = value
        self.valueChanged.emit(self._value)

    def stick_dead_zone_changed(self, value):
        if value == self._value.get("stick_dead_zone"):
            return
        self._value["stick_dead_zone"] = value
        self.valueChanged.emit(self._value)

    def trigger_dead_zone_changed(self, value):
        if value == self._value.get("trigger_dead_zone"):
            return
        self._value["trigger_dead_zone"] = value
        self.valueChanged.emit(self._value)

    def stroke_end_threshold_changed(self, value):
        if value == self._value.get("stroke_end_threshold"):
            return
        self._value["stroke_end_threshold"] = value
        self.valueChanged.emit(self._value)

    def mapping_changed(self):
        text = self._mapping_text_edit.toPlainText()
        if text == self._value.get("mapping"):
            return
        self._value["mapping"] = text
        self.valueChanged.emit(self._value)

    def reset_mapping(self):
        self._mapping_text_edit.setPlainText(DEFAULT_MAPPING)

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

import ctypes
import re
from copy import copy
from dataclasses import dataclass
from math import atan2, floor, hypot, sqrt, tau
from PyQt5.QtCore import QVariant, pyqtSignal, Qt
from PyQt5.QtGui import QFont
from plover.resource import resource_exists, resource_filename
from plover.machine.base import ThreadedStenotypeBase
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
    SDL_WaitEventTimeout,
    SDL_WasInit,
)


def get_keys_for_stroke(stroke_str):
    passed_hyphen = False
    keys = []
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


def parse_mappings(text):
    stick_segment_counts = {}
    stick_offsets = {}
    stick_directions = {}
    ordered_mappings = {}
    unordered_mappings = []
    for line in text.splitlines():
        if not line or line.startswith("//"):
            continue
        if match := re.match(
            r"(\w+) stick has (\d) segments offset by ([0-9-.]+) degrees \(([a-z,]+)\)",
            line,
        ):
            stick_segment_counts[match[1]] = int(match[2])
            stick_offsets[match[1]] = float(match[3])
            stick_directions[match[1]] = match[4].split(",")
        elif match := re.match(r"([a-z0-9,]+) -> ([A-Z-*#]+)", line):
            unordered_mappings.append(
                (match[1].split(","), get_keys_for_stroke(match[2]))
            )
        elif match := re.match(r"(left|right)\(([a-z,]+)\) -> ([A-Z-*#]+)", line):
            ordered_mappings[
                tuple(f"{match[1]}{pos}" for pos in match[2].split(","))
            ] = get_keys_for_stroke(match[3])
        else:
            print(f"don't know how to parse '{line}', skipping")
    return (
        stick_segment_counts,
        stick_offsets,
        stick_directions,
        unordered_mappings,
        ordered_mappings,
    )


mapping_path = "asset:plover_controller:assets/default_mapping.txt"
if not resource_exists(mapping_path):
    raise Exception("couldn't find default mapping file")

with open(resource_filename(mapping_path), "r") as f:
    DEFAULT_MAPPING = f.read()


def sdl_init(reinitialize=False):
    SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS, b"1")
    SDL_SetHint(SDL_HINT_NO_SIGNAL_HANDLERS, b"1")
    if reinitialize:
        SDL_Quit()
    SDL_Init(SDL_INIT_VIDEO | SDL_INIT_JOYSTICK | SDL_INIT_GAMECONTROLLER)
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


class ControllerMachine(ThreadedStenotypeBase):
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
    _stick_segment_counts = {}
    _stick_offsets = {}
    _stick_directions = {}

    def __init__(self, params):
        super().__init__()
        self._params = params
        (
            self._stick_segment_counts,
            self._stick_offsets,
            self._stick_directions,
            self._unordered_mappings,
            self._ordered_mappings,
        ) = parse_mappings(self._params["mapping"])

    def run(self):
        event = SDL_Event()
        timeout = int(self._params["timeout"] * 1000)
        while not self.finished.is_set():
            if SDL_WaitEventTimeout(event, timeout) != 0:
                self.handle_sdl_event(event)
            elif error := SDL_GetError():
                errstr = SDL_GetError().decode("utf-8")
                if errstr == "That operation is not supported":
                    self._stopped()
                    return
                self._error()
                raise Exception(errstr)
        self._stopped()

    def handle_sdl_event(self, event):
        self._ready()
        if event.type == SDL_CONTROLLERAXISMOTION:
            self.handle_axis_motion(event.caxis)
        elif event.type in [SDL_CONTROLLERBUTTONUP, SDL_CONTROLLERBUTTONDOWN]:
            self.handle_button(event.cbutton)
        elif event.type == SDL_CONTROLLERDEVICEREMOVED:
            self.handle_device_removed(event)

    def handle_axis_motion(self, event):
        if event.which != self._controller_instance_id:
            return
        axis = SDL_GameControllerGetStringForAxis(event.axis).decode("utf-8")
        value = float(event.value) / 32768
        if axis in ["lefttrigger", "righttrigger"]:
            self._trigger_states[axis] = value
        else:
            self._stick_states[axis] = value
        self.check_axes()
        self.maybe_complete_ordered_chord()
        self.maybe_complete_stroke()

    def handle_button(self, event):
        if event.which != self._controller_instance_id:
            return
        button = SDL_GameControllerGetStringForButton(event.button).decode("utf-8")
        if event.state:
            self._pressed_buttons.add(button)
            if button not in self._unsequenced_buttons:
                self._unsequenced_buttons.add(button)
        else:
            self._pressed_buttons.discard(button)
            self.maybe_complete_stroke()

    def handle_device_removed(self, event):
        if event.cdevice.which != self._controller_instance_id:
            return
        self.finished.set()

    def maybe_complete_ordered_chord(self):
        for stick in ["left", "right"]:
            if any(
                k.startswith(stick) and abs(v) > self._params["stroke_end_threshold"]
                for k, v in self._stick_states.items()
            ):
                continue
            pending_stick_movements = self._pending_stick_movements.get(stick, [])
            if (
                result := self._ordered_mappings.get(tuple(pending_stick_movements))
            ) is not None:
                self._pending_stick_movements[stick] = []
                self._pending_keys.update(result)
            else:
                for key in pending_stick_movements:
                    self._unsequenced_buttons.add(key)
                self._pending_stick_movements[stick] = []

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
        for axis in ["left", "right"]:
            lr = self._stick_states.get(f"{axis}x", 0)
            ud = self._stick_states.get(f"{axis}y", 0)
            self.check_stick(axis, lr, ud)
        for axis in ["lefttrigger", "righttrigger"]:
            val = self._trigger_states.get(axis, 0)
            if val > 0:
                self._unsequenced_buttons.add(axis)

    def check_stick(self, stick, lr, ud):
        if hypot(lr, ud) < self._params["stick_dead_zone"] * sqrt(2):
            return
        segment_count = self._stick_segment_counts[stick]
        offset = self._stick_offsets[stick] / 360 * tau
        segment_size = tau / segment_count
        angle = atan2(ud, lr) - offset
        while angle < 0:
            angle += tau
        while angle > tau:
            angle -= tau
        segment = floor(angle / tau * segment_count)
        direction = self._stick_directions[stick][segment % segment_count]
        segment_name = f"{stick}{direction}"
        if stick not in self._pending_stick_movements:
            self._pending_stick_movements[stick] = []
        inorder_list = self._pending_stick_movements[stick]
        if len(inorder_list) == 0 or segment_name != inorder_list[-1]:
            inorder_list.append(segment_name)

    def start_capture(self):
        sdl_init()
        for i in range(SDL_NumJoysticks()):
            if not SDL_IsGameController(i):
                continue
            gc = SDL_GameControllerOpen(i)
            js = SDL_GameControllerGetJoystick(gc)
            self._controller = gc
            self._joystick = js
            self._controller_instance_id = SDL_JoystickInstanceID(js)
            break
        if self._controller is not None:
            super().start_capture()
        else:
            self._error()

    def stop_capture(self):
        if self._controller:
            SDL_GameControllerClose(self._controller)
            self._controller = None
            self._joystick = None
            self._controller_instance_id = None
        SDL_Quit()
        super().stop_capture()

    @classmethod
    def get_option_info(cls):
        return {
            "mapping": (DEFAULT_MAPPING, str),
            "timeout": (1.0, float),
            "stick_dead_zone": (0.6, float),
            "trigger_dead_zone": (0.9, float),
            "stroke_end_threshold": (0.4, float),
        }


@dataclass
class JoystickInfo:
    name: str
    guid: str
    n_axes: int
    n_balls: int
    n_hats: int
    n_buttons: int


def enumerate_joysticks():
    joysticks = {}
    for i in range(SDL_NumJoysticks()):
        if not SDL_IsGameController(i):
            continue
        js = SDL_JoystickOpen(i)
        guid = SDL_JoystickGetGUID(js)
        guid_buf = ctypes.create_string_buffer(33)
        SDL_JoystickGetGUIDString(guid, guid_buf, 33)
        guid_str = guid_buf.value.decode("utf-8")
        info = JoystickInfo(
            name=SDL_JoystickName(js).decode("utf-8"),
            guid=guid_buf.value.decode("utf-8"),
            n_axes=SDL_JoystickNumAxes(js),
            n_balls=SDL_JoystickNumBalls(js),
            n_hats=SDL_JoystickNumHats(js),
            n_buttons=SDL_JoystickNumButtons(js),
        )
        joysticks[info.guid] = info
        SDL_JoystickClose(js)
    return joysticks


class ControllerOption(QGroupBox):
    valueChanged = pyqtSignal(QVariant)
    _value = {}
    _joystick = None
    _joysticks = {}

    def __init__(self):
        super().__init__()
        self.valueChanged.connect(self.setValue)

        self._form_layout = QFormLayout(self)

        self._device_label = QLabel("Device:", self)
        self._device_selector = QComboBox(self)
        self._device_selector.setEnabled(False)
        self._device_selector.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Preferred
        )
        self._device_refresh_button = QPushButton("Refresh", self)
        self._device_refresh_button.clicked.connect(self.refresh_devices)
        self._device_layout = QHBoxLayout()
        self._device_layout.addWidget(self._device_selector)
        self._device_layout.addWidget(self._device_refresh_button)
        self._form_layout.addRow(self._device_label, self._device_layout)

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

        self.populate_devices()

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

    def populate_devices(self):
        sdl_init(reinitialize=False)
        self._joysticks = enumerate_joysticks()
        for joystick in self._joysticks.values():
            self._device_selector.addItem(joystick.name, joystick.guid)

    def refresh_devices(self):
        sdl_init(reinitialize=True)
        self._device_selector.clear()
        self._joysticks = enumerate_joysticks()
        for joystick in self._joysticks.values():
            self._device_selector.addItem(joystick.name, joystick.guid)

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

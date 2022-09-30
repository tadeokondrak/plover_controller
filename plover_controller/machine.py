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
from plover.steno import Stroke
from copy import copy
from dataclasses import dataclass
from math import atan2, floor, hypot, sqrt, tau
from PyQt5.QtCore import QVariant, pyqtSignal, Qt
from PyQt5.QtGui import QFont
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
    SDL_GameControllerClose,
    SDL_GameControllerGetJoystick,
    SDL_GameControllerGetStringForAxis,
    SDL_GameControllerGetStringForButton,
    SDL_GameControllerOpen,
    SDL_GetError,
    SDL_HINT_GAMECONTROLLER_USE_BUTTON_LABELS,
    SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS,
    SDL_HINT_JOYSTICK_HIDAPI,
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
            unordered_mappings.append((match[1].split(","), Stroke(match[2]).keys()))
        elif match := re.match(r"(left|right)\(([a-z,]+)\) -> ([A-Z-*#]+)", line):
            ordered_mappings[
                tuple(f"{match[1]}{pos}" for pos in match[2].split(","))
            ] = Stroke(match[3]).keys()
        else:
            print(f"don't know how to parse '{line}', skipping")
    return (
        stick_segment_counts,
        stick_offsets,
        stick_directions,
        unordered_mappings,
        ordered_mappings,
    )


DEFAULT_MAPPING = """left stick has 6 segments offset by 0 degrees (dr,d,dl,ul,u,ur)
right stick has 6 segments offset by 0 degrees (dr,d,dl,ul,u,ur)

a -> -Z
b -> -S
x -> -D
y -> -T
back -> *
// guide ->
start -> #
leftstick -> S-
rightstick -> *
lefttrigger -> A-
leftshoulder -> O-
rightshoulder -> -E
righttrigger -> -U
// dpup ->
// dpdown ->
// dpleft ->
// dpright ->
// misc1 ->
// paddle1 ->
// paddle2 ->
// paddle3 ->
// paddle4 ->
// touchpad ->
leftdr -> R-
leftd -> W-
leftdl -> K-
leftul -> T-
leftu -> P-
leftur -> H-
rightdr -> -G
rightd -> -B
rightdl -> -R
rightul -> -F
rightu -> -P
rightur -> -L

left(d,dl,ul,dl) -> TW-
left(d,dl,ul,u,ul) -> KPW-
left(d,dl,ul,u,ul,dl,d) -> PW-
left(d,dl,ul,u,ul,dl) -> TPW-
left(d,dl,ul,u,ur,dr,ur,u,ul) -> KPWHR-
left(d,dl,ul,u,ur,dr,ur,u,ul,dl,d) -> WR-
left(d,dl,ul,u,ur,dr,ur) -> TKPWR-
left(d,dl,ul,u,ur,u,ul) -> KPWH-
left(d,dl,ul,u,ur,u,ul,dl,d) -> WH-
left(d,dl,ul,u,ur,u,ul,dl) -> TWH-
left(d,dl,ul,u,ur,u) -> TKWH-
left(d,dl,ul,u) -> PW-
left(d,dl,ul) -> TW-
left(d,dr,ur,dr) -> WH-
left(d,dr,ur,u,ul,dl) -> KW-
left(d,dr,ur,u,ul,dl,ul) -> KPWHR-
left(d,dr,ur,u,ul,dl,ul,u,ur,dr,d) -> KW-
left(d,dr,ur,u,ul,dl,ul,u,ur) -> TKPWR-
left(d,dr,ur,u,ul,u,ur,dr,d) -> TW-
left(d,dr,ur,u,ul,u,ur,dr) -> TWH-
left(d,dr,ur,u,ul,u,ur) -> TPWR-
left(d,dr,ur,u,ul,u) -> TWHR-
left(d,dr,ur,u,ul) -> TW-
left(d,dr,ur,u,ur,dr,d) -> PW-
left(d,dr,ur,u,ur,dr) -> PWH-
left(d,dr,ur,u,ur) -> PWR-
left(d,dr,ur,u) -> PW-
left(dl,d,dr,d) -> KR-
left(dl,d,dr,ur,dr) -> KWH-
left(dl,d,dr,ur,dr,d) -> KHR-
left(dl,d,dr,ur,dr,d,dl) -> KH-
left(dl,d,dr,ur,u,ul,u,ur,dr,d,dl) -> TK-
left(dl,d,dr,ur,u,ul,u,ur,dr) -> TKPWH-
left(dl,d,dr,ur,u,ul,u) -> TKWHR-
left(dl,d,dr,ur,u,ul) -> TK-
left(dl,d,dr,ur,u,ur) -> KPWR-
left(dl,d,dr,ur,u,ur,dr) -> KPWH-
left(dl,d,dr,ur,u,ur,dr,d) -> KPR-
left(dl,d,dr,ur,u,ur,dr,d,dl) -> KP-
left(dl,ul,u,ul) -> KP-
left(dl,ul,u,ur,dr,d,dr,ur,u,ul,dl) -> KW-
left(dl,ul,u,ur,dr,d,dr,ur,u) -> TKWHR-
left(dl,ul,u,ur,dr,d,dr) -> TKPWH-
left(dl,ul,u,ur,dr,ur,u,ul) -> KPR-
left(dl,ul,u,ur,dr,ur,u,ul,dl) -> KR-
left(dl,ul,u,ur,dr,ur,u) -> TKHR-
left(dl,ul,u,ur,dr,ur) -> TKPR-
left(dl,ul,u,ur,u,ul) -> KPH-
left(dl,ul,u,ur,u,ul,dl) -> KH-
left(dl,ul,u,ur,u) -> TKH-
left(dr,d,dl) -> KR-
left(dr,d,dl,d) -> KR-
left(dr,d,dl,ul,dl,d,dr) -> TR-
left(dr,d,dl,ul,dl,d) -> TKR-
left(dr,d,dl,ul,dl) -> TWR-
left(dr,d,dl,ul,u,ul) -> KPWR-
left(dr,d,dl,ul,u,ul,dl,d) -> KPR-
left(dr,d,dl,ul,u,ul,dl,d,dr) -> PR-
left(dr,d,dl,ul,u,ul,dl) -> TPWR-
left(dr,d,dl,ul,u,ur) -> HR-
left(dr,d,dl,ul,u,ur,u,ul,dl,d,dr) -> HR-
left(dr,d,dl,ul,u,ur,u,ul,dl) -> TPWHR-
left(dr,d,dl,ul,u,ur,u) -> TKWHR-
left(dr,d,dl,ul,u) -> PR-
left(dr,d,dl,ul) -> TR-
left(dr,ur,u,ul,dl) -> KR-
left(dr,ur,u,ul,dl,d,dl,ul,u,ur,dr) -> WR-
left(dr,ur,u,ul,dl,d,dl,ul,u) -> TKWHR-
left(dr,ur,u,ul,dl,d,dl) -> TPWHR-
left(dr,ur,u,ul,dl,d) -> WR-
left(dr,ur,u,ul,dl,ul) -> KPHR-
left(dr,ur,u,ul,dl,ul,u,ur) -> KPR-
left(dr,ur,u,ul,dl,ul,u,ur,dr) -> KR-
left(dr,ur,u,ul,dl,ul,u) -> TKHR-
left(dr,ur,u,ul,u,ur,dr) -> TR-
left(dr,ur,u,ul,u,ur) -> TPR-
left(dr,ur,u,ul,u) -> THR-
left(dr,ur,u,ul) -> TR-
left(dr,ur,u,ur) -> PR-
left(dr,ur,u) -> PR-
left(u,ul,dl) -> KP-
left(u,ul,dl,d,dl,ul) -> KPW-
left(u,ul,dl,d,dl,ul,u) -> PW-
left(u,ul,dl,d,dl) -> TPW-
left(u,ul,dl,d,dr,d,dl,ul) -> KPR-
left(u,ul,dl,d,dr,d,dl,ul,u) -> PR-
left(u,ul,dl,d,dr,d,dl) -> TPWR-
left(u,ul,dl,d,dr,d) -> TKPR-
left(u,ul,dl,d,dr,ur,dr,d,dl,ul,u) -> PH-
left(u,ul,dl,d,dr,ur,dr,d,dl) -> TPWHR-
left(u,ul,dl,d,dr,ur,dr) -> TKPWH-
left(u,ul,dl,ul) -> KP-
left(u,ur,dr,d,dl) -> KP-
left(u,ur,dr,d,dl,d) -> KPHR-
left(u,ur,dr,d,dl,d,dr) -> KPWH-
left(u,ur,dr,d,dl,d,dr,ur) -> KPR-
left(u,ur,dr,d,dl,d,dr,ur,u) -> KP-
left(u,ur,dr,d,dl,ul,dl,d,dr,ur,u) -> TP-
left(u,ur,dr,d,dl,ul,dl,d,dr) -> TKPWH-
left(u,ur,dr,d,dl,ul,dl) -> TPWHR-
left(u,ur,dr,d,dl,ul) -> TP-
left(u,ur,dr,d,dr,ur,u) -> PW-
left(u,ur,dr,d,dr,ur) -> PWR-
left(u,ur,dr,d,dr) -> PWH-
left(u,ur,dr,ur) -> PR-
left(ul,dl,d,dl) -> TW-
left(ul,dl,d,dr,d,dl,ul) -> TR-
left(ul,dl,d,dr,d,dl) -> TWR-
left(ul,dl,d,dr,d) -> TKR-
left(ul,dl,d,dr,ur,dr,d,dl,ul) -> TH-
left(ul,dl,d,dr,ur,dr,d,dl) -> TWH-
left(ul,dl,d,dr,ur,dr,d) -> TKHR-
left(ul,dl,d,dr,ur,dr) -> TKWH-
left(ul,dl,d,dr,ur,u,ur,dr,d,dl,ul) -> TP-
left(ul,dl,d,dr,ur,u,ur,dr,d) -> TKPHR-
left(ul,dl,d,dr,ur,u,ur) -> TKPWR-
left(ul,u,ur,dr,d,dl,d,dr,ur,u,ul) -> TK-
left(ul,u,ur,dr,d,dl,d,dr,ur) -> TKPWR-
left(ul,u,ur,dr,d,dl,d) -> TKPHR-
left(ul,u,ur,dr,d,dr,ur,u,ul) -> TW-
left(ul,u,ur,dr,d,dr,ur,u) -> TWH-
left(ul,u,ur,dr,d,dr,ur) -> TPWR-
left(ul,u,ur,dr,d,dr) -> TPWH-
left(ul,u,ur,dr,ur,u,ul) -> TR-
left(ul,u,ur,dr,ur,u) -> THR-
left(ul,u,ur,dr,ur) -> TPR-
left(ul,u,ur,u) -> TH-
left(ur,dr,d,dl) -> KH-
left(ur,dr,d,dl,d) -> KHR-
left(ur,dr,d,dl,d,dr) -> KWH-
left(ur,dr,d,dl,d,dr,ur) -> KH-
left(ur,dr,d,dl,ul,dl,d,dr,ur) -> TH-
left(ur,dr,d,dl,ul,dl,d,dr) -> TWH-
left(ur,dr,d,dl,ul,dl,d) -> TKHR-
left(ur,dr,d,dl,ul,dl) -> TWHR-
left(ur,dr,d,dl,ul,u,ul) -> KPWHR-
left(ur,dr,d,dl,ul,u,ul,dl,d,dr,ur) -> PH-
left(ur,dr,d,dl,ul,u,ul,dl,d) -> TKPHR-
left(ur,dr,d,dl,ul,u) -> PH-
left(ur,dr,d,dl,ul) -> TH-
left(ur,dr,d,dr) -> WH-
left(ur,dr,d) -> WH-
left(ur,u,ul,dl) -> KH-
left(ur,u,ul,dl,d,dl,ul) -> KPWH-
left(ur,u,ul,dl,d,dl,ul,u,ur) -> WH-
left(ur,u,ul,dl,d,dl,ul,u) -> TWH-
left(ur,u,ul,dl,d,dl) -> TPWH-
left(ur,u,ul,dl,d,dr,d,dl,ul) -> KPWHR-
left(ur,u,ul,dl,d,dr,d,dl,ul,u,ur) -> HR-
left(ur,u,ul,dl,d,dr,d) -> TKPHR-
left(ur,u,ul,dl,d) -> WH-
left(ur,u,ul,dl,ul) -> KPH-
left(ur,u,ul,dl,ul,u,ur) -> KH-
left(ur,u,ul,dl,ul,u) -> TKH-
left(ur,u,ul,u) -> TH-
left(ur,u,ul) -> TH-

right(dl,d,dr,d) -> -RG
right(dl,d,dr,ur,dr) -> -RBL
right(dl,d,dr,ur,dr,d,dl) -> -RL
right(dl,d,dr,ur,dr,d) -> -RLG
right(dl,d,dr,ur,u,ul) -> -FR
right(dl,d,dr,ur,u,ul,u) -> -FRBLG
right(dl,d,dr,ur,u,ul,u,ur,dr) -> -FRPBL
right(dl,d,dr,ur,u,ul,u,ur,dr,d,dl) -> -FR
right(dl,d,dr,ur,u,ur,dr,d,dl) -> -RP
right(dl,d,dr,ur,u,ur,dr,d) -> -RPG
right(dl,d,dr,ur,u,ur,dr) -> -RPBL
right(dl,d,dr,ur,u,ur) -> -RPBG
right(dl,ul,u,ul) -> -RP
right(dl,ul,u,ur,dr,d,dr) -> -FRPBL
right(dl,ul,u,ur,dr,d,dr,ur,u) -> -FRBLG
right(dl,ul,u,ur,dr,d,dr,ur,u,ul,dl) -> -RB
right(dl,ul,u,ur,dr,ur) -> -FRPG
right(dl,ul,u,ur,dr,ur,u) -> -FRLG
right(dl,ul,u,ur,dr,ur,u,ul,dl) -> -RG
right(dl,ul,u,ur,dr,ur,u,ul) -> -RPG
right(dl,ul,u,ur,u) -> -FRL
right(dl,ul,u,ur,u,ul,dl) -> -RL
right(dl,ul,u,ur,u,ul) -> -RPL
right(d,dl,ul) -> -FB
right(d,dl,ul,dl) -> -FB
right(d,dl,ul,u) -> -PB
right(d,dl,ul,u,ul,dl) -> -FPB
right(d,dl,ul,u,ul,dl,d) -> -PB
right(d,dl,ul,u,ul) -> -RPB
right(d,dl,ul,u,ur,dr,ur) -> -FRPBG
right(d,dl,ul,u,ur,dr,ur,u,ul,dl,d) -> -BG
right(d,dl,ul,u,ur,dr,ur,u,ul) -> -RPBLG
right(d,dl,ul,u,ur,u) -> -FRBL
right(d,dl,ul,u,ur,u,ul,dl) -> -FBL
right(d,dl,ul,u,ur,u,ul,dl,d) -> -BL
right(d,dl,ul,u,ur,u,ul) -> -RPBL
right(d,dr,ur,dr) -> -BL
right(d,dr,ur,u) -> -PB
right(d,dr,ur,u,ul) -> -FB
right(d,dr,ur,u,ul,dl) -> -RB
right(d,dr,ur,u,ul,dl,ul,u,ur) -> -FRPBG
right(d,dr,ur,u,ul,dl,ul,u,ur,dr,d) -> -RB
right(d,dr,ur,u,ul,dl,ul) -> -RPBLG
right(d,dr,ur,u,ul,u) -> -FBLG
right(d,dr,ur,u,ul,u,ur) -> -FPBG
right(d,dr,ur,u,ul,u,ur,dr) -> -FBL
right(d,dr,ur,u,ul,u,ur,dr,d) -> -FB
right(d,dr,ur,u,ur) -> -PBG
right(d,dr,ur,u,ur,dr) -> -PBL
right(d,dr,ur,u,ur,dr,d) -> -PB
right(dr,d,dl) -> -RG
right(dr,d,dl,d) -> -RG
right(dr,d,dl,ul) -> -FG
right(dr,d,dl,ul,dl) -> -FBG
right(dr,d,dl,ul,dl,d) -> -FRG
right(dr,d,dl,ul,dl,d,dr) -> -FG
right(dr,d,dl,ul,u) -> -PG
right(dr,d,dl,ul,u,ul,dl) -> -FPBG
right(dr,d,dl,ul,u,ul,dl,d,dr) -> -PG
right(dr,d,dl,ul,u,ul,dl,d) -> -RPG
right(dr,d,dl,ul,u,ul) -> -RPBG
right(dr,d,dl,ul,u,ur) -> -LG
right(dr,d,dl,ul,u,ur,u) -> -FRBLG
right(dr,d,dl,ul,u,ur,u,ul,dl) -> -FPBLG
right(dr,d,dl,ul,u,ur,u,ul,dl,d,dr) -> -LG
right(dr,ur,u) -> -PG
right(dr,ur,u,ul) -> -FG
right(dr,ur,u,ul,dl) -> -RG
right(dr,ur,u,ul,dl,d) -> -BG
right(dr,ur,u,ul,dl,d,dl) -> -FPBLG
right(dr,ur,u,ul,dl,d,dl,ul,u) -> -FRBLG
right(dr,ur,u,ul,dl,d,dl,ul,u,ur,dr) -> -BG
right(dr,ur,u,ul,dl,ul,u) -> -FRLG
right(dr,ur,u,ul,dl,ul,u,ur,dr) -> -RG
right(dr,ur,u,ul,dl,ul,u,ur) -> -RPG
right(dr,ur,u,ul,dl,ul) -> -RPLG
right(dr,ur,u,ul,u) -> -FLG
right(dr,ur,u,ul,u,ur) -> -FPG
right(dr,ur,u,ul,u,ur,dr) -> -FG
right(dr,ur,u,ur) -> -PG
right(ul,dl,d,dl) -> -FB
right(ul,dl,d,dr,d) -> -FRG
right(ul,dl,d,dr,d,dl) -> -FBG
right(ul,dl,d,dr,d,dl,ul) -> -FG
right(ul,dl,d,dr,ur,dr) -> -FRBL
right(ul,dl,d,dr,ur,dr,d) -> -FRLG
right(ul,dl,d,dr,ur,dr,d,dl) -> -FBL
right(ul,dl,d,dr,ur,dr,d,dl,ul) -> -FL
right(ul,dl,d,dr,ur,u,ur) -> -FRPBG
right(ul,dl,d,dr,ur,u,ur,dr,d) -> -FRPLG
right(ul,dl,d,dr,ur,u,ur,dr,d,dl,ul) -> -FP
right(ul,u,ur,dr,d,dl,d) -> -FRPLG
right(ul,u,ur,dr,d,dl,d,dr,ur) -> -FRPBG
right(ul,u,ur,dr,d,dl,d,dr,ur,u,ul) -> -FR
right(ul,u,ur,dr,d,dr) -> -FPBL
right(ul,u,ur,dr,d,dr,ur) -> -FPBG
right(ul,u,ur,dr,d,dr,ur,u) -> -FBL
right(ul,u,ur,dr,d,dr,ur,u,ul) -> -FB
right(ul,u,ur,dr,ur) -> -FPG
right(ul,u,ur,dr,ur,u) -> -FLG
right(ul,u,ur,dr,ur,u,ul) -> -FG
right(ul,u,ur,u) -> -FL
right(u,ul,dl,d,dl) -> -FPB
right(u,ul,dl,d,dl,ul,u) -> -PB
right(u,ul,dl,d,dl,ul) -> -RPB
right(u,ul,dl,d,dr,d) -> -FRPG
right(u,ul,dl,d,dr,d,dl) -> -FPBG
right(u,ul,dl,d,dr,d,dl,ul,u) -> -PG
right(u,ul,dl,d,dr,d,dl,ul) -> -RPG
right(u,ul,dl,d,dr,ur,dr) -> -FRPBL
right(u,ul,dl,d,dr,ur,dr,d,dl) -> -FPBLG
right(u,ul,dl,d,dr,ur,dr,d,dl,ul,u) -> -PL
right(u,ul,dl,ul) -> -RP
right(u,ul,dl) -> -RP
right(u,ur,dr,d,dl,d,dr,ur,u) -> -RP
right(u,ur,dr,d,dl,d,dr,ur) -> -RPG
right(u,ur,dr,d,dl,d,dr) -> -RPBL
right(u,ur,dr,d,dl,d) -> -RPLG
right(u,ur,dr,d,dl,ul) -> -FP
right(u,ur,dr,d,dl,ul,dl) -> -FPBLG
right(u,ur,dr,d,dl,ul,dl,d,dr) -> -FRPBL
right(u,ur,dr,d,dl,ul,dl,d,dr,ur,u) -> -FP
right(u,ur,dr,d,dl) -> -RP
right(u,ur,dr,d,dr) -> -PBL
right(u,ur,dr,d,dr,ur) -> -PBG
right(u,ur,dr,d,dr,ur,u) -> -PB
right(u,ur,dr,ur) -> -PG
right(ur,dr,d) -> -BL
right(ur,dr,d,dl,d,dr) -> -RBL
right(ur,dr,d,dl,d,dr,ur) -> -RL
right(ur,dr,d,dl,d) -> -RLG
right(ur,dr,d,dl,ul) -> -FL
right(ur,dr,d,dl,ul,dl) -> -FBLG
right(ur,dr,d,dl,ul,dl,d) -> -FRLG
right(ur,dr,d,dl,ul,dl,d,dr) -> -FBL
right(ur,dr,d,dl,ul,dl,d,dr,ur) -> -FL
right(ur,dr,d,dl,ul,u) -> -PL
right(ur,dr,d,dl,ul,u,ul,dl,d) -> -FRPLG
right(ur,dr,d,dl,ul,u,ul,dl,d,dr,ur) -> -PL
right(ur,dr,d,dl,ul,u,ul) -> -RPBLG
right(ur,dr,d,dl) -> -RL
right(ur,dr,d,dr) -> -BL
right(ur,u,ul) -> -FL
right(ur,u,ul,dl,d) -> -BL
right(ur,u,ul,dl,d,dl) -> -FPBL
right(ur,u,ul,dl,d,dl,ul,u) -> -FBL
right(ur,u,ul,dl,d,dl,ul,u,ur) -> -BL
right(ur,u,ul,dl,d,dl,ul) -> -RPBL
right(ur,u,ul,dl,d,dr,d) -> -FRPLG
right(ur,u,ul,dl,d,dr,d,dl,ul,u,ur) -> -LG
right(ur,u,ul,dl,d,dr,d,dl,ul) -> -RPBLG
right(ur,u,ul,dl,ul,u) -> -FRL
right(ur,u,ul,dl,ul,u,ur) -> -RL
right(ur,u,ul,dl,ul) -> -RPL
right(ur,u,ul,dl) -> -RL
right(ur,u,ul,u) -> -FL
"""


def sdl_init(reinitialize=False):
    SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS, b"1")
    SDL_SetHint(SDL_HINT_NO_SIGNAL_HANDLERS, b"1")
    if reinitialize:
        SDL_Quit()
    SDL_Init(SDL_INIT_VIDEO | SDL_INIT_JOYSTICK | SDL_INIT_GAMECONTROLLER)


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


def enumerate_joysticks() -> dict[str, JoystickInfo]:
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

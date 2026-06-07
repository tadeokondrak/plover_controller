from math import cos, sin, tau
from plover_controller.qt_compat import (
    Qt,
    QRectF,
    QPointF,
    QPainter,
    QPen,
    QBrush,
    QColor,
    QWidget,
    QSizePolicy,
)
from plover_controller.config import Mappings
from plover_controller.machine import (
    Event,
    AxisEvent,
    ButtonEvent,
    ControllerButtonEvent,
    HatEvent,
)
from plover_controller.util import stick_segment

try:
    from PySide6.QtGui import QPainterPath, QFont, QFontMetrics
except ImportError:
    from PyQt5.QtGui import QPainterPath, QFont, QFontMetrics

REF_W = 1000
REF_H = 580

BODY_COLOR = QColor(40, 40, 44)
BODY_STROKE = QColor(65, 65, 70)
INACTIVE_FILL = QColor(58, 58, 64)
INACTIVE_STROKE = QColor(85, 85, 92)
ACTIVE_FILL = QColor(255, 255, 255)
ACTIVE_STROKE = QColor(220, 220, 220)
LABEL_COLOR = QColor(170, 170, 175)
LABEL_ACTIVE_COLOR = QColor(25, 25, 25)
STICK_BG = QColor(30, 30, 34)
DPAD_BASE = QColor(48, 48, 54)


def _body_path():
    p = QPainterPath()
    p.moveTo(190, 95)
    p.cubicTo(230, 42, 380, 22, 500, 22)
    p.cubicTo(620, 22, 770, 42, 810, 95)
    p.cubicTo(845, 140, 858, 210, 852, 270)
    p.lineTo(838, 370)
    p.cubicTo(832, 420, 808, 480, 755, 518)
    p.cubicTo(715, 545, 678, 540, 648, 508)
    p.cubicTo(618, 472, 592, 415, 562, 385)
    p.cubicTo(542, 365, 458, 365, 438, 385)
    p.cubicTo(408, 415, 382, 472, 352, 508)
    p.cubicTo(322, 540, 285, 545, 245, 518)
    p.cubicTo(192, 480, 168, 420, 162, 370)
    p.lineTo(148, 270)
    p.cubicTo(142, 210, 155, 140, 190, 95)
    p.closeSubpath()
    return p


BODY = _body_path()

FRONT_ELEMENTS = {
    "y":              ("circle", "Y",  718, 162, 26),
    "x":              ("circle", "X",  660, 220, 26),
    "b":              ("circle", "B",  776, 220, 26),
    "a":              ("circle", "A",  718, 278, 26),

    "dpadu":          ("dpad_arm", None, 261, 316, 38, 51, "up"),
    "dpadd":          ("dpad_arm", None, 261, 367, 38, 51, "down"),
    "dpadl":          ("dpad_arm", None, 229, 348, 51, 38, "left"),
    "dpadr":          ("dpad_arm", None, 280, 348, 51, 38, "right"),

    "leftshoulder":   ("rect", "LB", 178, 68, 185, 34, 12),
    "rightshoulder":  ("rect", "RB", 638, 68, 185, 34, 12),

    "lefttrigger":    ("rect", "LT", 200, 22, 142, 40, 10),
    "righttrigger":   ("rect", "RT", 658, 22, 142, 40, 10),

    "guide":          ("circle", None, 500, 170, 20),
    "back":           ("circle", None, 418, 192, 14),
    "start":          ("circle", None, 582, 192, 14),
    "misc1":          ("circle", None, 500, 222, 12),

    "leftstick":      ("stick", "LS", 280, 190, 52),
    "rightstick":     ("stick", "RS", 640, 365, 52),

    "touchpad":       ("rect", "TP", 452, 250, 96, 42, 14),
}

BACK_ELEMENTS = {
    "lefttrigger":   ("rect", "LT", 200, 22, 142, 52, 10),
    "righttrigger":  ("rect", "RT", 658, 22, 142, 52, 10),
    "paddle1":       ("rect", "P1", 655, 240, 55, 100, 14),
    "paddle2":       ("rect", "P2", 720, 270, 55, 100, 14),
    "paddle3":       ("rect", "P3", 225, 270, 55, 100, 14),
    "paddle4":       ("rect", "P4", 290, 240, 55, 100, 14),
}

STICK_RADIUS = 52
STICK_POSITIONS = {
    "left": (280, 190),
    "right": (640, 365),
}

DPAD_CENTER = QPointF(280, 367)
DPAD_SIZE = 18

INPUT_LABELS = {
    "guide": "◉",
    "back": "◁",
    "start": "▷",
    "misc1": "☆",
}


def _build_steno_labels(mappings):
    labels = {}
    for inputs, keys in mappings.unordered_mappings:
        if len(inputs) == 1:
            steno = "".join(keys)
            labels[inputs[0]] = steno
    return labels


class ControllerView(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pressed = set()
        self._stick_axes = {}
        self._trigger_values = {}
        self._chroma_color = QColor(0, 177, 64)
        self._layout_mode = "horizontal"
        self._steno_labels = {}
        self._mappings = None
        self._stick_dead_zone = 0.6
        self._active_segments = {}
        self._show_back = True
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(300, 200)

    def set_chroma_color(self, color):
        self._chroma_color = QColor(color) if isinstance(color, str) else color
        self.update()

    def set_layout_mode(self, mode):
        self._layout_mode = mode
        self.update()

    def set_show_back(self, show):
        self._show_back = bool(show)
        self.update()

    def set_mappings(self, mappings, params):
        self._mappings = mappings
        self._stick_dead_zone = params.get("stick_dead_zone", 0.6)
        if mappings:
            self._steno_labels = _build_steno_labels(mappings)
        self.update()

    def handle_event(self, event):
        if isinstance(event, ControllerButtonEvent):
            if event.state:
                self._pressed.add(event.name)
            else:
                self._pressed.discard(event.name)
            self.update()

        elif isinstance(event, ButtonEvent):
            name = f"b{event.button}"
            if self._mappings:
                alias = self._mappings.buttons.get(name)
                if alias:
                    name = alias.renamed
            if event.state:
                self._pressed.add(name)
            else:
                self._pressed.discard(name)
            self.update()

        elif isinstance(event, AxisEvent):
            axis_key = f"a{event.axis}"
            self._stick_axes[axis_key] = event.value

            if self._mappings:
                trigger = self._mappings.triggers.get(axis_key)
                if trigger:
                    self._trigger_values[trigger.renamed] = event.value
                    self.update()
                    return

                for stick in self._mappings.sticks.values():
                    if axis_key in (stick.x_axis, stick.y_axis):
                        lr = self._stick_axes.get(stick.x_axis, 0.0)
                        ud = self._stick_axes.get(stick.y_axis, 0.0)
                        seg = stick_segment(
                            stick_dead_zone=self._stick_dead_zone,
                            offset=stick.offset,
                            segment_count=len(stick.segments),
                            lr=lr,
                            ud=ud,
                        )
                        if seg is not None:
                            self._active_segments[stick.name] = stick.segments[seg]
                        else:
                            self._active_segments.pop(stick.name, None)
                        self.update()
                        return

        elif isinstance(event, HatEvent):
            hat_key = f"h{event.hat}"
            if self._mappings:
                alias = self._mappings.hats.get(hat_key)
                if alias:
                    hat_key = alias.renamed
            for d, bit in [("u", 1), ("d", 4), ("l", 8), ("r", 2)]:
                name = f"{hat_key}{d}"
                if event.value & bit:
                    self._pressed.add(name)
                else:
                    self._pressed.discard(name)
            self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), self._chroma_color)

        if not self._show_back:
            front_rect = QRectF(0, 0, self.width(), self.height())
        elif self._layout_mode == "horizontal":
            front_rect = QRectF(0, 0, self.width() / 2, self.height())
            back_rect = QRectF(self.width() / 2, 0, self.width() / 2, self.height())
        else:
            front_rect = QRectF(0, 0, self.width(), self.height() / 2)
            back_rect = QRectF(0, self.height() / 2, self.width(), self.height() / 2)

        self._draw_view(painter, front_rect, "front")
        if self._show_back:
            self._draw_view(painter, back_rect, "back")

    def _setup_transform(self, painter, rect):
        padding = 8
        inner = rect.adjusted(padding, padding, -padding, -padding)
        scale = min(inner.width() / REF_W, inner.height() / REF_H)
        sw = REF_W * scale
        sh = REF_H * scale
        ox = inner.x() + (inner.width() - sw) / 2
        oy = inner.y() + (inner.height() - sh) / 2
        painter.translate(ox, oy)
        painter.scale(scale, scale)

    def _draw_view(self, painter, rect, view):
        painter.save()
        self._setup_transform(painter, rect)
        self._draw_body(painter)
        if view == "front":
            self._draw_front(painter)
        else:
            self._draw_back(painter)
        painter.restore()

    def _draw_body(self, painter):
        painter.setPen(QPen(BODY_STROKE, 3))
        painter.setBrush(QBrush(BODY_COLOR))
        painter.drawPath(BODY)

    def _draw_front(self, painter):
        self._draw_dpad_base(painter)

        for name, elem in FRONT_ELEMENTS.items():
            active = name in self._pressed
            shape = elem[0]
            if shape == "stick":
                self._draw_stick_base(painter, elem, active)
            elif shape == "dpad_arm":
                self._draw_dpad_arm(painter, name, elem, active)
            else:
                steno = self._steno_labels.get(name)
                self._draw_button(painter, elem, active, steno, INPUT_LABELS.get(name))

        self._draw_stick_segments(painter)
        self._draw_stick_indicators(painter)
        self._draw_trigger_fill(painter, "left", FRONT_ELEMENTS)
        self._draw_trigger_fill(painter, "right", FRONT_ELEMENTS)

    def _is_trigger_active(self, name):
        if not self._mappings:
            return False
        for trigger in self._mappings.triggers.values():
            val = self._trigger_values.get(trigger.renamed, 0.0)
            if val > 0.05:
                if name == "lefttrigger" and trigger.renamed.startswith("l"):
                    return True
                if name == "righttrigger" and trigger.renamed.startswith("r"):
                    return True
        return False

    def _draw_back(self, painter):
        for name, elem in BACK_ELEMENTS.items():
            if name in ("lefttrigger", "righttrigger"):
                self._draw_button(painter, elem, False, self._steno_labels.get(name))
            else:
                active = name in self._pressed
                self._draw_button(painter, elem, active, self._steno_labels.get(name))
        self._draw_trigger_fill(painter, "left", BACK_ELEMENTS)
        self._draw_trigger_fill(painter, "right", BACK_ELEMENTS)

    def _draw_button(self, painter, elem, active, steno_label=None, icon=None):
        shape = elem[0]
        label = elem[1]

        fill = ACTIVE_FILL if active else INACTIVE_FILL
        stroke = ACTIVE_STROKE if active else INACTIVE_STROKE

        painter.setPen(QPen(stroke, 1.8))
        painter.setBrush(QBrush(fill))

        if shape == "circle":
            cx, cy, r = elem[2], elem[3], elem[4]
            painter.drawEllipse(QPointF(cx, cy), r, r)
            self._draw_text(painter, cx, cy, label, steno_label, icon, active, r * 2)
        elif shape == "rect":
            x, y, w, h, cr = elem[2], elem[3], elem[4], elem[5], elem[6]
            painter.drawRoundedRect(QRectF(x, y, w, h), cr, cr)
            self._draw_text(painter, x + w / 2, y + h / 2, label, steno_label, icon, active, min(w, h))

    def _draw_stick_base(self, painter, elem, active):
        cx, cy, r = elem[2], elem[3], elem[4]
        painter.setPen(QPen(INACTIVE_STROKE, 1.5))
        painter.setBrush(QBrush(STICK_BG))
        painter.drawEllipse(QPointF(cx, cy), r, r)
        if active:
            painter.setPen(QPen(ACTIVE_FILL, 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(cx, cy), r + 4, r + 4)

    def _draw_dpad_base(self, painter):
        cx, cy = DPAD_CENTER.x(), DPAD_CENTER.y()
        arm_w = 38
        arm_h = 42
        cross = QPainterPath()
        cross.addRoundedRect(QRectF(cx - arm_w / 2, cy - arm_h - DPAD_SIZE / 2, arm_w, arm_h * 2 + DPAD_SIZE), 6, 6)
        horiz = QPainterPath()
        horiz.addRoundedRect(QRectF(cx - arm_h - DPAD_SIZE / 2, cy - arm_w / 2, arm_h * 2 + DPAD_SIZE, arm_w), 6, 6)
        cross = cross.united(horiz)

        painter.setPen(QPen(QColor(55, 55, 60), 1.5))
        painter.setBrush(QBrush(DPAD_BASE))
        painter.drawPath(cross)

    def _draw_dpad_arm(self, painter, name, elem, active):
        _, _, x, y, w, h, direction = elem
        if not active:
            return
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(ACTIVE_FILL))
        painter.drawRoundedRect(QRectF(x, y, w, h), 6, 6)

    def _draw_stick_segments(self, painter):
        if not self._mappings:
            return
        for stick in self._mappings.sticks.values():
            if stick.name not in STICK_POSITIONS:
                continue
            cx, cy = STICK_POSITIONS[stick.name]
            n = len(stick.segments)
            active_dir = self._active_segments.get(stick.name)

            for i, seg_dir in enumerate(stick.segments):
                seg_name = f"{stick.name}{seg_dir}"
                is_active = (seg_dir == active_dir)
                angle_start = stick.offset + (i * 360.0 / n)
                angle_span = 360.0 / n

                if is_active:
                    path = QPainterPath()
                    path.moveTo(cx, cy)
                    r = STICK_RADIUS - 4
                    rect = QRectF(cx - r, cy - r, r * 2, r * 2)
                    path.arcTo(rect, -angle_start, -angle_span)
                    path.closeSubpath()
                    painter.setPen(Qt.PenStyle.NoPen)
                    color = QColor(ACTIVE_FILL)
                    color.setAlpha(180)
                    painter.setBrush(QBrush(color))
                    painter.drawPath(path)

                steno = self._steno_labels.get(seg_name)
                if steno:
                    mid_angle = angle_start + angle_span / 2
                    rad = mid_angle * tau / 360.0
                    label_r = STICK_RADIUS * 0.6
                    lx = cx + label_r * cos(rad)
                    ly = cy + label_r * sin(rad)
                    text_col = LABEL_ACTIVE_COLOR if is_active else QColor(140, 140, 145)
                    font = QFont("Sans", 9)
                    font.setBold(True)
                    painter.setFont(font)
                    painter.setPen(QPen(text_col))
                    painter.drawText(
                        QRectF(lx - 22, ly - 10, 44, 20),
                        Qt.AlignmentFlag.AlignCenter,
                        steno,
                    )

    def _draw_stick_indicators(self, painter):
        if not self._mappings:
            return
        for stick in self._mappings.sticks.values():
            if stick.name not in STICK_POSITIONS:
                continue
            cx, cy = STICK_POSITIONS[stick.name]
            lr = self._stick_axes.get(stick.x_axis, 0.0)
            ud = self._stick_axes.get(stick.y_axis, 0.0)
            r = STICK_RADIUS - 6
            dx = cx + lr * r
            dy = cy + ud * r
            painter.setPen(QPen(QColor(200, 200, 200, 180), 1.5))
            painter.setBrush(QBrush(QColor(230, 230, 230, 220)))
            painter.drawEllipse(QPointF(dx, dy), 9, 9)

    def _draw_trigger_fill(self, painter, side, elements):
        if not self._mappings:
            return
        for trigger in self._mappings.triggers.values():
            val = self._trigger_values.get(trigger.renamed, 0.0)
            if val <= 0.01:
                continue
            if side == "left" and not trigger.renamed.startswith("l"):
                continue
            if side == "right" and not trigger.renamed.startswith("r"):
                continue

            elem = elements.get(f"{side}trigger")
            if not elem:
                continue
            x, y, w, h, cr = elem[2], elem[3], elem[4], elem[5], elem[6]
            fill_w = w * min(val, 1.0)
            painter.setPen(Qt.PenStyle.NoPen)
            color = QColor(ACTIVE_FILL)
            color.setAlpha(140)
            painter.setBrush(QBrush(color))
            clip = QPainterPath()
            clip.addRoundedRect(QRectF(x, y, w, h), cr, cr)
            painter.save()
            painter.setClipPath(clip)
            painter.drawRect(QRectF(x, y, fill_w, h))
            painter.restore()

    def _draw_text(self, painter, cx, cy, label, steno_label, icon, active, size):
        text_color = LABEL_ACTIVE_COLOR if active else LABEL_COLOR

        display = steno_label or icon or label
        if not display:
            return

        painter.setPen(QPen(text_color))
        if steno_label:
            font_size = max(8, min(14, int(size * 0.35)))
        else:
            font_size = max(8, min(16, int(size * 0.4)))
        font = QFont("Sans", font_size)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(
            QRectF(cx - 40, cy - font_size, 80, font_size * 2),
            Qt.AlignmentFlag.AlignCenter,
            display,
        )

from copy import copy

from math import hypot, sqrt
from plover_controller.config import Alias, Mappings, Stick
from plover_controller.machine import (
    AxisEvent,
    ButtonEvent,
    ControllerButtonEvent,
    Event,
    HatEvent,
    HAT_VALUES,
    DEFAULT_MAPPING,
    get_controller_thread,
)
from plover_controller.qt_compat import (
    Signal,
    Qt,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFont,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTimer,
    QVBoxLayout,
    QWidget,
    QColor,
    QAbstractItemView,
    exec_dialog,
)
from plover_controller.util import get_keys_for_stroke, keys_to_stroke
from plover_controller import profiles


_suppress_steno_output = False


def set_suppress_steno(value):
    global _suppress_steno_output
    _suppress_steno_output = value


def is_steno_suppressed():
    return _suppress_steno_output


DETECT_HIGHLIGHT = QColor(255, 255, 180)


class HardwareTab(QWidget):
    changed = Signal()
    detection_event = Signal(object)

    def __init__(self):
        super().__init__()
        self._detecting_table = None
        self._detecting_row = None
        self._detecting_btn = None
        self._stick_detect_step = 0
        self._stick_dead_zone = 0.6
        self._axis_states: dict[int, float] = {}
        self._mappings: Mappings | None = None

        layout = QVBoxLayout(self)

        self._sub_tabs = QTabWidget()
        layout.addWidget(self._sub_tabs)

        sticks_page = QWidget()
        sticks_layout = QVBoxLayout(sticks_page)
        self._sticks_table = QTableWidget(0, 6)
        self._sticks_table.setHorizontalHeaderLabels(
            ["Name", "X Axis", "Y Axis", "Offset", "Segments", ""]
        )
        self._sticks_table.horizontalHeader().setStretchLastSection(True)
        self._sticks_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._sticks_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._sticks_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._sticks_table.cellChanged.connect(self._on_cell_changed)
        sticks_layout.addWidget(self._sticks_table)
        sticks_btns = QHBoxLayout()
        add_stick = QPushButton("Add Stick")
        add_stick.clicked.connect(self._add_stick_row)
        rm_stick = QPushButton("Remove Selected")
        rm_stick.clicked.connect(lambda: self._remove_selected(self._sticks_table))
        sticks_btns.addWidget(add_stick)
        sticks_btns.addWidget(rm_stick)
        sticks_btns.addStretch()
        sticks_layout.addLayout(sticks_btns)
        self._sub_tabs.addTab(sticks_page, "Sticks")

        buttons_page = QWidget()
        buttons_layout = QVBoxLayout(buttons_page)
        self._buttons_table = QTableWidget(0, 3)
        self._buttons_table.setHorizontalHeaderLabels(["Button #", "Name", ""])
        self._buttons_table.horizontalHeader().setStretchLastSection(True)
        self._buttons_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._buttons_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._buttons_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._buttons_table.cellChanged.connect(self._on_cell_changed)
        buttons_layout.addWidget(self._buttons_table)
        btn_btns = QHBoxLayout()
        add_btn = QPushButton("Add Button")
        add_btn.clicked.connect(self._add_button_row)
        rm_btn = QPushButton("Remove Selected")
        rm_btn.clicked.connect(lambda: self._remove_selected(self._buttons_table))
        btn_btns.addWidget(add_btn)
        btn_btns.addWidget(rm_btn)
        btn_btns.addStretch()
        buttons_layout.addLayout(btn_btns)
        self._sub_tabs.addTab(buttons_page, "Buttons")

        triggers_page = QWidget()
        triggers_layout = QVBoxLayout(triggers_page)
        self._triggers_table = QTableWidget(0, 3)
        self._triggers_table.setHorizontalHeaderLabels(["Axis #", "Name", ""])
        self._triggers_table.horizontalHeader().setStretchLastSection(True)
        self._triggers_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._triggers_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._triggers_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._triggers_table.cellChanged.connect(self._on_cell_changed)
        triggers_layout.addWidget(self._triggers_table)
        trg_btns = QHBoxLayout()
        add_trg = QPushButton("Add Trigger")
        add_trg.clicked.connect(self._add_trigger_row)
        rm_trg = QPushButton("Remove Selected")
        rm_trg.clicked.connect(lambda: self._remove_selected(self._triggers_table))
        trg_btns.addWidget(add_trg)
        trg_btns.addWidget(rm_trg)
        trg_btns.addStretch()
        triggers_layout.addLayout(trg_btns)
        self._sub_tabs.addTab(triggers_page, "Triggers")

        hats_page = QWidget()
        hats_layout = QVBoxLayout(hats_page)
        self._hats_table = QTableWidget(0, 3)
        self._hats_table.setHorizontalHeaderLabels(["Hat #", "Name", ""])
        self._hats_table.horizontalHeader().setStretchLastSection(True)
        self._hats_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._hats_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._hats_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._hats_table.cellChanged.connect(self._on_cell_changed)
        hats_layout.addWidget(self._hats_table)
        hat_btns = QHBoxLayout()
        add_hat = QPushButton("Add Hat")
        add_hat.clicked.connect(self._add_hat_row)
        rm_hat = QPushButton("Remove Selected")
        rm_hat.clicked.connect(lambda: self._remove_selected(self._hats_table))
        hat_btns.addWidget(add_hat)
        hat_btns.addWidget(rm_hat)
        hat_btns.addStretch()
        hats_layout.addLayout(hat_btns)
        self._sub_tabs.addTab(hats_page, "Hats / D-Pads")

        feedback_layout = QHBoxLayout()
        self._feedback_label = QLabel("")
        self._feedback_label.setFont(QFont("Monospace"))
        feedback_layout.addWidget(QLabel("Last event:"))
        feedback_layout.addWidget(self._feedback_label)
        feedback_layout.addStretch()
        layout.addLayout(feedback_layout)

        self.detection_event.connect(self._on_detection_event)
        get_controller_thread().add_listener(self._controller_event)
        self.destroyed.connect(self._cleanup)

    def _cleanup(self):
        self._cancel_detection()
        try:
            get_controller_thread().remove_listener(self._controller_event)
        except (KeyError, RuntimeError):
            pass

    def _controller_event(self, ev):
        try:
            self.detection_event.emit(ev)
        except RuntimeError:
            pass

    def _on_detection_event(self, ev):
        self._update_feedback(ev)
        if self._detecting_table is None:
            return

        if self._detecting_table is self._buttons_table:
            if isinstance(ev, ButtonEvent) and ev.state:
                self._set_cell(self._detecting_table, self._detecting_row, 0, str(ev.button))
                self._finish_detection()

        elif self._detecting_table is self._triggers_table:
            if isinstance(ev, AxisEvent) and abs(ev.value) > 0.5:
                self._set_cell(self._detecting_table, self._detecting_row, 0, str(ev.axis))
                self._finish_detection()

        elif self._detecting_table is self._hats_table:
            if isinstance(ev, HatEvent) and ev.value != 0:
                self._set_cell(self._detecting_table, self._detecting_row, 0, str(ev.hat))
                self._finish_detection()

        elif self._detecting_table is self._sticks_table:
            if isinstance(ev, AxisEvent) and abs(ev.value) > 0.5:
                if self._stick_detect_step == 0:
                    self._set_cell(self._sticks_table, self._detecting_row, 1, str(ev.axis))
                    self._stick_detect_step = 1
                    self._detecting_btn.setText("Cancel (move Y)")
                elif self._stick_detect_step == 1:
                    if str(ev.axis) != self._cell_text(self._sticks_table, self._detecting_row, 1):
                        self._set_cell(self._sticks_table, self._detecting_row, 2, str(ev.axis))
                        self._finish_detection()

    def set_stick_dead_zone(self, value):
        self._stick_dead_zone = value

    def _find_stick_for_axis(self, axis_num: int) -> tuple[str | None, float | None]:
        axis_key = f"a{axis_num}"
        if self._mappings is None:
            return None, None
        for stick in self._mappings.sticks.values():
            if axis_key == stick.x_axis:
                other = self._axis_states.get(int(stick.y_axis[1:]), 0.0)
                return stick.name, other
            if axis_key == stick.y_axis:
                other = self._axis_states.get(int(stick.x_axis[1:]), 0.0)
                return stick.name, other
        return None, None

    def _update_feedback(self, ev):
        if isinstance(ev, AxisEvent):
            self._axis_states[ev.axis] = ev.value
            if abs(ev.value) < 0.05:
                return
            stick_name, other_axis = self._find_stick_for_axis(ev.axis)
            if stick_name is not None:
                dist = hypot(ev.value, other_axis or 0.0)
                threshold = self._stick_dead_zone * sqrt(2)
                indicator = "active" if dist >= threshold else "deadzone"
                msg = f"Axis {ev.axis} ({stick_name}): {ev.value:.2f} [dist: {dist:.2f}, threshold: {threshold:.2f}, {indicator}]"
            else:
                msg = f"Axis {ev.axis}: {ev.value:.2f}"
        elif isinstance(ev, ControllerButtonEvent):
            msg = f"Controller: {ev.name} {'pressed' if ev.state else 'released'}"
        elif isinstance(ev, ButtonEvent):
            msg = f"Button {ev.button} {'pressed' if ev.state else 'released'}"
        elif isinstance(ev, HatEvent):
            val = HAT_VALUES.get(ev.value, str(ev.value))
            msg = f"Hat {ev.hat}: {val}"
        else:
            return
        try:
            self._feedback_label.setText(msg)
        except RuntimeError:
            pass

    def _make_detect_btn(self, table, row):
        btn = QPushButton("Detect")

        def on_click():
            if self._detecting_table is table and self._detecting_row == row:
                self._cancel_detection()
            else:
                self._start_detection(table, row, btn)

        btn.clicked.connect(on_click)
        return btn

    def _start_detection(self, table, row, btn):
        self._cancel_detection()
        self._detecting_table = table
        self._detecting_row = row
        self._detecting_btn = btn
        self._stick_detect_step = 0
        btn.setText("Cancel" if table is not self._sticks_table else "Cancel (move X)")
        set_suppress_steno(True)
        for col in range(table.columnCount() - 1):
            item = table.item(row, col)
            if item:
                item.setBackground(DETECT_HIGHLIGHT)

    def _finish_detection(self):
        self._clear_highlight()
        if self._detecting_btn:
            self._detecting_btn.setText("Detect")
        self._detecting_table = None
        self._detecting_row = None
        self._detecting_btn = None
        self._stick_detect_step = 0
        set_suppress_steno(False)
        self.changed.emit()

    def _cancel_detection(self):
        self._clear_highlight()
        if self._detecting_btn:
            self._detecting_btn.setText("Detect")
        self._detecting_table = None
        self._detecting_row = None
        self._detecting_btn = None
        self._stick_detect_step = 0
        set_suppress_steno(False)

    def _clear_highlight(self):
        if self._detecting_table and self._detecting_row is not None:
            for col in range(self._detecting_table.columnCount() - 1):
                item = self._detecting_table.item(self._detecting_row, col)
                if item:
                    item.setBackground(QColor(0, 0, 0, 0))

    def _set_cell(self, table, row, col, text):
        table.blockSignals(True)
        item = table.item(row, col)
        if item:
            item.setText(text)
        table.blockSignals(False)

    def _cell_text(self, table, row, col):
        item = table.item(row, col)
        return item.text() if item else ""

    def _on_cell_changed(self, row, col):
        self.changed.emit()

    def _remove_selected(self, table):
        rows = sorted(set(idx.row() for idx in table.selectedIndexes()), reverse=True)
        if not rows:
            cur = table.currentRow()
            if cur >= 0:
                rows = [cur]
        for row in rows:
            table.removeRow(row)
        self.changed.emit()

    def _add_stick_row(self):
        self._sticks_table.blockSignals(True)
        row = self._sticks_table.rowCount()
        self._sticks_table.insertRow(row)
        self._sticks_table.setItem(row, 0, QTableWidgetItem(""))
        self._sticks_table.setItem(row, 1, QTableWidgetItem(""))
        self._sticks_table.setItem(row, 2, QTableWidgetItem(""))
        self._sticks_table.setItem(row, 3, QTableWidgetItem("0"))
        self._sticks_table.setItem(row, 4, QTableWidgetItem("dr,d,dl,ul,u,ur"))
        self._sticks_table.setCellWidget(row, 5, self._make_detect_btn(self._sticks_table, row))
        self._sticks_table.blockSignals(False)

    def _add_button_row(self):
        self._buttons_table.blockSignals(True)
        row = self._buttons_table.rowCount()
        self._buttons_table.insertRow(row)
        self._buttons_table.setItem(row, 0, QTableWidgetItem(""))
        self._buttons_table.setItem(row, 1, QTableWidgetItem(""))
        self._buttons_table.setCellWidget(row, 2, self._make_detect_btn(self._buttons_table, row))
        self._buttons_table.blockSignals(False)

    def _add_trigger_row(self):
        self._triggers_table.blockSignals(True)
        row = self._triggers_table.rowCount()
        self._triggers_table.insertRow(row)
        self._triggers_table.setItem(row, 0, QTableWidgetItem(""))
        self._triggers_table.setItem(row, 1, QTableWidgetItem(""))
        self._triggers_table.setCellWidget(
            row, 2, self._make_detect_btn(self._triggers_table, row)
        )
        self._triggers_table.blockSignals(False)

    def _add_hat_row(self):
        self._hats_table.blockSignals(True)
        row = self._hats_table.rowCount()
        self._hats_table.insertRow(row)
        self._hats_table.setItem(row, 0, QTableWidgetItem(""))
        self._hats_table.setItem(row, 1, QTableWidgetItem(""))
        self._hats_table.setCellWidget(
            row, 2, self._make_detect_btn(self._hats_table, row)
        )
        self._hats_table.blockSignals(False)

    def populate(self, mappings):
        self._cancel_detection()
        self._mappings = mappings

        self._sticks_table.blockSignals(True)
        self._sticks_table.setRowCount(0)
        for stick in mappings.sticks.values():
            row = self._sticks_table.rowCount()
            self._sticks_table.insertRow(row)
            self._sticks_table.setItem(row, 0, QTableWidgetItem(stick.name))
            self._sticks_table.setItem(row, 1, QTableWidgetItem(stick.x_axis[1:]))
            self._sticks_table.setItem(row, 2, QTableWidgetItem(stick.y_axis[1:]))
            offset_str = str(int(stick.offset)) if stick.offset == int(stick.offset) else str(stick.offset)
            self._sticks_table.setItem(row, 3, QTableWidgetItem(offset_str))
            self._sticks_table.setItem(row, 4, QTableWidgetItem(",".join(stick.segments)))
            self._sticks_table.setCellWidget(
                row, 5, self._make_detect_btn(self._sticks_table, row)
            )
        self._sticks_table.blockSignals(False)

        self._buttons_table.blockSignals(True)
        self._buttons_table.setRowCount(0)
        for alias in mappings.buttons.values():
            row = self._buttons_table.rowCount()
            self._buttons_table.insertRow(row)
            self._buttons_table.setItem(row, 0, QTableWidgetItem(alias.actual[1:]))
            self._buttons_table.setItem(row, 1, QTableWidgetItem(alias.renamed))
            self._buttons_table.setCellWidget(
                row, 2, self._make_detect_btn(self._buttons_table, row)
            )
        self._buttons_table.blockSignals(False)

        self._triggers_table.blockSignals(True)
        self._triggers_table.setRowCount(0)
        for alias in mappings.triggers.values():
            row = self._triggers_table.rowCount()
            self._triggers_table.insertRow(row)
            self._triggers_table.setItem(row, 0, QTableWidgetItem(alias.actual[1:]))
            self._triggers_table.setItem(row, 1, QTableWidgetItem(alias.renamed))
            self._triggers_table.setCellWidget(
                row, 2, self._make_detect_btn(self._triggers_table, row)
            )
        self._triggers_table.blockSignals(False)

        self._hats_table.blockSignals(True)
        self._hats_table.setRowCount(0)
        for alias in mappings.hats.values():
            row = self._hats_table.rowCount()
            self._hats_table.insertRow(row)
            self._hats_table.setItem(row, 0, QTableWidgetItem(alias.actual[1:]))
            self._hats_table.setItem(row, 1, QTableWidgetItem(alias.renamed))
            self._hats_table.setCellWidget(
                row, 2, self._make_detect_btn(self._hats_table, row)
            )
        self._hats_table.blockSignals(False)

    def read_sticks(self):
        sticks = {}
        for row in range(self._sticks_table.rowCount()):
            name = self._cell_text(self._sticks_table, row, 0).strip()
            x = self._cell_text(self._sticks_table, row, 1).strip()
            y = self._cell_text(self._sticks_table, row, 2).strip()
            offset = self._cell_text(self._sticks_table, row, 3).strip()
            segments = self._cell_text(self._sticks_table, row, 4).strip()
            if not name:
                continue
            try:
                offset_f = float(offset) if offset else 0.0
            except ValueError:
                offset_f = 0.0
            seg_list = [s.strip() for s in segments.split(",") if s.strip()] if segments else []
            stick = Stick(
                name=name,
                x_axis=f"a{x}" if x else "a0",
                y_axis=f"a{y}" if y else "a1",
                offset=offset_f,
                segments=seg_list if seg_list else ["dr", "d", "dl", "ul", "u", "ur"],
            )
            sticks[stick.name] = stick
        return sticks

    def read_buttons(self):
        buttons = {}
        for row in range(self._buttons_table.rowCount()):
            num = self._cell_text(self._buttons_table, row, 0).strip()
            name = self._cell_text(self._buttons_table, row, 1).strip()
            if not num or not name:
                continue
            actual = f"b{num}"
            buttons[actual] = Alias(renamed=name, actual=actual)
        return buttons

    def read_triggers(self):
        triggers = {}
        for row in range(self._triggers_table.rowCount()):
            num = self._cell_text(self._triggers_table, row, 0).strip()
            name = self._cell_text(self._triggers_table, row, 1).strip()
            if not num or not name:
                continue
            actual = f"a{num}"
            triggers[actual] = Alias(renamed=name, actual=actual)
        return triggers

    def read_hats(self):
        hats = {}
        for row in range(self._hats_table.rowCount()):
            num = self._cell_text(self._hats_table, row, 0).strip()
            name = self._cell_text(self._hats_table, row, 1).strip()
            if not num or not name:
                continue
            actual = f"h{num}"
            hats[actual] = Alias(renamed=name, actual=actual)
        return hats


class StenoTab(QWidget):
    changed = Signal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Input", "Steno Output", ""])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._table.cellChanged.connect(self._on_cell_changed)
        layout.addWidget(self._table)

        btns = QHBoxLayout()
        add_btn = QPushButton("Add Mapping")
        add_btn.clicked.connect(self._add_row)
        rm_btn = QPushButton("Remove Selected")
        rm_btn.clicked.connect(self._remove_selected)
        btns.addWidget(add_btn)
        btns.addWidget(rm_btn)
        btns.addStretch()
        layout.addLayout(btns)

    def _on_cell_changed(self, row, col):
        if col == 1:
            item = self._table.item(row, col)
            if item:
                text = item.text().strip()
                if text:
                    try:
                        get_keys_for_stroke(text)
                        item.setBackground(QColor(0, 0, 0, 0))
                    except Exception:
                        item.setBackground(QColor(255, 200, 200))
                else:
                    item.setBackground(QColor(0, 0, 0, 0))
        self.changed.emit()

    def _add_row(self):
        self._table.blockSignals(True)
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem(""))
        self._table.setItem(row, 1, QTableWidgetItem(""))
        rm = QPushButton("Remove")
        rm.clicked.connect(lambda checked=False, r=row: self._remove_row(r))
        self._table.setCellWidget(row, 2, rm)
        self._table.blockSignals(False)

    def _remove_row(self, row):
        if row < self._table.rowCount():
            self._table.removeRow(row)
            self._rebuild_remove_buttons()
            self.changed.emit()

    def _remove_selected(self):
        rows = sorted(set(idx.row() for idx in self._table.selectedIndexes()), reverse=True)
        if not rows:
            cur = self._table.currentRow()
            if cur >= 0:
                rows = [cur]
        for row in rows:
            self._table.removeRow(row)
        self._rebuild_remove_buttons()
        self.changed.emit()

    def _rebuild_remove_buttons(self):
        for row in range(self._table.rowCount()):
            rm = QPushButton("Remove")
            rm.clicked.connect(lambda checked=False, r=row: self._remove_row(r))
            self._table.setCellWidget(row, 2, rm)

    def populate(self, mappings):
        self._table.blockSignals(True)
        self._table.setRowCount(0)
        for lhs, rhs in mappings.unordered_mappings:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(",".join(lhs)))
            self._table.setItem(row, 1, QTableWidgetItem(keys_to_stroke(rhs)))
            rm = QPushButton("Remove")
            rm.clicked.connect(lambda checked=False, r=row: self._remove_row(r))
            self._table.setCellWidget(row, 2, rm)
        self._table.blockSignals(False)

    def read_mappings(self):
        result = []
        for row in range(self._table.rowCount()):
            inp_item = self._table.item(row, 0)
            out_item = self._table.item(row, 1)
            if not inp_item:
                continue
            inp = inp_item.text().strip()
            if not inp:
                continue
            out = out_item.text().strip() if out_item else ""
            lhs = [s.strip() for s in inp.split(",") if s.strip()]
            rhs = get_keys_for_stroke(out) if out else ()
            result.append((lhs, rhs))
        return result


class SettingsTab(QWidget):
    changed = Signal()

    SPIN_BOXES = {
        "timeout": ("Timeout:", "How long to wait (seconds) before finalizing a stroke"),
        "stick_dead_zone": ("Stick dead zone:", "How far the stick must move to register a direction (0–1)"),
        "trigger_dead_zone": ("Trigger dead zone:", "How far a trigger must be pressed to register (0–1)"),
        "stroke_end_threshold": ("Stroke end threshold:", "How close to center the stick must return to end a stroke (0–1)"),
    }

    DRIVER_BOXES = {
        "use_hidapi": "Use HIDAPI driver (better button names, but may change numbering)",
        "use_rawinput": "Use raw input driver (Windows only)",
        "correlate_rawinput": "Correlate raw input with XInput (Windows only)",
        "use_joystick_thread": "Use background joystick thread",
    }

    def __init__(self):
        super().__init__()
        self._spin_boxes = {}
        self._check_boxes = {}
        self._updating = False

        layout = QVBoxLayout(self)

        tuning_group = QGroupBox("Sensitivity")
        tuning_form = QFormLayout(tuning_group)
        for prop, (label, tooltip) in self.SPIN_BOXES.items():
            spin = QDoubleSpinBox()
            spin.setSingleStep(0.1)
            spin.setToolTip(tooltip)
            spin.valueChanged.connect(self._on_changed)
            lbl = QLabel(label)
            lbl.setToolTip(tooltip)
            tuning_form.addRow(lbl, spin)
            self._spin_boxes[prop] = spin
        layout.addWidget(tuning_group)

        feedback_group = QGroupBox("Feedback")
        feedback_layout = QVBoxLayout(feedback_group)
        self._rumble_cb = QCheckBox("Rumble on stroke")
        self._rumble_cb.setToolTip("Briefly vibrate the controller when a stroke is sent")
        self._rumble_cb.setChecked(True)
        self._rumble_cb.toggled.connect(self._on_rumble_toggled)
        feedback_layout.addWidget(self._rumble_cb)

        self._rumble_form = QFormLayout()

        self._rumble_duration = QDoubleSpinBox()
        self._rumble_duration.setRange(10, 500)
        self._rumble_duration.setDecimals(0)
        self._rumble_duration.setSuffix(" ms")
        self._rumble_duration.setSingleStep(10)
        self._rumble_duration.setValue(80)
        self._rumble_duration.setToolTip("How long the vibration lasts")
        self._rumble_duration.valueChanged.connect(self._on_changed)
        self._rumble_form.addRow(QLabel("Duration:"), self._rumble_duration)

        self._rumble_low = QDoubleSpinBox()
        self._rumble_low.setRange(0.0, 1.0)
        self._rumble_low.setDecimals(2)
        self._rumble_low.setSingleStep(0.05)
        self._rumble_low.setValue(0.5)
        self._rumble_low.setToolTip("Intensity of the heavy/rumbly motor (0–1)")
        self._rumble_low.valueChanged.connect(self._on_changed)
        self._rumble_form.addRow(QLabel("Low motor:"), self._rumble_low)

        self._rumble_high = QDoubleSpinBox()
        self._rumble_high.setRange(0.0, 1.0)
        self._rumble_high.setDecimals(2)
        self._rumble_high.setSingleStep(0.05)
        self._rumble_high.setValue(0.25)
        self._rumble_high.setToolTip("Intensity of the light/buzzy motor (0–1)")
        self._rumble_high.valueChanged.connect(self._on_changed)
        self._rumble_form.addRow(QLabel("High motor:"), self._rumble_high)

        feedback_layout.addLayout(self._rumble_form)
        layout.addWidget(feedback_group)

        display_group = QGroupBox("Controller Display")
        display_form = QFormLayout(display_group)

        self._chroma_btn = QPushButton()
        self._chroma_btn.setFixedSize(60, 24)
        self._chroma_btn.clicked.connect(self._pick_chroma_color)
        self._chroma_color = "#00b140"
        self._update_chroma_preview()
        display_form.addRow(QLabel("Chroma key color:"), self._chroma_btn)

        self._layout_combo = QComboBox()
        self._layout_combo.addItem("Horizontal (side by side)", "horizontal")
        self._layout_combo.addItem("Vertical (top and bottom)", "vertical")
        self._layout_combo.currentIndexChanged.connect(self._on_changed)
        display_form.addRow(QLabel("Layout:"), self._layout_combo)

        self._show_back_cb = QCheckBox("Show back view (paddles & triggers)")
        self._show_back_cb.setChecked(True)
        self._show_back_cb.toggled.connect(self._on_changed)
        display_form.addRow(self._show_back_cb)

        layout.addWidget(display_group)

        driver_group = QGroupBox("Advanced: Driver Settings")
        driver_group.setCheckable(True)
        driver_group.setChecked(False)
        driver_layout = QVBoxLayout(driver_group)
        warn = QLabel(
            "Changing these may alter how your controller is detected.\n"
            "Button and axis numbers can change, which will break\n"
            "your current hardware mappings. Restart Plover after changing."
        )
        warn.setStyleSheet("color: #b45309; font-style: italic;")
        warn.setWordWrap(True)
        driver_layout.addWidget(warn)
        driver_form = QFormLayout()
        for prop, label in self.DRIVER_BOXES.items():
            cb = QCheckBox(label)
            cb.toggled.connect(self._on_changed)
            driver_form.addRow(cb)
            self._check_boxes[prop] = cb
        driver_layout.addLayout(driver_form)
        layout.addWidget(driver_group)

        layout.addStretch()

    def _on_changed(self, _=None):
        if not self._updating:
            self.changed.emit()

    def _on_rumble_toggled(self, checked):
        self._rumble_duration.setEnabled(checked)
        self._rumble_low.setEnabled(checked)
        self._rumble_high.setEnabled(checked)
        self._on_changed()

    def _pick_chroma_color(self):
        color = QColorDialog.getColor(QColor(self._chroma_color), self, "Chroma Key Color")
        if color.isValid():
            self._chroma_color = color.name()
            self._update_chroma_preview()
            self._on_changed()

    def _update_chroma_preview(self):
        self._chroma_btn.setStyleSheet(
            f"background-color: {self._chroma_color}; border: 1px solid #888;"
        )

    def populate(self, value):
        self._updating = True
        for prop, spin in self._spin_boxes.items():
            if prop in value:
                spin.setValue(value[prop])
        for prop, cb in self._check_boxes.items():
            if prop in value:
                cb.setChecked(bool(value[prop]))
        if "rumble_on_stroke" in value:
            self._rumble_cb.setChecked(bool(value["rumble_on_stroke"]))
        if "rumble_duration" in value:
            self._rumble_duration.setValue(value["rumble_duration"])
        if "rumble_low_freq" in value:
            self._rumble_low.setValue(value["rumble_low_freq"])
        if "rumble_high_freq" in value:
            self._rumble_high.setValue(value["rumble_high_freq"])
        self._on_rumble_toggled(self._rumble_cb.isChecked())
        if "display_chroma_color" in value:
            self._chroma_color = value["display_chroma_color"]
            self._update_chroma_preview()
        if "display_layout" in value:
            idx = self._layout_combo.findData(value["display_layout"])
            if idx >= 0:
                self._layout_combo.setCurrentIndex(idx)
        if "display_show_back" in value:
            self._show_back_cb.setChecked(bool(value["display_show_back"]))
        self._updating = False

    def read_settings(self):
        result = {}
        for prop, spin in self._spin_boxes.items():
            result[prop] = spin.value()
        for prop, cb in self._check_boxes.items():
            result[prop] = cb.isChecked()
        result["rumble_on_stroke"] = self._rumble_cb.isChecked()
        result["rumble_duration"] = int(self._rumble_duration.value())
        result["rumble_low_freq"] = self._rumble_low.value()
        result["rumble_high_freq"] = self._rumble_high.value()
        result["display_chroma_color"] = self._chroma_color
        result["display_layout"] = self._layout_combo.currentData()
        result["display_show_back"] = self._show_back_cb.isChecked()
        return result


class ProfilesTab(QWidget):
    profile_loaded = Signal(str)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        self._list = QListWidget()
        layout.addWidget(self._list)

        btns = QHBoxLayout()
        load_btn = QPushButton("Load")
        load_btn.clicked.connect(self._load)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        save_as_btn = QPushButton("Save As...")
        save_as_btn.clicked.connect(self._save_as)
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self._delete)
        import_btn = QPushButton("Import...")
        import_btn.clicked.connect(self._import)
        export_btn = QPushButton("Export...")
        export_btn.clicked.connect(self._export)
        btns.addWidget(load_btn)
        btns.addWidget(save_btn)
        btns.addWidget(save_as_btn)
        btns.addWidget(delete_btn)
        btns.addStretch()
        btns.addWidget(import_btn)
        btns.addWidget(export_btn)
        layout.addLayout(btns)

        self._current_name = None
        self._get_mapping_text = None
        self.refresh_list()

    def current_name(self):
        return self._current_name

    def set_current(self, name):
        self._current_name = name or None
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.text() == name:
                self._list.setCurrentItem(item)
                return
        self._list.clearSelection()

    def set_mapping_getter(self, fn):
        self._get_mapping_text = fn

    def refresh_list(self):
        self._list.clear()
        for name in profiles.list_profile_names():
            item = QListWidgetItem(name)
            if profiles.is_builtin(name):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._list.addItem(item)

    def _selected_name(self):
        item = self._list.currentItem()
        return item.text() if item else None

    def _load(self):
        name = self._selected_name()
        if not name:
            return
        text = profiles.load_profile(name)
        if text is not None:
            self._current_name = name
            self.profile_loaded.emit(text)

    def _save(self):
        if not self._current_name or profiles.is_builtin(self._current_name):
            self._save_as()
            return
        if self._get_mapping_text:
            text = self._get_mapping_text()
            profiles.save_profile(self._current_name, text)
            self.refresh_list()

    def _save_as(self):
        name, ok = QInputDialog.getText(self, "Save Profile", "Profile name:")
        if not ok or not name or not name.strip():
            return
        name = name.strip()
        if profiles.is_builtin(name):
            QMessageBox.warning(self, "Error", "Cannot overwrite a built-in profile.")
            return
        if self._get_mapping_text:
            text = self._get_mapping_text()
            profiles.save_profile(name, text)
            self._current_name = name
            self.refresh_list()

    def _delete(self):
        name = self._selected_name()
        if not name:
            return
        if profiles.is_builtin(name):
            QMessageBox.warning(self, "Error", "Cannot delete a built-in profile.")
            return
        reply = QMessageBox.question(
            self,
            "Delete Profile",
            f"Delete profile '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            profiles.delete_profile(name)
            if self._current_name == name:
                self._current_name = None
            self.refresh_list()

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Profile", "", "Text Files (*.txt);;All Files (*)"
        )
        if not path:
            return
        from pathlib import Path

        name, text = profiles.import_profile(Path(path))
        profiles.save_profile(name, text)
        self.refresh_list()

    def _export(self):
        name = self._selected_name()
        if not name:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Profile", f"{name}.txt", "Text Files (*.txt);;All Files (*)"
        )
        if not path:
            return
        from pathlib import Path

        profiles.export_profile(name, Path(path))


class RawEditorDialog(QDialog):
    def __init__(self, parent, text):
        super().__init__(parent)
        self.setWindowTitle("Raw Mapping Editor")
        self.resize(700, 500)
        layout = QVBoxLayout(self)
        self._editor = QTextEdit()
        self._editor.setFont(QFont("Monospace"))
        self._editor.setPlainText(text)
        layout.addWidget(self._editor)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_text(self):
        return self._editor.toPlainText()


class ControllerOption(QGroupBox):
    valueChanged = Signal(object)

    def __init__(self):
        super().__init__()
        self._value = {}
        self._mappings = Mappings.empty()
        self._updating = False

        layout = QVBoxLayout(self)

        self._tabs = QTabWidget()
        self._hardware_tab = HardwareTab()
        self._steno_tab = StenoTab()
        self._settings_tab = SettingsTab()
        self._profiles_tab = ProfilesTab()

        self._tabs.addTab(self._hardware_tab, "Hardware")
        self._tabs.addTab(self._steno_tab, "Steno Mapping")
        self._tabs.addTab(self._settings_tab, "Settings")
        self._tabs.addTab(self._profiles_tab, "Profiles")
        layout.addWidget(self._tabs)

        bottom = QHBoxLayout()
        raw_btn = QPushButton("Raw Editor...")
        raw_btn.clicked.connect(self._open_raw_editor)
        reset_btn = QPushButton("Reset to Default")
        reset_btn.clicked.connect(self._reset_to_default)
        bottom.addWidget(raw_btn)
        bottom.addWidget(reset_btn)
        bottom.addStretch()
        layout.addLayout(bottom)

        self._hardware_tab.changed.connect(self._on_tab_changed)
        self._steno_tab.changed.connect(self._on_tab_changed)
        self._settings_tab.changed.connect(self._on_tab_changed)
        self._profiles_tab.profile_loaded.connect(self._on_profile_loaded)
        self._profiles_tab.set_mapping_getter(self._get_mapping_text)

    def _on_tab_changed(self):
        if self._updating:
            return
        self._rebuild_and_emit()

    def _rebuild_and_emit(self):
        self._mappings.sticks = self._hardware_tab.read_sticks()
        self._mappings.buttons = self._hardware_tab.read_buttons()
        self._mappings.triggers = self._hardware_tab.read_triggers()
        self._mappings.hats = self._hardware_tab.read_hats()
        self._mappings.unordered_mappings = self._steno_tab.read_mappings()

        self._value["mapping"] = self._mappings.serialize()
        self._value.update(self._settings_tab.read_settings())
        self._hardware_tab.set_stick_dead_zone(self._value.get("stick_dead_zone", 0.6))
        self.valueChanged.emit(copy(self._value))

    def _on_profile_loaded(self, text):
        self._updating = True
        self._value["profile"] = self._profiles_tab.current_name() or ""
        self._mappings = Mappings.parse(text)
        self._value["mapping"] = text
        self._hardware_tab.populate(self._mappings)
        self._steno_tab.populate(self._mappings)
        self._updating = False
        self._rebuild_and_emit()

    def _get_mapping_text(self):
        return self._mappings.serialize()

    def _open_raw_editor(self):
        dlg = RawEditorDialog(self, self._mappings.serialize())
        if exec_dialog(dlg) == QDialog.DialogCode.Accepted:
            text = dlg.get_text()
            self._updating = True
            self._mappings = Mappings.parse(text)
            self._value["mapping"] = text
            self._hardware_tab.populate(self._mappings)
            self._steno_tab.populate(self._mappings)
            self._updating = False
            self._rebuild_and_emit()

    def _reset_to_default(self):
        self._updating = True
        self._value["profile"] = ""
        self._mappings = Mappings.parse(DEFAULT_MAPPING)
        self._value["mapping"] = DEFAULT_MAPPING
        self._hardware_tab.populate(self._mappings)
        self._steno_tab.populate(self._mappings)
        self._profiles_tab.set_current("")
        self._updating = False
        self._rebuild_and_emit()

    def setValue(self, value):
        self._updating = True
        self._value = copy(value)
        mapping = value.get("mapping", DEFAULT_MAPPING)
        self._mappings = Mappings.parse(mapping)
        self._hardware_tab.populate(self._mappings)
        self._hardware_tab.set_stick_dead_zone(value.get("stick_dead_zone", 0.6))
        self._steno_tab.populate(self._mappings)
        self._settings_tab.populate(value)
        self._profiles_tab.set_current(value.get("profile", ""))
        self._updating = False

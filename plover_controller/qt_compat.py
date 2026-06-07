try:
    from PySide6.QtCore import Signal, Qt, QSize, QLineF, QPointF, QRectF, QTimer
    from PySide6.QtGui import QFont, QPainter, QPen, QBrush, QColor
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QCheckBox,
        QColorDialog,
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QDoubleSpinBox,
        QFileDialog,
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
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    from PyQt5.QtCore import (
        pyqtSignal as Signal,
        Qt,
        QSize,
        QLineF,
        QPointF,
        QRectF,
        QTimer,
    )
    from PyQt5.QtGui import QFont, QPainter, QPen, QBrush, QColor
    from PyQt5.QtWidgets import (
        QAbstractItemView,
        QCheckBox,
        QColorDialog,
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QDoubleSpinBox,
        QFileDialog,
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
        QVBoxLayout,
        QWidget,
    )


def exec_dialog(dialog):
    if hasattr(dialog, "exec"):
        return dialog.exec()
    return dialog.exec_()

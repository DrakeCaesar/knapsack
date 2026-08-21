"""Dark Qt theme for the Endless Sky data tools."""

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

# Dark theme colors shared by all tabs.
BG = "#1e1e1e"
FG = "#e0e0e0"
ENTRY_BG = "#2d2d2d"
SELECT_BG = "#264f78"

# Header row background (drawn by the delegate) and column-header styling.
HEADER_BG = "#2d2d2d"
BORDER = "#111111"

_STYLESHEET = """
QWidget { color: #e0e0e0; }
QMainWindow, QDialog { background-color: #1e1e1e; }
QTabWidget::pane { border: 1px solid #333333; }
QTabBar::tab {
    background: #2d2d2d;
    padding: 6px 14px;
    border: 1px solid #333333;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected { background: #1e1e1e; color: #ffffff; }
QTabBar::tab:hover { background: #3a3a3a; }
QTableView {
    background: #2d2d2d;
    border: 1px solid #111111;
    selection-background-color: #264f78;
    gridline-color: #111111;
}
QHeaderView::section {
    background: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #111111;
    padding: 4px;
    font-weight: normal;
}
QScrollBar:vertical { background: #2d2d2d; width: 12px; margin: 0; }
QScrollBar::handle:vertical { background: #3a3a3a; min-height: 24px; }
QScrollBar::handle:vertical:hover { background: #4a4a4a; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: #2d2d2d; height: 12px; margin: 0; }
QScrollBar::handle:horizontal { background: #3a3a3a; min-width: 24px; }
QScrollBar::handle:horizontal:hover { background: #4a4a4a; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QSplitter::handle { background: #333333; }
QCheckBox { spacing: 6px; }
QCheckBox::indicator { width: 14px; height: 14px; }
QLabel { background: transparent; }
QPushButton { background: #333333; border: 1px solid #444444; padding: 4px 12px; }
QPushButton:hover { background: #3c3c3c; }
QPushButton:pressed { background: #2a2a2a; }
QLineEdit, QSpinBox { background: #2d2d2d; border: 1px solid #444444; padding: 3px; }
QListWidget { background: #2d2d2d; border: 1px solid #111111; }
QMenu { background: #2d2d2d; color: #e0e0e0; border: 1px solid #444444; }
QMenu::item:selected { background: #264f78; }
"""


def apply_theme(app: QApplication):
    """Apply the shared dark theme to the whole application."""
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(BG))
    palette.setColor(QPalette.ColorRole.Base, QColor(ENTRY_BG))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#2a2a2a"))
    palette.setColor(QPalette.ColorRole.Text, QColor(FG))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(FG))
    palette.setColor(QPalette.ColorRole.Button, QColor("#333333"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(FG))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(SELECT_BG))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(ENTRY_BG))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(FG))
    app.setPalette(palette)

    app.setStyleSheet(_STYLESHEET)

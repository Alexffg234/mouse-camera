import sys
import os

os.environ["PYTHONIOENCODING"] = "utf-8"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from desktop_app.config_manager import ConfigManager
from desktop_app.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("手势鼠标控制")
    app.setStyle("Fusion")

    app.setStyleSheet("""
        QMainWindow { background: #2a2a2a; }
        QTabWidget::pane { background: #2a2a2a; border: 1px solid #444; border-radius: 6px; }
        QTabBar::tab { background: #333; color: #aaa; padding: 8px 16px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
        QTabBar::tab:selected { background: #3b82f6; color: #fff; }
        QTabBar::tab:hover { background: #444; }
        QComboBox { background: #333; color: #eee; border: 1px solid #555; border-radius: 4px; padding: 4px; }
        QComboBox::drop-down { border: none; }
        QComboBox QAbstractItemView { background: #333; color: #eee; selection-background-color: #3b82f6; }
        QSpinBox { background: #333; color: #eee; border: 1px solid #555; border-radius: 4px; padding: 4px; }
        QSlider::groove:horizontal { background: #444; height: 4px; border-radius: 2px; }
        QSlider::handle:horizontal { background: #3b82f6; width: 14px; margin: -5px 0; border-radius: 7px; }
        QCheckBox { color: #eee; spacing: 8px; }
        QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 1px solid #555; background: #333; }
        QCheckBox::indicator:checked { background: #3b82f6; border: 1px solid #3b82f6; }
        QScrollArea { border: none; }
        QFrame#binding_row { background: #333; border: 1px solid #444; border-radius: 6px; margin: 4px; padding: 8px; }
        QLabel { background: transparent; }
    """)

    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    config_manager = ConfigManager(config_path)

    window = MainWindow(config_manager)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

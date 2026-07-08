import os
import sys

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QSplitter, QTabWidget, QPushButton, QLabel,
                              QMessageBox, QFileDialog, QApplication)
from PyQt6.QtCore import Qt, QTimer

from desktop_app.camera_worker import CameraWorker
from desktop_app.config_manager import ConfigManager
from desktop_app.widgets.camera_view import CameraView
from desktop_app.widgets.status_bar import StatusBarWidget
from desktop_app.widgets.gesture_bindings_tab import GestureBindingsTab
from desktop_app.widgets.sensitivity_tab import SensitivityTab
from desktop_app.widgets.recognition_tab import RecognitionTab
from desktop_app.widgets.calibration_tab import CalibrationTab
from desktop_app.widgets.tracking_tab import TrackingTab
from desktop_app.widgets.import_export_tab import ImportExportTab
from desktop_app.wizard import OnboardingWizard, TUTORIAL_STEPS


class MainWindow(QMainWindow):
    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self._config_manager = config_manager
        self._worker = None
        self._save_timer = None

        self.setWindowTitle("手势鼠标控制")
        self.setMinimumSize(1100, 750)
        self.resize(1280, 800)

        # Central widget with splitter
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Splitter: camera on top, settings below
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Camera section
        camera_section = QWidget()
        camera_layout = QVBoxLayout(camera_section)
        camera_layout.setContentsMargins(0, 0, 0, 0)

        self.camera_view = CameraView()
        camera_layout.addWidget(self.camera_view)

        self.status_bar = StatusBarWidget()
        camera_layout.addWidget(self.status_bar)

        splitter.addWidget(camera_section)

        # Settings section
        self.tabs = QTabWidget()
        config = config_manager.get_config()

        self.gesture_tab = GestureBindingsTab(config)
        self.sens_tab = SensitivityTab(config)
        self.recog_tab = RecognitionTab(config)
        self.calib_tab = CalibrationTab(config)
        self.tracking_tab = TrackingTab(config)
        self.import_tab = ImportExportTab(config_manager)

        self.tabs.addTab(self.gesture_tab, "手势绑定")
        self.tabs.addTab(self.sens_tab, "灵敏度")
        self.tabs.addTab(self.recog_tab, "识别")
        self.tabs.addTab(self.calib_tab, "校准")
        self.tabs.addTab(self.tracking_tab, "追踪")
        self.tabs.addTab(self.import_tab, "导入/导出")

        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([400, 400])

        main_layout.addWidget(splitter)

        # Action bar
        action_bar = QHBoxLayout()

        self.save_btn = QPushButton("保存配置")
        self.save_btn.setStyleSheet("padding: 6px 20px; background: #3b82f6; color: #fff; border-radius: 6px; font-weight: bold;")
        self.save_btn.clicked.connect(self._save_config)
        action_bar.addWidget(self.save_btn)

        self.reset_btn = QPushButton("恢复默认")
        self.reset_btn.setStyleSheet("padding: 6px 20px; background: #555; color: #eee; border-radius: 6px;")
        self.reset_btn.clicked.connect(self._reset_config)
        action_bar.addWidget(self.reset_btn)

        action_bar.addStretch()

        self.camera_btn = QPushButton("启动摄像头")
        self.camera_btn.setStyleSheet("padding: 6px 20px; background: #22c55e; color: #fff; border-radius: 6px; font-weight: bold;")
        self.camera_btn.clicked.connect(self._toggle_camera)
        action_bar.addWidget(self.camera_btn)

        main_layout.addLayout(action_bar)

        # Start camera thread
        self._start_camera()

        # Show wizard if first run
        if not ConfigManager.tutorial_done():
            self._show_wizard()

    def _start_camera(self):
        config = self._config_manager.get_config()
        self._worker = CameraWorker(config)
        self._worker.frame_ready.connect(self.camera_view.update_frame)
        self._worker.gesture_update.connect(self._on_gesture_update)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.start()
        self.camera_btn.setText("停止摄像头")
        self.camera_btn.setStyleSheet("padding: 6px 20px; background: #ef4444; color: #fff; border-radius: 6px; font-weight: bold;")

    def _on_gesture_update(self, gesture, action, confidence, hold_progress, user_status, fps):
        self.status_bar.update(gesture, action, confidence, hold_progress, user_status, fps)
        if hasattr(self, "_wizard") and self._wizard.isVisible():
            self._wizard.on_gesture(gesture, confidence)

    def _on_error(self, msg):
        QMessageBox.warning(self, "错误", msg)

    def _save_config(self):
        merged = self._merge_config()
        if self._config_manager.set_config(merged):
            self._config_manager.save()
            if self._worker:
                self._worker.update_config(self._config_manager.get_config())
            # Flash the save button
            self.save_btn.setText("✓ 已保存")
            QTimer.singleShot(1500, lambda: self.save_btn.setText("保存配置"))
        else:
            QMessageBox.warning(self, "保存失败", "配置验证失败，请检查设置")

    def _merge_config(self) -> dict:
        """Merge all tab configs into one."""
        base = self._config_manager.get_config()
        # Collect from gesture bindings tab
        gm = self.gesture_tab.collect_config()
        base["gesture_mouse_map"] = gm
        # Sensitivity
        s = self.sens_tab.collect()
        base["sensitivity"] = s["sensitivity"]
        # Recognition
        r = self.recog_tab.collect()
        base["recognizer"] = r["recognizer"]
        # Calibration
        c = self.calib_tab.collect()
        base["calibration"] = c["calibration"]
        # Tracking
        t = self.tracking_tab.collect()
        base["tracking"] = t["tracking"]
        base["multi_angle"] = t["multi_angle"]
        return base

    def _reset_config(self):
        if QMessageBox.question(self, "确认", "确定恢复默认配置？") != QMessageBox.StandardButton.Yes:
            return
        self.gesture_tab.load_config(self._config_manager.get_config())
        self.sens_tab.load_config(self._config_manager.get_config())
        self.recog_tab.load_config(self._config_manager.get_config())
        self.calib_tab.load_config(self._config_manager.get_config())
        self.tracking_tab.load_config(self._config_manager.get_config())

    def _toggle_camera(self):
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(2000)
            self.camera_view.show_message("摄像头已停止")
        else:
            self._start_camera()

    def _show_wizard(self):
        self._wizard = OnboardingWizard(self.camera_view, self)
        self._wizard.finished.connect(lambda: self._wizard.hide())
        self._wizard.move(self.camera_view.mapToGlobal(self.camera_view.rect().center()))
        self._wizard.resize(self.camera_view.size())
        self._wizard.show()
        QTimer.singleShot(100, self._resize_wizard_to_camera)

    def _resize_wizard_to_camera(self):
        if hasattr(self, "_wizard") and self._wizard.isVisible():
            self._wizard.resize(self.camera_view.size())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(200, self._resize_wizard_to_camera)

    def closeEvent(self, event):
        if self._worker:
            self._worker.stop()
            self._worker.wait(2000)
        event.accept()

import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QTextEdit, QMessageBox, QFileDialog)


class ImportExportTab(QWidget):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self._config_manager = config_manager
        layout = QVBoxLayout(self)

        btn_layout = QHBoxLayout()
        export_btn = QPushButton("导出 JSON")
        export_btn.clicked.connect(self._export)
        import_btn = QPushButton("导入 JSON")
        import_btn.clicked.connect(self._import)
        btn_layout.addWidget(export_btn)
        btn_layout.addWidget(import_btn)
        layout.addLayout(btn_layout)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet("background: #1a1a1a; color: #aaa; font-family: monospace; font-size: 11px;")
        self._refresh()
        layout.addWidget(self.text_edit)

    def _refresh(self):
        self.text_edit.setPlainText(self._config_manager.export_json())

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出配置", "gesture_mouse_config.json", "JSON (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._config_manager.export_json())

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入配置", "", "JSON (*.json)")
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()
                if self._config_manager.import_json(text):
                    self._refresh()
                    QMessageBox.information(self, "成功", "配置已导入，请保存生效")
            except Exception as e:
                QMessageBox.warning(self, "错误", str(e))

    def load_config(self, config):
        self._refresh()

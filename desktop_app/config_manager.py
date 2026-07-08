import copy
import json
import os

from PyQt6.QtCore import QObject, pyqtSignal, QSettings

from gesture_mapper import GestureMapper


class ConfigManager(QObject):
    config_saved = pyqtSignal()
    config_changed = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, path="config.json", parent=None):
        super().__init__(parent)
        self._path = path
        self._config = self._load()

    def get_path(self) -> str:
        return self._path

    def get_config(self) -> dict:
        return copy.deepcopy(self._config)

    def set_config(self, config: dict) -> bool:
        """In-memory update with validation."""
        try:
            tmp_mapper = GestureMapper(self._path)
            tmp_mapper.set_config(config)
            self._config = copy.deepcopy(config)
            self.config_changed.emit(config)
            return True
        except Exception as e:
            self.error.emit(str(e))
            return False

    def update_section(self, section: str, values: dict):
        """Update a top-level section of config (e.g. 'sensitivity')."""
        self._config.setdefault(section, {}).update(values)
        self.config_changed.emit(self._config)

    def save(self):
        """Write to disk atomically."""
        try:
            GestureMapper(self._path).set_config(self._config)
            tmp = self._path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            os.replace(tmp, self._path)
            self.config_saved.emit()
        except Exception as e:
            self.error.emit(str(e))

    def _load(self) -> dict:
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def export_json(self) -> str:
        return json.dumps(self._config, indent=2, ensure_ascii=False)

    def import_json(self, text: str) -> bool:
        try:
            config = json.loads(text)
            return self.set_config(config)
        except (json.JSONDecodeError, Exception) as e:
            self.error.emit(str(e))
            return False

    @staticmethod
    def tutorial_done(app_name="GestureMouse") -> bool:
        s = QSettings(app_name, "GestureMouse")
        return s.value("tutorial_done", False, type=bool)

    @staticmethod
    def set_tutorial_done(app_name="GestureMouse"):
        s = QSettings(app_name, "GestureMouse")
        s.setValue("tutorial_done", True)

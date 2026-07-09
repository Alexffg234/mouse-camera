import json
import os
import threading
from functools import wraps

from flask import Flask, jsonify, request, send_from_directory

from gesture_mapper import GestureMapper

app = Flask(__name__, static_folder="web", static_url_path="")

_server_thread = None
running = False


def _get_config_path() -> str:
    return os.environ.get("CONFIG_PATH", "config.json")


@app.route("/")
def index():
    return send_from_directory("", "web/config.html")


@app.route("/api/config")
def get_config():
    mapper = GestureMapper(_get_config_path())
    return jsonify(mapper.get_config())


@app.route("/api/config", methods=["POST"])
def save_config():
    data = request.get_json()
    if data is None:
        return jsonify({"error": "invalid JSON"}), 400

    config_path = _get_config_path()

    try:
        _validate_config(data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    tmp_path = config_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, config_path)

    return jsonify({"ok": True})


@app.route("/api/metadata")
def metadata():
    return jsonify({
        "supported_gestures": GestureMapper.SUPPORTED_GESTURES,
        "valid_actions": GestureMapper.VALID_ACTIONS,
        "valid_modes": GestureMapper.VALID_MODES,
    })


def _validate_config(data: dict):
    """Validate config before writing to avoid corrupting config.json."""
    gm = data.get("gesture_mouse_map", {})
    for action, cfg in gm.items():
        if action not in GestureMapper.VALID_ACTIONS:
            raise ValueError(f"Unknown action '{action}'")
        tr = cfg.get("trigger", {})
        mode = tr.get("mode", "")
        if mode not in GestureMapper.VALID_MODES:
            raise ValueError(f"Invalid mode '{mode}' for '{action}'")
        from_g = tr.get("from", "")
        to_g = tr.get("to", "")
        if from_g not in GestureMapper.SUPPORTED_GESTURES:
            raise ValueError(f"Invalid gesture '{from_g}' for '{action}'")
        if to_g not in GestureMapper.SUPPORTED_GESTURES:
            raise ValueError(f"Invalid gesture '{to_g}' for '{action}'")
        if mode == "transition" and from_g == to_g:
            raise ValueError(f"transition mode requires from != to for '{action}'")
        threshold = tr.get("threshold")
        if threshold is not None and threshold <= 0:
            raise ValueError(f"threshold must be > 0 for '{action}'")
        hold_ms = tr.get("hold_ms")
        if hold_ms is not None and hold_ms <= 0:
            raise ValueError(f"hold_ms must be > 0 for '{action}'")

    sensitivity = data.get("sensitivity", {})
    sf = sensitivity.get("smoothing_factor", 0.3)
    if not (0 < sf <= 1):
        raise ValueError("smoothing_factor must be in (0, 1]")

    cal = data.get("calibration", {})
    if cal.get("max_x", 0) <= cal.get("min_x", 0):
        raise ValueError("max_x must be > min_x")
    if cal.get("max_y", 0) <= cal.get("min_y", 0):
        raise ValueError("max_y must be > min_y")


def start_server(host="127.0.0.1", port=18960, config_path="config.json"):
    """Start the Flask config server in a background daemon thread."""
    global running, _server_thread
    if running:
        return

    os.environ["CONFIG_PATH"] = config_path
    running = True

    def _run():
        global running
        app.run(host=host, port=port, debug=False, use_reloader=False)
        running = False

    _server_thread = threading.Thread(target=_run, daemon=True)
    _server_thread.start()
    print(f"[配置服务] 运行于 http://{host}:{port}/")


def stop_server():
    global running
    running = False

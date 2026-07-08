import os
import sys
import time

import cv2

from calibration import CalibrationHelper
from config_server import start_server
from gesture_mapper import GestureMapper
from gesture_recognizer import GestureRecognizer
from hand_tracker import HandTracker
from mouse_controller import MouseController
from user_tracker import UserTracker

# Fix Windows console Chinese output
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"


def draw_overlay(frame, gesture: str, action: str, hold_progress: float,
                 user_status: dict, fps: float, transitions: list,
                 confidence: float = 1.0):
    h, w = frame.shape[:2]
    y = 30
    line_h = 25

    if gesture:
        conf_text = f" ({confidence:.0%})" if confidence < 1.0 else ""
        cv2.putText(frame, f"手势: {gesture}{conf_text}", (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        y += line_h

    if action:
        color = _action_color(action)
        cv2.putText(frame, f"操作: {action}", (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        y += line_h
        _draw_action_indicator(frame, action, w, h)

    if hold_progress > 0:
        bar_w = min(int(hold_progress * 200), 200)
        cv2.rectangle(frame, (10, y - 12), (210, y + 2), (100, 100, 100), -1)
        cv2.rectangle(frame, (10, y - 12), (10 + bar_w, y + 2), (0, 255, 0), -1)
        y += 20

    for t in transitions:
        if t.get("fired"):
            cv2.putText(frame, f"过渡: {t['from']} -> {t['to']}", (10, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
            y += line_h

    locked = user_status.get("locked", False)
    depth = user_status.get("depth")
    if locked and depth is not None:
        cv2.putText(frame, f"已锁定 (d={depth:.2f})", (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
        y += line_h

    cv2.putText(frame, f"FPS: {fps:.0f}", (w - 150, h - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)


def _action_color(action: str) -> tuple:
    colors = {
        "left_click": (255, 255, 0),
        "right_click": (0, 255, 255),
        "double_click": (255, 165, 0),
        "scroll_up": (186, 85, 211),
        "scroll_down": (186, 85, 211),
        "copy": (0, 255, 0),
        "paste": (144, 238, 144),
        "cut": (255, 105, 180),
        "drag": (200, 200, 0),
        "show_desktop": (255, 0, 255),
    }
    return colors.get(action, (255, 255, 0))


def _draw_action_indicator(frame, action: str, w: int, h: int):
    cx, cy = w - 60, h - 80
    radius = 25

    indicators = {
        "left_click": {"symbol": "L", "color": (255, 255, 0)},
        "right_click": {"symbol": "R", "color": (0, 255, 255)},
        "double_click": {"symbol": "D", "color": (255, 165, 0)},
        "scroll_up": {"symbol": "↑", "color": (186, 85, 211)},
        "scroll_down": {"symbol": "↓", "color": (186, 85, 211)},
        "copy": {"symbol": "C", "color": (0, 255, 0)},
        "paste": {"symbol": "V", "color": (144, 238, 144)},
        "cut": {"symbol": "X", "color": (255, 105, 180)},
        "drag": {"symbol": "⇔", "color": (200, 200, 0)},
        "show_desktop": {"symbol": "⬚", "color": (255, 0, 255)},
    }

    info = indicators.get(action)
    if not info:
        return

    color = info["color"]
    cv2.circle(frame, (cx, cy), radius, color, 2)
    cv2.circle(frame, (cx, cy), radius - 2, (*[c // 4 for c in color],), -1)
    cv2.putText(frame, info["symbol"], (cx - 10, cy + 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)


def main():
    print("手势鼠标控制 — 按 Q 退出，按 C 校准")

    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    start_server(config_path=config_path)
    mapper = GestureMapper(config_path)
    config = mapper.get_config()

    tr = config.get("tracking", {})
    tracker = HandTracker(
        max_hands=tr.get("max_hands", 2),
        min_detection_confidence=tr.get("min_hand_confidence", 0.5),
        min_tracking_confidence=tr.get("min_tracking_confidence", 0.5),
    )
    recognizer_cfg = config.get("recognizer", {})
    recognizer = GestureRecognizer(
        finger_margin=recognizer_cfg.get("finger_margin", 1.05),
    )
    mouse_ctrl = MouseController(config)
    user_trk = UserTracker(lock_timeout_ms=tr.get("user_lock_timeout_ms", 3000))

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print("错误：无法打开摄像头")
        return

    hold_start: dict[str, float] = {}
    transition_state: dict[str, dict] = {}
    prev_stable_gesture = ""
    prev_time = time.time()
    fps = 30.0
    TIP_MAP = {"index_tip": 8, "middle_tip": 12, "palm_center": 9}

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            now = time.time()
            fps = fps * 0.95 + (1.0 / max((now - prev_time), 0.001)) * 0.05
            prev_time = now

            # Config hot-reload
            if mapper.check_reload():
                config = mapper.get_config()
                mouse_ctrl.update_config(config)
                print("[热加载] config.json 已更新")

            # Hand tracking (VIDEO mode: pass ms timestamp)
            all_hands = tracker.process(frame, timestamp_ms=int(now * 1000))
            selected = user_trk.select_hand(all_hands)

            current_gesture = ""
            current_action = ""
            hold_progress = 0.0
            trans_info = []

            if selected:
                tracker.draw(frame, [selected])
                # Stable recognition for action triggers (instant/hold/transition)
                current_gesture = recognizer.recognize(selected, now)
                current_time_ms = now * 1000

                # --- Transition detection ---
                all_transitions = mapper.get_transitions()
                for t in all_transitions:
                    key = f"{t['from']}->{t['to']}"
                    t_state = transition_state.get(key)
                    if t_state is None:
                        if prev_stable_gesture == t["from"]:
                            transition_state[key] = {"fired": False, "ts": now}
                    else:
                        elapsed = (now - t_state["ts"]) * 1000
                        if elapsed > t["timeout_ms"]:
                            del transition_state[key]
                            continue
                        if current_gesture == t["to"] and not t_state["fired"]:
                            current_action = t["action"]
                            mouse_ctrl.execute(t["action"], mapper.get_action_params(t["action"]))
                            t_state["fired"] = True
                    trans_info.append({"from": t["from"], "to": t["to"], "fired": transition_state.get(key, {}).get("fired", False)})

                # --- Process all triggers by mode ---
                gm = config.get("gesture_mouse_map", {})

                # Follow mode: use raw gesture (no stability filter) for low latency
                follow_actions = mapper.get_follow_actions()
                raw_gesture = recognizer.get_raw_gesture()
                for action_name in follow_actions:
                    trigger = mapper.get_trigger(action_name)
                    if trigger["from"] == raw_gesture:
                        landmark = trigger.get("landmark", "index_tip")
                        tip_id = TIP_MAP.get(landmark, 8)
                        pos = selected.get(tip_id)
                        mouse_ctrl.execute(action_name, mapper.get_action_params(action_name), pos)

                # Swipe mode: call detect_swipe once per gesture, dispatch by direction
                swipe_dir = recognizer.detect_swipe(selected)
                if swipe_dir:
                    for action_name, action_cfg in gm.items():
                        trigger = action_cfg.get("trigger", {})
                        if (trigger.get("mode") == "swipe"
                                and trigger["from"] == current_gesture
                                and trigger.get("swipe_direction") == swipe_dir):
                            current_action = action_name
                            mouse_ctrl.execute(action_name, mapper.get_action_params(action_name))

                # Instant & Hold mode
                for action_name, action_cfg in gm.items():
                    trigger = action_cfg.get("trigger", {})
                    mode = trigger.get("mode")
                    if mode == "instant" and trigger["from"] == current_gesture:
                        current_action = action_name
                        mouse_ctrl.execute(action_name, mapper.get_action_params(action_name))
                    elif mode == "hold" and trigger["from"] == current_gesture:
                        if action_name not in hold_start:
                            hold_start[action_name] = current_time_ms
                        elapsed = current_time_ms - hold_start[action_name]
                        hold_ms = trigger.get("hold_ms", 800)
                        progress = min(elapsed / hold_ms, 1.0)
                        if elapsed >= hold_ms:
                            current_action = action_name
                            lm_key = trigger.get("landmark", "index_tip")
                            tip_id = TIP_MAP.get(lm_key, 8)
                            pos = selected.get(tip_id)
                            mouse_ctrl.execute(action_name, mapper.get_action_params(action_name), pos)
                            del hold_start[action_name]
                        hold_progress = max(hold_progress, progress)

                # Stop drag if no follow gesture active
                if current_gesture not in (t["from"] for a in follow_actions for t in [mapper.get_trigger(a)]):
                    mouse_ctrl.stop_drag()

                # Update stable gesture for transition tracking
                if current_gesture != "none":
                    prev_stable_gesture = current_gesture

            else:
                mouse_ctrl.stop_drag()
                prev_stable_gesture = ""

            draw_overlay(frame, current_gesture, current_action, hold_progress,
                         user_trk.get_status(), fps, trans_info,
                         recognizer.get_confidence())

            cv2.imshow("Camera Mouse Control", frame)
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break
            elif key == ord("c"):
                cap.release()
                cv2.destroyAllWindows()
                cal = CalibrationHelper(config_path)
                cal.run()
                mapper.check_reload()
                config = mapper.get_config()
                mouse_ctrl.update_config(config)
                cap = cv2.VideoCapture(0)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                prev_time = time.time()

    finally:
        cap.release()
        tracker.close()
        cv2.destroyAllWindows()

    print("已停止。")


if __name__ == "__main__":
    main()

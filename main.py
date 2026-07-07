import sys
import time

import cv2

from calibration import CalibrationHelper
from gesture_mapper import GestureMapper
from gesture_recognizer import GestureRecognizer
from hand_tracker import HandTracker
from mouse_controller import MouseController
from user_tracker import UserTracker


def draw_overlay(frame, gesture: str, action: str, hold_progress: float,
                 user_status: dict, fps: float):
    h, w = frame.shape[:2]
    y = 30
    line_h = 25

    if gesture:
        cv2.putText(frame, f"Gesture: {gesture}", (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        y += line_h

    if action:
        cv2.putText(frame, f"Action: {action}", (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        y += line_h

    if hold_progress > 0:
        bar_w = min(int(hold_progress * 200), 200)
        cv2.rectangle(frame, (10, y - 12), (210, y + 2), (100, 100, 100), -1)
        cv2.rectangle(frame, (10, y - 12), (10 + bar_w, y + 2), (0, 255, 0), -1)
        y += 20

    locked = user_status.get("locked", False)
    depth = user_status.get("depth")
    if locked and depth is not None:
        cv2.putText(frame, f"Locked (d={depth:.2f})", (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
        y += line_h

    cv2.putText(frame, f"FPS: {fps:.0f}", (w - 150, h - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)


def main():
    print("Camera Mouse Control — press Q to quit, C for calibration")

    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    mapper = GestureMapper(config_path)
    config = mapper.get_config()

    tr = config.get("tracking", {})
    tracker = HandTracker(
        max_hands=tr.get("max_hands", 2),
        min_detection_confidence=tr.get("min_hand_confidence", 0.5),
        min_tracking_confidence=tr.get("min_tracking_confidence", 0.5),
    )
    recognizer = GestureRecognizer()
    mouse_ctrl = MouseController(config)
    user_trk = UserTracker(lock_timeout_ms=tr.get("user_lock_timeout_ms", 3000))

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print("ERROR: Cannot open camera")
        return

    hold_start: dict[str, float] = {}
    prev_time = time.time()
    fps = 30.0

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
                print("[reload] config.json updated")

            # Hand tracking
            all_hands = tracker.process(frame)
            selected = user_trk.select_hand(all_hands)

            current_gesture = ""
            current_action = ""
            landmark_pos = None

            if selected:
                tracker.draw(frame, [selected])
                current_gesture = recognizer.recognize(selected, now)
                current_time_ms = now * 1000

                if current_gesture != "none":
                    action_name = mapper.get_action_for_gesture(current_gesture)
                    if action_name:
                        params = mapper.get_action_params(action_name)
                        hold_ms = params.get("hold_ms")

                        if hold_ms and action_name not in hold_start:
                            hold_start[action_name] = current_time_ms

                        if hold_ms:
                            elapsed = current_time_ms - hold_start.get(action_name, current_time_ms)
                            progress = min(elapsed / hold_ms, 1.0)
                            if elapsed >= hold_ms:
                                current_action = action_name
                                lm_key = params.get("landmark", "index_tip")
                                tip_map = {"index_tip": 8, "middle_tip": 12, "palm_center": 9}
                                tip_id = tip_map.get(lm_key, 8)
                                pos = selected.get(tip_id)
                                mouse_ctrl.execute(action_name, params, pos)
                                del hold_start[action_name]
                            hold_progress = progress
                        else:
                            current_action = action_name
                            hold_progress = 0.0
                            lm_key = params.get("landmark", "index_tip")
                            tip_map = {"index_tip": 8, "middle_tip": 12, "palm_center": 9}
                            tip_id = tip_map.get(lm_key, 8)
                            pos = selected.get(tip_id)
                            mouse_ctrl.execute(action_name, params, pos)
                    else:
                        hold_progress = 0.0
                else:
                    hold_progress = 0.0

                if not current_gesture or current_gesture == "none":
                    mouse_ctrl.stop_drag()

            else:
                hold_progress = 0.0
                mouse_ctrl.stop_drag()

            draw_overlay(frame, current_gesture, current_action, hold_progress,
                         user_trk.get_status(), fps)

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

    print("Stopped.")


if __name__ == "__main__":
    main()

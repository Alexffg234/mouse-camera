import json
import os

import cv2
import numpy as np

from hand_tracker import HandTracker


class CalibrationHelper:
    CORNERS = ["TOP-LEFT", "TOP-RIGHT", "BOTTOM-RIGHT", "BOTTOM-LEFT"]

    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.tracker = HandTracker()

    def run(self):
        """Interactive calibration — point index finger to each corner."""
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        if not cap.isOpened():
            print("ERROR: Cannot open camera for calibration")
            return

        screen = self._get_screen_size()
        corner_positions = [
            (0, 0),
            (screen[0], 0),
            (screen[0], screen[1]),
            (0, screen[1]),
        ]
        detected: list = []
        current = 0

        try:
            while current < 4:
                ret, frame = cap.read()
                if not ret:
                    break

                hands = self.tracker.process(frame)
                text = f"Point index finger to {self.CORNERS[current]}\nPress Space to confirm"
                cv2.putText(frame, text, (20, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

                if hands:
                    self.tracker.draw(frame, hands)
                    idx_tip = hands[0].get(8)
                    if idx_tip:
                        cx, cy = int(idx_tip[0] * frame.shape[1]), int(idx_tip[1] * frame.shape[0])
                        cv2.circle(frame, (cx, cy), 8, (0, 255, 0), -1)

                cv2.imshow("Calibration", frame)
                key = cv2.waitKey(30) & 0xFF

                if key == 32 and hands:
                    idx_tip = hands[0].get(8)
                    if idx_tip:
                        detected.append((idx_tip, corner_positions[current]))
                        current += 1
                        print(f"  Corner {current}/4: {self.CORNERS[current - 1]} -> {idx_tip[:2]}")
                elif key == ord("q"):
                    print("Calibration cancelled.")
                    break
        finally:
            cap.release()
            self.tracker.close()
            cv2.destroyAllWindows()

        if len(detected) == 4:
            self._save_calibration(detected, screen)
        else:
            print("Calibration incomplete. Keeping existing config.")

    @staticmethod
    def _get_screen_size():
        try:
            import pyautogui
            return pyautogui.size()
        except ImportError:
            return (1920, 1080)

    def _save_calibration(self, detected, screen):
        with open(self.config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        config["calibration"] = {
            "min_x": 0, "max_x": screen[0],
            "min_y": 0, "max_y": screen[1],
        }
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        print(f"Calibration saved to {self.config_path}")


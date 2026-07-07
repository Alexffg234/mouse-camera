import json
import os

import cv2
import numpy as np

from hand_tracker import HandTracker


class CalibrationHelper:
    CORNERS = ["左上", "右上", "右下", "左下"]

    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.tracker = HandTracker()

    def run(self):
        """Interactive calibration — point index finger to each corner."""
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        if not cap.isOpened():
            print("错误：无法打开摄像头进行校准")
            return

        screen = self._get_screen_size()
        corner_positions = [
            (0, 0),
            (screen[0], 0),
            (screen[0], screen[1]),
            (0, screen[1]),
        ]
        detected = []
        current = 0

        try:
            while current < 4:
                ret, frame = cap.read()
                if not ret:
                    break

                hands = self.tracker.process(frame)
                text = f"食指指向屏幕{self.CORNERS[current]}\n按空格确认"
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
                        print(f"  角落 {current}/4: {self.CORNERS[current - 1]} -> {idx_tip[:2]}")
                elif key == ord("q"):
                    print("校准已取消。")
                    break
        finally:
            cap.release()
            self.tracker.close()
            cv2.destroyAllWindows()

        if len(detected) == 4:
            self._save_calibration(detected, screen)
        else:
            print("校准未完成，保留现有配置。")

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
        print(f"校准已保存到 {self.config_path}")


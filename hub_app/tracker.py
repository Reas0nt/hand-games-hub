"""Webcam capture and hand landmark detection (MediaPipe Tasks API).

Never raises on camera or detector failure: read() returns an empty HandFrame.
"""

import os
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from hub_app.gestures import Landmark

CAPTURE_WIDTH = 320
CAPTURE_HEIGHT = 240


@dataclass
class HandFrame:
    landmarks: list[Landmark] | None
    rgb: np.ndarray | None


class HandTracker:
    def __init__(self, model_path: Path, camera_index: int = 0) -> None:
        self.model_path = Path(model_path)
        self.camera_index = camera_index
        self._cap = None
        self._landmarker = None
        self._last_ts_ms = -1

    def open(self) -> bool:
        self.close()
        try:
            options = vision.HandLandmarkerOptions(
                base_options=mp_python.BaseOptions(model_asset_path=str(self.model_path)),
                running_mode=vision.RunningMode.VIDEO,
                num_hands=1,
                min_hand_detection_confidence=0.6,
                min_tracking_confidence=0.5,
            )
            landmarker = vision.HandLandmarker.create_from_options(options)
        except Exception:
            return False

        try:
            if os.name == "nt":
                cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            else:
                cap = cv2.VideoCapture(self.camera_index)
            if not cap.isOpened():
                cap.release()
                landmarker.close()
                return False
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_HEIGHT)
        except Exception:
            landmarker.close()
            return False

        self._cap = cap
        self._landmarker = landmarker
        self._last_ts_ms = -1
        return True

    def _next_timestamp_ms(self) -> int:
        now_ms = int(time.monotonic() * 1000)
        self._last_ts_ms = max(self._last_ts_ms + 1, now_ms)
        return self._last_ts_ms

    def read(self) -> HandFrame:
        empty = HandFrame(None, None)
        if self._cap is None or self._landmarker is None:
            return empty
        try:
            ok, frame = self._cap.read()
            if not ok or frame is None:
                return empty

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self._landmarker.detect_for_video(image, self._next_timestamp_ms())

            landmarks = None
            if result.hand_landmarks:
                landmarks = [(lm.x, lm.y) for lm in result.hand_landmarks[0]]
            return HandFrame(landmarks, rgb)
        except Exception:
            return empty

    def close(self) -> None:
        if self._landmarker is not None:
            try:
                self._landmarker.close()
            except Exception:
                pass
            self._landmarker = None
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None

"""
Module ensemble nhận diện cho AuraBeam.

Nhiệm vụ của module này:
- Tải hai model YOLO: `best.pt` và `model_ai.pt`
- Chạy detect song song theo từng frame
- Hợp nhất bbox của hai model bằng IoU + weighted fusion
- Gán detection vào track hiện có bằng khoảng cách tới trạng thái Kalman dự đoán
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from ultralytics import YOLO

from .sensor_fusion import KalmanFilter3D


IOU_FUSE_THRESHOLD = 0.35
TRACK_MATCH_DISTANCE = 140.0


class EnsembleDetector:
    """
    Bộ nhận diện kết hợp hai model YOLO cho bài toán headlight/rearlight.
    """

    def __init__(
        self,
        primary_model_path: str = "model/yolov5.pt",
        secondary_model_path: str = "model/model_ai.pt",
        conf_threshold: float = 0.25,
        detector_mode: str = "ensemble_weighted",
        fuse_iou_threshold: float = IOU_FUSE_THRESHOLD,
    ) -> None:
        self.primary_model_path = self._resolve_model_path(primary_model_path)
        self.secondary_model_path = self._resolve_model_path(secondary_model_path)
        self.conf_threshold = float(conf_threshold)
        self.detector_mode = str(detector_mode)
        self.fuse_iou_threshold = float(fuse_iou_threshold)

        self.primary_model = YOLO(self.primary_model_path)
        self.secondary_model = YOLO(self.secondary_model_path)

    def detect(self, frame) -> list[dict]:
        """
        Chạy hai model trên cùng một frame rồi hợp nhất detection.
        """
        primary_detections = self._run_model_detection(self.primary_model, frame, "model/yolov5.pt")
        secondary_detections = self._run_model_detection(self.secondary_model, frame, "model/model_ai.pt")
        if self.detector_mode == "primary":
            return primary_detections
        if self.detector_mode == "secondary":
            return secondary_detections
        if self.detector_mode == "ensemble_nms":
            return self._fuse_model_detections_nms(primary_detections, secondary_detections)
        return self._fuse_model_detections_weighted(primary_detections, secondary_detections)

    def assign_tracks(
        self,
        fused_detections: list[dict],
        kalman_trackers: dict[int, KalmanFilter3D],
        predicted_states: dict[int, tuple[float, float, float]],
        last_classes: dict[int, int],
        dt: float,
        next_track_id: int,
    ) -> tuple[list[dict], set[int], int]:
        """
        Gán detection đã fuse vào các track hiện có hoặc tạo track mới.

        Returns:
            tuple:
                - Danh sách detection đã gắn `track_id`, `center_x`, `center_y`
                - Tập các track_id đã được gán trong frame hiện tại
                - next_track_id mới
        """
        assigned_tracks: set[int] = set()
        assigned_detections: list[dict] = []

        for detection in fused_detections:
            box = detection["box"]
            cls_id = detection["cls"]
            center_x, center_y = self.center_of_box(box)

            best_track_id = None
            best_distance = TRACK_MATCH_DISTANCE

            for track_id, predicted_state in predicted_states.items():
                if track_id in assigned_tracks:
                    continue
                if last_classes.get(track_id, cls_id) != cls_id:
                    continue

                pred_x, pred_y, _ = predicted_state
                distance = float(np.hypot(center_x - pred_x, center_y - pred_y))
                if distance < best_distance:
                    best_distance = distance
                    best_track_id = track_id

            if best_track_id is None:
                best_track_id = next_track_id
                next_track_id += 1

                tracker = KalmanFilter3D(dt=dt)
                tracker.initialize(center_x, center_y, 0.0)
                kalman_trackers[best_track_id] = tracker
                predicted_states[best_track_id] = tracker.get_state()

            assigned_tracks.add(best_track_id)

            assigned_detection = dict(detection)
            assigned_detection["track_id"] = best_track_id
            assigned_detection["center_x"] = center_x
            assigned_detection["center_y"] = center_y
            assigned_detections.append(assigned_detection)

        return assigned_detections, assigned_tracks, next_track_id

    @staticmethod
    def _resolve_model_path(path_str: str) -> str:
        """
        Bắt buộc file model phải tồn tại.
        """
        if not Path(path_str).exists():
            raise FileNotFoundError(f"Không tìm thấy model: {path_str}")
        return path_str

    def _run_model_detection(self, model: YOLO, frame, model_name: str) -> list[dict]:
        """
        Chạy một model YOLO ở chế độ detect để lấy bbox thô.
        """
        detections: list[dict] = []
        results = model.predict(frame, conf=self.conf_threshold, verbose=False)

        if not results:
            return detections

        boxes = results[0].boxes
        if boxes is None:
            return detections

        xyxy = boxes.xyxy.cpu().numpy() if boxes.xyxy is not None else np.empty((0, 4), dtype=np.float32)
        cls = boxes.cls.int().cpu().tolist() if boxes.cls is not None else []
        confs = boxes.conf.cpu().tolist() if boxes.conf is not None else []

        for box, cls_id, conf in zip(xyxy, cls, confs):
            detections.append(
                {
                    "box": box.astype(np.float64),
                    "cls": int(cls_id),
                    "conf": float(conf),
                    "source": model_name,
                }
            )

        return detections

    def _fuse_model_detections_weighted(self, primary_dets: list[dict], secondary_dets: list[dict]) -> list[dict]:
        """
        Hợp nhất detection của hai model bằng weighted box fusion đơn giản.
        """
        fused_detections: list[dict] = []
        used_secondary: set[int] = set()

        for primary in primary_dets:
            best_match_index = -1
            best_iou = 0.0

            for sec_index, secondary in enumerate(secondary_dets):
                if sec_index in used_secondary or primary["cls"] != secondary["cls"]:
                    continue

                iou = self.compute_iou(primary["box"], secondary["box"])
                if iou > best_iou:
                    best_iou = iou
                    best_match_index = sec_index

            if best_match_index >= 0 and best_iou >= self.fuse_iou_threshold:
                secondary = secondary_dets[best_match_index]
                used_secondary.add(best_match_index)

                weight_primary = max(primary["conf"], 1e-6)
                weight_secondary = max(secondary["conf"], 1e-6)
                fused_box = (
                    primary["box"] * weight_primary + secondary["box"] * weight_secondary
                ) / (weight_primary + weight_secondary)

                fused_detections.append(
                    {
                        "box": fused_box,
                        "cls": primary["cls"],
                        "conf": max(primary["conf"], secondary["conf"]),
                        "source": "ensemble",
                    }
                )
            else:
                fused_detections.append(primary)

        for sec_index, secondary in enumerate(secondary_dets):
            if sec_index not in used_secondary:
                fused_detections.append(secondary)

        fused_detections.sort(key=lambda item: item["conf"], reverse=True)
        return fused_detections

    def _fuse_model_detections_nms(self, primary_dets: list[dict], secondary_dets: list[dict]) -> list[dict]:
        candidates = [dict(item) for item in primary_dets] + [dict(item) for item in secondary_dets]
        candidates.sort(key=lambda item: item["conf"], reverse=True)

        kept: list[dict] = []
        for candidate in candidates:
            suppress = False
            for kept_item in kept:
                if candidate["cls"] != kept_item["cls"]:
                    continue
                if self.compute_iou(candidate["box"], kept_item["box"]) >= self.fuse_iou_threshold:
                    suppress = True
                    break
            if not suppress:
                kept.append(candidate)

        return kept

    @staticmethod
    def compute_iou(box_a: np.ndarray, box_b: np.ndarray) -> float:
        """
        Tính Intersection over Union để đo mức chồng lấp giữa 2 bbox.
        """
        x1 = max(float(box_a[0]), float(box_b[0]))
        y1 = max(float(box_a[1]), float(box_b[1]))
        x2 = min(float(box_a[2]), float(box_b[2]))
        y2 = min(float(box_a[3]), float(box_b[3]))

        inter_w = max(0.0, x2 - x1)
        inter_h = max(0.0, y2 - y1)
        intersection = inter_w * inter_h

        area_a = max(0.0, float(box_a[2] - box_a[0])) * max(0.0, float(box_a[3] - box_a[1]))
        area_b = max(0.0, float(box_b[2] - box_b[0])) * max(0.0, float(box_b[3] - box_b[1]))
        union = area_a + area_b - intersection

        if union <= 0.0:
            return 0.0

        return intersection / union

    @staticmethod
    def center_of_box(box: np.ndarray) -> tuple[float, float]:
        """
        Tính tâm hình học của bounding box.
        """
        return (float(box[0] + box[2]) * 0.5, float(box[1] + box[3]) * 0.5)

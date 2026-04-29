"""
File thực thi trung tâm cho prototype AuraBeam trên PC.

Pipeline chính:
1. Đọc frame từ webcam hoặc video file.
2. Chạy song song 2 model YOLO: `best.pt` và `model_ai.pt`.
3. Hợp nhất detection của hai model trước khi gán ID nội bộ.
4. Dùng Kalman Filter 3D để làm mượt quỹ đạo và điền khuyết khi mất frame ngắn.
5. Ánh xạ mục tiêu sang 4 vùng đèn và gửi lệnh qua Serial.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict, deque
from pathlib import Path

import cv2

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from aura_beam.detector_ensemble import EnsembleDetector
from aura_beam.pseudo_radar import VirtualRadar
from aura_beam.sensor_fusion import KalmanFilter3D
from aura_beam.serial_manager import SerialController
from aura_beam.zone_logic import Matrix8x8Controller


TRAJECTORY_LENGTH = 30


def parse_args() -> argparse.Namespace:
    """
    Parse tham số đầu vào cho file thực thi.
    """
    parser = argparse.ArgumentParser(description="AuraBeam PC prototype runner")
    parser.add_argument("--primary-model", type=str, default="model/yolov5.pt", help="Model YOLO chính.")
    parser.add_argument("--secondary-model", type=str, default="model/model_ai.pt", help="Model YOLO phụ.")
    parser.add_argument("--source", type=str, default="demo_video/fogging_1.mp4", help="Nguồn video hoặc webcam.")
    parser.add_argument("--serial-port", type=str, default="COM3", help="Cổng COM kết nối Arduino.")
    parser.add_argument("--baudrate", type=int, default=115200, help="Baudrate Serial.")
    parser.add_argument("--conf", type=float, default=0.25, help="Ngưỡng confidence YOLO.")
    parser.add_argument("--radar-initial-z", type=float, default=100.0, help="Khoảng cách radar ban đầu, đơn vị mét.")
    parser.add_argument("--radar-target-speed", type=float, default=15.0, help="Tốc độ tiếp cận giả lập của radar, m/s.")
    parser.add_argument(
        "--track-hold-seconds",
        type=float,
        default=1,
        help="Số giây Kalman tiếp tục dự đoán sau khi xe rời khỏi frame.",
    )
    return parser.parse_args()


def open_capture(source_arg: str) -> cv2.VideoCapture:
    """
    Mở webcam hoặc file video.
    """
    source = int(source_arg) if source_arg.isdigit() else source_arg
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"Không mở được nguồn video: {source_arg}")
    return cap


def draw_dashed_rectangle(
    frame,
    pt1: tuple[int, int],
    pt2: tuple[int, int],
    color: tuple[int, int, int],
    thickness: int = 2,
    dash_length: int = 8,
) -> None:
    """
    Vẽ bounding box nét đứt để biểu diễn đo lường AI còn nhiễu.
    """
    x1, y1 = pt1
    x2, y2 = pt2

    for x in range(x1, x2, dash_length * 2):
        x_end = min(x + dash_length, x2)
        cv2.line(frame, (x, y1), (x_end, y1), color, thickness)
        cv2.line(frame, (x, y2), (x_end, y2), color, thickness)

    for y in range(y1, y2, dash_length * 2):
        y_end = min(y + dash_length, y2)
        cv2.line(frame, (x1, y), (x1, y_end), color, thickness)
        cv2.line(frame, (x2, y), (x2, y_end), color, thickness)


def main() -> None:
    """
    Chạy toàn bộ pipeline prototype AuraBeam trên PC với ensemble 2 model.
    """
    args = parse_args()
    detector = EnsembleDetector(
        primary_model_path=args.primary_model,
        secondary_model_path=args.secondary_model,
        conf_threshold=args.conf,
    )
    serial_controller = SerialController(port=args.serial_port, baudrate=args.baudrate, timeout=0.1)

    cap = open_capture(args.source)
    screen_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    if screen_width <= 0:
        screen_width = 1280.0

    screen_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    if screen_height <= 0:
        screen_height = 720.0

    fps = cap.get(cv2.CAP_PROP_FPS)
    dt = 1.0 / fps if fps and fps > 1e-6 else 1.0 / 30.0
    effective_fps = fps if fps and fps > 1e-6 else 30.0

    radar = VirtualRadar(
        fps=effective_fps,
        initial_z=args.radar_initial_z,
        target_speed=args.radar_target_speed,
    )

    matrix_controller = Matrix8x8Controller(matrix_width=8, matrix_height=8)

    max_missed_frames = max(1, int(round(effective_fps * args.track_hold_seconds))) if fps and fps > 1e-6 else int(
        round(30.0 * args.track_hold_seconds)
    )

    kalman_trackers: dict[int, KalmanFilter3D] = {}
    track_histories: dict[int, deque[tuple[int, int]]] = defaultdict(lambda: deque(maxlen=TRAJECTORY_LENGTH))
    last_seen_frames: dict[int, int] = {}
    last_classes: dict[int, int] = {}
    predicted_states: dict[int, tuple[float, float, float]] = {}
    next_track_id = 1
    frame_index = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_index += 1
            z_radar = radar.get_distance(frame_index)
            smoothed_vehicles: list[tuple[int, float, float, float, int]] = []
            detections_for_draw: list[tuple[int, int, int, int, int, int, float, str]] = []
            assigned_tracks: set[int] = set()

            for track_id, tracker in list(kalman_trackers.items()):
                missed_count = frame_index - last_seen_frames.get(track_id, frame_index)
                if missed_count > max_missed_frames:
                    kalman_trackers.pop(track_id, None)
                    track_histories.pop(track_id, None)
                    last_seen_frames.pop(track_id, None)
                    last_classes.pop(track_id, None)
                    predicted_states.pop(track_id, None)
                    continue

                predicted_states[track_id] = tracker.predict()

            fused_detections = detector.detect(frame)
            assigned_detections, assigned_tracks, next_track_id = detector.assign_tracks(
                fused_detections=fused_detections,
                kalman_trackers=kalman_trackers,
                predicted_states=predicted_states,
                last_classes=last_classes,
                dt=dt,
                next_track_id=next_track_id,
            )

            for detection in assigned_detections:
                box = detection["box"]
                cls_id = detection["cls"]
                source_name = detection["source"]
                best_track_id = detection["track_id"]
                center_x = detection["center_x"]
                center_y = detection["center_y"]
                tracker = kalman_trackers[best_track_id]

                smoothed_state = tracker.update(center_x, center_y, z_radar, predict_first=False)
                last_seen_frames[best_track_id] = frame_index
                last_classes[best_track_id] = cls_id

                sx, sy, sz = smoothed_state
                track_histories[best_track_id].append((int(sx), int(sy)))
                smoothed_vehicles.append((best_track_id, sx, sy, sz, cls_id))
                detections_for_draw.append(
                    (
                        int(box[0]),
                        int(box[1]),
                        int(box[2]),
                        int(box[3]),
                        best_track_id,
                        cls_id,
                        z_radar,
                        source_name,
                    )
                )

            for track_id, tracker in kalman_trackers.items():
                if track_id in assigned_tracks:
                    continue

                missed_count = frame_index - last_seen_frames.get(track_id, frame_index)
                if missed_count <= max_missed_frames:
                    sx, sy, sz = tracker.update(None, None, z_radar, predict_first=False)
                    cls_id = last_classes.get(track_id, -1)
                    track_histories[track_id].append((int(sx), int(sy)))
                    smoothed_vehicles.append((track_id, sx, sy, sz, cls_id))

            active_command = None
            active_target = None
            if smoothed_vehicles:
                active_target = min(smoothed_vehicles, key=lambda item: item[3])
                _, smooth_x, smooth_y, smooth_z, _ = active_target
                active_command = matrix_controller.get_dark_box(
                    smooth_x=smooth_x,
                    smooth_y=smooth_y,
                    smooth_z=smooth_z,
                    screen_width=screen_width,
                    screen_height=screen_height,
                )

            serial_controller.send_command(active_command)

            overlay_y = 30
            command_text = active_command.strip() if active_command is not None else "BOX:-1:-1:-1:-1"
            cv2.putText(
                frame,
                f"COM: {command_text}",
                (20, overlay_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 255),
                2,
                cv2.LINE_AA,
            )
            overlay_y += 30

            cv2.putText(
                frame,
                f"Serial: {args.serial_port} @ {args.baudrate}",
                (20, overlay_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 255),
                2,
                cv2.LINE_AA,
            )
            overlay_y += 30

            if active_target is not None:
                cv2.putText(
                    frame,
                    f"Nearest target Z: {active_target[3]:.1f}m | Radar: {z_radar:.1f}m",
                    (20, overlay_y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA,
                )
                overlay_y += 30
            else:
                cv2.putText(
                    frame,
                    f"Radar: {z_radar:.1f}m",
                    (20, overlay_y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA,
                )
                overlay_y += 30

            cv2.putText(
                frame,
                f"Track hold: {args.track_hold_seconds:.1f}s ({max_missed_frames} frames)",
                (20, overlay_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

            for x1, y1, x2, y2, track_id, cls_id, z_meas, source_name in detections_for_draw:
                draw_dashed_rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), thickness=2)
                cv2.putText(
                    frame,
                    f"ID {track_id} | CLS {cls_id} | Zm {z_meas:.1f} | {source_name}",
                    (x1, max(20, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 255),
                    2,
                    cv2.LINE_AA,
                )

            for track_id, history in track_histories.items():
                points = list(history)
                if len(points) >= 2:
                    for idx in range(1, len(points)):
                        cv2.line(frame, points[idx - 1], points[idx], (255, 255, 0), 2)

                if points:
                    cv2.circle(frame, points[-1], 6, (0, 255, 0), -1)
                    cv2.putText(
                        frame,
                        f"KF {track_id}",
                        (points[-1][0] + 8, points[-1][1] - 8),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        2,
                        cv2.LINE_AA,
                    )

            cv2.imshow("AuraBeam Ensemble Prototype", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        serial_controller.send_command(None)
        serial_controller.close()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

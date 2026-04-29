"""
Script danh gia metric cho AuraBeam theo workflow Q2.

Muc tieu:
- Ho tro cac baseline B1-B4 va control ablation C1-C4.
- Luu ket qua theo cau hinh/scenario/run de phuc vu viet paper.
- Sinh summary JSON + per-frame CSV trong thu muc rieng cua moi experiment.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from aura_beam.detector_ensemble import EnsembleDetector
from aura_beam.pseudo_radar import VirtualRadar
from aura_beam.sensor_fusion import KalmanFilter2D, KalmanFilter3D
from aura_beam.zone_logic import HoldTimeBoxScheduler, Matrix8x8Controller


TRACK_MATCH_DISTANCE = 140.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate AuraBeam metrics for the Q2 workflow")
    parser.add_argument("--primary-model", type=str, default="model/yolov5.pt")
    parser.add_argument("--secondary-model", type=str, default="model/model_ai.pt")
    parser.add_argument("--source", type=str, required=True)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument(
        "--detector-mode",
        type=str,
        default="ensemble_weighted",
        choices=("primary", "secondary", "ensemble_nms", "ensemble_weighted"),
        help="A1/A2/A3/A4 trong workflow.",
    )
    parser.add_argument(
        "--tracking-mode",
        type=str,
        default="kf3d",
        choices=("raw", "kf2d", "kf3d"),
        help="B1/B2/B3/B4 trong workflow.",
    )
    parser.add_argument(
        "--observation-mode",
        type=str,
        default="adaptive",
        choices=("fixed", "adaptive"),
        help="C3/C4 trong workflow. Chi ap dung cho kf3d.",
    )
    parser.add_argument(
        "--control-mode",
        type=str,
        default="hold",
        choices=("direct", "hold"),
        help="C1/C2 trong workflow.",
    )
    parser.add_argument("--tau-conf", type=float, default=0.25, help="Nguong confidence cho adaptive switching.")
    parser.add_argument(
        "--adaptive-min-low-conf-frames",
        type=int,
        default=2,
        help="So frame low-confidence lien tiep toi thieu de kich hoat z-only mode.",
    )
    parser.add_argument(
        "--switch-policy",
        type=str,
        default="best_conf",
        choices=("best_conf", "active_track_conf_or_missing", "low_conf_pred_or_missing"),
        help="Policy xac dinh low-confidence frame cho adaptive switching.",
    )
    parser.add_argument(
        "--adaptive-min-prediction-only-frames",
        type=int,
        default=0,
        help="So frame prediction-only lien tiep toi thieu (dua tren lich su truoc frame hien tai) de cho phep switch.",
    )
    parser.add_argument(
        "--adaptive-switch-cooldown-frames",
        type=int,
        default=0,
        help="So frame toi thieu giua hai lan bat z-only mode.",
    )
    parser.add_argument("--fuse-iou-threshold", type=float, default=0.35)
    parser.add_argument("--radar-initial-z", type=float, default=100.0)
    parser.add_argument("--radar-target-speed", type=float, default=15.0)
    parser.add_argument("--track-hold-seconds", type=float, default=1.0)
    parser.add_argument("--hold-time-frames", type=int, default=5)
    parser.add_argument("--gt-csv", type=str, default=None, help="Ground truth CSV voi cot frame,x1,y1,x2,y2[,z].")
    parser.add_argument("--gt-coco", type=str, default=None, help="COCO JSON annotation.")
    parser.add_argument("--gt-folder", type=str, default=None, help="Thu muc Roboflow COCO.")
    parser.add_argument(
        "--gt-align",
        type=str,
        default="uniform",
        choices=("none", "uniform"),
        help="Can chinh frame ground truth vao video.",
    )
    parser.add_argument("--gssr-iou-threshold", type=float, default=0.5)
    parser.add_argument("--experiment-name", type=str, default=None)
    parser.add_argument("--scenario-name", type=str, default=None)
    parser.add_argument("--run-name", type=str, default="run_01")
    parser.add_argument(
        "--occlusion-json",
        type=str,
        default=None,
        help="JSON chua cac khoang occlusion/degradation theo scenario.",
    )
    parser.add_argument("--output-root", type=str, default="artifacts/results")
    parser.add_argument("--output-json", type=str, default=None)
    parser.add_argument("--output-csv", type=str, default=None)
    parser.add_argument("--progress", dest="progress", action="store_true")
    parser.add_argument("--no-progress", dest="progress", action="store_false")
    parser.set_defaults(progress=True)
    return parser.parse_args()


def sanitize_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned.strip("._-") or "unnamed"


def format_duration(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    minutes, remaining_seconds = divmod(seconds, 60)
    hours, remaining_minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours:d}:{remaining_minutes:02d}:{remaining_seconds:02d}"
    return f"{remaining_minutes:02d}:{remaining_seconds:02d}"


def build_progress_line(
    *,
    label: str,
    completed: int,
    total: int | None,
    elapsed_seconds: float,
    bar_width: int = 24,
) -> str:
    fps = completed / elapsed_seconds if elapsed_seconds > 1e-9 else 0.0
    if total and total > 0:
        ratio = min(max(completed / total, 0.0), 1.0)
        filled = min(bar_width, int(round(ratio * bar_width)))
        bar = f"[{'#' * filled}{'-' * (bar_width - filled)}]"
        eta_seconds = ((total - completed) / fps) if fps > 1e-9 else 0.0
        percent = ratio * 100.0
        return (
            f"\r{label} {bar} {completed}/{total} "
            f"({percent:5.1f}%) elapsed {format_duration(elapsed_seconds)} "
            f"eta {format_duration(eta_seconds)}"
        )

    return f"\r{label} frames={completed} elapsed {format_duration(elapsed_seconds)} rate={fps:.2f} fps"


def infer_experiment_name(args: argparse.Namespace) -> str:
    if args.experiment_name:
        return sanitize_name(args.experiment_name)

    parts = [
        args.detector_mode,
        args.tracking_mode,
    ]
    if args.tracking_mode == "kf3d":
        parts.append(args.observation_mode)
    parts.append(args.control_mode)
    return sanitize_name("__".join(parts))


def infer_scenario_name(args: argparse.Namespace) -> str:
    if args.scenario_name:
        return sanitize_name(args.scenario_name)
    return sanitize_name(Path(args.source).stem)


def resolve_output_paths(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    experiment_name = infer_experiment_name(args)
    scenario_name = infer_scenario_name(args)
    run_name = sanitize_name(args.run_name)
    run_dir = Path(args.output_root) / experiment_name / scenario_name / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    output_json = Path(args.output_json) if args.output_json else run_dir / "summary.json"
    output_csv = Path(args.output_csv) if args.output_csv else run_dir / "per_frame_metrics.csv"
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    return run_dir, output_json, output_csv


def open_capture(source_arg: str) -> cv2.VideoCapture:
    source = int(source_arg) if source_arg.isdigit() else source_arg
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open source: {source_arg}")
    return cap


def resolve_coco_annotation_path(gt_coco: str | None, gt_folder: str | None) -> Path | None:
    if gt_coco:
        coco_path = Path(gt_coco)
        if not coco_path.exists():
            raise FileNotFoundError(f"Khong tim thay COCO annotation: {gt_coco}")
        return coco_path

    if gt_folder:
        folder_path = Path(gt_folder)
        if not folder_path.is_dir():
            raise NotADirectoryError(f"Khong tim thay thu muc ground truth: {gt_folder}")

        coco_path = folder_path / "_annotations.coco.json"
        if not coco_path.exists():
            raise FileNotFoundError(f"Khong tim thay file _annotations.coco.json trong: {gt_folder}")
        return coco_path

    return None


def load_ground_truth(csv_path: str | None) -> dict[int, dict]:
    if not csv_path:
        return {}

    gt_map: dict[int, dict] = {}
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"frame", "x1", "y1", "x2", "y2"}
        if not required.issubset(reader.fieldnames or set()):
            raise ValueError("GT CSV must contain columns: frame,x1,y1,x2,y2")

        for row in reader:
            frame_id = int(row["frame"])
            gt_map[frame_id] = {
                "x1": float(row["x1"]),
                "y1": float(row["y1"]),
                "x2": float(row["x2"]),
                "y2": float(row["y2"]),
                "z": float(row["z"]) if row.get("z") not in (None, "") else None,
            }
    return gt_map


def extract_frame_id_from_name(name: str) -> int | None:
    match = re.search(r"-(\d+)(?:_jpg|\.jpg|\.png|\.jpeg)", name, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def load_ground_truth_coco(coco_path: str | None) -> dict[int, dict]:
    if not coco_path:
        return {}

    coco = json.loads(Path(coco_path).read_text(encoding="utf-8"))
    images_by_id = {image["id"]: image for image in coco.get("images", [])}
    anns_by_frame: dict[int, list[dict[str, float]]] = {}

    for ann in coco.get("annotations", []):
        image_info = images_by_id.get(ann["image_id"])
        if image_info is None:
            continue

        source_name = image_info.get("extra", {}).get("name") or image_info.get("file_name") or ""
        frame_id = extract_frame_id_from_name(source_name)
        if frame_id is None:
            continue

        bbox = ann.get("bbox", [])
        if len(bbox) != 4:
            continue

        x1, y1, width, height = map(float, bbox)
        x2 = x1 + width
        y2 = y1 + height
        area = float(ann.get("area", width * height))

        anns_by_frame.setdefault(frame_id + 1, []).append(
            {
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "area": area,
                "category_id": float(ann.get("category_id", -1)),
                "z": None,
            }
        )

    gt_map: dict[int, dict] = {}
    for frame_id, annotations in anns_by_frame.items():
        primary = max(annotations, key=lambda item: item["area"])
        gt_map[frame_id] = {
            "x1": primary["x1"],
            "y1": primary["y1"],
            "x2": primary["x2"],
            "y2": primary["y2"],
            "z": primary["z"],
            "num_annotations": len(annotations),
        }
    return gt_map


def extract_annotation_track_id(annotation: dict) -> int | None:
    direct_candidates = [
        annotation.get("track_id"),
        annotation.get("instance_id"),
        annotation.get("object_id"),
    ]
    for candidate in direct_candidates:
        if candidate not in (None, ""):
            return int(candidate)

    attributes = annotation.get("attributes", {})
    if isinstance(attributes, dict):
        for key in ("track_id", "instance_id", "object_id", "id"):
            candidate = attributes.get(key)
            if candidate not in (None, ""):
                return int(candidate)
    return None


def load_ground_truth_track_map_coco(coco_path: str | None) -> tuple[dict[int, list[dict]], bool]:
    if not coco_path:
        return {}, False

    coco = json.loads(Path(coco_path).read_text(encoding="utf-8"))
    images_by_id = {image["id"]: image for image in coco.get("images", [])}
    track_map: dict[int, list[dict]] = {}
    has_track_ids = False

    for ann in coco.get("annotations", []):
        image_info = images_by_id.get(ann["image_id"])
        if image_info is None:
            continue

        source_name = image_info.get("extra", {}).get("name") or image_info.get("file_name") or ""
        frame_id = extract_frame_id_from_name(source_name)
        if frame_id is None:
            continue

        bbox = ann.get("bbox", [])
        if len(bbox) != 4:
            continue

        track_id = extract_annotation_track_id(ann)
        if track_id is None:
            continue

        has_track_ids = True
        x1, y1, width, height = map(float, bbox)
        track_map.setdefault(frame_id + 1, []).append(
            {
                "track_id": int(track_id),
                "cls": int(ann.get("category_id", -1)),
                "box": np.array([x1, y1, x1 + width, y1 + height], dtype=np.float64),
            }
        )
    return track_map, has_track_ids


def detector_box_iou(box_a: np.ndarray, box_b: np.ndarray) -> float:
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


def greedy_match_iou(predicted_objects: list[dict], gt_objects: list[dict], iou_threshold: float) -> list[tuple[int, int]]:
    candidates: list[tuple[float, int, int]] = []
    for pred_index, pred in enumerate(predicted_objects):
        for gt_index, gt in enumerate(gt_objects):
            if int(pred.get("cls", -1)) != int(gt.get("cls", -1)):
                continue
            iou = detector_box_iou(pred["box"], gt["box"])
            if iou >= iou_threshold:
                candidates.append((iou, pred_index, gt_index))

    candidates.sort(reverse=True, key=lambda item: item[0])
    used_pred: set[int] = set()
    used_gt: set[int] = set()
    matches: list[tuple[int, int]] = []
    for _, pred_index, gt_index in candidates:
        if pred_index in used_pred or gt_index in used_gt:
            continue
        used_pred.add(pred_index)
        used_gt.add(gt_index)
        matches.append((pred_index, gt_index))
    return matches


def compute_multi_target_idf1(pair_counts: dict[int, dict[int, int]], total_gt_detections: int, total_pred_detections: int) -> float | None:
    if total_gt_detections <= 0:
        return None

    weighted_pairs: list[tuple[int, int, int]] = []
    for pred_id, gt_counts in pair_counts.items():
        for gt_id, count in gt_counts.items():
            weighted_pairs.append((count, pred_id, gt_id))

    weighted_pairs.sort(reverse=True)
    used_pred_ids: set[int] = set()
    used_gt_ids: set[int] = set()
    idtp = 0
    for count, pred_id, gt_id in weighted_pairs:
        if pred_id in used_pred_ids or gt_id in used_gt_ids:
            continue
        used_pred_ids.add(pred_id)
        used_gt_ids.add(gt_id)
        idtp += count

    idfp = max(0, total_pred_detections - idtp)
    idfn = max(0, total_gt_detections - idtp)
    denominator = (2 * idtp) + idfp + idfn
    if denominator <= 0:
        return 0.0
    return (2.0 * idtp) / denominator


def remap_gt_frames_uniform(gt_map: dict[int, dict], total_video_frames: int) -> dict[int, dict]:
    if not gt_map or total_video_frames <= 0:
        return gt_map

    sorted_items = sorted(gt_map.items())
    if len(sorted_items) == 1:
        only_key, only_value = sorted_items[0]
        return {1: {**only_value, "source_gt_frame": only_key}}

    remapped: dict[int, dict] = {}
    last_target = 0
    num_items = len(sorted_items)
    for idx, (source_frame, gt_value) in enumerate(sorted_items):
        target_frame = int(round(idx * (total_video_frames - 1) / (num_items - 1))) + 1
        target_frame = max(target_frame, last_target + 1)
        target_frame = min(target_frame, total_video_frames)
        remapped[target_frame] = {**gt_value, "source_gt_frame": source_frame}
        last_target = target_frame
    return remapped


def load_occlusion_intervals(occlusion_json_path: str | None, scenario_name: str, source_path: str) -> list[tuple[int, int]]:
    if not occlusion_json_path:
        return []

    json_path = Path(occlusion_json_path)
    if not json_path.exists():
        raise FileNotFoundError(f"Khong tim thay file occlusion JSON: {occlusion_json_path}")

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    scenario_key_candidates = [
        sanitize_name(scenario_name),
        scenario_name,
        sanitize_name(Path(source_path).stem),
        Path(source_path).stem,
    ]

    raw_intervals: Any = None
    if isinstance(payload, dict):
        scenarios = payload.get("scenarios")
        if isinstance(scenarios, dict):
            for key in scenario_key_candidates:
                if key in scenarios:
                    raw_intervals = scenarios[key]
                    break
        if raw_intervals is None:
            for key in scenario_key_candidates:
                if key in payload:
                    raw_intervals = payload[key]
                    break

    if raw_intervals is None:
        return []

    if not isinstance(raw_intervals, list):
        raise ValueError("Occlusion JSON phai map scenario -> list interval.")

    intervals: list[tuple[int, int]] = []
    for item in raw_intervals:
        if not isinstance(item, dict):
            raise ValueError("Moi occlusion interval phai la object co start/end.")
        start = int(item["start"])
        end = int(item["end"])
        if end < start:
            raise ValueError(f"Occlusion interval khong hop le: start={start}, end={end}")
        intervals.append((start, end))

    intervals.sort()
    return intervals


def is_frame_in_intervals(frame_index: int, intervals: list[tuple[int, int]]) -> bool:
    for start, end in intervals:
        if start <= frame_index <= end:
            return True
    return False


def matrix_box_to_tuple(command: str | None) -> tuple[int, int, int, int] | None:
    if command is None:
        return None
    parts = command.strip().split(":")
    if len(parts) != 5 or parts[0] != "BOX":
        return None
    col_start, col_end, row_start, row_end = map(int, parts[1:])
    if col_start < 0 or col_end < 0 or row_start < 0 or row_end < 0:
        return None
    return col_start, col_end, row_start, row_end


def discrete_box_iou(box_a: tuple[int, int, int, int] | None, box_b: tuple[int, int, int, int] | None) -> float:
    if box_a is None or box_b is None:
        return 0.0

    ax1, ax2, ay1, ay2 = box_a
    bx1, bx2, by1, by2 = box_b
    inter_x1 = max(ax1, bx1)
    inter_x2 = min(ax2, bx2)
    inter_y1 = max(ay1, by1)
    inter_y2 = min(ay2, by2)
    if inter_x1 > inter_x2 or inter_y1 > inter_y2:
        return 0.0

    intersection = (inter_x2 - inter_x1 + 1) * (inter_y2 - inter_y1 + 1)
    area_a = (ax2 - ax1 + 1) * (ay2 - ay1 + 1)
    area_b = (bx2 - bx1 + 1) * (by2 - by1 + 1)
    union = area_a + area_b - intersection
    return float(intersection) / float(union) if union > 0 else 0.0


def euclidean_distance(point_a: tuple[float, float], point_b: tuple[float, float]) -> float:
    return math.hypot(point_a[0] - point_b[0], point_a[1] - point_b[1])


def rms(values: list[float]) -> float:
    if not values:
        return 0.0
    return math.sqrt(sum(value * value for value in values) / len(values))


def safe_mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def estimate_depth_from_box_width(box: np.ndarray) -> float:
    width = max(1.0, float(box[2] - box[0]))
    return 8000.0 / width


def get_predicted_xy(state: tuple[float, ...]) -> tuple[float, float]:
    return float(state[0]), float(state[1])


def initialize_tracker(tracking_mode: str, dt: float, center_x: float, center_y: float):
    if tracking_mode == "kf2d":
        tracker = KalmanFilter2D(dt=dt)
        tracker.initialize(center_x, center_y)
        return tracker

    tracker = KalmanFilter3D(dt=dt)
    tracker.initialize(center_x, center_y, 0.0)
    return tracker


def assign_tracks_generic(
    detections: list[dict],
    trackers: dict[int, Any],
    predicted_states: dict[int, tuple[float, ...]],
    last_classes: dict[int, int],
    tracking_mode: str,
    dt: float,
    next_track_id: int,
) -> tuple[list[dict], set[int], int]:
    assigned_tracks: set[int] = set()
    assigned_detections: list[dict] = []

    for detection in detections:
        center_x, center_y = EnsembleDetector.center_of_box(detection["box"])
        cls_id = detection["cls"]
        best_track_id = None
        best_distance = TRACK_MATCH_DISTANCE

        for track_id, predicted_state in predicted_states.items():
            if track_id in assigned_tracks:
                continue
            if last_classes.get(track_id, cls_id) != cls_id:
                continue
            pred_x, pred_y = get_predicted_xy(predicted_state)
            distance = float(np.hypot(center_x - pred_x, center_y - pred_y))
            if distance < best_distance:
                best_distance = distance
                best_track_id = track_id

        if best_track_id is None:
            best_track_id = next_track_id
            next_track_id += 1
            tracker = initialize_tracker(tracking_mode, dt, center_x, center_y)
            trackers[best_track_id] = tracker
            predicted_states[best_track_id] = tracker.get_state()

        assigned_tracks.add(best_track_id)
        assigned_detection = dict(detection)
        assigned_detection["track_id"] = best_track_id
        assigned_detection["center_x"] = float(center_x)
        assigned_detection["center_y"] = float(center_y)
        assigned_detections.append(assigned_detection)

    return assigned_detections, assigned_tracks, next_track_id


def main() -> None:
    args = parse_args()
    run_dir, output_json_path, output_csv_path = resolve_output_paths(args)
    scenario_name = infer_scenario_name(args)
    coco_annotation_path = resolve_coco_annotation_path(args.gt_coco, args.gt_folder)
    gt_map = load_ground_truth(args.gt_csv)
    gt_track_map: dict[int, list[dict]] = {}
    gt_has_track_ids = False
    if coco_annotation_path is not None:
        gt_map = load_ground_truth_coco(str(coco_annotation_path))
        gt_track_map, gt_has_track_ids = load_ground_truth_track_map_coco(str(coco_annotation_path))
    occlusion_intervals = load_occlusion_intervals(args.occlusion_json, scenario_name, args.source)

    cap = open_capture(args.source)
    screen_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1280.0
    screen_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720.0
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if gt_map and args.gt_align == "uniform":
        gt_map = remap_gt_frames_uniform(gt_map, total_video_frames)

    detector = EnsembleDetector(
        primary_model_path=args.primary_model,
        secondary_model_path=args.secondary_model,
        conf_threshold=args.conf,
        detector_mode=args.detector_mode,
        fuse_iou_threshold=args.fuse_iou_threshold,
    )

    effective_fps = fps if fps and fps > 1e-6 else 30.0
    sampled_fps = effective_fps
    if gt_map and total_video_frames > 0:
        sampled_fps = effective_fps * (len(gt_map) / total_video_frames)
        sampled_fps = max(sampled_fps, 1e-6)
    dt = 1.0 / sampled_fps
    total_processed_frames = len(gt_map) if gt_map else (total_video_frames if total_video_frames > 0 else None)
    progress_label = f"[eval {infer_experiment_name(args)}/{scenario_name}/{sanitize_name(args.run_name)}]"
    progress_start = time.perf_counter()
    last_progress_update = progress_start

    radar = VirtualRadar(
        fps=sampled_fps,
        initial_z=args.radar_initial_z,
        target_speed=args.radar_target_speed,
    )
    matrix_controller = Matrix8x8Controller(matrix_width=8, matrix_height=8)
    scheduler = HoldTimeBoxScheduler(hold_time_frames=args.hold_time_frames if args.control_mode == "hold" else 0)
    max_missed_frames = max(1, int(round(sampled_fps * args.track_hold_seconds)))

    trackers: dict[int, Any] = {}
    last_seen_frames: dict[int, int] = {}
    last_classes: dict[int, int] = {}
    last_depths: dict[int, float] = {}
    predicted_states: dict[int, tuple[float, ...]] = {}
    next_track_id = 1
    video_frame_index = 0
    processed_frame_index = 0

    total_processing_times_ms: list[float] = []
    detection_times_ms: list[float] = []
    fusion_times_ms: list[float] = []
    raw_jitter_px: list[float] = []
    smooth_jitter_px: list[float] = []
    raw_centers: list[tuple[float, float]] = []
    smooth_centers: list[tuple[float, float]] = []
    serial_box_changes = 0
    predicted_only_frames = 0
    active_target_frames = 0
    mode_switch_count = 0
    adaptive_z_only_frames = 0
    low_conf_frame_count = 0
    consecutive_low_conf_frames = 0
    consecutive_prediction_only_frames = 0
    current_active_track_id: int | None = None
    last_switch_frame_index = -10**9

    rmse_x_errors: list[float] = []
    rmse_y_errors: list[float] = []
    rmse_z_errors: list[float] = []
    dark_box_ious: list[float] = []
    glare_success_flags: list[int] = []
    gt_present_frames = 0
    gt_present_but_no_box = 0
    false_darkening_frames = 0
    predicted_dark_frames = 0
    occlusion_gt_frames = 0
    occlusion_gt_present_but_no_box = 0
    occlusion_false_darkening_frames = 0
    occlusion_predicted_dark_frames = 0
    occlusion_dark_box_ious: list[float] = []
    occlusion_glare_success_flags: list[int] = []
    occlusion_rmse_x_errors: list[float] = []
    occlusion_rmse_y_errors: list[float] = []
    occlusion_rmse_z_errors: list[float] = []
    id_pair_counts: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    idf1_total_gt_detections = 0
    idf1_total_pred_detections = 0

    last_command: str | None = None
    per_frame_rows: list[dict[str, object]] = []

    try:
        while True:
            frame_start = time.perf_counter()
            ret, frame = cap.read()
            if not ret:
                break

            video_frame_index += 1
            if gt_map and video_frame_index not in gt_map:
                continue

            processed_frame_index += 1
            z_radar = radar.get_distance(processed_frame_index)
            smoothed_vehicles: list[tuple[int, float, float, float, int]] = []
            assigned_tracks: set[int] = set()
            gt = gt_map.get(video_frame_index)
            gt_center: tuple[float, float] | None = None
            if gt is not None:
                gt_center = ((gt["x1"] + gt["x2"]) * 0.5, (gt["y1"] + gt["y2"]) * 0.5)

            use_tracker = args.tracking_mode != "raw"
            use_3d = args.tracking_mode == "kf3d"
            if use_tracker:
                for track_id, tracker in list(trackers.items()):
                    missed_count = processed_frame_index - last_seen_frames.get(track_id, processed_frame_index)
                    if missed_count > max_missed_frames:
                        trackers.pop(track_id, None)
                        last_seen_frames.pop(track_id, None)
                        last_classes.pop(track_id, None)
                        last_depths.pop(track_id, None)
                        predicted_states.pop(track_id, None)
                        continue
                    predicted_states[track_id] = tracker.predict()
                if current_active_track_id is not None and current_active_track_id not in trackers:
                    current_active_track_id = None

            detect_start = time.perf_counter()
            fused_detections = detector.detect(frame)
            detection_times_ms.append((time.perf_counter() - detect_start) * 1000.0)
            assigned_detections: list[dict] = []
            predicted_objects_for_idf1: list[dict] = []
            best_conf_per_frame = max((float(det["conf"]) for det in fused_detections), default=None)

            if use_tracker:
                assigned_detections, assigned_tracks, next_track_id = assign_tracks_generic(
                    detections=fused_detections,
                    trackers=trackers,
                    predicted_states=predicted_states,
                    last_classes=last_classes,
                    tracking_mode=args.tracking_mode,
                    dt=dt,
                    next_track_id=next_track_id,
                )
            else:
                for detection in fused_detections:
                    assigned_detection = dict(detection)
                    assigned_detection["center_x"], assigned_detection["center_y"] = EnsembleDetector.center_of_box(
                        detection["box"]
                    )
                    assigned_detections.append(assigned_detection)

            switch_conf_per_frame = best_conf_per_frame
            switch_active_track_missing = False
            if (
                args.switch_policy in ("active_track_conf_or_missing", "low_conf_pred_or_missing")
                and use_tracker
                and current_active_track_id is not None
            ):
                active_track_detection = next(
                    (det for det in assigned_detections if int(det["track_id"]) == current_active_track_id),
                    None,
                )
                if active_track_detection is not None:
                    switch_conf_per_frame = float(active_track_detection["conf"])
                else:
                    switch_conf_per_frame = None
                    switch_active_track_missing = True

            low_conf_condition = bool(
                switch_conf_per_frame is not None
                and switch_conf_per_frame < args.tau_conf
            )
            prediction_only_guard_passed = (
                consecutive_prediction_only_frames >= max(0, int(args.adaptive_min_prediction_only_frames))
            )
            cooldown_guard_passed = (
                processed_frame_index - last_switch_frame_index > max(0, int(args.adaptive_switch_cooldown_frames))
            )

            policy_triggered = False
            if args.switch_policy == "best_conf":
                policy_triggered = low_conf_condition
            elif args.switch_policy == "active_track_conf_or_missing":
                policy_triggered = low_conf_condition or switch_active_track_missing
            elif args.switch_policy == "low_conf_pred_or_missing":
                policy_triggered = low_conf_condition and (prediction_only_guard_passed or switch_active_track_missing)

            low_conf_candidate_frame = bool(
                args.tracking_mode == "kf3d"
                and args.observation_mode == "adaptive"
                and policy_triggered
            )
            if low_conf_candidate_frame:
                low_conf_frame_count += 1
                consecutive_low_conf_frames += 1
            else:
                consecutive_low_conf_frames = 0
            frame_should_use_z_only = bool(
                args.tracking_mode == "kf3d"
                and args.observation_mode == "adaptive"
                and consecutive_low_conf_frames >= max(1, int(args.adaptive_min_low_conf_frames))
                and cooldown_guard_passed
            )

            fusion_start = time.perf_counter()
            raw_active_center: tuple[float, float] | None = None
            smooth_active_center: tuple[float, float] | None = None
            active_target: tuple[int, float, float, float, int] | None = None
            frame_observation_mode = "raw"
            active_detection_conf: float | None = None
            frame_used_adaptive_z_only = False

            if use_tracker:
                for detection in assigned_detections:
                    best_track_id = int(detection["track_id"])
                    center_x = float(detection["center_x"])
                    center_y = float(detection["center_y"])
                    cls_id = int(detection["cls"])
                    conf_score = float(detection["conf"])
                    tracker = trackers[best_track_id]
                    depth_from_box = estimate_depth_from_box_width(detection["box"])
                    last_depths[best_track_id] = depth_from_box

                    if args.tracking_mode == "kf2d":
                        sx, sy = tracker.update(center_x, center_y, predict_first=False)
                        sz = depth_from_box
                        obs_mode = "xy"
                    else:
                        use_z_only = frame_should_use_z_only
                        if use_z_only:
                            sx, sy, sz = tracker.update(None, None, z_radar, predict_first=False)
                            frame_used_adaptive_z_only = True
                            obs_mode = "z_only"
                        else:
                            sx, sy, sz = tracker.update(center_x, center_y, z_radar, predict_first=False)
                            obs_mode = "full"

                    last_seen_frames[best_track_id] = processed_frame_index
                    last_classes[best_track_id] = cls_id
                    frame_observation_mode = obs_mode if frame_observation_mode == "raw" else frame_observation_mode

                    smoothed_vehicles.append((best_track_id, float(sx), float(sy), float(sz), cls_id))
                    predicted_objects_for_idf1.append(
                        {
                            "track_id": best_track_id,
                            "cls": cls_id,
                            "box": np.array(detection["box"], dtype=np.float64),
                        }
                    )

                frame_has_prediction_only = False
                for track_id, tracker in trackers.items():
                    if track_id in assigned_tracks:
                        continue

                    missed_count = processed_frame_index - last_seen_frames.get(track_id, processed_frame_index)
                    if missed_count <= max_missed_frames:
                        if args.tracking_mode == "kf2d":
                            sx, sy = tracker.update(None, None, predict_first=False)
                            sz = last_depths.get(track_id, z_radar)
                        else:
                            sx, sy, sz = tracker.update(None, None, z_radar, predict_first=False)
                        cls_id = last_classes.get(track_id, -1)
                        smoothed_vehicles.append((track_id, float(sx), float(sy), float(sz), cls_id))
                        frame_has_prediction_only = True
                        frame_observation_mode = "prediction_only"

                if frame_has_prediction_only:
                    predicted_only_frames += 1
            else:
                for detection_index, detection in enumerate(assigned_detections, start=1):
                    center_x = float(detection["center_x"])
                    center_y = float(detection["center_y"])
                    cls_id = int(detection["cls"])
                    meas_z = estimate_depth_from_box_width(detection["box"])
                    smoothed_vehicles.append((detection_index, center_x, center_y, meas_z, cls_id))
                    predicted_objects_for_idf1.append(
                        {
                            "track_id": int((processed_frame_index * 100000) + detection_index),
                            "cls": cls_id,
                            "box": np.array(detection["box"], dtype=np.float64),
                        }
                    )

            if assigned_detections:
                if gt_center is not None:
                    best_detection = min(
                        assigned_detections,
                        key=lambda item: euclidean_distance((float(item["center_x"]), float(item["center_y"])), gt_center),
                    )
                else:
                    best_detection = max(assigned_detections, key=lambda item: item["conf"])
                raw_active_center = (float(best_detection["center_x"]), float(best_detection["center_y"]))
                active_detection_conf = float(best_detection["conf"])

            if frame_used_adaptive_z_only:
                adaptive_z_only_frames += 1
                mode_switch_count += 1
                last_switch_frame_index = processed_frame_index

            active_command_pre_hold: str | None = None
            if smoothed_vehicles:
                if gt_center is not None:
                    active_target = min(
                        smoothed_vehicles,
                        key=lambda item: euclidean_distance((float(item[1]), float(item[2])), gt_center),
                    )
                else:
                    active_target = min(smoothed_vehicles, key=lambda item: item[3])
                _, smooth_x, smooth_y, smooth_z, _ = active_target
                smooth_active_center = (float(smooth_x), float(smooth_y))
                active_target_frames += 1
                if use_tracker:
                    current_active_track_id = int(active_target[0])
                active_command_pre_hold = matrix_controller.get_dark_box(
                    smooth_x=smooth_x,
                    smooth_y=smooth_y,
                    smooth_z=smooth_z,
                    screen_width=screen_width,
                    screen_height=screen_height,
                )

            active_command = scheduler.apply(active_command_pre_hold, processed_frame_index)
            fusion_times_ms.append((time.perf_counter() - fusion_start) * 1000.0)

            if frame_observation_mode == "prediction_only":
                consecutive_prediction_only_frames += 1
            else:
                consecutive_prediction_only_frames = 0

            if raw_active_center is not None:
                raw_centers.append(raw_active_center)
                if len(raw_centers) >= 2:
                    raw_jitter_px.append(euclidean_distance(raw_centers[-1], raw_centers[-2]))

            if smooth_active_center is not None:
                smooth_centers.append(smooth_active_center)
                if len(smooth_centers) >= 2:
                    smooth_jitter_px.append(euclidean_distance(smooth_centers[-1], smooth_centers[-2]))

            if active_command != last_command:
                serial_box_changes += 1
                last_command = active_command

            gt_matrix_box = None
            if gt is not None:
                gt_present_frames += 1
                frame_is_occlusion = is_frame_in_intervals(video_frame_index, occlusion_intervals)
                if frame_is_occlusion:
                    occlusion_gt_frames += 1
                gt_center_x = (gt["x1"] + gt["x2"]) * 0.5
                gt_center_y = (gt["y1"] + gt["y2"]) * 0.5
                gt_z = gt["z"] if gt["z"] is not None else (active_target[3] if active_target is not None else z_radar)
                gt_box_cmd = matrix_controller.get_dark_box(
                    smooth_x=gt_center_x,
                    smooth_y=gt_center_y,
                    smooth_z=gt_z,
                    screen_width=screen_width,
                    screen_height=screen_height,
                )
                gt_matrix_box = matrix_box_to_tuple(gt_box_cmd)

                if smooth_active_center is not None:
                    error_x = smooth_active_center[0] - gt_center_x
                    error_y = smooth_active_center[1] - gt_center_y
                    rmse_x_errors.append(error_x)
                    rmse_y_errors.append(error_y)
                    if frame_is_occlusion:
                        occlusion_rmse_x_errors.append(error_x)
                        occlusion_rmse_y_errors.append(error_y)
                    if gt["z"] is not None and active_target is not None:
                        error_z = active_target[3] - float(gt["z"])
                        rmse_z_errors.append(error_z)
                        if frame_is_occlusion:
                            occlusion_rmse_z_errors.append(error_z)

                pred_matrix_box = matrix_box_to_tuple(active_command)
                iou = discrete_box_iou(pred_matrix_box, gt_matrix_box)
                dark_box_ious.append(iou)
                glare_success = 1 if iou >= args.gssr_iou_threshold else 0
                glare_success_flags.append(glare_success)
                if frame_is_occlusion:
                    occlusion_dark_box_ious.append(iou)
                    occlusion_glare_success_flags.append(glare_success)

                if pred_matrix_box is not None:
                    predicted_dark_frames += 1
                    if gt_matrix_box is None or iou < args.gssr_iou_threshold:
                        false_darkening_frames += 1
                    if frame_is_occlusion:
                        occlusion_predicted_dark_frames += 1
                        if gt_matrix_box is None or iou < args.gssr_iou_threshold:
                            occlusion_false_darkening_frames += 1

                if gt_matrix_box is not None and pred_matrix_box is None:
                    gt_present_but_no_box += 1
                    if frame_is_occlusion:
                        occlusion_gt_present_but_no_box += 1
            else:
                frame_is_occlusion = is_frame_in_intervals(video_frame_index, occlusion_intervals)

            gt_track_objects = gt_track_map.get(video_frame_index, [])
            if gt_has_track_ids and gt_track_objects:
                idf1_total_gt_detections += len(gt_track_objects)
                idf1_total_pred_detections += len(predicted_objects_for_idf1)
                id_matches = greedy_match_iou(predicted_objects_for_idf1, gt_track_objects, args.gssr_iou_threshold)
                for pred_index, gt_index in id_matches:
                    pred_track_id = int(predicted_objects_for_idf1[pred_index]["track_id"])
                    gt_track_id = int(gt_track_objects[gt_index]["track_id"])
                    id_pair_counts[pred_track_id][gt_track_id] += 1

            total_processing_times_ms.append((time.perf_counter() - frame_start) * 1000.0)
            per_frame_rows.append(
                {
                    "frame": processed_frame_index,
                    "video_frame": video_frame_index,
                    "processed_frame": processed_frame_index,
                    "is_occlusion_frame": int(frame_is_occlusion),
                    "observation_mode": frame_observation_mode,
                    "best_conf_per_frame": None if best_conf_per_frame is None else round(best_conf_per_frame, 6),
                    "switch_conf_per_frame": None if switch_conf_per_frame is None else round(switch_conf_per_frame, 6),
                    "switch_active_track_missing": int(switch_active_track_missing),
                    "active_detection_conf": None if active_detection_conf is None else round(active_detection_conf, 6),
                    "tau_conf": round(args.tau_conf, 6),
                    "consecutive_low_conf_frames": consecutive_low_conf_frames,
                    "consecutive_prediction_only_frames": consecutive_prediction_only_frames,
                    "prediction_only_guard_passed": int(prediction_only_guard_passed),
                    "cooldown_guard_passed": int(cooldown_guard_passed),
                    "low_conf_candidate_frame": int(low_conf_candidate_frame),
                    "frame_should_use_z_only": int(frame_should_use_z_only),
                    "z_radar": round(z_radar, 4),
                    "num_detections": len(fused_detections),
                    "num_tracks": len(trackers),
                    "has_active_target": int(active_target is not None),
                    "raw_center_x": None if raw_active_center is None else round(raw_active_center[0], 4),
                    "raw_center_y": None if raw_active_center is None else round(raw_active_center[1], 4),
                    "smooth_center_x": None if smooth_active_center is None else round(smooth_active_center[0], 4),
                    "smooth_center_y": None if smooth_active_center is None else round(smooth_active_center[1], 4),
                    "smooth_z": None if active_target is None else round(active_target[3], 4),
                    "command_pre_hold": active_command_pre_hold.strip() if active_command_pre_hold is not None else "BOX:-1:-1:-1:-1",
                    "command": active_command.strip() if active_command is not None else "BOX:-1:-1:-1:-1",
                    "gt_present": int(gt is not None),
                    "predicted_dark": int(matrix_box_to_tuple(active_command) is not None),
                    "gt_box_iou": None if gt_matrix_box is None else round(dark_box_ious[-1], 4),
                    "glare_success": None if gt_matrix_box is None else glare_success_flags[-1],
                }
            )

            if args.progress:
                now = time.perf_counter()
                should_refresh = (
                    processed_frame_index == 1
                    or total_processed_frames == processed_frame_index
                    or (now - last_progress_update) >= 1.0
                )
                if should_refresh:
                    sys.stdout.write(
                        build_progress_line(
                            label=progress_label,
                            completed=processed_frame_index,
                            total=total_processed_frames,
                            elapsed_seconds=now - progress_start,
                        )
                    )
                    sys.stdout.flush()
                    last_progress_update = now
    finally:
        cap.release()

    if args.progress and processed_frame_index > 0:
        sys.stdout.write(
            build_progress_line(
                label=progress_label,
                completed=processed_frame_index,
                total=total_processed_frames,
                elapsed_seconds=time.perf_counter() - progress_start,
            )
        )
        sys.stdout.write("\n")
        sys.stdout.flush()

    raw_jitter_mean = safe_mean(raw_jitter_px)
    smooth_jitter_mean = safe_mean(smooth_jitter_px)
    jitter_reduction_percent = 0.0
    if raw_jitter_mean > 1e-9:
        jitter_reduction_percent = ((raw_jitter_mean - smooth_jitter_mean) / raw_jitter_mean) * 100.0

    metrics: dict[str, Any] = {
        "experiment_name": infer_experiment_name(args),
        "scenario_name": infer_scenario_name(args),
        "run_name": sanitize_name(args.run_name),
        "run_dir": str(run_dir),
        "source": args.source,
        "detector_mode": args.detector_mode,
        "tracking_mode": args.tracking_mode,
        "observation_mode": args.observation_mode,
        "control_mode": args.control_mode,
        "tau_conf": args.tau_conf,
        "adaptive_min_low_conf_frames": args.adaptive_min_low_conf_frames,
        "switch_policy": args.switch_policy,
        "adaptive_min_prediction_only_frames": args.adaptive_min_prediction_only_frames,
        "adaptive_switch_cooldown_frames": args.adaptive_switch_cooldown_frames,
        "fuse_iou_threshold": args.fuse_iou_threshold,
        "hold_time_frames": args.hold_time_frames if args.control_mode == "hold" else 0,
        "gt_coco_source": None if coco_annotation_path is None else str(coco_annotation_path),
        "occlusion_json": args.occlusion_json,
        "occlusion_interval_count": len(occlusion_intervals),
        "gt_has_track_ids": gt_has_track_ids,
        "video_frames_seen": video_frame_index,
        "frames_processed": processed_frame_index,
        "effective_video_fps": effective_fps,
        "evaluated_fps": round(sampled_fps, 4),
        "avg_detection_time_ms": round(safe_mean(detection_times_ms), 4),
        "avg_fusion_time_ms": round(safe_mean(fusion_times_ms), 4),
        "avg_total_latency_ms": round(safe_mean(total_processing_times_ms), 4),
        "estimated_pipeline_fps": round(1000.0 / safe_mean(total_processing_times_ms), 4) if total_processing_times_ms else 0.0,
        "active_target_rate_percent": round((active_target_frames / processed_frame_index) * 100.0, 4) if processed_frame_index else 0.0,
        "predicted_only_frame_ratio_percent": round((predicted_only_frames / processed_frame_index) * 100.0, 4) if processed_frame_index else 0.0,
        "adaptive_z_only_frame_ratio_percent": round((adaptive_z_only_frames / processed_frame_index) * 100.0, 4) if processed_frame_index else 0.0,
        "low_conf_candidate_frame_ratio_percent": round((low_conf_frame_count / processed_frame_index) * 100.0, 4) if processed_frame_index else 0.0,
        "low_conf_candidate_frames": low_conf_frame_count,
        "mode_switch_count": mode_switch_count,
        "avg_raw_jitter_px": round(raw_jitter_mean, 4),
        "avg_smooth_jitter_px": round(smooth_jitter_mean, 4),
        "jitter_reduction_percent": round(jitter_reduction_percent, 4),
        "box_command_change_rate_percent": round((serial_box_changes / processed_frame_index) * 100.0, 4) if processed_frame_index else 0.0,
        "box_command_changes": serial_box_changes,
    }

    if gt_present_frames > 0:
        multi_target_idf1 = compute_multi_target_idf1(id_pair_counts, idf1_total_gt_detections, idf1_total_pred_detections)
        metrics.update(
            {
                "gt_frames": gt_present_frames,
                "rmse_x_px": round(rms(rmse_x_errors), 4),
                "rmse_y_px": round(rms(rmse_y_errors), 4),
                "rmse_xy_px": round(math.sqrt((rms(rmse_x_errors) ** 2 + rms(rmse_y_errors) ** 2) / 2.0), 4),
                "rmse_z_m": round(rms(rmse_z_errors), 4) if rmse_z_errors else None,
                "avg_dark_box_iou": round(safe_mean(dark_box_ious), 4),
                "gssr_percent": round((sum(glare_success_flags) / gt_present_frames) * 100.0, 4),
                "idf1_percent": None if multi_target_idf1 is None else round(multi_target_idf1 * 100.0, 4),
                "idf1_mode": "multi_target",
                "idf1_status": "ok" if multi_target_idf1 is not None else "unavailable_missing_gt_track_ids",
                "missed_glare_rate_percent": round((gt_present_but_no_box / gt_present_frames) * 100.0, 4),
                "false_darkening_rate_percent": round((false_darkening_frames / gt_present_frames) * 100.0, 4),
                "dark_box_precision_percent": round((sum(glare_success_flags) / predicted_dark_frames) * 100.0, 4) if predicted_dark_frames else 0.0,
                "gssr_iou_threshold": args.gssr_iou_threshold,
            }
        )
        if occlusion_gt_frames > 0:
            metrics.update(
                {
                    "occlusion_gt_frames": occlusion_gt_frames,
                    "occlusion_frame_ratio_percent": round((occlusion_gt_frames / gt_present_frames) * 100.0, 4),
                    "occlusion_rmse_x_px": round(rms(occlusion_rmse_x_errors), 4),
                    "occlusion_rmse_y_px": round(rms(occlusion_rmse_y_errors), 4),
                    "occlusion_rmse_xy_px": round(
                        math.sqrt((rms(occlusion_rmse_x_errors) ** 2 + rms(occlusion_rmse_y_errors) ** 2) / 2.0),
                        4,
                    ),
                    "occlusion_rmse_z_m": round(rms(occlusion_rmse_z_errors), 4) if occlusion_rmse_z_errors else None,
                    "occlusion_avg_dark_box_iou": round(safe_mean(occlusion_dark_box_ious), 4),
                    "occlusion_gssr_percent": round((sum(occlusion_glare_success_flags) / occlusion_gt_frames) * 100.0, 4),
                    "occlusion_missed_glare_rate_percent": round(
                        (occlusion_gt_present_but_no_box / occlusion_gt_frames) * 100.0,
                        4,
                    ),
                    "occlusion_false_darkening_rate_percent": round(
                        (occlusion_false_darkening_frames / occlusion_gt_frames) * 100.0,
                        4,
                    ),
                    "occlusion_dark_box_precision_percent": round(
                        (sum(occlusion_glare_success_flags) / occlusion_predicted_dark_frames) * 100.0,
                        4,
                    )
                    if occlusion_predicted_dark_frames
                    else 0.0,
                }
            )

    config_payload = {
        "source": args.source,
        "primary_model": args.primary_model,
        "secondary_model": args.secondary_model,
        "detector_mode": args.detector_mode,
        "tracking_mode": args.tracking_mode,
        "observation_mode": args.observation_mode,
        "control_mode": args.control_mode,
        "tau_conf": args.tau_conf,
        "adaptive_min_low_conf_frames": args.adaptive_min_low_conf_frames,
        "hold_time_frames": args.hold_time_frames,
        "track_hold_seconds": args.track_hold_seconds,
        "radar_initial_z": args.radar_initial_z,
        "radar_target_speed": args.radar_target_speed,
        "fuse_iou_threshold": args.fuse_iou_threshold,
        "gt_csv": args.gt_csv,
        "gt_coco": args.gt_coco,
        "gt_folder": args.gt_folder,
        "gt_align": args.gt_align,
        "occlusion_json": args.occlusion_json,
        "occlusion_intervals": [{"start": start, "end": end} for start, end in occlusion_intervals],
        "gssr_iou_threshold": args.gssr_iou_threshold,
    }

    (run_dir / "config.json").write_text(json.dumps(config_payload, indent=2), encoding="utf-8")
    output_json_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    with output_csv_path.open("w", encoding="utf-8", newline="") as f:
        if per_frame_rows:
            writer = csv.DictWriter(f, fieldnames=list(per_frame_rows[0].keys()))
            writer.writeheader()
            writer.writerows(per_frame_rows)

    print(json.dumps(metrics, indent=2))
    print(f"Saved summary to: {output_json_path}")
    print(f"Saved per-frame metrics to: {output_csv_path}")


if __name__ == "__main__":
    main()

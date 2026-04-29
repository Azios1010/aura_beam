"""
Danh gia ensemble bang evaluator custom.

Script nay chuyen dung cho mo hinh gop 2 model YOLO, co ho tro confidence sweep
de tim nguong dep nhat theo metric mong muon.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from aura_beam.detector_ensemble import EnsembleDetector


def canonicalize_class_name(name: str) -> str:
    normalized = name.strip().lower().replace("-", "_").replace(" ", "_")
    alias_map = {
        "head_light": "head_light",
        "headlight": "head_light",
        "front_light": "head_light",
        "car_front": "head_light",
        "front_car": "head_light",
        "rear_light": "rear_light",
        "rearlight": "rear_light",
        "back_light": "rear_light",
        "car_rear": "rear_light",
        "rear_car": "rear_light",
    }
    return alias_map.get(normalized, normalized)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate ensemble on a Roboflow COCO folder")
    parser.add_argument("--primary-model", type=str, default="model/yolov5.pt")
    parser.add_argument("--secondary-model", type=str, default="model/model_ai.pt")
    parser.add_argument("--gt-folder", type=str, required=True)
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence fallback")
    parser.add_argument("--iou-threshold", type=float, default=0.5)
    parser.add_argument(
        "--conf-sweep",
        type=str,
        default="0.05,0.10,0.15,0.20,0.25,0.30,0.35,0.40",
        help="Danh sach confidence cach nhau boi dau phay",
    )
    parser.add_argument(
        "--optimize",
        type=str,
        default="map50",
        choices=("map50", "f1", "recall"),
        help="Metric chon confidence tot nhat",
    )
    parser.add_argument("--output-json", type=str, default="artifacts/metrics/ensemble_metrics.json")
    parser.add_argument("--output-csv", type=str, default="artifacts/metrics/ensemble_per_class.csv")
    return parser.parse_args()


def load_coco_dataset(gt_folder: str) -> tuple[list[dict], dict[int, list[dict]], list[str]]:
    folder_path = Path(gt_folder)
    coco_path = folder_path / "_annotations.coco.json"
    if not coco_path.exists():
        raise FileNotFoundError(f"Khong tim thay file COCO: {coco_path}")

    coco = json.loads(coco_path.read_text(encoding="utf-8"))
    image_infos = coco.get("images", [])
    annotations = coco.get("annotations", [])
    categories = coco.get("categories", [])

    category_id_to_name = {
        int(category["id"]): canonicalize_class_name(str(category["name"]))
        for category in categories
        if int(category["id"]) > 0
    }

    annotations_by_image: dict[int, list[dict]] = {}
    for ann in annotations:
        bbox = ann.get("bbox", [])
        if len(bbox) != 4:
            continue
        class_name = category_id_to_name.get(int(ann["category_id"]))
        if class_name is None:
            continue

        x1, y1, width, height = map(float, bbox)
        annotations_by_image.setdefault(int(ann["image_id"]), []).append(
            {
                "bbox": np.array([x1, y1, x1 + width, y1 + height], dtype=np.float64),
                "cls_name": class_name,
            }
        )

    valid_class_names = sorted(set(category_id_to_name.values()))
    return image_infos, annotations_by_image, valid_class_names


def resolve_image_path(gt_folder: str, image_info: dict) -> Path:
    folder_path = Path(gt_folder)
    candidates = [
        folder_path / image_info.get("file_name", ""),
        folder_path / image_info.get("extra", {}).get("name", ""),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Khong tim thay file anh cho image_id={image_info.get('id')}")


def compute_iou(box_a: np.ndarray, box_b: np.ndarray) -> float:
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


def compute_ap(recalls: list[float], precisions: list[float]) -> float:
    if not recalls or not precisions:
        return 0.0

    recall_points = np.array([0.0] + recalls + [1.0], dtype=np.float64)
    precision_points = np.array([0.0] + precisions + [0.0], dtype=np.float64)
    for idx in range(len(precision_points) - 2, -1, -1):
        precision_points[idx] = max(precision_points[idx], precision_points[idx + 1])

    changing_points = np.where(recall_points[1:] != recall_points[:-1])[0]
    ap = np.sum(
        (recall_points[changing_points + 1] - recall_points[changing_points]) * precision_points[changing_points + 1]
    )
    return float(ap)


def compute_f1(precision: float, recall: float) -> float:
    if precision + recall <= 1e-12:
        return 0.0
    return 2.0 * precision * recall / (precision + recall)


def parse_conf_sweep(conf_sweep: str) -> list[float]:
    values = []
    for part in conf_sweep.split(","):
        stripped = part.strip()
        if not stripped:
            continue
        value = float(stripped)
        if 0.0 <= value <= 1.0:
            values.append(value)
    if not values:
        values = [0.25]
    return sorted(set(values))


def run_single_model(model, image, conf_threshold: float, model_name: str) -> list[dict]:
    detections: list[dict] = []
    results = model.predict(image, conf=conf_threshold, verbose=False)
    if not results or results[0].boxes is None:
        return detections

    boxes = results[0].boxes
    xyxy = boxes.xyxy.cpu().numpy() if boxes.xyxy is not None else np.empty((0, 4), dtype=np.float32)
    classes = boxes.cls.int().cpu().tolist() if boxes.cls is not None else []
    confs = boxes.conf.cpu().tolist() if boxes.conf is not None else []

    for box, cls_id, conf in zip(xyxy, classes, confs):
        detections.append(
            {"box": box.astype(np.float64), "cls": int(cls_id), "conf": float(conf), "source": model_name}
        )
    return detections


def remap_predictions_to_canonical(predictions: list[dict], model_names: dict[int, str]) -> list[dict]:
    remapped: list[dict] = []
    for pred in predictions:
        cls_id = int(pred["cls"])
        remapped.append(
            {
                **pred,
                "cls_name": canonicalize_class_name(str(model_names.get(cls_id, cls_id))),
            }
        )
    return remapped


def evaluate_ensemble(
    detector: EnsembleDetector,
    image_infos: list[dict],
    annotations_by_image: dict[int, list[dict]],
    valid_class_names: list[str],
    gt_folder: str,
    conf_threshold: float,
    iou_threshold: float,
) -> tuple[dict[str, float], list[dict[str, object]]]:
    stats_by_class: dict[str, dict[str, object]] = {
        cls_name: {"num_gt": 0, "predictions": []}
        for cls_name in valid_class_names
    }

    total_inference_time = 0.0
    total_images = 0

    for image_info in image_infos:
        image_id = int(image_info["id"])
        image_path = resolve_image_path(gt_folder, image_info)
        image = cv2.imread(str(image_path))
        if image is None:
            continue

        total_images += 1
        gt_objects = annotations_by_image.get(image_id, [])
        gt_by_class: dict[str, list[np.ndarray]] = {cls_name: [] for cls_name in valid_class_names}
        for gt in gt_objects:
            gt_by_class[str(gt["cls_name"])].append(gt["bbox"])
            stats_by_class[str(gt["cls_name"])]["num_gt"] += 1

        infer_start = time.perf_counter()
        primary_dets = run_single_model(detector.primary_model, image, conf_threshold, "primary")
        secondary_dets = run_single_model(detector.secondary_model, image, conf_threshold, "secondary")
        predictions = detector._fuse_model_detections(primary_dets, secondary_dets)
        predictions = remap_predictions_to_canonical(predictions, detector.secondary_model.names)
        total_inference_time += time.perf_counter() - infer_start

        preds_by_class: dict[str, list[dict]] = {cls_name: [] for cls_name in valid_class_names}
        for pred in predictions:
            if pred["cls_name"] in preds_by_class:
                preds_by_class[str(pred["cls_name"])].append(pred)

        for cls_name in valid_class_names:
            gt_boxes = gt_by_class[cls_name]
            gt_used = [False] * len(gt_boxes)
            preds_sorted = sorted(preds_by_class[cls_name], key=lambda item: float(item["conf"]), reverse=True)

            for pred in preds_sorted:
                best_iou = 0.0
                best_gt_index = -1
                for gt_index, gt_box in enumerate(gt_boxes):
                    if gt_used[gt_index]:
                        continue
                    iou = compute_iou(pred["box"], gt_box)
                    if iou > best_iou:
                        best_iou = iou
                        best_gt_index = gt_index

                is_true_positive = 0
                if best_gt_index >= 0 and best_iou >= iou_threshold:
                    gt_used[best_gt_index] = True
                    is_true_positive = 1

                stats_by_class[cls_name]["predictions"].append(
                    {"conf": float(pred["conf"]), "tp": is_true_positive, "fp": 1 - is_true_positive}
                )

    per_class_rows: list[dict[str, object]] = []
    class_precisions: list[float] = []
    class_recalls: list[float] = []
    class_aps: list[float] = []
    total_tp = 0
    total_fp = 0
    total_gt = 0

    for cls_name in valid_class_names:
        num_gt = int(stats_by_class[cls_name]["num_gt"])
        predictions = sorted(stats_by_class[cls_name]["predictions"], key=lambda item: item["conf"], reverse=True)

        cumulative_tp = 0
        cumulative_fp = 0
        recalls: list[float] = []
        precisions: list[float] = []

        for pred in predictions:
            cumulative_tp += int(pred["tp"])
            cumulative_fp += int(pred["fp"])
            recall = cumulative_tp / num_gt if num_gt else 0.0
            precision = cumulative_tp / (cumulative_tp + cumulative_fp) if (cumulative_tp + cumulative_fp) else 0.0
            recalls.append(recall)
            precisions.append(precision)

        ap50 = compute_ap(recalls, precisions)
        final_tp = sum(int(pred["tp"]) for pred in predictions)
        final_fp = sum(int(pred["fp"]) for pred in predictions)
        final_precision = final_tp / (final_tp + final_fp) if (final_tp + final_fp) else 0.0
        final_recall = final_tp / num_gt if num_gt else 0.0

        total_tp += final_tp
        total_fp += final_fp
        total_gt += num_gt
        class_precisions.append(final_precision)
        class_recalls.append(final_recall)
        class_aps.append(ap50)

        per_class_rows.append(
            {
                "class_name": cls_name,
                "num_gt": num_gt,
                "precision": round(final_precision, 4),
                "recall": round(final_recall, 4),
                "ap50": round(ap50, 4),
            }
        )

    macro_precision = float(np.mean(class_precisions)) if class_precisions else 0.0
    macro_recall = float(np.mean(class_recalls)) if class_recalls else 0.0
    map50 = float(np.mean(class_aps)) if class_aps else 0.0
    micro_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else 0.0
    micro_recall = total_tp / total_gt if total_gt else 0.0
    fps = total_images / total_inference_time if total_inference_time > 1e-9 else 0.0

    summary = {
        "images_evaluated": total_images,
        "num_gt_total": total_gt,
        "map50": round(map50, 4),
        "precision": round(macro_precision, 4),
        "recall": round(macro_recall, 4),
        "f1": round(compute_f1(macro_precision, macro_recall), 4),
        "micro_precision": round(micro_precision, 4),
        "micro_recall": round(micro_recall, 4),
        "micro_f1": round(compute_f1(micro_precision, micro_recall), 4),
        "fps": round(fps, 4),
    }
    return summary, per_class_rows


def main() -> None:
    args = parse_args()
    image_infos, annotations_by_image, valid_class_names = load_coco_dataset(args.gt_folder)
    detector = EnsembleDetector(
        primary_model_path=args.primary_model,
        secondary_model_path=args.secondary_model,
        conf_threshold=args.conf,
    )

    best_summary: dict[str, float] | None = None
    best_rows: list[dict[str, object]] = []
    best_conf = args.conf
    conf_candidates = parse_conf_sweep(args.conf_sweep)

    for current_conf in conf_candidates:
        summary, rows = evaluate_ensemble(
            detector=detector,
            image_infos=image_infos,
            annotations_by_image=annotations_by_image,
            valid_class_names=valid_class_names,
            gt_folder=args.gt_folder,
            conf_threshold=current_conf,
            iou_threshold=args.iou_threshold,
        )

        current_score = summary["map50"]
        if args.optimize == "f1":
            current_score = summary["f1"]
        elif args.optimize == "recall":
            current_score = summary["recall"]

        best_score = -1.0
        if best_summary is not None:
            best_score = best_summary["map50"]
            if args.optimize == "f1":
                best_score = best_summary["f1"]
            elif args.optimize == "recall":
                best_score = best_summary["recall"]

        if best_summary is None or current_score > best_score:
            best_summary = summary
            best_rows = rows
            best_conf = current_conf

    if best_summary is None:
        raise RuntimeError("Khong danh gia duoc ensemble.")

    output_json = {
        "dataset_folder": args.gt_folder,
        "primary_model": args.primary_model,
        "secondary_model": args.secondary_model,
        "iou_threshold": args.iou_threshold,
        "optimize": args.optimize,
        "conf_sweep": conf_candidates,
        "best_conf": round(best_conf, 4),
        "results": best_summary,
    }

    output_json_path = Path(args.output_json)
    output_csv_path = Path(args.output_csv)
    output_json_path.write_text(json.dumps(output_json, indent=2), encoding="utf-8")

    csv_lines = ["class_name,num_gt,precision,recall,ap50"]
    for row in best_rows:
        csv_lines.append(
            f"{row['class_name']},{row['num_gt']},{row['precision']},{row['recall']},{row['ap50']}"
        )
    output_csv_path.write_text("\n".join(csv_lines) + "\n", encoding="utf-8")

    print(json.dumps(output_json, indent=2))
    print(f"Saved summary to: {output_json_path}")
    print(f"Saved per-class metrics to: {output_csv_path}")


if __name__ == "__main__":
    main()

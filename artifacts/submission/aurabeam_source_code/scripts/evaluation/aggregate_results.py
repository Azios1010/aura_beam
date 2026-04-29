from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate AuraBeam experiment summaries")
    parser.add_argument("--results-root", type=str, default="artifacts/results")
    parser.add_argument("--output-csv", type=str, default="artifacts/tables/aggregated_results.csv")
    parser.add_argument(
        "--metrics",
        type=str,
        default="gssr_percent,missed_glare_rate_percent,false_darkening_rate_percent,rmse_xy_px,jitter_reduction_percent,avg_total_latency_ms,occlusion_gssr_percent,occlusion_missed_glare_rate_percent,occlusion_false_darkening_rate_percent,occlusion_rmse_xy_px",
    )
    return parser.parse_args()


def safe_mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def safe_std(values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0
    mean_value = safe_mean(values)
    variance = sum((value - mean_value) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance)


def main() -> None:
    args = parse_args()
    metrics_to_collect = [item.strip() for item in args.metrics.split(",") if item.strip()]
    results_root = Path(args.results_root)
    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for summary_path in results_root.glob("*/*/*/summary.json"):
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
        key = (str(payload.get("experiment_name", "unknown")), str(payload.get("scenario_name", "unknown")))
        grouped[key].append(payload)

    fieldnames = ["experiment_name", "scenario_name", "num_runs"]
    for metric_name in metrics_to_collect:
        fieldnames.extend([f"{metric_name}_mean", f"{metric_name}_std"])

    with output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for (experiment_name, scenario_name), payloads in sorted(grouped.items()):
            row: dict[str, Any] = {
                "experiment_name": experiment_name,
                "scenario_name": scenario_name,
                "num_runs": len(payloads),
            }
            for metric_name in metrics_to_collect:
                values = [
                    float(payload[metric_name])
                    for payload in payloads
                    if payload.get(metric_name) is not None
                ]
                row[f"{metric_name}_mean"] = round(safe_mean(values), 4) if values else None
                row[f"{metric_name}_std"] = round(safe_std(values), 4) if values else None
            writer.writerow(row)

    print(f"Saved aggregate table to: {output_csv}")


if __name__ == "__main__":
    main()

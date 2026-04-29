from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sweep tau_conf for B4 on occlusion scenarios")
    parser.add_argument("--primary-model", type=str, default="model/yolov5.pt")
    parser.add_argument("--secondary-model", type=str, default="model/model_ai.pt")
    parser.add_argument("--tau-values", type=str, default="0.25,0.35,0.45,0.55,0.65")
    parser.add_argument("--run-name", type=str, default="run_01")
    parser.add_argument("--output-root", type=str, default="artifacts/results_tau_sweep")
    parser.add_argument("--output-csv", type=str, default="artifacts/tables/tau_conf_sweep_results.csv")
    parser.add_argument("--occlusion-json", type=str, default="configs/occlusion_intervals.json")
    parser.add_argument("--adaptive-min-low-conf-frames", type=int, default=2)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--hold-time-frames", type=int, default=5)
    parser.add_argument("--track-hold-seconds", type=float, default=1.0)
    parser.add_argument("--fuse-iou-threshold", type=float, default=0.35)
    parser.add_argument("--gssr-iou-threshold", type=float, default=0.5)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def format_tau_name(tau: float) -> str:
    return str(tau).replace(".", "p")


def occlusion_scenarios() -> list[dict[str, str]]:
    return [
        {"name": "rain_1", "source": "demo_video/rain_1.mp4", "gt_folder": "rain_1"},
        {"name": "thunder_1", "source": "demo_video/thunder_1.mp4", "gt_folder": "thunder_1"},
        {"name": "fogging_1", "source": "demo_video/fogging_1.mp4", "gt_folder": "fogging_1"},
    ]


def load_summary(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    args = parse_args()
    tau_values = [float(item.strip()) for item in args.tau_values.split(",") if item.strip()]
    evaluate_script = PROJECT_ROOT / "scripts" / "evaluation" / "evaluate_metrics.py"
    output_root = PROJECT_ROOT / args.output_root
    output_root.mkdir(parents=True, exist_ok=True)
    output_csv = PROJECT_ROOT / args.output_csv
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    for tau in tau_values:
        experiment_name = f"b4_tau_{format_tau_name(tau)}"
        for scenario in occlusion_scenarios():
            command = [
                sys.executable,
                str(evaluate_script),
                "--primary-model",
                args.primary_model,
                "--secondary-model",
                args.secondary_model,
                "--source",
                scenario["source"],
                "--gt-folder",
                scenario["gt_folder"],
                "--experiment-name",
                experiment_name,
                "--scenario-name",
                scenario["name"],
                "--run-name",
                args.run_name,
                "--output-root",
                str(output_root),
                "--conf",
                str(args.conf),
                "--tau-conf",
                str(tau),
                "--adaptive-min-low-conf-frames",
                str(args.adaptive_min_low_conf_frames),
                "--hold-time-frames",
                str(args.hold_time_frames),
                "--track-hold-seconds",
                str(args.track_hold_seconds),
                "--fuse-iou-threshold",
                str(args.fuse_iou_threshold),
                "--gssr-iou-threshold",
                str(args.gssr_iou_threshold),
                "--detector-mode",
                "ensemble_weighted",
                "--tracking-mode",
                "kf3d",
                "--observation-mode",
                "adaptive",
                "--control-mode",
                "hold",
                "--occlusion-json",
                args.occlusion_json,
            ]
            print(" ".join(command))
            if args.dry_run:
                continue

            subprocess.run(command, check=True, cwd=PROJECT_ROOT)
            summary_path = output_root / experiment_name / scenario["name"] / args.run_name / "summary.json"
            payload = load_summary(summary_path)
            rows.append(
                {
                    "tau_conf": tau,
                    "experiment_name": experiment_name,
                    "scenario_name": scenario["name"],
                    "gssr_percent": payload.get("gssr_percent"),
                    "missed_glare_rate_percent": payload.get("missed_glare_rate_percent"),
                    "false_darkening_rate_percent": payload.get("false_darkening_rate_percent"),
                    "occlusion_gssr_percent": payload.get("occlusion_gssr_percent"),
                    "occlusion_missed_glare_rate_percent": payload.get("occlusion_missed_glare_rate_percent"),
                    "occlusion_false_darkening_rate_percent": payload.get("occlusion_false_darkening_rate_percent"),
                    "rmse_xy_px": payload.get("rmse_xy_px"),
                    "occlusion_rmse_xy_px": payload.get("occlusion_rmse_xy_px"),
                    "mode_switch_count": payload.get("mode_switch_count"),
                    "adaptive_z_only_frame_ratio_percent": payload.get("adaptive_z_only_frame_ratio_percent"),
                    "low_conf_candidate_frame_ratio_percent": payload.get("low_conf_candidate_frame_ratio_percent"),
                    "adaptive_min_low_conf_frames": payload.get("adaptive_min_low_conf_frames"),
                    "avg_total_latency_ms": payload.get("avg_total_latency_ms"),
                }
            )

    if rows:
        with output_csv.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"Saved tau_conf sweep table to: {output_csv}")


if __name__ == "__main__":
    main()

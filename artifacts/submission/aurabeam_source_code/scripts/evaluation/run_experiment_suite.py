from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run AuraBeam experiment suite from a JSON config")
    parser.add_argument("--config", type=str, default="configs/experiment_suite.json")
    parser.add_argument("--primary-model", type=str, default="model/yolov5.pt")
    parser.add_argument("--secondary-model", type=str, default="model/model_ai.pt")
    parser.add_argument("--run-name", type=str, default="run_01")
    parser.add_argument("--output-root", type=str, default=None)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--tau-conf", type=float, default=None)
    parser.add_argument("--adaptive-min-low-conf-frames", type=int, default=None)
    parser.add_argument("--switch-policy", type=str, default=None)
    parser.add_argument("--adaptive-min-prediction-only-frames", type=int, default=None)
    parser.add_argument("--adaptive-switch-cooldown-frames", type=int, default=None)
    parser.add_argument("--hold-time-frames", type=int, default=5)
    parser.add_argument("--track-hold-seconds", type=float, default=1.0)
    parser.add_argument("--fuse-iou-threshold", type=float, default=0.35)
    parser.add_argument("--gssr-iou-threshold", type=float, default=0.5)
    parser.add_argument("--occlusion-json", type=str, default=None)
    parser.add_argument("--no-progress", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_path = Path(args.config)
    config = json.loads(config_path.read_text(encoding="utf-8"))

    evaluate_script = PROJECT_ROOT / "scripts" / "evaluation" / "evaluate_metrics.py"
    output_root = args.output_root or config.get("output_root", "artifacts/results")
    occlusion_json = args.occlusion_json or config.get("occlusion_json")
    tau_conf = args.tau_conf if args.tau_conf is not None else config.get("tau_conf", 0.25)
    adaptive_min_low_conf_frames = (
        args.adaptive_min_low_conf_frames
        if args.adaptive_min_low_conf_frames is not None
        else config.get("adaptive_min_low_conf_frames", 2)
    )
    switch_policy = args.switch_policy if args.switch_policy is not None else config.get("switch_policy", "best_conf")
    adaptive_min_prediction_only_frames = (
        args.adaptive_min_prediction_only_frames
        if args.adaptive_min_prediction_only_frames is not None
        else config.get("adaptive_min_prediction_only_frames", 0)
    )
    adaptive_switch_cooldown_frames = (
        args.adaptive_switch_cooldown_frames
        if args.adaptive_switch_cooldown_frames is not None
        else config.get("adaptive_switch_cooldown_frames", 0)
    )
    experiments = config.get("runs", [])
    scenarios = config.get("scenarios", [])
    total_jobs = len(experiments) * len(scenarios)
    completed_jobs = 0
    suite_start = time.perf_counter()

    for experiment in experiments:
        for scenario in scenarios:
            completed_jobs += 1
            if not args.no_progress:
                elapsed_seconds = time.perf_counter() - suite_start
                avg_job_seconds = elapsed_seconds / (completed_jobs - 1) if completed_jobs > 1 else 0.0
                remaining_jobs = total_jobs - completed_jobs + 1
                eta_seconds = avg_job_seconds * remaining_jobs if completed_jobs > 1 else 0.0
                print(
                    f"[suite {completed_jobs}/{total_jobs}] "
                    f"{experiment['name']} :: {scenario['name']} :: {args.run_name} "
                    f"(elapsed {elapsed_seconds/60.0:.1f}m, eta {eta_seconds/60.0:.1f}m)"
                )
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
                experiment["name"],
                "--scenario-name",
                scenario["name"],
                "--run-name",
                args.run_name,
                "--output-root",
                output_root,
                "--conf",
                str(args.conf),
                "--tau-conf",
                str(tau_conf),
                "--adaptive-min-low-conf-frames",
                str(adaptive_min_low_conf_frames),
                "--switch-policy",
                str(switch_policy),
                "--adaptive-min-prediction-only-frames",
                str(adaptive_min_prediction_only_frames),
                "--adaptive-switch-cooldown-frames",
                str(adaptive_switch_cooldown_frames),
                "--hold-time-frames",
                str(args.hold_time_frames),
                "--track-hold-seconds",
                str(args.track_hold_seconds),
                "--fuse-iou-threshold",
                str(args.fuse_iou_threshold),
                "--gssr-iou-threshold",
                str(args.gssr_iou_threshold),
                "--no-progress" if args.no_progress else "--progress",
                "--detector-mode",
                experiment["detector_mode"],
                "--tracking-mode",
                experiment["tracking_mode"],
                "--observation-mode",
                experiment["observation_mode"],
                "--control-mode",
                experiment["control_mode"],
            ]
            if occlusion_json:
                command.extend(["--occlusion-json", occlusion_json])

            print(" ".join(command))
            if not args.dry_run:
                subprocess.run(command, check=True, cwd=PROJECT_ROOT)

    if not args.no_progress:
        total_elapsed_seconds = time.perf_counter() - suite_start
        print(f"[suite done] {total_jobs} jobs finished in {total_elapsed_seconds/60.0:.1f}m")


if __name__ == "__main__":
    main()

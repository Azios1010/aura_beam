# AuraBeam Submission Package

This package contains the source code, selected demo assets, model weights, and generated Q2 experiment results for the AuraBeam project. The LaTeX manuscript is not included because the paper source is maintained separately on Overleaf.

## Package Contents

```text
aurabeam_source_code/
|-- src/
|-- scripts/
|-- configs/
|-- firmware/
|-- tests/
|-- notebooks/
|-- model/
|   |-- *.pt
|-- demo_video/
|   |-- fogging_1.mp4
|   |-- rain_1.mp4
|   |-- thunder_1.mp4
|   |-- night_1.mp4
|   `-- norm_1.mp4
|-- fogging_1/
|-- rain_1/
|-- thunder_1/
|-- night_1/
|-- norm_1/
|-- artifacts/
|   |-- tables/
|   |-- figures/
|   |   `-- q2_ready_figures/
|   |-- results_q2_a1_a4/
|   |-- results_q2_b1_b2/
|   |-- results_q2_c1_c4/
|   `-- results_final_q2_lock/
|-- metrics_ultralytics/
|   |-- ensemble/
|   `-- each_model/
|       `-- five_case.csv
|-- requirements.txt
|-- SETUP.md
|-- PROJECT_STRUCTURE.md
|-- AGENTS.md
|-- .gitignore
|-- run_experiment_suite.py
|-- evaluate_metrics.py
|-- aggregate_results.py
|-- run_q2_a1_a4.ps1
|-- run_q2_b1_b2.ps1
`-- run_q2_c1_c4.ps1
```

## Main Components

- `src/aura_beam/`: reusable core logic for detector ensemble, pseudo-radar depth surrogate, sensor fusion, zone logic, and serial communication.
- `scripts/evaluation/`: experiment runners, metric calculation, aggregation, and parameter sweep scripts.
- `configs/`: JSON experiment suites and occlusion interval definitions.
- `firmware/`: Arduino firmware for the 8x8 LED matrix.
- `tests/`: lightweight pytest checks for project structure and behavior.
- `notebooks/`: supporting notebooks and dataset notes used during analysis.
- `model/`: PyTorch model weights only, copied as `.pt` files. In this package, `yolov5.pt` is Model 1 (YOLOv5), and `model_ai.pt` is Model 2 (YOLOv8).
- `demo_video/`: selected demo videos for the five submitted scenarios.
- Scenario folders: annotations and related data for `fogging_1`, `rain_1`, `thunder_1`, `night_1`, and `norm_1`.
- `artifacts/`: generated tables, figures, and Q2 result folders used for analysis.
- `metrics_ultralytics/each_model/five_case.csv`: per-model metrics for the five selected cases.
- `metrics_ultralytics/ensemble/`: ensemble metrics for the five selected cases, including NMS and weighted-NMS result files.

## Environment Setup

Run the following commands in Windows PowerShell from the package root:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks virtual environment activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

Quick checks:

```powershell
python --version
python run_experiment_suite.py --help
python aggregate_results.py --help
```

## Included Demo Scenarios

The package includes five selected scenarios:

```text
fogging_1
rain_1
thunder_1
night_1
norm_1
```

The matching video files are:

```text
demo_video/fogging_1.mp4
demo_video/rain_1.mp4
demo_video/thunder_1.mp4
demo_video/night_1.mp4
demo_video/norm_1.mp4
```

## Model Weights

The submitted model weights use the following naming convention:

```text
model/yolov5.pt    -> Model 1 (YOLOv5)
model/model_ai.pt  -> Model 2 (YOLOv8)
```

## Q2 Experiment Results

Generated Q2 results are included under:

```text
artifacts/results_q2_a1_a4/
artifacts/results_q2_b1_b2/
artifacts/results_q2_c1_c4/
artifacts/results_final_q2_lock/
```

Summary tables are included under:

```text
artifacts/tables/
metrics_ultralytics/each_model/five_case.csv
metrics_ultralytics/ensemble/
```

Manuscript-ready figures are included under:

```text
artifacts/figures/q2_ready_figures/
```

## Reproducing Q2 Batches

The package includes three PowerShell scripts for the Q2 experiment batches:

```powershell
.\run_q2_a1_a4.ps1
.\run_q2_b1_b2.ps1
.\run_q2_c1_c4.ps1
```

Each script runs the configured batch and aggregates the results after completion. A partial run can be launched with:

```powershell
.\run_q2_b1_b2.ps1 -StartRun 3 -EndRun 5
```

Manual aggregation:

```powershell
python aggregate_results.py --results-root artifacts/results_q2_a1_a4 --output-csv artifacts/tables/q2_a1_a4_results.csv
python aggregate_results.py --results-root artifacts/results_q2_b1_b2 --output-csv artifacts/tables/q2_b1_b2_results.csv
python aggregate_results.py --results-root artifacts/results_q2_c1_c4 --output-csv artifacts/tables/q2_c1_c4_results.csv
```

## Validation

Run the test suite with:

```powershell
python -m pytest
```

For structure-only validation:

```powershell
python -m pytest tests/test_project_structure.py
```

## Notes

- The manuscript source is intentionally excluded from this package.
- The `model/` directory should contain only `.pt` weights.
- Virtual environments, cache folders, `.git/`, and temporary local runs should not be included in the submitted zip.
- Root-level Python files are compatibility wrappers. Core logic should be read from `src/aura_beam/`, while evaluation logic is under `scripts/evaluation/`.

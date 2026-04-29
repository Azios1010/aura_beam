# AuraBeam: Robust Nighttime Vehicle Localization under Headlight Saturation

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **AuraBeam** is an application-oriented machine-vision framework for analyzing closed-loop Adaptive Driving Beam (ADB) behavior under nighttime visual degradation. It evaluates perception, tracking, and physical actuation when standard camera pipelines collapse due to intense glare, fog, or exposure disruption.

## 📖 Overview

Nighttime driving is a disproportionately hazardous condition. Modern intelligent headlight systems (like Adaptive Driving Beam - ADB) rely heavily on cameras to dim specific regions of the headlight to avoid blinding oncoming drivers. However, these systems become fragile when intense headlights, heavy rain, or fog cause "visual collapse" (the camera is temporarily blinded).

**AuraBeam** bridges the gap between purely image-space detection and physical light actuation by combining:
1. **Ensemble Vision Front-End:** Fuses YOLOv5 and YOLOv8 via Weighted Non-Maximum Suppression (NMS) for robust glare detection.
2. **Pseudo-Radar Depth Surrogate:** A physics-based depth estimator that survives temporary camera saturation.
3. **Adaptive 3-D Kalman Filter:** A 6-state tracking module that gracefully falls back to depth-only tracking when the visual confidence drops.
4. **Hardware-in-the-Loop (HIL) Actuation:** Projects the suppression region onto an Arduino-driven 8x8 LED matrix to evaluate the final physical actuation using the **Glare Suppression Success Rate (GSSR)** metric.

## 📁 Repository Structure

- `src/aura_beam/`: Core reusable logic (detector ensemble, pseudo-radar, sensor fusion, zone logic, serial manager).
- `scripts/evaluation/`: Experiment runners, metric calculators, and parameter sweeps.
- `configs/`: JSON configuration files defining the experiment suites (e.g., A1-A4, B1-B2, C1-C4).
- `firmware/`: Arduino firmware (`arduino_8x8_matrix.ino`) for the LED matrix actuation.
- `model/`: Pre-trained PyTorch weights (`.pt` files).
- `demo_video/` & Scenario Folders: Annotated test sequences (e.g., fogging, rain, thunder, norm).
- `artifacts/`: Generated results, summary tables, and figures.

## ⚙️ Hardware Setup (Optional HIL)

To run the full closed-loop evaluation, the following low-cost setup is used:
- **Processing Unit:** PC/Laptop with a discrete GPU.
- **Microcontroller:** Arduino Uno R3.
- **Actuator:** 1588BS 8x8 LED Matrix module.
- **Camera:** Standard 1080p USB Webcam.
- *Note:* The evaluation scripts can be run entirely in Software-in-the-Loop (offline replay) mode if hardware is not connected.

## 🚀 Getting Started

### 1. Clone the repository
```powershell
git clone https://github.com/Azios1010/aura_beam.git
cd "CV Model"
```

### 2. Environment Setup
It is recommended to use a virtual environment.
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```
*(If PowerShell blocks the script, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` before activating).*

### 3. Verify Installation
```powershell
python --version
python run_experiment_suite.py --help
python aggregate_results.py --help
```

## 📊 Running Experiments

The project uses predefined JSON configs to run ablation studies. Pre-configured PowerShell scripts are available to run the core Q2 batches.

```powershell
# Run Perception Ablations (A1-A4)
.\run_q2_a1_a4.ps1

# Run Tracking Ablations (B1-B2)
.\run_q2_b1_b2.ps1

# Run Control & Switching Ablations (C1-C4)
.\run_q2_c1_c4.ps1
```

Each script will automatically execute the runs across multiple scenarios and aggregate the results into `artifacts/tables/`.

If you need to manually aggregate results:
```powershell
python aggregate_results.py --results-root artifacts/results_q2_a1_a4 --output-csv artifacts/tables/q2_a1_a4_results.csv
```

## 📄 License
This project is licensed under the MIT License - see the `LICENSE` file for details.

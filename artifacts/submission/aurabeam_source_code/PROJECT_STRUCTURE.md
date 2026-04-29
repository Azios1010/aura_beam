# AuraBeam Project Structure

Tai lieu nay mo ta cau truc hien tai cua du an `AuraBeam` theo huong phuc vu:

- phat trien he thong
- chay baseline va ablation
- tong hop ket qua cho manuscript Q2
- ban giao de cong su co the chay lai de dang

## Muc tieu cau truc

- tach ro `core code`, `evaluation script`, `firmware`, `report`, `artifact`
- giu wrapper o thu muc goc de tuong thich voi lenh cu
- cho phep chay batch experiment bang file config
- cho phep giao viec cho nhieu nguoi qua cac file `.ps1`

## Cay thu muc chinh

```text
CV Model/
|-- src/
|   `-- aura_beam/
|       |-- __init__.py
|       |-- detector_ensemble.py
|       |-- pseudo_radar.py
|       |-- sensor_fusion.py
|       |-- serial_manager.py
|       `-- zone_logic.py
|
|-- scripts/
|   `-- evaluation/
|       |-- __init__.py
|       |-- aggregate_results.py
|       |-- ensemble_eval.py
|       |-- evaluate_metrics.py
|       |-- run_experiment_suite.py
|       |-- single_model_official_val.py
|       `-- sweep_tau_conf.py
|
|-- configs/
|   |-- experiment_suite.json
|   |-- final_evaluation_suite.json
|   |-- final_evaluation_suite_active_track.json
|   |-- q2_a1_a4_suite.json
|   |-- q2_b1_b2_suite.json
|   |-- q2_c1_c4_suite.json
|   |-- b4_q2_candidate_active_guarded.json
|   |-- b4_q2_candidate_lowconf_pred_or_missing_a.json
|   |-- b4_q2_candidate_lowconf_pred_or_missing_b.json
|   |-- b4_q2_candidate_lowconf_pred_or_missing_c.json
|   |-- occlusion_intervals.json
|   |-- occlusion_screening_suite.json
|   `-- occlusion_intervals_rain3_candidate_*.json
|
|-- firmware/
|   `-- arduino_8x8_matrix.ino
|
|-- report/
|   |-- q2_report.tex
|   `-- draft_q2.tex
|
|-- md_folder/
|   `-- Q2_WORKFLOW.md
|
|-- artifacts/
|   |-- figures/
|   |-- metrics/
|   |-- tables/
|   |-- results/
|   |-- results_final_eval/
|   |-- results_final_eval_active_track/
|   |-- results_final_q2_lock/
|   |-- results_logic_reeval/
|   |-- results_q2_b4_candidates/
|   |-- results_rain2_probe/
|   |-- results_rain3_candidates/
|   |-- results_rain3_probe/
|   |-- results_rain4_probe/
|   `-- results_tau_sweep/
|
|-- model/
|   |-- yolov5.pt
|   `-- model_ai.pt
|
|-- demo_video/
|-- fogging_1/
|-- night_1/
|-- norm_1/
|-- norm_2/
|-- rain_1/
|-- rain_2/
|-- rain_3/
|-- rain_4/
|-- snow_1/
|-- snow_12/
|-- thunder_1/
|
|-- tests/
|
|-- main.py
|-- evaluate_metrics.py
|-- ensemble_eval.py
|-- aggregate_results.py
|-- run_experiment_suite.py
|-- detector_ensemble.py
|-- pseudo_radar.py
|-- sensor_fusion.py
|-- serial_manager.py
|-- zone_logic.py
|-- run_q2_a1_a4.ps1
|-- run_q2_b1_b2.ps1
|-- run_q2_c1_c4.ps1
|-- SETUP.md
|-- PROJECT_STRUCTURE.md
`-- requirements.txt
```

## Y nghia tung nhom

### `src/aura_beam/`

Day la noi dat code loi cua he thong. Moi thay doi thuat toan nen uu tien dat o day.

- `detector_ensemble.py`: chay 2 model va fusion detection
- `pseudo_radar.py`: depth surrogate / pseudo-radar
- `sensor_fusion.py`: KF2D, KF3D, tracking logic
- `serial_manager.py`: giao tiep voi Arduino
- `zone_logic.py`: mapping target sang vung LED va control logic

Nguyen tac:

- khong dat logic manuscript vao day
- neu them baseline hoac adaptive logic moi, sua o day truoc

### `scripts/evaluation/`

Chua cac script phuc vu danh gia va sinh so lieu.

- `evaluate_metrics.py`: script danh gia chinh cho B1-B4 va C1-C4
- `run_experiment_suite.py`: chay nhieu config/scenario tu file JSON
- `aggregate_results.py`: gom nhieu `run_xx` thanh bang `mean/std`
- `ensemble_eval.py`: danh gia detector ensemble
- `single_model_official_val.py`: baseline detector don
- `sweep_tau_conf.py`: quet tham so `tau_conf`

### `configs/`

Chua ma tran thuc nghiem.

Nhom config quan trong hien tai:

- `final_evaluation_suite.json`: final eval co ban cho B3/B4
- `final_evaluation_suite_active_track.json`: final eval theo policy `active_track_conf_or_missing`
- `q2_a1_a4_suite.json`: batch detector ablation A1-A4
- `q2_b1_b2_suite.json`: batch baseline con thieu B1-B2
- `q2_c1_c4_suite.json`: batch control/switching C1-C4

### `artifacts/`

Chua output sinh ra tu experiment.

- `results*/`: ket qua raw theo tung experiment/scenario/run
- `tables/`: bang tong hop CSV
- `figures/`: hinh sinh ra de dua vao bao cao
- `metrics/`: metric phu, neu co script xuat rieng

Nguyen tac:

- day la output, khong phai source code
- khong sua tay neu co the sinh lai bang script

### `report/`

Chua manuscript LaTeX.

- `q2_report.tex`: ban manuscript dang dung
- `draft_q2.tex`: ban thao cu hon / tham khao cau truc

### `md_folder/`

Chua tai lieu noi bo.

- `Q2_WORKFLOW.md`: checklist va lo trinh huong toi bai bao Q2

### Scenario folders

Cac folder nhu `fogging_1/`, `rain_1/`, `thunder_1/` chua annotation va frame data cho benchmark.

### `demo_video/`

Chua video nguon dung cho evaluation.

### `model/`

Chua model weight can co san truoc khi chay experiment.

## Root-level wrappers

Nhieu file o thu muc goc duoc giu lai de tuong thich voi lenh cu:

- `main.py`
- `evaluate_metrics.py`
- `ensemble_eval.py`
- `aggregate_results.py`
- `run_experiment_suite.py`
- `detector_ensemble.py`
- `pseudo_radar.py`
- `sensor_fusion.py`
- `serial_manager.py`
- `zone_logic.py`

Vai tro cua chung:

- goi sang `scripts/` hoac `src/`
- giu lenh ngan, de copy-paste nhanh

Nguyen tac:

- khong nen phat trien feature moi truc tiep trong wrapper root
- moi logic that su nen nam trong `src/` hoac `scripts/`

## File ho tro chay batch cho cong su

Ba file PowerShell moi:

- `run_q2_a1_a4.ps1`
- `run_q2_b1_b2.ps1`
- `run_q2_c1_c4.ps1`

Moi file se:

- chay tu `run_01` den `run_05`
- hien progress
- tu dong aggregate ket qua sau khi xong

Tai lieu ban giao:

- `SETUP.md`: huong dan clone, tao moi truong, chay batch, aggregate

## Quy uoc phat trien tiep

Neu them mot baseline hoac ablation moi:

1. cap nhat logic trong `src/aura_beam/` neu can
2. them hoac sua script trong `scripts/evaluation/`
3. tao config moi trong `configs/`
4. dam bao output di vao `artifacts/results_*`
5. neu can giao cho nguoi khac chay, them file `.ps1` o root

## Ket luan

Cau truc hien tai duoc chia thanh cac lop ro rang:

1. `src/` cho logic loi
2. `scripts/` cho danh gia va automation
3. `configs/` cho ma tran thuc nghiem
4. `artifacts/` cho output
5. `report/` cho manuscript
6. root wrappers va `.ps1` cho van hanh nhanh

Day la cau truc phu hop de tiep tuc chay baseline, ablation, tong hop ket qua, va ban giao cho cong su trong workflow Q2.

# Setup va Chay Experiment Q2

Tai lieu nay danh cho cong su chay cac batch `A1-A4`, `B1-B2`, `C1-C4` tren Windows PowerShell.

## 1. Yeu cau

- Git
- Python
- Windows PowerShell

Repo sau khi clone can co san cac thu muc/file sau:

- `model/yolov5.pt`
- `model/model_ai.pt`
- `demo_video/`
- cac folder annotation nhu `night_1/`, `norm_1/`, `rain_1/`, `fogging_1/`, `thunder_1/`

Neu clone xong ma thieu cac file lon nay thi can sync them truoc khi chay.

## 2. Clone Repo

```powershell
git clone <repo-url>
cd "CV Model"
```

Neu repo da co san tren may thi bo qua buoc nay.

## 3. Tao Moi Truong

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Neu PowerShell chan script activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

## 4. Kiem Tra Nhanh

```powershell
python --version
python run_experiment_suite.py --help
python aggregate_results.py --help
```

Neu 3 lenh tren chay duoc thi moi truong on.

## 5. Config Can Dung

- `configs/q2_a1_a4_suite.json`
- `configs/q2_b1_b2_suite.json`
- `configs/q2_c1_c4_suite.json`

Ket qua se duoc luu tach rieng:

- `artifacts/results_q2_a1_a4`
- `artifacts/results_q2_b1_b2`
- `artifacts/results_q2_c1_c4`

Progress bar/frame progress mac dinh da bat. Khong can them tham so gi neu muon xem tien do.

## 6. File Chay Co San

```powershell
run_q2_a1_a4.ps1
run_q2_b1_b2.ps1
run_q2_c1_c4.ps1
```

Moi file se:

- chay tu `run_01` den `run_05`
- hien progress mac dinh
- tu dong aggregate sau khi chay xong

## 7. Cach Chay De Xuat

Nguoi 1:

```powershell
.\venv\Scripts\Activate.ps1
.\run_q2_a1_a4.ps1
```

Nguoi 2:

```powershell
.\venv\Scripts\Activate.ps1
.\run_q2_b1_b2.ps1
```

Nguoi 3:

```powershell
.\venv\Scripts\Activate.ps1
.\run_q2_c1_c4.ps1
```

## 8. Chay Lai Mot Khoang Run

Neu bi loi giua chung, co the chay lai mot doan:

```powershell
.\run_q2_b1_b2.ps1 -StartRun 3 -EndRun 5
```

Co the doi ten file theo nhu cau:

- `run_q2_a1_a4.ps1`
- `run_q2_b1_b2.ps1`
- `run_q2_c1_c4.ps1`

## 9. Xuat Bang Tong Hop

Sau khi chay xong tung nhom, xuat CSV tong hop rieng:

```powershell
python aggregate_results.py --results-root artifacts/results_q2_a1_a4 --output-csv artifacts/tables/q2_a1_a4_results.csv
python aggregate_results.py --results-root artifacts/results_q2_b1_b2 --output-csv artifacts/tables/q2_b1_b2_results.csv
python aggregate_results.py --results-root artifacts/results_q2_c1_c4 --output-csv artifacts/tables/q2_c1_c4_results.csv
```

## 10. Cau Truc Ket Qua

Moi lan chay se tao data theo dang:

```text
artifacts/results_q2_a1_a4/<experiment_name>/<scenario_name>/<run_name>/
artifacts/results_q2_b1_b2/<experiment_name>/<scenario_name>/<run_name>/
artifacts/results_q2_c1_c4/<experiment_name>/<scenario_name>/<run_name>/
```

Trong moi folder `run_xx` se co:

- `summary.json`
- `per_frame_metrics.csv`

## 11. Loi Thuong Gap

`ModuleNotFoundError`:
chua activate `venv` hoac chua `pip install -r requirements.txt`.

`File not found`:
thieu model, video, hoac folder annotation.

Khong thay progress:
kiem tra xem co truyen `--no-progress` hay khong. Mac dinh script da bat progress.

Muon chay tiep tu run cu:
chi can doi `--run-name`, vi du `run_03`, `run_04`, `run_05`.

Luu y:

- Cac file `.ps1` da tu dong aggregate sau khi chay xong.
- 3 lenh tren chi can dung khi muon aggregate lai thu cong.

## 12. Lenh Mau Day Du

Neu muon chay tron bo tu dau den cuoi:

```powershell
.\venv\Scripts\Activate.ps1

.\run_q2_a1_a4.ps1
.\run_q2_b1_b2.ps1
.\run_q2_c1_c4.ps1
```

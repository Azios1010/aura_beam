# Workflow Huong Toi Bai Bao Q2 Cho AuraBeam

## 1. Muc tieu cua workflow

File nay chuyen cac y tuong cai tien thanh mot lo trinh co the thuc thi de dua `AuraBeam` tu muc do do an / paper som len muc do bai bao Q2.

Muc tieu khong phai la "them that nhieu ket qua", ma la:

- Chot dong gop khoa hoc ro rang.
- Xay dung protocol thi nghiem chat che.
- Chay ablation day du va co y nghia.
- Bao cao thong ke dung chuan.
- Trinh bay ket qua sach, thuyet phuc, va kho bi reviewer bat loi.

## 2. Dinh vi bai bao

Truoc khi lam them experiment, can chot lai bai nay la mot paper ve `system robustness for ADB under glare-induced camera failure`, khong phai paper phat minh detector moi.

Ba claim nen duoc giu on dinh trong toan bo bai:

1. `Ensemble + Weighted NMS` giup tang robustness cua perception duoi blooming, glare, scattering.
2. `3D KF + pseudo-radar + adaptive switching` giup duy tri tracking va glare suppression khi camera bi mu.
3. Cai thien perception/tracking phai duoc chung minh o muc `control outcome`, khong chi o muc `mAP` hay `RMSE`, ma bang `GSSR`, `MGR`, `FDR`.

Neu mot experiment khong phuc vu it nhat mot claim tren, can xem xet bo.

## 3. Nguyen tac uu tien

Thu tu uu tien dung:

1. Siet protocol va evaluation.
2. Bo sung baseline va ablation.
3. Bao cao thong ke.
4. Lam sach bang, hinh, narrative.
5. Chi retrain model khi co bang chung detector la nut that chinh.

Khong nen retrain ngay neu:

- Baseline chua day du.
- Ablation chua tach duoc dong gop tung module.
- Chua co `mean +- std`.
- Chua co significance test.
- Chua co hinh dinh tinh quan trong.

## 4. Ke hoach tong the theo giai doan

### Giai doan 1. Khoa protocol nghien cuu

Muc tieu:

- Co mot protocol co the lap lai.
- Xac dinh ro du lieu nao dung de train, val, test.
- Xac dinh metric chinh va metric phu.

Cong viec:

1. Chot lai cac split:
   - `train`
   - `validation`
   - `golden test`
2. Ghi ro:
   - so luong mau moi split
   - tieu chi chia split
   - co hay khong overlap theo video / scene
3. Khoa metric chinh:
   - `GSSR`
   - `MGR`
   - `FDR`
4. Khoa metric phu:
   - `RMSE_xy`
   - `JR%`
   - `IDF1` neu mo rong tracking nhieu target
   - latency / FPS
5. Khoa seed va cach lap lai:
   - nen co `n = 3` toi thieu
   - tot hon la `n = 5`

Deliverable:

- Mot bang protocol trong paper.
- Mot file ghi cau hinh experiment.

Tieu chi hoan thanh:

- Bat ky ket qua nao dua vao paper deu phai truy nguon ve cung mot protocol.

### Giai doan 2. Hoan thien baseline tracking

Muc tieu:

- Chung minh ro phan gain den tu dau.
- Tach bach perception gain va fusion gain.

Bat buoc phai co 4 baseline tracking:

1. `raw detector`
2. `detector + 2D KF`
3. `detector + 3D KF without mode switching`
4. `detector + 3D KF + pseudo-radar + adaptive switching`

Y nghia khoa hoc:

- `(1) -> (2)` do tac dong cua smoothing 2D.
- `(2) -> (3)` do tac dong cua state 3D nhung chua co adaptive logic.
- `(3) -> (4)` do tac dong thuc su cua `adaptive switching`.

Metric can bao cao:

- `RMSE_xy`
- `JR%`
- `GSSR`
- `MGR`
- `FDR`

Deliverable:

- 1 bang tracking baseline comparison.
- 2 hinh trajectory qualitative:
  - lightning
  - rain / long dropout

Tieu chi hoan thanh:

- Reader nhin vao phai thay ro vi sao `adaptive 3D fusion` can thiet, khong chi "KF nao cung duoc".

### Giai doan 3. Ablation chi tiet hon

Muc tieu:

- Chung minh tung thanh phan co gia tri rieng.

Ablation bat buoc:

1. `single model vs ensemble`
2. `Weighted NMS vs standard NMS`
3. `no hold-time vs hold-time`
4. `fixed full-observation vs adaptive switching`

Neu du thoi gian, bo sung:

5. `single specialized model vs general model vs ensemble`
6. `vision-only 3D KF vs 3D KF + pseudo-radar`

Moi ablation nen tra loi mot cau hoi reviewer:

- Ensemble co that su can thiet khong?
- Weighted NMS co tot hon NMS thuong khong?
- Hold-time co giam flicker hay chi tao lag?
- Adaptive switching co tot hon fixed observation khong?

Deliverable:

- 1 bang ablation chinh.
- 1 bang ablation phu neu so lieu nhieu.

Tieu chi hoan thanh:

- Moi thanh phan trong he thong deu co bang chung dinh luong.

### Giai doan 4. Sensitivity analysis

Muc tieu:

- Cho thay he thong khong chi "tinh co chon dung tham so".

Thong so can quet:

- nguong `tau_conf`
- nguong `tau_NMS`
- hold-time `T_h`
- process noise `Q`
- measurement noise `R`

Cach lam:

1. Quet tung tham so mot, giu co dinh cac tham so con lai.
2. Danh gia tren:
   - full test set
   - hard subset, dac biet la lightning va curved road
3. Ve duong cong:
   - `GSSR`
   - `MGR`
   - `FDR`
   - latency neu co tac dong

Deliverable:

- 1 hinh sensitivity cho `tau_conf`, `tau_NMS`, `T_h`
- 1 hinh hoac bang phu cho `Q/R`

Tieu chi hoan thanh:

- Chon tham so co ly do ro rang, khong phai "empirically chosen" mot cach mo ho.

### Giai doan 5. Bao cao thong ke

Muc tieu:

- Nang ket qua tu "mot lan chay dep" thanh "ket qua dang tin cay".

Bat buoc:

- Bao cao `mean +- std`
- Neu co the, them significance test don gian

Kien nghi:

- Neu so sanh theo cung scenario/frame: dung `paired t-test`
- Neu phan phoi khong dep hoac nho: dung `Wilcoxon signed-rank`

So sanh uu tien:

1. `single model` vs `ensemble`
2. `2D KF` vs `3D KF without switching`
3. `fixed full-observation` vs `adaptive switching`
4. `best baseline` vs `full AuraBeam`

Deliverable:

- Bang ket qua co cot:
  - mean
  - std
  - p-value neu co

Tieu chi hoan thanh:

- Reviewer khong the noi rang gain la do may man hoac mot scenario le.

### Giai doan 6. Nang cap qualitative evidence

Muc tieu:

- Giam su tru tuong.
- Cho thay system hoat dong dung o cac failure case quan trong.

Bat buoc phai co cac hinh sau:

1. `YOLO-only fail`
2. `AuraBeam recover`
3. `grid mapping dung / sai`
4. `occlusion interval`
5. `input frame -> detection -> fused track -> 8x8 suppression grid`

Goi y:

- Nen co caption rat cu the.
- Mỗi hinh phai phuc vu mot claim.

Deliverable:

- 1 figure pipeline tong quan dep.
- 1 figure qualitative comparison split-screen.
- 1 figure timeline cho occlusion.

Tieu chi hoan thanh:

- Nguoi doc khong can doc het cong thuc van hieu ngay bai nay giai quyet loi gi.

### Giai doan 7. Lam sach manuscript

Muc tieu:

- Bien ban thao thanh ban gui journal, khong con dau vet do an.

Danh sach bat buoc:

1. Sua cac bang chua sach, dac biet:
   - `Table 5` dang co dau hieu lap cot / lap so lieu
2. Giai thich ngan gon `JR% am`
3. Dam bao ten model, training protocol, implementation, va paper khop nhau
4. Bo placeholder figure bang hinh that
5. Kiem tra lai logic giua:
   - methodology
   - implementation
   - results
6. Viet lai limitations theo giong journal:
   - ro rang
   - trung thuc
   - co dinh huong future work

Deliverable:

- Ban `report.tex` da dong nhat notation, bang, hinh, caption, references.

Tieu chi hoan thanh:

- Ban thao doc lien mach, khong co cho nao lam reviewer mat niem tin.

## 5. Experiment matrix de thuc thi

### Nhom A. Perception

| ID | Cau hinh | Muc dich |
| --- | --- | --- |
| A1 | single model M1 | baseline specialist |
| A2 | single model M2 | baseline generalist |
| A3 | ensemble + standard NMS | tach tac dong ensemble va fusion rule |
| A4 | ensemble + Weighted NMS | cau hinh de xuat |

Metric:

- mAP@0.5
- Precision
- Recall
- GSSR sau khi dua qua pipeline control neu can

### Nhom B. Tracking and fusion

| ID | Cau hinh | Muc dich |
| --- | --- | --- |
| B1 | raw detector | baseline toi thieu |
| B2 | detector + 2D KF | gain tu smoothing 2D |
| B3 | detector + 3D KF no switching | gain tu state 3D |
| B4 | detector + 3D KF + pseudo-radar + adaptive switching | full AuraBeam |

Metric:

- RMSE_xy
- JR%
- GSSR
- MGR
- FDR

### Nhom C. Control and scheduling

| ID | Cau hinh | Muc dich |
| --- | --- | --- |
| C1 | no hold-time | baseline |
| C2 | hold-time enabled | anti-flicker |
| C3 | fixed observation | khong co switching |
| C4 | adaptive switching | cau hinh de xuat |

Metric:

- GSSR
- MGR
- FDR
- box command change rate

### Nhom D. Sensitivity

| Nhom tham so | Bien |
| --- | --- |
| detector threshold | `tau_conf` |
| fusion threshold | `tau_NMS` |
| temporal smoothing | `T_h` |
| filter dynamics | `Q`, `R` |

## 6. Cach ra quyet dinh co retrain hay khong

Khong retrain ngay neu:

- Full AuraBeam da thang ro o `GSSR/MGR/FDR`.
- Diem yeu hien tai chu yeu la thieu baseline, thieu statistics, thieu qualitative.
- Reviewer co the bi thuyet phuc bang system-level evidence.

Nen retrain neu:

- `single vs ensemble` chua thuyet phuc.
- Recall tren hard cases qua thap.
- Weighted NMS khong giup nhieu.
- Gain cua full system bi gioi han boi detector.
- Training section khong du nghiem tuc cho journal muc tieu.

Neu retrain, phai lam theo protocol:

1. Khoa lai split.
2. Train lai cong bang cho single va ensemble.
3. Luu seed, augmentation, epoch, early stopping.
4. Bao cao tren cung mot test set.

## 7. Lich trinh de xuat 8 tuan

### Tuan 1

- Chot claim.
- Chot protocol.
- Chot metric.
- Chot experiment matrix.

### Tuan 2

- Implement day du baseline tracking.
- Implement cac co ablation can thiet.

### Tuan 3

- Chay perception ablation.
- Chay tracking baseline.
- Luu ket qua theo scenario va theo lan lap.

### Tuan 4

- Chay sensitivity analysis.
- Gom ket qua latency va stability.

### Tuan 5

- Tong hop `mean +- std`.
- Chay significance test.
- Kiem tra consistency ket qua.

### Tuan 6

- Tao hinh qualitative.
- Tao hinh pipeline.
- Tao trajectory plots.

### Tuan 7

- Viet lai Results.
- Viet lai Discussion.
- Lam sach limitations.

### Tuan 8

- Sua toan bo manuscript.
- So khop caption, notation, references.
- Chon journal phu hop va canh chinh format.

## 8. Checklist truoc khi gui Q2

Can dat duoc cac muc sau:

- [ ] Claim khoa hoc ro va nhat quan.
- [ ] Co baseline tracking day du.
- [ ] Co ablation cho ensemble, NMS, hold-time, switching.
- [ ] Co sensitivity analysis cho tham so chinh.
- [ ] Co `mean +- std`.
- [ ] Co significance test cho so sanh quan trong.
- [ ] Co hinh qualitative bat buoc.
- [ ] Co pipeline figure end-to-end.
- [ ] Bang ket qua khong loi format, khong lap so lieu.
- [ ] Training / implementation / manuscript khop nhau.
- [ ] Discussion va limitations trung thuc, co chieu sau.

## 9. Uu tien neu it thoi gian

Neu khong du thoi gian lam het, thu tu uu tien la:

1. Hoan thien `tracking baselines`
2. Them `adaptive switching ablation`
3. Bao cao `mean +- std`
4. Them qualitative figures
5. Chay significance test
6. Chay sensitivity analysis
7. Xem xet retrain

## 10. Dau ra cuoi cung mong muon

Sau workflow nay, bai bao phai chuyen tu:

- "He thong nay hoat dong kha tot tren vai scenario"

thanh:

- "Chung toi co mot system-level contribution ro rang, duoc kiem chung bang baseline day du, ablation co kiem soat, thong ke dang tin cay, va control-level metrics phu hop voi bai toan ADB."

Do la muc toi thieu de co co hoi nghiem tuc voi mot venue Q2.

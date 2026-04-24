# Q2 Post-Run Task Assignment

Tai lieu nay dung de giao viec cho cong su sau khi cac batch `A1-A4`, `B1-B2`, `B3-B4`, `C1-C4` da chay xong.

Muc tieu:

- khong dung lai o muc "da co so lieu"
- bien output raw thanh bang, hinh, va noi dung co the dua vao manuscript
- chia viec ro rang de moi nguoi co dau ra cu the

## 1. Dinh nghia "da xong so lieu"

Chi duoc xem la "da xong so lieu" khi dong thoi thoa cac dieu kien sau:

- moi batch da co du `run_01` den `run_05`
- moi config co du tat ca scenario can thiet
- da co CSV aggregate cho tung nhom
- khong co run hong, file thieu, hay so lieu bi lech folder

Neu chua du 4 dieu kien nay thi chua duoc chuyen sang buoc viet report.

## 2. File va thu muc chinh can dung

### Config

- `configs/q2_a1_a4_suite.json`
- `configs/q2_b1_b2_suite.json`
- `configs/q2_c1_c4_suite.json`

### Output raw

- `artifacts/results_q2_a1_a4`
- `artifacts/results_q2_b1_b2`
- `artifacts/results_q2_c1_c4`
- `artifacts/results_final_q2_lock`

### Bang tong hop

- `artifacts/tables/q2_a1_a4_results.csv`
- `artifacts/tables/q2_b1_b2_results.csv`
- `artifacts/tables/q2_c1_c4_results.csv`
- `artifacts/tables/final_evaluation_results_q2_lock.csv`

### Manuscript

- `report/q2_report.tex`

### Tai lieu quy trinh

- `md_folder/Q2_WORKFLOW.md`

## 3. Chia viec de xuat cho 4 nguoi

### Nguoi 1 - Data QC va aggregate owner

Phu trach:

- kiem tra tat ca folder run cua `A1-A4`, `B1-B2`, `C1-C4`, `B3-B4`
- dam bao moi config/scenario co du `run_01` den `run_05`
- aggregate lai CSV neu can
- lap danh sach cho nao thieu, cho nao bi loi

Dau ra phai nop:

- 1 bang tong hop trang thai cac run
- 4 file CSV aggregate cuoi cung
- 1 note ngan ghi ro config/scenario nao co van de

Checklist:

- [ ] `A1-A4` du 5 run moi scenario
- [ ] `B1-B2` du 5 run moi scenario
- [ ] `C1-C4` du 5 run moi scenario
- [ ] `B3-B4` du 5 run moi scenario
- [ ] CSV aggregate tao thanh cong
- [ ] khong co run bi trung ten sai folder

Lenh hay dung:

```powershell
python aggregate_results.py --results-root artifacts/results_q2_a1_a4 --output-csv artifacts/tables/q2_a1_a4_results.csv
python aggregate_results.py --results-root artifacts/results_q2_b1_b2 --output-csv artifacts/tables/q2_b1_b2_results.csv
python aggregate_results.py --results-root artifacts/results_q2_c1_c4 --output-csv artifacts/tables/q2_c1_c4_results.csv
python aggregate_results.py --results-root artifacts/results_final_q2_lock --output-csv artifacts/tables/final_evaluation_results_q2_lock.csv
```

### Nguoi 2 - Table builder

Phu trach:

- doc CSV aggregate
- map cot CSV vao cac bang trong manuscript
- trich them chi so chua co trong CSV tu `summary.json`
- chuan bi bang "gan cuoi" de dua vao `q2_report.tex`

Dau ra phai nop:

- 1 file note hoac spreadsheet map "cot CSV -> cot bang"
- so lieu day du cho cac bang:
  - A1-A4
  - B1-B4
  - C1-C4
  - bang B3/B4 final protocol
- danh sach chi so phai lay them tu `summary.json`

Checklist:

- [ ] xac dinh bang nao trong `q2_report.tex` dang con placeholder
- [ ] dien du cac cot mean/std tu CSV
- [ ] lay them `mode_switch_count` neu bang can
- [ ] danh dau ro cho nao chua co `p-value`
- [ ] khong nhap tay bang cach copy so lieu lung tung

Can tap trung vao cac bang placeholder sau:

- `tab:res_a_ablation`
- `tab:res_b_ablation`
- `tab:res_c_ablation`
- `tab:q2_controls`
- `tab:q2_occlusion`

### Nguoi 3 - Statistics va consistency owner

Phu trach:

- tinh them `p-value` cho cac so sanh chinh
- kiem tra xem so lieu trong CSV co hop ly khong
- doi chieu summary raw va bang aggregate
- viet ket luan ngan: khac biet nao co y nghia, khac biet nao khong

Dau ra phai nop:

- 1 file ket qua thong ke bo sung
- 1 bang `comparison -> p-value -> ket luan`
- 1 note "co du bang chung de claim hay chua"

So sanh toi thieu can co:

- `A1 vs A4`
- `B1 vs B2`
- `B2 vs B3`
- `B3 vs B4`
- `C3 vs C4`

Checklist:

- [ ] xac dinh dung metric so sanh chinh cho tung cap
- [ ] tinh `p-value` tren dung tap run
- [ ] khong dua ra claim "tot hon" khi so lieu khong ung ho
- [ ] danh dau limitation case rieng, khong gop vo dieu kien thanh cong

### Nguoi 4 - Manuscript integration owner

Phu trach:

- cap nhat `report/q2_report.tex`
- thay bang placeholder bang so lieu that
- viet lai Results va Discussion cho khop so lieu cuoi
- thay cac figure placeholder neu da co hinh

Dau ra phai nop:

- ban `q2_report.tex` da cap nhat
- danh sach figure con thieu
- danh sach placeholder chua thay duoc

Checklist:

- [ ] cap nhat bang A1-A4
- [ ] cap nhat bang B1-B4
- [ ] cap nhat bang C1-C4
- [ ] cap nhat bang negative controls va occlusion protocol
- [ ] sua text Results cho khop bang
- [ ] sua text Discussion cho khop claim
- [ ] khong de text noi mot kieu, bang ra mot kieu

## 4. Thu tu lam viec de tranh dung nhau

Lam theo thu tu sau:

1. Nguoi 1 xac nhan output va aggregate xong
2. Nguoi 2 lap bang so lieu tam
3. Nguoi 3 tinh `p-value` va xac nhan consistency
4. Nguoi 4 moi cap nhat manuscript

Khong nen de Nguoi 2 va Nguoi 4 cung sua bang trong `q2_report.tex` cung luc.

## 5. Nhung viec "nghe nho" nhung bat buoc phai lam

- kiem tra ten scenario trong CSV va trong manuscript co trung nhau khong
- kiem tra `B3` va `C3` co bi nham nhau khong
- kiem tra metric full-sequence va occlusion-window co bi tron lan khong
- kiem tra bang nao dang viet "mean of five replays"
- kiem tra config nao dung `best_conf`, config nao dung policy khac
- kiem tra folder output co bi lay nham `results_final_eval` va `results_final_q2_lock` khong

## 6. Tieu chi hoan thanh cho tung nguoi

### Nguoi 1 xong khi:

- co du 4 file CSV aggregate cuoi
- co note xac nhan khong thieu run

### Nguoi 2 xong khi:

- tat ca bang co so lieu da co du nguon de dien
- biet ro cot nao tu CSV, cot nao tu summary raw

### Nguoi 3 xong khi:

- co bang `p-value`
- co note ngan ve significance va limitation

### Nguoi 4 xong khi:

- manuscript khong con bang placeholder ve so lieu chinh
- Results va Discussion khop voi so lieu cuoi

## 7. Dau ra cuoi cung mong muon

Sau khi 4 nguoi lam xong, nhom phai co:

- CSV tong hop cho A, B, C, final B3/B4
- bang co the copy vao manuscript
- ket qua thong ke bo sung
- manuscript cap nhat
- danh sach figure con thieu neu chua kip lam

## 8. Ghi chu quan trong

Chay xong so lieu khong co nghia la xong paper.

Neu chi chay xong ma khong co:

- aggregate sach
- kiem tra consistency
- `p-value`
- table integration
- Results/Discussion update

thi nhom moi chi xong phan "raw experiment", chua xong phan "paper-ready evidence".

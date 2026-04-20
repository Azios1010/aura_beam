# Workflow Hướng Tới Bài Báo Q2 Cho AuraBeam

## 1. Mục tiêu của workflow

File này chuyển các ý tưởng cải tiến thành một lộ trình có thể thực thi để đưa `AuraBeam` từ mức độ đồ án / paper sơm lên mức độ bài báo Q2.

Mục tiêu không phải là "thêm thật nhiều kết quả", mà là:

- Chốt đóng góp khoa học rõ ràng.
- Xây dựng protocol thí nghiệm chặt chẽ.
- Chạy ablation đầy đủ và có ý nghĩa.
- Báo cáo thống kê đúng chuẩn.
- Trình bày kết quả sạch, thuyết phục, và khó bị reviewer bắt lỗi.

## 2. Định vị bài báo

Trước khi làm thêm experiment, cần chốt lại bài này là một paper về `system robustness for ADB under glare-induced camera failure`, không phải paper phát minh detector mới.

Ba claim nên được giữ ổn định trong toàn bộ bài:

1. `Ensemble + Weighted NMS` giúp tăng robustness của perception dưới blooming, glare, scattering.
2. `3D KF + pseudo-radar + adaptive switching` giúp duy trì tracking và glare suppression khi camera bị mù.
3. Cải thiện perception/tracking phải được chứng minh ở mức `control outcome`, không chỉ ở mức `mAP` hay `RMSE`, mà bằng `GSSR`, `MGR`, `FDR`.

Nếu một experiment không phục vụ ít nhất một claim trên, cần xem xét bỏ.

## 3. Nguyên tắc ưu tiên

Thứ tự ưu tiên đúng:

1. Siết protocol và evaluation.
2. Bổ sung baseline và ablation.
3. Báo cáo thống kê.
4. Làm sạch bảng, hình, narrative.
5. Chỉ retrain model khi có bằng chứng detector là nút thắt chính.

Không nên retrain ngay nếu:

- Baseline chưa đầy đủ.
- Ablation chưa tách được đóng góp từng module.
- Chưa có `mean +- std`.
- Chưa có significance test.
- Chưa có hình định tính quan trọng.

## 4. Kế hoạch tổng thể theo giai đoạn (tối ưu cho 3 tuần)

### Giai đoạn 1. Khóa protocol nghiên cứu (Ngày 1-2)

Mục tiêu:
- Có một protocol có thể lặp lại.
- Xác định rõ dữ liệu nào dùng để train, val, test.
- Xác định metric chính và metric phụ.

Công việc:
1. Chốt lại các split: `train`, `validation`, `golden test`
2. Ghi rõ: số lượng mẫu mỗi split, tiêu chí chia split
3. Khóa metric chính: `GSSR`, `MGR`, `FDR`
4. Khóa metric phụ: `RMSE_xy`, `JR%`, latency / FPS
5. Khóa seed và cách lặp lại: `n = 3` tối thiểu

Deliverable:
- Một file cấu hình experiment.
- Bảng protocol trong paper.

### Giai đoạn 2. Hoàn thiện baseline tracking (Ngày 3-7)

Mục tiêu:
- Chứng minh rõ phần gain đến từ đâu.
- Tách bạch perception gain và fusion gain.

Bắt buộc phải có 4 baseline tracking:
1. `raw detector`
2. `detector + 2D KF`
3. `detector + 3D KF without mode switching`
4. `detector + 3D KF + pseudo-radar + adaptive switching`

Ý nghĩa khoa học:
- `(1) -> (2)` do tác động của smoothing 2D.
- `(2) -> (3)` do tác động của state 3D nhưng chưa có adaptive logic.
- `(3) -> (4)` do tác động thực sự của `adaptive switching`.

Metric cần báo cáo:
- `RMSE_xy`, `JR%`, `GSSR`, `MGR`, `FDR`

Deliverable:
- 1 bảng tracking baseline comparison.
- 1 hình trajectory qualitative: lightning hoặc rain.

### Giai đoạn 3. Ablation quan trọng (Ngày 8-9)

Mục tiêu:
- Chứng minh từng thành phần có giá trị riêng (tác động riêng).

Ablation bắt buộc:
1. `single model vs ensemble` - kiểm chứng Weighted NMS
2. `fixed full-observation vs adaptive switching` - kiểm chứng điều chỉnh theo camera state

Deliverable:
- 1 bảng ablation chính (ensemble + switching).

### Giai đoạn 4. Báo cáo thống kê (Ngày 10-11)

Mục tiêu:
- Nâng kết quả từ "một lần chạy đẹp" thành "kết quả đáng tin cây".

Bắt buộc:
- Tính `mean +- std` cho các baseline và ablation (n=3).
- Chạy `paired t-test` cho so sánh quan trọng:
  - single vs ensemble
  - 3D KF without switching vs 3D KF + adaptive switching
  - best baseline vs full AuraBeam

Deliverable:
- Bảng kết quả có cột: mean, std, p-value.

### Giai đoạn 5. Nâng cấp qualitative evidence (Ngày 12-14)

Mục tiêu:
- Giảm sự trừu tượng.
- Cho thấy system hoạt động đúng ở các failure case.

Bắt buộc phải có các hình sau:
1. `YOLO-only fail` -> `AuraBeam recover`
2. `Occlusion interval` và tracking stability

Gợi ý:
- Nên có caption rất cụ thể.
- Mỗi hình phải phục vụ một claim.

Deliverable:
- 1 figure qualitative comparison (failure + recovery).
- 1 figure timeline (nếu có thời gian).

### Giai đoạn 6. Làm sạch manuscript (Ngày 15-21)

Mục tiêu:
- Biến bản thảo thành bản gửi journal.

Danh sách bắt buộc:
1. Sửa các bảng đã có, đảm bảo format và số liệu không có lỗi.
2. Viết Results: miêu tả bảng và hình, hoàn thiện.
3. Viết Discussion: giải thích vì sao, nối về claim.
4. Sửa limitations: trung thực và có construction.
5. Kiểm tra cross-reference: banner, hình, notation.

Deliverable:
- Bản `report.tex` đã đồng nhất notation, bảng, hình, caption.

## 5. Experiment matrix để thực thi

### Nhóm A. Perception

| ID | Cấu hình | Mục đích |
| --- | --- | --- |
| A1 | single model M1 | baseline specialist |
| A2 | single model M2 | baseline generalist |
| A3 | ensemble + standard NMS | tách tác động ensemble và fusion rule |
| A4 | ensemble + Weighted NMS | cấu hình đề xuất |

Metric:

- mAP@0.5
- Precision
- Recall
- GSSR sau khi đưa qua pipeline control nếu cần

### Nhóm B. Tracking and fusion

| ID | Cấu hình | Mục đích |
| --- | --- | --- |
| B1 | raw detector | baseline tối thiểu |
| B2 | detector + 2D KF | gain từ smoothing 2D |
| B3 | detector + 3D KF no switching | gain từ state 3D |
| B4 | detector + 3D KF + pseudo-radar + adaptive switching | full AuraBeam |

Metric:

- RMSE_xy
- JR%
- GSSR
- MGR
- FDR

### Nhóm C. Control and scheduling

| ID | Cấu hình | Mục đích |
| --- | --- | --- |
| C1 | no hold-time | baseline |
| C2 | hold-time enabled | anti-flicker |
| C3 | fixed observation | không có switching |
| C4 | adaptive switching | cấu hình đề xuất |

Metric:

- GSSR
- MGR
- FDR
- box command change rate

### Nhóm D. Sensitivity

| Nhóm tham số | Biến |
| --- | --- |
| detector threshold | `tau_conf` |
| fusion threshold | `tau_NMS` |
| temporal smoothing | `T_h` |
| filter dynamics | `Q`, `R` |

## 6. Cách ra quyết định có retrain hay không

Không retrain ngay nếu:

- Full AuraBeam đã thắng rõ ở `GSSR/MGR/FDR`.
- Điểm yếu hiện tại chủ yếu là thiếu baseline, thiếu statistics, thiếu qualitative.
- Reviewer có thể bị thuyết phục bằng system-level evidence.

Nên retrain nếu:

- `single vs ensemble` chưa thuyết phục.
- Recall trên hard cases quá thấp.
- Weighted NMS không giúp nhiều.
- Gain của full system bị giới hạn bởi detector.
- Training section không đủ nghiêm túc cho journal mục tiêu.

Nếu retrain, phải làm theo protocol:

1. Khóa lại split.
2. Train lại công bằng cho single và ensemble.
3. Lưu seed, augmentation, epoch, early stopping.
4. Báo cáo trên cùng một test set.

## 7. Lịch trình đề xuất 3 tuần

### Tuần 1 (Ngày 1-7): Khóa protocol và chạy baseline

**Ngày 1-2: Đồng nhất và chốt**
- Chốt claim và 3 claim chính.
- Chốt protocol: train/val/test split, metric, n=3 lập tối thiểu.
- Chốt experiment matrix: chọn 6-8 config tối quan trọng (bổ sung config phụ).
- Chốt bảng caption và hình layout template.

**Ngày 3-5: Implement và chạy baseline**
- Implement đầy đủ 4 baseline tracking: B1, B2, B3, B4.
- Implement ablation quan trọng: ensemble (A1 vs A4), switching (B3 vs B4).
- Chạy trên golden test set, lưu chi tiết kết quả theo scenario.

**Ngày 6-7: Kiểm tra kết quả sơ cấp**
- So sánh baseline tracking: RMSE_xy, JR%, GSSR, MGR, FDR.
- Kiểm tra xem baseline đã rõ chưa (phải thấy rõ vì sao B4 tốt hơn B1).
- Nếu baseline còn mố tay, dừng lại debugg immediately.

### Tuần 2 (Ngày 8-14): Chạy ablation đầy đủ và statistics

**Ngày 8-9: Chạy ablation chính (Group A, C)**
- A1, A2, A3, A4 (perception ablation).
- C1, C2, C3, C4 (control ablation).
- Trên cùng golden test set, lưu lại kết quả.

**Ngày 10-11: Tổng hợp và tính thống kê**
- Tính `mean +- std` cho từng ablation trên n=3 lần chạy.
- Tính `paired t-test` hoặc `Wilcoxon` cho so sánh chính:
  - single vs ensemble
  - 2D KF vs 3D KF without switching
  - fixed vs adaptive switching
  - best baseline vs full AuraBeam
- Ghi lại p-value và kết luận.

**Ngày 12-14: Tạo hình và qualitative evidence**
- Tạo 2-3 hình qualitative: failure case + recovery.
- Tạo timeline figure: occlusion interval, grid suppression.
- Tạo bảng baseline tracking và ablation comparison.
- Chuẩn bị hình pipeline dùng bỏ (có thể để sang tuần 3 nếu cần).

### Tuần 3 (Ngày 15-21): Viết lạp và hoàn thiện

**Ngày 15-17: Viết Results và Discussion**
- Viết Results theo bảng và hình đã có.
- Viết Discussion từ bằng chứng: tách bảg gain, ưu tiên nào chính?
- Nối kết nối tới claim:
  - Ensemble + Weighted NMS có tăng robustness không? (đưa bảng A).
  - 3D KF + switching có duy trì tracking không? (đưa bảng B).
  - Control outcome có từng giảm không? (đưa bảng C).

**Ngày 18-19: Làm sạch manuscript**
- Sửa notation, notation khớp với implementation.
- Sửa bảng: format, unit, footnote.
- Đảm bảo caption: mỗi hình phải rõ mục đích.
- Bỏ placeholder, giữ chỉ hình thức.
- Kiểm tra cross-reference giữa các bảng/hình.

**Ngày 20-21: Xem xét toàn thể và finalize**
- Đọc lại toàn bộ: intro -> method -> result -> discussion -> conclusion cần thảo xuất?
- Kiểm tra limitations: trung thực, không lỏ cảm? 
- Sửa references, abstract, keywords.
- Đóng góp khoa học đã rõ rõ chưa?

## 8. Checklist trước khi gửi Q2 (3 tuần - bắt buộc vs tùy chọa)

### Bắt buộc (phải có)

- [ ] Claim khoa học rõ và nhất quán (tối đa 3 claim).
- [ ] Có baseline tracking đầy đủ (B1, B2, B3, B4).
- [ ] Có ablation cho ensemble và adaptive switching (A1 vs A4, B3 vs B4).
- [ ] Có `mean +- std` (n >= 3).
- [ ] Có significance test cho so sánh chính (paired t-test).
- [ ] Có hình qualitative: failure + recovery (ít nhất 2 hình).
- [ ] Bảng tracking baseline và ablation: có cột mean, std, p-value.
- [ ] Training / implementation / manuscript khớp nhau.
- [ ] Discussion logic: bằng chứng -> interpretations -> claim.

### Tùy chọa (nếu có đủ thời gian)

- [ ] Pipeline figure end-to-end.
- [ ] Sensitivity analysis cho 1 tham số chính.
- [ ] Trajectory plot timeline.
- [ ] Bảng ablation phụ (hold-time, NMS variants).

### Dừng retrain trừ khi:

- [ ] Ensemble gain từ "may mắn" không phải từ design (phải có bằng chứng).
- [ ] Single baseline recall < 50% trên hard case (lightning/heavy rain).

## 9. Ư u tiên nếu ít thời gian (3 tuần)

Với 3 tuần, lần lượt ưu tiên:

1. Hoàn thiện `tracking baselines` (B1-B4) - bắt buộc.
2. Chạy ablation quan trọng: `ensemble` và `adaptive switching` - bắt buộc.
3. Báo cáo `mean +- std` và `paired t-test` - bắt buộc.
4. Tạo qualitative figures (failure case + recovery) - bắt buộc.
5. Pipeline figure và timeline - nếu đủ thời gian.
6. Sensitivity analysis - bỏ, chỉ chọa một tham số quan trọng nhất nếu có đủ thời gian (ưu tiên `tau_conf`).
7. Retrain - bỏ, dùng khi có bằng chứng thực sự cần thiết.

## 10. Đầu ra cuối cùng mong muốn

Sau workflow này, bài báo phải chuyển từ:

- "Hệ thống này hoạt động khá tốt trên vài scenario"

thành:

- "Chung tôi có một system-level contribution rõ ràng, được kiểm chứng bằng baseline đầy đủ, ablation có kiểm soát, thống kê đáng tin cậy, và control-level metrics phù hợp với bài toán ADB."

Đó là mục tối thiểu để có cơ hội nghiêm túc với một venue Q2.

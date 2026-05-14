# Script Phản Biện Học Thuật — AuraBeam
> **Vai trò:** Giám khảo khoa học hà khắc | Mục tiêu: Bắt bẻ mọi điểm yếu học thuật trước khi bảo vệ

---

## 1. NHỮNG ĐIỂM QUAN TRỌNG NHẤT (Góc nhìn giám khảo)

### 1.1 Cái gì thực sự mới

1. **GSSR metric** — Đây là đóng góp kỹ thuật sắc nét nhất. Thay vì dừng ở pixel-space (mAP, Precision, Recall), nhóm định nghĩa một metric trực tiếp trên LED grid 8×8 (Eq. 4–5), kết nối perception với actuation. Đây là khoảng trống thực sự trong literature: VIL/HIL papers (Cheng et al., Langer et al.) tập trung functional verification, không quan tâm glare-induced collapse.

2. **Nghịch lý B3 > B4** — Kết quả chính của bài **không phải là thành công**, mà là **thất bại có kiểm soát**: B4 (adaptive) thua B3 (fixed) ở occlusion GSSR (77.19% vs 84.60%, Table 5). Đây là honest negative result — hiếm và có giá trị nếu bảo vệ đúng cách.

3. **Pseudo-Radar như depth surrogate** — Ý tưởng dùng `Z(t) = Z₀ − v_app·t` (Eq. 1) thay thế radar vật lý là pragmatic và low-cost. Tổng chi phí phần cứng chỉ ~$23 (Table 1).

4. **Protocol 5-case có cấu trúc** — Tách biệt rõ negative controls, targeted degradation, và limitation case. Đây là thiết kế evaluation nghiêm túc, phòng thủ tốt trước cáo buộc cherry-picking.

5. **HIL closed-loop** — Kết nối software → Arduino → LED matrix → GSSR là end-to-end thực sự, không chỉ simulation.

### 1.2 Cái dễ bị đánh đổ

6. **Dataset quá nhỏ** — 953 frames tổng (Table 2): mountain=76, urban=204, rain=219, fog=215, thunder=239. Chỉ 76 frames cho mountain curve là cực kỳ mỏng.

7. **5 lần replay deterministic** — Bài thừa nhận "five offline replays are deterministic executions of the same fixed scenarios" (Section 4.1). Wilcoxon p-values (Table 7) trên data deterministic là questionable.

8. **Detector fogging cực tệ** — mAP@0.5 = 0.009, Recall = 0.056 (Table 4) trên foggy night. Hệ thống gần như mù hoàn toàn, nhưng vẫn báo GSSR = 98.25% — điều này cần giải thích thuyết phục.

9. **Pseudo-Radar không có ground truth** — `v_app` là nominal prior, không đo thực. Error tăng bậc hai: `ΔZ(t) = −½·a_real·t²` (Eq. 3).

10. **LED grid 8×8 quá thô** — 64 cells cho toàn bộ field of view. Một cell sai = sai hoàn toàn. Không phản ánh production ADB.

---

## 2. LOGIC CỐT LÕI CẦN NẮM VỮNG

### 2.1 Mối liên hệ giữa các module

```
[Camera] → [M1: YOLOv5] ─┐
                          ├→ [Weighted NMS] → d_t=[cx,cy,w,h,ŝ]
[Camera] → [M2: YOLOv8] ─┘
                               ↓
[Pseudo-Radar] → Z(t)=Z₀-v·t  ↓
                               ↓
                    [Adaptive KF3D]
                    ŝ ≥ τ_conf (0.35)?
                    L<2 consecutive low?
                     YES → H_full, R_full (Eq.6-8)
                     NO  → H_occ, R_occ  (Eq.9-11)
                               ↓
                    x̂_k = [cx, cy, Z, ċx, ċy, Ż]
                               ↓
                    [Zone Mapping Eq.14] → g_col, g_row
                    [Depth Policy Table 3] → duty cycle
                    [Hysteresis T_h=5 Eq.15]
                               ↓
                    [Arduino LED 8×8] → GSSR
```

### 2.2 Tại sao so sánh B3 vs B4 là trung tâm

- B1→B2: Chứng minh KF cần thiết (RMSE: 122→56 px, Table 5)
- B2→B3: Chứng minh depth cần thiết (GSSR: 71→91%, Table 5)
- **B3→B4: Câu hỏi nghiên cứu thực sự** — adaptive switching có giúp không?

Trả lời: **Không nhất quán**. Fog=tie, Thunder=tie, Rain=B4 thua rõ (GSSR: 77.78%→55.56%, Table 6). Đây là honest finding, không phải thất bại.

### 2.3 Tại sao B3 mạnh hơn tưởng?

Process noise Q cực nhỏ: `Q = diag(0.08, 0.08, 0.03, 0.03, 0.03, 0.02)` (Eq.4). Filter trust motion model hơn measurement → smoother output → ít flicker trên LED grid. Đây là intentional low-pass filter design, không phải lỗi tuning.

---

## 3. NHỮNG ĐIỂM DỄ BỊ CÔNG KÍCH NHẤT

### 3.1 Giả định của Pseudo-Radar

**Lỗ hổng:** `Z(t) = Z₀ − v_app·t` giả định constant velocity. Eq. 2–3 thừa nhận error `ΔZ = −½·a·t²`. Với braking a≈−0.5g: error ≈ 2.45m sau 1 giây. Với a≈−0.9g: error ≈ 4.4m. Không có validation nào so với ground truth depth thực.

**Nguy hiểm hơn:** `Z₀` được estimate từ pinhole camera model với prior vehicle width. Nếu xe khác kích thước (xe tải, xe máy), `Z₀` sai ngay từ đầu. Bài không báo cáo sensitivity analysis này.

### 3.2 Dataset quá nhỏ và thiếu đa dạng

- 953 frames tổng từ 5 video clips (không phải 5 independent sequences từ nhiều nguồn)
- Mountain curve chỉ 76 frames — khoảng 2.5 giây video ở 30fps
- Không có multi-vehicle scenarios
- Không có oncoming trucks, motorcycles, bicycles
- Tất cả videos có vẻ từ cùng một camera setup

### 3.3 Wilcoxon p-values trên data deterministic

Table 7 báo cáo Wilcoxon signed-rank p-values như `7.9×10⁻⁵` và `0.025`. Bài thừa nhận 5 replays là "deterministic executions". P-value từ 5 data points deterministic **không có ý nghĩa thống kê thực sự**. Giám khảo có thể hỏi thẳng: "Tại sao dùng Wilcoxon test khi data không phải independent random samples?"

### 3.4 GSSR = 98.25% khi detector gần như mù

Foggy night: detector mAP@0.5=0.009, Recall=0.056 — nhưng occlusion GSSR B3=B4=98.25% (Table 6). Điều này chỉ có thể xảy ra nếu **Kalman filter propagate trajectory đúng từ trước khi fog**, không phải vì detector hoạt động. Cần giải thích rõ: đây là success của KF memory, không phải success của adaptive switching.

### 3.5 FDR cao ở negative controls

Mountain curve: FDR = 15.79% (Table 5). Tức là 15.79% frames, hệ thống suppress LED khi không có xe. Trên đường cua ban đêm, điều này có thể gây mất visibility cho driver. Bài không thảo luận safety implication này.

### 3.6 Không so sánh với state-of-the-art

Không có baseline nào từ literature được so sánh trực tiếp. DeepSORT, ByteTrack, hay bất kỳ tracking method nào khác đều vắng mặt. Nhóm so sánh internal ablations (B1-B4), không phải external baselines.

### 3.7 Real-time và latency

Latency trung bình: B3=277.65ms/frame, B4=282.12ms/frame (Section 5.4). Tức là ~3.6fps — **không phải real-time** (thường yêu cầu ≥30fps cho automotive). Bài không thảo luận về điều này một cách trực diện.

### 3.8 LED grid 8×8 không đại diện

Production ADB có thể có hàng trăm hoặc hàng nghìn pixels (matrix headlights). 8×8=64 cells là quá coarse. IoU≥0.5 trên 64 cells rất dễ đạt, nhưng trên grid thực tế sẽ khó hơn nhiều.

---

## 4. CÂU HỎI GIÁM KHẢO KHẮC NGHIỆT + KỊCH BẢN BẮT BẺ

### Q1: "Nếu B4 thua B3 trên aggregate, tại sao bài báo này đáng publish?"

**Kịch bản bắt bẻ:** "Bạn tốn một paper để chứng minh rằng giải pháp phức tạp hơn (adaptive switching) không tốt hơn giải pháp đơn giản (fixed). Đây là negative result. Tại sao điều này có giá trị?"

**Trả lời hiệu quả:**
> "Chính xác — đây là **honest negative result**, và đó là đóng góp. Literature thường chỉ publish positive results. Chúng tôi chứng minh rằng confidence-based switching **không phải universal solution** — nó hoạt động trong fog và thunder (GSSR match 100%), nhưng fail trong rain (GSSR: 77.78%→55.56%, Table 6). Điều quan trọng là chúng tôi đã xây dựng framework để **đo lường được** khi nào nó fail — thông qua GSSR metric và 5-case protocol. Biết giới hạn của một phương pháp là bước đầu để cải thiện nó."

---

### Q2: "Pseudo-Radar của bạn không phải radar. Tại sao không dùng radar thật?"

**Kịch bản bắt bẻ:** "Bạn gọi nó là Pseudo-Radar nhưng thực chất chỉ là linear extrapolation với constant velocity assumption. Điều này trivial và không novel."

**Trả lời hiệu quả:**
> "Đúng — Pseudo-Radar (Eq.1) là intentionally simple. Điểm mấu chốt không phải accuracy của depth estimate, mà là **independence from camera**. Khi camera saturated bởi headlight glare, radar-camera fusion literature (Yao et al., Deng et al.) đã chứng minh value của camera-independent modality. Chúng tôi instantiate nguyên lý đó trong low-cost ADB setting ($23 total hardware, Table 1). Giới hạn của approximation được định lượng rõ: ΔZ = −½·a·t² (Eq.3), với a≈−0.5g thì error ≈2.45m sau 1 giây — chấp nhận được cho short dropout intervals. Mục tiêu của framework là research platform, không phải production radar replacement."

---

### Q3: "953 frames là quá ít. Kết quả có thể generalize không?"

**Kịch bản bắt bẻ:** "Mountain curve chỉ 76 frames, tương đương ~2.5 giây. Làm sao bạn có thể rút ra kết luận từ 2.5 giây video?"

**Trả lời hiệu quả:**
> "Giới hạn dataset được thừa nhận trong Limitations (Section 5.5). Tuy nhiên, 953 frames được chọn là **Golden Test Set** — manually annotated, không dùng cho training. Mục đích không phải generalization rộng, mà là **controlled ablation** trong fixed protocol. Các negative controls (76+204 frames) đủ để verify rằng B3/B4 không degrade normal operation. Targeted cases (215+239 frames) đủ để observe switching behavior trong annotated degradation windows. Đây là proof-of-concept research platform, không phải large-scale benchmark. Future work cần broader validation — điều này được ghi nhận rõ trong Conclusion."

---

### Q4: "Wilcoxon p-value trên 5 replays deterministic là gì?"

**Kịch bản bắt bẻ:** "5 lần replay identical scenario cho ra identical results. P-value từ 5 điểm deterministic không có nghĩa gì về statistical significance."

**Trả lời hiệu quả:**
> "Hoàn toàn đúng — và bài báo thừa nhận điều này một cách minh bạch: 'these values should not be interpreted as evidence from independent stochastic trials; they serve solely as protocol-level consistency checks' (Section 5.5, caption Table 7). P-values ở đây không phải inferential statistics. Chúng là **directional consistency checks** — xác nhận rằng mỗi design change produces consistent direction trong fixed protocol. Primary evidence cho main claim là scenario-level occlusion metrics (Table 6), không phải p-values."

---

### Q5: "GSSR=98.25% khi fog detector recall=0.056 — có vẻ mâu thuẫn?"

**Kịch bản bắt bẻ:** "Detector gần như mù (recall 5.6%) nhưng GSSR 98%. Đây là contradiction hay magic?"

**Trả lời hiệu quả:**
> "Đây không phải mâu thuẫn — đây là bằng chứng cho **value của KF memory**. Trước khi fog onset, detector đã acquire target và KF3D đã initialize state vector x̂ với [cx, cy, Z, ċx, ċy, Ż] (Eq.5). Trong fog window, Kalman predict step (Eq.12-13) propagates trajectory qua motion model F (Eq.3). Với Q cực nhỏ (Eq.4), filter tin tuyệt đối vào motion model — suppression region ít di chuyển = ít miss trên LED grid. GSSR=98.25% đo **actuation continuity**, không phải detector accuracy. Đây chính xác là lý do tại sao GSSR là primary metric thay vì mAP."

---

### Q6: "Tại sao không so sánh với DeepSORT, ByteTrack, hay BoT-SORT?"

**Kịch bản bắt bẻ:** "Không có external baseline nào. Làm sao biết KF3D của bạn tốt hơn state-of-the-art trackers?"

**Trả lời hiệu quả:**
> "Câu hỏi công bằng. Scope của paper là **ADB-specific framework**, không phải general tracker benchmark. DeepSORT/ByteTrack được thiết kế cho multi-object tracking với Re-ID — không có depth-aware state hay observation mode switching. Chúng tôi so sánh với trong cùng pipeline (B1-B4, Table 5) để isolate effect của từng component. Incorporating external trackers là interesting future direction, nhưng ngoài scope của câu hỏi nghiên cứu: 'does adaptive observation switching improve ADB actuation?' Câu hỏi đó không cần external tracker baseline."

---

### Q7: "277ms/frame không phải real-time. ADB cần real-time thì sao?"

**Kịch bản bắt bẻ:** "3-4fps là không đủ cho automotive safety application."

**Trả lời hiệu quả:**
> "Đúng — và đây là một trong các limitations được thừa nhận. Bottleneck là dual-model inference (YOLOv5 + YOLOv8) trên CPU/GPU không optimize. Platform dùng AMD Ryzen 5 7535HS, không phải automotive-grade hardware. Framework này là **research platform** để study degradation behavior, không phải production system. Real-time deployment sẽ cần model quantization, TensorRT optimization, hoặc single-model pipeline. Mục tiêu của paper là establish evaluation methodology (GSSR + 5-case protocol), không phải ship production code."

---

### Q8: "FDR=15.79% ở mountain curve có nghĩa là gì về safety?"

**Kịch bản bắt bẻ:** "15.79% frames hệ thống dim headlight không cần thiết. Trên đường cua ban đêm, điều này nguy hiểm không?"

**Trả lời hiệu quả:**
> "FDR 15.79% (Table 5) ở mountain curve là trade-off được observe. Nguyên nhân: hysteresis hold-time T_h=5 frames (Eq.15) giữ suppression sau khi target disappears — conservative safety choice để reduce MGR. FDR tăng = system occasionally dims khi không cần. Đây là trade-off tường minh: MGR (miss glare) vs FDR (unnecessary dim). Trong ADB context, missing oncoming glare thường được coi là nguy hiểm hơn unnecessary dim — driver vẫn thấy đường, chỉ hơi tối hơn. Hold-time T_h có thể tune down để reduce FDR, nhưng đó là hyperparameter study nằm ngoài scope hiện tại. Bài báo report cả hai metrics để reader có đủ thông tin."

---

## 5. CHECKLIST TỰ KIỂM TRA TRƯỚC KHI BẢO VỆ

### Số liệu phải nhớ chính xác (không được tra cứu):

| Metric | Giá trị |
|--------|---------|
| Tổng frames Golden Test Set | 953 frames (Table 2) |
| Hardware cost | ~$23 (Table 1) |
| B3 occlusion GSSR (aggregate) | 84.60% |
| B4 occlusion GSSR (aggregate) | 77.19% |
| B3→B4 occlusion GSSR drop | −7.41 pp |
| Rain: B3 occlusion GSSR | 77.78% |
| Rain: B4 occlusion GSSR | 55.56% |
| Fog: B3=B4 occlusion GSSR | 98.25% |
| Thunder: B3=B4 occlusion GSSR | 77.78% |
| RMSE B1→B2 improvement | 122.32 → 56.16 px |
| GSSR B2→B3 improvement | 71.10% → 91.10% |
| Fog detector mAP@0.5 | 0.009 |
| Fog detector Recall | 0.056 |
| τ_conf threshold | 0.35 |
| Hold-time T_h | 5 frames (~167ms) |
| Frame latency B3/B4 | 277.65ms / 282.12ms |
| YOLOv5 five-case mAP@0.5 | 0.306 |
| YOLOv8 five-case mAP@0.5 | 0.243 |
| Ensemble (A4) five-case mAP@0.5 | 0.292 |
| Mountain curve GSSR (B3=B4) | 84.21% |
| Urban night GSSR (B3=B4) | 95.59% |

### Tài liệu cần mang theo:
- [ ] Bản in q2_report.tex (full paper)
- [ ] Table 5 (B1-B4) và Table 6 (B3 vs B4 occlusion) print riêng, highlight màu
- [ ] Figure fogging_switch_timeline (Fig.10) và rain_limitation_timeline (Fig.11)
- [ ] Bản tóm tắt 5-case protocol (Table 3)
- [ ] Equation list: Eq.1 (Pseudo-Radar), Eq.4 (Q matrix), Eq.15 (Hysteresis)
- [ ] Slide diagram pipeline (Module A→E)

### Điều cần làm trước bảo vệ:
- [ ] Đọc lại phần Limitations (Section 5.5) — giám khảo sẽ probe từng điểm
- [ ] Luyện giải thích tại sao B4 thua B3 là CONTRIBUTION, không phải failure
- [ ] Chuẩn bị giải thích GSSR=98.25% khi recall=0.056 (fog case)
- [ ] Chuẩn bị trả lời về real-time (277ms bottleneck)
- [ ] Nắm rõ tại sao p-values trong Table 7 không phải inferential statistics
- [ ] Biết cách phân biệt MGR vs FDR vs MR (Eq.6,7,8)

---

## 6. CHIẾN THUẬT TRẢ LỜI

### Khi không biết câu trả lời:

> "Câu hỏi của thầy/cô chạm đúng vào một giới hạn của nghiên cứu này. Chúng tôi chưa có dữ liệu để trả lời trực tiếp, nhưng framework của chúng tôi được thiết kế để extend theo hướng đó — cụ thể là [pivot sang limitation đã được document trong Section 5.5]."

**Tuyệt đối không:**
- Đoán số liệu
- Nói "tôi không biết" và dừng lại
- Cãi lại khi giám khảo đúng

---

### Khi bị ép vào chân tường (bị bắt lỗi logic thực):

**Bước 1 — Thừa nhận:**
> "Thầy/cô đúng — đây là một limitation thực sự của thiết kế hiện tại."

**Bước 2 — Contextualize:**
> "Tuy nhiên, trong scope của một research platform với mục tiêu là [X], điều này là acceptable vì [Y]."

**Bước 3 — Future work:**
> "Đây chính xác là lý do tại sao future work section của chúng tôi đề xuất [Z]."

**Ví dụ cụ thể — bị tấn công về dataset size:**
> "Đúng — 953 frames là nhỏ. Nhưng mục tiêu không phải benchmark generalization, mà là controlled ablation trong fixed protocol. 5-case structure (negative controls + targeted + limitation) cho phép chúng tôi draw bounded conclusions. Extension đến large-scale real-world validation là bước tiếp theo rõ ràng."

---

### Khi bị hỏi về thứ ngoài paper:

> "Câu hỏi rất hay về [topic X]. Trong nghiên cứu này chúng tôi không address [X] vì scope được giới hạn ở [Y]. Nhưng literature như [reference liên quan] có examine [X] và kết quả của họ consistent với/khác với approach của chúng tôi vì..."

---

### Chiến thuật xoay hướng sang đóng góp tích cực:

Khi bất kỳ câu hỏi nào khó, pivot về **3 đóng góp core**:

1. **GSSR metric** — "Đây là actuation-aware metric đầu tiên kết nối perception với LED grid suppression, bổ sung cho pixel-space metrics không capture downstream behavior."

2. **5-case protocol với honest negative result** — "Chúng tôi không chỉ publish khi B4 thắng. Chúng tôi publish cả khi B4 thua (rain case) vì protocol đủ rigorous để detect điều đó."

3. **$23 HIL platform** — "Framework này reproducible cho bất kỳ lab nào — không cần automotive-grade hardware để study ADB degradation behavior."

---

### Câu mở đầu chuẩn khi bị tấn công mạnh:

> "Cảm ơn câu hỏi sắc bén này — đây chính xác là loại bắt bẻ mà chúng tôi anticipate khi thiết kế evaluation protocol. Để trả lời trực tiếp..."

---

*Script này được tạo dựa trên full text của q2_report.tex. Mọi số liệu có thể trace về Table/Figure/Equation cụ thể trong paper.*

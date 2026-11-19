# Báo cáo Day 09 — Nguyễn Chí Tài, 2A202603223

## 1. Kết luận trước

**Hold.** Loại 19/224 ảnh ở intake, xuất **205 ảnh** dưới dạng bản nháp. Sau sửa và duyệt mô phỏng 80 ảnh: **0 lỗi bắt buộc**, còn **38/205 ảnh chưa duyệt có cảnh báo (18,54%)**, vượt ngưỡng 10%. Nguồn: `reports/08_summary.json`, `export/clean_v1/manifest.json`.

## 2. Lỗi và phân việc

`02_error_list_v1.csv`: **208 cờ, gồm 55 ERROR và 153 WARN**. Bảng ghi số cờ/số ảnh riêng biệt; một ảnh có thể có nhiều mã. Mẫu số intake: 224 ảnh; QC: 205 ảnh; “dataset” chỉ lỗi cấp file/thống kê.

| Mã lỗi | Cờ / ảnh | Phân việc |
|---|---:|---|
| CORRUPT_IMAGE | 2 / 2 | Máy loại ở intake |
| BAD_SIZE | 3 / 3 | Máy loại ở intake |
| DUP_IMAGE_EXACT | 8 / 8 | Máy loại ở intake |
| DUP_IMAGE_NEAR | 2 / 2 | Máy loại ở intake |
| LEAK_TEST | 4 / 4 | Máy loại trùng kho test/val |
| BAD_FORMAT | 3 / 3 | Máy bỏ dòng hỏng |
| BAD_CLASS_ID | 6 / 6 | Máy bỏ dòng ID sai |
| BOX_ZERO | 4 / 4 | Máy bỏ dòng không có diện tích |
| BOX_OUT_OF_IMAGE | 8 / 8 | Máy cắt box vào ảnh |
| DUP_BOX | 7 / 7 | Máy bỏ dòng sau trùng lớp/box |
| BAD_CLASS_NAME | 2 / dataset | Máy chuẩn hóa names |
| MISSING_LABEL_FILE | 6 / 6 | Người gán, máy không tạo nhãn rỗng |
| EMPTY_LABEL | 12 / 12 | Người xác nhận nền/thiếu nhãn |
| BOX_TINY | 6 / 4 | Người kiểm guideline |
| BOX_HUGE | 3 / 3 | Người kiểm biên box |
| CLASS_RARE | 4 / dataset | Người xem phân bố lớp/ID lạ |
| POSSIBLE_MISSING | 53 / 52 | Người xác nhận bỏ sót |
| POSSIBLE_WRONG_CLASS | 18 / 18 | Người xác nhận lớp |
| POSSIBLE_LOOSE_BOX | 28 / 24 | Người kiểm biên box |
| POSSIBLE_FALSE_POS | 29 / 27 | Người xác nhận box thừa |

`03_fixes.csv`: 20 bỏ dòng, 8 cắt box, 1 sửa names, 6 chuyển người gán. Hàng đợi **125 ảnh**, ngân sách **80/125**. `img_0020` đứng đầu (11,524 điểm: nhiều cảnh báo + dòng bị bỏ), sau đó sáu ảnh thiếu nhãn (10 điểm/ảnh), theo trọng số cố định và confidence; hòa điểm xếp theo tên. Người mô phỏng bao phủ **94/123 cờ ngữ nghĩa trên 74/103 ảnh** ở QC2; số cờ được xem không đồng nghĩa số lỗi thật đã xác nhận.

## 3. Calibration hai ngưỡng

Hai sweep và phép đo cấu hình đã chọn: `calibration/calibration_report.md`, `calibration.json`. P/R bên dưới lấy từ sweep, không phải ước lượng trên raw.

| Tham số | Khởi đầu → chọn | P/R trước → sau |
|---|---|---|
| duplicates.phash_dist | 2 → **4** | NEAR: 1,000/0,500 → 1,000/0,667 |
| second_opinion.conf | 0,25 → **0,6** | WRONG_CLASS: 0,556/0,833 → 0,625/0,833; MISSING: 0,500/1,000 → 0,571/1,000 |

Chọn 4: bắt trùng gần từ 3/6 lên 4/6, không FP trên calib; mức nhỏ nhất đạt kết quả này. Chọn 0,6: giữ recall MISSING 8/8 và WRONG_CLASS 5/6, giảm báo động giả; 0,8 làm MISSING còn 6/8. Đánh đổi: LOOSE_BOX từ 2/5 xuống 1/5; FALSE_POS vẫn P=0,312/R=1,000 vì dùng `fp_conf` riêng.

**Bẫy:** calib chỉ 39 ảnh. Ở phash=16, NEAR P=1/R=0,833 nhưng phép đo intake trên raw loại 31/224 thay vì 19/224 ở mức 4; mức 20 loại tới 137/224. Phép đo dùng hai check có sẵn `images.run` và `duplicates.run`, chỉ thay phash trong bản sao cấu hình. Đây là tín hiệu cần kiểm tra, chưa chứng minh số FP trên raw; không chọn F1 lớn nhất để tự động loại nhiều ảnh chưa xác nhận.

## 4. Cửa chặn và điểm mù

Chứng minh gate bằng lệnh `python -m pipeline.run --budget 0 --work work/nb --reports work/rep_nb --export-dir work/exp_nb`: **Rework, mã 20, còn 6 lỗi thiếu file nhãn, không tạo `work/exp_nb/clean_v1/`**. Báo cáo thử nghiệm nằm riêng trong `work/rep_nb/`, không ghi đè báo cáo chính.

Điểm mù có đáp án calibration: trùng gần bỏ sót **2/6** (`calib_037`, `calib_038`); box lỏng bỏ sót **4/5** (`calib_002`, `calib_006`, `calib_012`, `calib_024`). WRONG_CLASS cũng bỏ sót `calib_009` (1/6). Đối chiếu `calibration/calibration.json` với MANIFEST của bộ calib. Hết ERROR không đồng nghĩa nhãn hoàn toàn đúng.

**Ba quan sát trực tiếp của học viên trên task CVAT dùng ảnh raw**:

- `img_0020`, frame 0: học viên xác nhận người phụ nữ áo xanh là cùng người trong box đen `3:93` ở PNG. Lỗi gốc là **BAD_CLASS_ID** (93 thay vì person/ID 1), làm box vắng trên CVAT khi nhập. Đề xuất đổi ID 93→1 trên bản làm việc, không thêm box trùng.
- `img_0031`, frame 1: thấy nhiều car và một bus chưa được đánh dấu; raw chưa có file nhãn. Đề xuất người gán nhãn các vật thể.
- `img_0030`, frame 19, box 79/dòng gốc 9: học viên nhận xét box thừa và tràn mép trái; đề xuất xóa. Tọa độ xác nhận mép trái −0,022998; xóa nếu không có person tương ứng, còn tràn đơn thuần thì cắt box vào ảnh. Đây không tự động là lỗi sai lớp.

Đây là đề xuất trên bản xem raw; dataset đã train và các số liệu pipeline giữ nguyên.

## 5. Train raw vs clean

Notebook đã chạy: [Colab của bài nộp](https://colab.research.google.com/drive/1WaMnwteC2gxpQmcmrpNPahjD7e_oIDSy?usp=sharing).

Đã train trên Colab T4: **yolo26n, 20 epoch, batch 16, imgsz 640; seed 0 và 1** cho cả hai biến thể; cùng val 40 ảnh/test 100 ảnh. Bốn JSON khớp cấu hình và log; clean khớp manifest. Cả hai seed raw thực dùng **213/224 ảnh**, bỏ 11 ảnh/nhãn lỗi; clean dùng **205/205 ảnh**, không có corrupt. Bảng script bên dưới vẫn ghi số file đầu vào (raw 224), không phải số loader thực dùng. Log Colab gốc được lưu tại máy để đối chiếu khi cần.

| biến thể | #ảnh train | số seed | map50 (TB ± độ lệch) | map50_95 (TB ± độ lệch) | precision (TB ± độ lệch) | recall (TB ± độ lệch) |
|---|---|---|---|---|---|---|
| raw | 224 | 2 | 0.726 ± 0.000 | 0.512 ± 0.004 | 0.764 ± 0.061 | 0.649 ± 0.028 |
| clean | 205 | 2 | 0.700 ± 0.030 | 0.486 ± 0.013 | 0.715 ± 0.073 | 0.615 ± 0.017 |

Chênh mAP50 (clean − raw) = **-0.025**.

Từ JSON chưa làm tròn: ΔmAP50 = **−0,0254** (−2,54 điểm phần trăm), nhỏ hơn SD giữa seed của clean **0,03048**; SD raw **0,00021** (bảng làm tròn thành 0,000). Clean thấp hơn raw ở cả seed 0 (−0,0468) và seed 1 (−0,0040); chưa chứng minh QC giúp tăng mAP hay mức giảm ổn định với chỉ hai seed. AP50 trung bình truck giảm 0,64845→0,55880, bus 0,69490→0,66665; car/person tăng nhẹ.

Hai giả thuyết cần kiểm: **(1)** raw có 4 cờ trùng ảnh test (`01_intake.csv`), có thể được lợi từ rò rỉ; kiểm bằng test độc lập với cấu hình cố định. **(2)** clean thực train ít hơn 8 ảnh (205 so với 213), thành phần/nhãn khác và còn 38 ảnh cảnh báo chưa duyệt, có thể ảnh hưởng truck/bus (clean chỉ 42/33 box); kiểm thí nghiệm cùng danh sách ảnh nhưng khác nhãn, đối chiếu AP từng lớp. Đây chưa phải kết luận nhân quả. Tiếp theo: thêm seed cặp và đánh giá test độc lập; quyết định dữ liệu vẫn **Hold**.

## 6. Quyết định và ghi chú AI

Giữ **Hold**. Muốn Release: hết ERROR và còn tối đa **20/205** ảnh cảnh báo chưa duyệt; cần quy trình xử lý/duyệt tiếp được dự án chấp thuận, không tự tăng ngân sách hoặc nới gate. Đã có task CVAT và ba nhận xét của học viên; phần thưởng lọc box nhỏ chưa đủ bằng chứng, chưa thêm check mới.

- Yêu cầu AI: YOLO 5 cột + cfg → Issue/log/verdict theo docstring và test; checks chỉ đọc, autofix chỉ ghi bản sao và có log.
- Kiểm chứng: 79 test gốc, 21 ca biên bổ sung tại máy, hai sweep lỗi chèn, hash file bảo vệ, thử gate không người duyệt.
- Một lần AI sai: dùng biến `status` chỉ đọc của zsh để thu mã thoát khiến lệnh xác minh dừng; đã đổi sang `subprocess.returncode`, chạy lại và xác nhận Rework/20/không export.

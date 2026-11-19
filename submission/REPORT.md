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

**Bẫy:** calib chỉ 39 ảnh. Ở phash=16, NEAR P=1/R=0,833 nhưng raw bị loại 31/224 thay vì 19/224 ở mức 4; mức 20 loại tới 137/224. Đây là tín hiệu cần kiểm tra, chưa chứng minh số FP trên raw. Không chọn F1 lớn nhất để tự động loại nhiều ảnh chưa xác nhận. Tái tạo bằng `python scripts/measure_intake_sensitivity.py`; bằng chứng: `evidence/intake_sensitivity.json`.

## 4. Cửa chặn và điểm mù

Thử `--budget 0` trong thư mục riêng: **Rework, mã 20, còn 6 lỗi thiếu file nhãn, không export**. Lệnh và kết quả: `evidence/no_review/proof.json`; báo cáo chính giữ nguyên.

Điểm mù có đáp án calibration: trùng gần bỏ sót **2/6** (`calib_037`, `calib_038`); box lỏng bỏ sót **4/5** (`calib_002`, `calib_006`, `calib_012`, `calib_024`). WRONG_CLASS cũng bỏ sót `calib_009` (1/6). Nguồn: `evidence/calibration_misses.json`. Hết ERROR không đồng nghĩa nhãn hoàn toàn đúng.

Ví dụ tự động để đối chiếu: `img_0014:1` sai định dạng, `img_0020:3` sai ID, `img_0030:9` tràn box. Học viên chưa xác nhận phần tự quan sát bằng mắt.

## 5. Train raw vs clean

**Chưa chạy.** Notebook đã trỏ đúng repo cho Colab T4: yolo26n, 20 epoch, seed 0 và 1 cho raw/clean, cùng val/test và siêu tham số. Cần push bản đã kiểm tra và chạy GPU; chưa có kết quả để kết luận clean tốt hơn raw. Sau train: tải JSON sinh bởi script, chạy `summarize_results.py`, bổ sung TB ± độ lệch và so chênh lệch với nhiễu.

## 6. Quyết định và ghi chú AI

Giữ **Hold**. Muốn Release: hết ERROR và còn tối đa **20/205** ảnh cảnh báo chưa duyệt; cần quy trình xử lý/duyệt tiếp được dự án chấp thuận, không tự tăng ngân sách hoặc nới gate. Chưa làm thưởng CVAT/check mới.

- Yêu cầu AI: YOLO 5 cột + cfg → Issue/log/verdict theo docstring và test; checks chỉ đọc, autofix chỉ ghi bản sao và có log.
- Kiểm chứng: 79 test gốc + 21 ca biên, hai sweep lỗi chèn, hash file bảo vệ, thử gate không người duyệt. Học viên cần tự đọc và hiểu code.
- Một lần AI sai: dùng biến `status` chỉ đọc của zsh để thu mã thoát khiến lệnh xác minh dừng; đã đổi sang `subprocess.returncode`, chạy lại và xác nhận Rework/20/không export.

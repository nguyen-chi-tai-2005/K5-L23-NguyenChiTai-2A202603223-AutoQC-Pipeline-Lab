# Chạy thí nghiệm raw/clean của Nguyễn Chí Tài

MSHV: **2A202603223**. Notebook đã trỏ tới repo bài làm:

[Mở notebook trên Colab](https://colab.research.google.com/github/nguyen-chi-tai-2005/K5-L23-Day09-2A202603223-NguyenChiTai-AutoQC-Pipeline-Lab/blob/main/notebooks/day09_train_compare.ipynb).

Trước khi mở, cần đẩy các commit đã kiểm tra lên GitHub public.
Nếu chưa push, Colab sẽ thấy bản cũ thiếu export.

1. Mở notebook, chọn **Runtime → Change runtime type → T4 GPU**.
2. Chạy lần lượt các ô. Cấu hình đã đặt: `raw`, `clean`; seed `[0, 1]`;
   20 epoch, yolo26n. Giữ nguyên siêu tham số giữa cả bốn lần train.
3. Ở ô kiểm tra export, xác nhận **Hold, 205 ảnh**. Đây là bản nháp để thử nghiệm,
   không phải dataset đã Release. Cùng val 40 ảnh và test 100 ảnh cho cả hai biến thể.
4. Chạy train, tổng hợp và tải `results.zip` ở ô cuối. Lưu log cảnh báo loader
   để biết có bao nhiêu ảnh raw thực sự được dùng sau khi Ultralytics bỏ nhãn hỏng.
5. Giải nén về repo, giữ nguyên file script sinh; cần bốn JSON
   `raw_seed0.json`, `raw_seed1.json`, `clean_seed0.json`, `clean_seed1.json`
   cùng `comparison.md`, `comparison.json`, `comparison.png` trong `submission/results/`.
6. Trên máy chạy `python scripts/summarize_results.py`, bổ sung mục 5 của
   `submission/REPORT.md`, rồi `make check PY=.venv/bin/python`.

## Xác nhận đúng dữ liệu trước train

- SHA1 cấu hình: `c13639f15b3e11b51864b00c08b651167b0a68b8`.
- SHA1 manifest: `0fab98913b51218f75aa6c73669b8c8f3ca1a1c1`.
- Export: 205 ảnh; phash_dist=4, conf=0.6; người duyệt mô phỏng 80 ảnh.

Có thể kiểm hash ở Colab bằng ô mới:

```python
import hashlib
from pathlib import Path
for path in ("configs/pipeline.yaml", "submission/export/clean_v1/manifest.json"):
    print(path, hashlib.sha1(Path(path).read_bytes()).hexdigest())
```

Nếu cấu hình hoặc export thay đổi, cần đối chiếu lại hash và chạy lại train.
Không trộn JSON từ hai phiên bản dataset. Không commit trọng số `.pt` hoặc `work/`.
Nếu hết quota giữa chừng, chạy lại lệnh train của notebook với `--skip-existing`
trong cùng runtime còn lưu kết quả; nếu reset runtime, cần lưu/tải lại các JSON trước.

Kết luận train phải so chênh lệch với độ lệch giữa seed. Hai giả thuyết cần kiểm:
raw có cờ trùng kho test/val nên metric có thể lệch; clean vẫn Hold và chưa được
duyệt hết nên còn nhiễu nhãn. Đối chiếu log intake, hàng đợi và AP từng lớp;
chưa có số liệu thì không khẳng định giả thuyết nào đã được chứng minh.

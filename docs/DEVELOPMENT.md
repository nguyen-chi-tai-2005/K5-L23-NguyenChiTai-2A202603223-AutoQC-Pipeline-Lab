# Phát triển và kiểm thử bốn module

Các bước chuẩn bị và triển khai dưới đây đã thực hiện ngày 19/11/2026.
Đây là ghi chú phát triển; báo cáo bài nộp vẫn là `submission/REPORT.md`.

## Chạy trên máy

Môi trường hiện tại dùng Python 3.11 trong `.venv/`. Để tạo lại:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

Để dùng Makefile trong môi trường này:

```bash
make test PY=.venv/bin/python
```

Không cần torch, GPU hoặc tải model cho giai đoạn này. `pip check` đã xác nhận
không có phụ thuộc bị thiếu hoặc xung đột trong môi trường đã cài.

## Bốn module đã triển khai

- `label_format`: đọc từng dòng nhãn theo số dòng gốc; phân biệt lỗi định dạng,
  ID lớp và kích thước không dương trước khi kiểm hình học. Kiểm bốn mép box,
  box trùng cùng lớp, box nhỏ theo pixel và box phủ gần hết ảnh. Chỉ đọc dữ liệu.
- `gate`: đếm lỗi bắt buộc và các ảnh riêng biệt còn cảnh báo chưa duyệt.
  ERROR luôn dẫn đến Rework. Nếu không có ERROR, so tỷ lệ thực với ngưỡng
  trước khi làm tròn giá trị trả về; cảnh báo cấp dataset không vào tử số.
- `autofix`: xử lý loại ảnh trước, rồi gom các lỗi theo file và số dòng gốc;
  xóa dòng ưu tiên hơn cắt box. Mỗi thay đổi có log trước/sau. Không tạo nhãn
  rỗng khi thiếu file và không sửa WARN. Có chốt từ chối ghi vào cây dữ liệu
  gốc của repo; caller phải truyền bản sao làm việc.
- `second_opinion`: so nhãn với dự đoán cache, ưu tiên nhãn cùng lớp trước
  khi nghi ngờ sai lớp. Dùng riêng ngưỡng `conf` và `fp_conf`; nhánh FALSE_POS
  vẫn xét dự đoán nhỏ hoặc confidence thấp hơn ngưỡng cảnh báo MISSING.
  Tất cả kết quả chỉ là WARN, giữ đúng thứ tự ảnh/dự đoán/số dòng nhãn.

## Kiểm chứng đã chạy

Trước khi triển khai: **55 failed, 24 passed** trên bộ test gốc.
Sau khi triển khai: **79 passed** trên bộ test gốc, gồm tích hợp pipeline,
khả năng chạy lại cho cùng kết quả, dừng/tiếp tục duyệt và chặn xuất khi Rework.

Có thêm **21 ca kiểm thử** trong `validation/test_module_edges.py`;
không thay đổi bất kỳ file nào của `tests/`. Các ca bổ sung kiểm tra ID
`inf/nan`, dòng có nhiều lỗi, ngưỡng biên, bảo toàn nội dung khi chỉ có WARN,
bảo vệ dữ liệu gốc, thứ tự cảnh báo và khả năng giữ nguyên các đầu vào chỉ đọc.

```bash
python -m pytest tests -q                 # 79 test gốc
python -m pytest validation -q            # 21 ca bổ sung
python -m pytest -q                       # cả hai: 100 passed
```

Lần chạy toàn bộ cuối giai đoạn này: **100 passed in 18.04s**.
Kiểm tra hash xác nhận 32 file được bảo vệ còn nguyên; trong các file nguồn,
dữ liệu, cấu hình và test ban đầu, chỉ bốn module được giao có thay đổi.
Toàn bộ `data/` và `configs/pipeline.yaml` giữ nguyên.

Log tại máy nằm trong `work/verification/`: `pytest-before.log`,
`pytest-after.log`, `pytest-edges.log`, `pytest-final.log`,
`initial_hashes.json`, `preparation_inspection.json` và `packages.txt`.
`work/` và `.venv/` được Git bỏ qua theo quy tắc đề.

## Bước quan sát của học viên

Đã chạy công cụ có sẵn để tạo 11 ảnh vẽ nhãn trong `work/viz/`:
`img_0001` đến `img_0009`, `img_0011`, `img_0012`.
`img_0010` được công cụ báo không mở được, không có PNG tương ứng.
Học viên cần tự mở các ảnh trên máy và ghi ba lỗi thực sự quan sát được;
không coi kiểm tra bằng script là việc duyệt bằng mắt của học viên.
Không gửi ảnh lên dịch vụ AI bên ngoài.

Kiểm tra chỉ đọc đã tìm được các ví dụ để đối chiếu:
`img_0014` dòng 1 sai định dạng; `img_0020` dòng 3 sai ID lớp;
`img_0030` dòng 9 box tràn ảnh; `img_0031` thiếu file nhãn.
Đây là phát hiện tự động, không phải ghi nhận quan sát bằng mắt.

Giai đoạn này chưa chạy calibration, chưa chọn hai ngưỡng,
chưa sinh đầu ra chính thức vào `submission/`, chưa train hay hoàn thiện báo cáo.
Test tích hợp chạy trong thư mục tạm, nên không thay thế `make run` của bước sau.

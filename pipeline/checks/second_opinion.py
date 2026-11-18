"""CHECK 6 — Ý kiến thứ hai: so nhãn với một model LỚN HƠN (yolo26l).   ★★★ (khó nhất, đáng điểm nhất)

Test:  pytest tests/test_second_opinion.py -q

Máy kiểm quy tắc, người kiểm ý nghĩa (slide). Các lỗi như thiếu nhãn / gán nhầm lớp hợp lệ / box lỏng
KHÔNG bắt được bằng quy tắc cú pháp. Ta nhờ một model mạnh hơn "nhìn lại" và CHỈ CẢNH BÁO (model cũng có thể sai):
những ảnh bị cờ sẽ vào hàng đợi cho NGƯỜI duyệt.

`preds[stem]` = list `[id_lớp, conf, cx, cy, w, h]` của model (lấy qua `get_preds(ds, cfg, "checker")` nếu preds=None).
`L = ds.valid_boxes(stem)` = list `(id_lớp, cx, cy, w, h)` của nhãn (đã bỏ dòng hỏng).
Ngưỡng ở `cfg["second_opinion"]`: conf, min_area_px, fp_conf, iou_missing, iou_match, iou_loose.

Thuật toán gợi ý, với từng ảnh (bỏ qua ảnh không có trong preds hoặc không có file nhãn):
  P = dự đoán có conf >= conf  VÀ diện tích px (w*W * h*H) >= min_area_px
  Với mỗi dự đoán r trong P: lấy các nhãn có IoU(r, nhãn) >= iou_missing  (cands)
   - không có cands                            -> POSSIBLE_MISSING     (model thấy vật mà nhãn không có box)
   - có cands cùng lớp, tốt nhất IoU < iou_loose -> POSSIBLE_LOOSE_BOX  (đúng vật, box lỏng/lệch)
   - không có cands cùng lớp, nhưng cands tốt nhất IoU >= iou_match (khác lớp) -> POSSIBLE_WRONG_CLASS
  Với mỗi dòng nhãn hợp lệ: nếu IoU với MỌI dự đoán (conf >= fp_conf, không lọc diện tích) đều < iou_missing
                                             -> POSSIBLE_FALSE_POS  (box nhãn không khớp vật nào model thấy; Issue.line = số dòng)

Chi tiết các ca biên (test kiểm đúng các ca này)
- `cands` gồm nhãn MỌI lớp có IoU >= iou_missing; "tốt nhất cùng lớp" = cands cùng lớp có IoU lớn nhất; "tốt nhất khác lớp" tương tự với cands khác lớp.
- Thứ tự quyết định cho mỗi dự đoán: (1) cands rỗng -> MISSING. (2) có cands cùng lớp: IoU tốt nhất < iou_loose -> LOOSE_BOX, ngược lại KHÔNG cờ
  (nhãn đúng lớp đã phủ vật này, kể cả khi còn nhãn khác lớp chồng lên). (3) không có cands cùng lớp: nếu IoU tốt nhất khác lớp >= iou_match -> WRONG_CLASS;
  nếu chỉ có khác lớp với IoU trong [iou_missing, iou_match) -> không cờ gì (mơ hồ: để cho FALSE_POS / lần duyệt khác).
- Một dự đoán sinh tối đa MỘT issue (MISSING / LOOSE_BOX / WRONG_CLASS); một ảnh có thể có nhiều issue.
- Thứ tự issue: theo `ds.image_files()` rồi theo thứ tự dự đoán trong `preds[stem]`, cuối cùng là các FALSE_POS theo số dòng; `Issue.image` = stem, `Issue.line` chỉ đặt cho FALSE_POS.

Lưu ý số dòng: dùng `ds.read_label_lines(stem)` (giữ số dòng gốc, kể cả dòng hỏng/trống) để lấy `Issue.line`; `valid_boxes` KHÔNG giữ số dòng.

Tất cả severity WARN; `Issue.extra` nên có {"conf": ...} hoặc {"iou": ...} (hàng đợi duyệt dùng conf để xếp ưu tiên).

Gợi ý
- `iou_xywh` có sẵn. Dòng nhãn hỏng không được làm script chết (dùng `ds.valid_boxes` và `parse_yolo_line` trong try).
- Kết quả phụ thuộc mạnh vào ngưỡng: calibrate chúng ở Bước 3 thay vì đoán.
"""
from ..common import WARN, Issue, iou_xywh, parse_yolo_line
from ..model_cache import get_preds


def run(ds, cfg, preds=None):
    if preds is None:
        preds = get_preds(ds, cfg, "checker")
    limits = cfg["second_opinion"]
    issues = []
    for image_path in ds.image_files():
        stem = image_path.stem
        lines = ds.read_label_lines(stem)
        if stem not in preds or lines is None:
            continue
        size = ds.image_size(stem)
        if size is None:
            continue

        # Giữ số dòng gốc để cảnh báo FALSE_POS mở đúng vị trí trong file.
        labels = []
        for line, text in lines:
            try:
                box = parse_yolo_line(text)
            except (ValueError, OverflowError):
                continue
            if 0 <= box[0] < len(ds.classes):
                labels.append((line, box))

        predictions = preds[stem]
        for cls, conf, x, y, w, h in predictions:
            if conf < limits["conf"] or (w * size[0]) * (h * size[1]) < limits["min_area_px"]:
                continue
            overlaps = [(box[0], iou_xywh((x, y, w, h), box[1:])) for _, box in labels]
            candidates = [(label_cls, overlap) for label_cls, overlap in overlaps
                          if overlap >= limits["iou_missing"]]
            extra = {"conf": conf}
            if not candidates:
                code = "POSSIBLE_MISSING"
                message = f"model thấy lớp {cls} nhưng không có nhãn khớp"
            else:
                same_class = [overlap for label_cls, overlap in candidates if label_cls == cls]
                if same_class:
                    best = max(same_class)
                    if best >= limits["iou_loose"]:
                        continue
                    code = "POSSIBLE_LOOSE_BOX"
                    message = f"nhãn cùng lớp {cls} có IoU thấp: {best:.4f}"
                else:
                    best = max(overlap for _, overlap in candidates)
                    if best < limits["iou_match"]:
                        continue
                    code = "POSSIBLE_WRONG_CLASS"
                    message = f"model dự đoán lớp {cls}, nhãn khớp vị trí nhưng khác lớp (IoU {best:.4f})"
                extra["iou"] = best
            issues.append(Issue("second_opinion", WARN, code, stem, message, extra=extra))

        # FALSE_POS dùng ngưỡng riêng và cả dự đoán vật nhỏ; không tái sử dụng tập lọc ở trên.
        supporting = [row for row in predictions if row[1] >= limits["fp_conf"]]
        for line, box in labels:
            overlaps = [iou_xywh(box[1:], row[2:]) for row in supporting]
            if not any(overlap >= limits["iou_missing"] for overlap in overlaps):
                issues.append(Issue("second_opinion", WARN, "POSSIBLE_FALSE_POS", stem,
                                    "box nhãn không khớp dự đoán nào đủ confidence", line,
                                    {"iou": max(overlaps, default=0.0)}))
    return issues

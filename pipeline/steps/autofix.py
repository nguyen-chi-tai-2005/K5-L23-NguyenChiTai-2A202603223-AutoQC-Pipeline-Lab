"""BƯỚC 2/4 — Sửa tự động những lỗi bắt buộc mà máy sửa được AN TOÀN.   ★★

Test:  pytest tests/test_autofix.py -q

`fix(ds, issues, cfg) -> list[dict]`: duyệt `issues` (chỉ lỗi severity ERROR), sửa thẳng vào thư mục `ds`,
và trả về danh sách thay đổi; mỗi phần tử có khoá: image, line, action, before, after
(đây chính là file `03_fixes.csv` — bằng chứng pipeline đã làm gì, người có thể kiểm lại).

| code lỗi                                       | cách sửa                                    | action           |
|------------------------------------------------|---------------------------------------------|------------------|
| BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO, DUP_BOX    | xoá dòng đó khỏi file nhãn                  | "drop_line"      |
| BOX_OUT_OF_IMAGE                               | cắt box về trong [0,1] (giữ nguyên lớp)     | "clip_box"       |
| MISSING_LABEL_FILE                             | KHÔNG sửa file (máy không thể bịa nhãn): ghi 1 dòng fix, before="(không có file)", after="chuyển người gán" | "needs_label" |
| BAD_CLASS_NAME                                 | ghi lại `names` trong data.yaml đúng `cfg["classes"]` | "rename_classes" |
| DUP_IMAGE_*, LEAK_TEST, CORRUPT_IMAGE, BAD_SIZE| xoá ảnh + nhãn khỏi `ds`                    | "remove_image"   |

Bẫy cần nghĩ tới (có test cho từng cái)
- Một file có NHIỀU dòng lỗi: số dòng trong `issues` là số dòng GỐC. Nếu xoá từng dòng một thì số dòng lệch.
  Gom theo file, rồi ghi lại MỘT lần.
- Sau khi cắt, box có thể không còn diện tích (nằm hẳn ngoài ảnh): lúc đó xoá dòng thay vì ghi box rỗng.
- Một dòng có 2 lỗi (vd. BOX_OUT_OF_IMAGE + DUP_BOX): xoá dòng thắng, chỉ ghi 1 fix `drop_line`, không ghi thêm `clip_box`. Dòng trống ở giữa file vẫn đếm vào số dòng gốc.
- Ảnh vừa bị xoá (DUP_IMAGE_*...) mà còn issue dòng của chính nó: bỏ qua êm, không được báo lỗi/chết.
- Không động tới lỗi WARN (cảnh báo là việc của người). Không sửa file ở `data/raw/` — chỉ sửa `ds`.
- Chạy lần 2 trên dữ liệu đã sửa phải không làm gì thêm (idempotent) — NGOẠI LỆ duy nhất: `needs_label` được ghi lại mỗi lần còn lỗi `MISSING_LABEL_FILE` (vì ảnh vẫn chưa có nhãn).

- `needs_label` KHÔNG tạo file nhãn rỗng (rỗng = "ảnh nền", khác với "chưa gán"). `review_queue` sẽ đẩy ảnh này lên đầu hàng đợi cho người.

Gợi ý: `yaml.safe_load / safe_dump`.
"""
from collections import defaultdict

import yaml

from ..common import ERROR, ROOT, parse_yolo_line


def fix(ds, issues, cfg):
    # Chặn thao tác ghi lên dữ liệu gốc, kể cả khi gọi nhầm API trực tiếp.
    source_dir = (ROOT / "data").resolve()
    target_dir = ds.root.resolve()
    if target_dir == source_dir or source_dir in target_dir.parents:
        raise ValueError("autofix chỉ được sửa bản sao làm việc, không sửa thư mục dữ liệu gốc")

    errors = [issue for issue in issues if issue.severity == ERROR]
    fixes = []

    def record(image, line, action, before, after):
        fixes.append(dict(image=image, line=line, action=action, before=before, after=after))

    # Loại ảnh trước: các lỗi dòng trên cùng ảnh không còn cần xử lý.
    removed = {i.image for i in errors
               if i.code.startswith("DUP_IMAGE_") or i.code in {"LEAK_TEST", "CORRUPT_IMAGE", "BAD_SIZE"}}
    for stem in sorted(removed):
        image_path = ds.image_path(stem)
        label_path = ds.label_path(stem)
        paths = [p for p in (image_path, label_path) if p is not None and p.exists()]
        if paths:
            before = "; ".join(p.name for p in paths)
            for path in paths:
                path.unlink()
            record(stem, None, "remove_image", before, "(đã loại ảnh và nhãn)")

    if any(i.code == "BAD_CLASS_NAME" for i in errors):
        data = yaml.safe_load(ds.yaml_path.read_text(encoding="utf-8")) if ds.yaml_path.exists() else {}
        data = data or {}
        expected = dict(enumerate(cfg["classes"]))
        if not ds.yaml_path.exists() or ds.yaml_names() != expected:
            before = str(data.get("names"))
            data["names"] = expected
            ds.yaml_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
            record("data.yaml", None, "rename_classes", before, str(expected))

    for stem in sorted({i.image for i in errors if i.code == "MISSING_LABEL_FILE"} - removed):
        if ds.image_path(stem) is not None and not ds.label_path(stem).exists():
            record(stem, None, "needs_label", "(không có file)", "chuyển người gán")

    drop_codes = {"BAD_FORMAT", "BAD_CLASS_ID", "BOX_ZERO", "DUP_BOX"}
    by_file = defaultdict(lambda: defaultdict(set))
    for issue in errors:
        if issue.image not in removed and issue.line is not None and issue.code in drop_codes | {"BOX_OUT_OF_IMAGE"}:
            by_file[issue.image][issue.line].add(issue.code)

    for stem in sorted(by_file):
        path = ds.label_path(stem)
        if not path.exists():
            continue
        original = path.read_text(encoding="utf-8", errors="replace")
        output = []
        for line, raw_line in enumerate(original.splitlines(keepends=True), 1):
            codes = by_file[stem].get(line, set())
            before = raw_line.rstrip("\r\n")
            if codes & drop_codes:
                record(stem, line, "drop_line", before, "")
                continue
            if "BOX_OUT_OF_IMAGE" not in codes:
                output.append(raw_line)
                continue
            try:
                cls, x, y, w, h = parse_yolo_line(before)
            except (ValueError, OverflowError):
                record(stem, line, "drop_line", before, "")
                continue
            left, top = max(0.0, x - w / 2), max(0.0, y - h / 2)
            right, bottom = min(1.0, x + w / 2), min(1.0, y + h / 2)
            if right <= left or bottom <= top:
                record(stem, line, "drop_line", before, "")
                continue
            after = str(cls) + " " + " ".join(f"{v:.12g}" for v in
                                             ((left + right) / 2, (top + bottom) / 2,
                                              right - left, bottom - top))
            output.append(after + raw_line[len(before):])
            if after != before:
                record(stem, line, "clip_box", before, after)
        updated = "".join(output)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
    return fixes

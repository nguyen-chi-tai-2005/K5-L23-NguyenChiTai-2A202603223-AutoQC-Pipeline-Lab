#!/usr/bin/env python3
"""Đo độ nhạy intake trên raw, chỉ đọc; không suy diễn đáp án lỗi của raw.

    python scripts/measure_intake_sensitivity.py
Đầu ra là bằng chứng phụ cho REPORT.md, không thay đổi cấu hình hoặc dữ liệu.
"""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.checks import duplicates, images
from pipeline.common import Dataset, load_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', default='submission/evidence/intake_sensitivity.json')
    args = parser.parse_args()
    cfg = load_config()
    ds = Dataset(ROOT / 'data' / 'raw', cfg['classes'])
    image_issues = images.run(ds, cfg)
    rows = []
    for distance in (2, 4, 8, 16, 20):
        candidate = deepcopy(cfg)
        candidate['duplicates']['phash_dist'] = distance
        issues = image_issues + duplicates.run(ds, candidate)
        rows.append(dict(phash_dist=distance, rejected_images=len({i.image for i in issues}),
                         counts=dict(sorted(Counter(i.code for i in issues).items())),
                         near_pairs=[dict(image=i.image, of=i.extra.get('of'))
                                     for i in issues if i.code == 'DUP_IMAGE_NEAR']))
        print(f"phash_dist={distance}: loại {rows[-1]['rejected_images']}/{len(ds.image_files())} ảnh")
    payload = dict(n_raw_images=len(ds.image_files()),
                   config_sha1=hashlib.sha1((ROOT / 'configs/pipeline.yaml').read_bytes()).hexdigest(),
                   note='Chỉ đo số cờ; chưa xác nhận FP/FN trên raw bằng người duyệt.', rows=rows)
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()

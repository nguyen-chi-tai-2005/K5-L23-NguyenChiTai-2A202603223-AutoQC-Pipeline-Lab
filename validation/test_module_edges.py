"""Kiểm thử bổ sung trên dữ liệu giả; giữ nguyên toàn bộ tests/ của đề."""
from copy import deepcopy
from pathlib import Path
import sys

import pytest
import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.common import Dataset, Issue, ROOT, load_config
from pipeline.checks import label_format, second_opinion
from pipeline.steps import autofix, gate


@pytest.fixture
def cfg():
    return deepcopy(load_config())


@pytest.fixture
def ds(tmp_path, cfg):
    root = tmp_path / 'sample'
    (root / 'images').mkdir(parents=True)
    (root / 'labels').mkdir()
    Image.new('RGB', (640, 480), 'white').save(root / 'images' / 'alpha.JPG')
    (root / 'labels' / 'alpha.txt').write_text('0 .5 .5 .2 .2\n')
    (root / 'data.yaml').write_text(yaml.safe_dump({'names': cfg['classes'], 'train': 'images', 'path': '.'}))
    return Dataset(root, cfg['classes'])


def error(code, line=None, image='alpha'):
    return Issue('edge', 'error', code, image, 'edge case', line)


@pytest.mark.parametrize('class_token', ['inf', '-inf', 'nan', '1.5'])
def test_nonfinite_or_fractional_class_is_reported_without_crashing(ds, cfg, class_token):
    ds.label_path('alpha').write_text(f'{class_token} .5 .5 .2 .2\n0 .9 .5 .4 .2\n')
    issues = label_format.run(ds, cfg)
    assert [(i.code, i.line) for i in issues] == [('BAD_FORMAT', 1), ('BOX_OUT_OF_IMAGE', 2)]


def test_negative_width_does_not_generate_geometry_warnings(ds, cfg):
    ds.label_path('alpha').write_text('0 2 2 -.2 .2\n')
    assert [(i.code, i.line) for i in label_format.run(ds, cfg)] == [('BOX_ZERO', 1)]


def test_orphan_label_still_has_syntax_checked(ds, cfg):
    ds.label_path('orphan').write_text('garbage\n')
    assert [(i.image, i.code) for i in label_format.run(ds, cfg)] == [('orphan', 'BAD_FORMAT')]


def test_overflow_and_duplicate_on_same_line_survive_blank_line(ds, cfg):
    ds.label_path('alpha').write_text('0 .95 .5 .2 .2\n\n0 .95 .5 .2 .2\n')
    issues = label_format.run(ds, cfg)
    assert {(i.code, i.line) for i in issues} == {
        ('BOX_OUT_OF_IMAGE', 1), ('BOX_OUT_OF_IMAGE', 3), ('DUP_BOX', 3)}
    fixes = autofix.fix(ds, issues, cfg)
    assert [(f['line'], f['action']) for f in fixes] == [(1, 'clip_box'), (3, 'drop_line')]
    assert ds.label_path('alpha').read_text().splitlines()[1] == ''
    assert label_format.run(ds, cfg) == []
    assert autofix.fix(ds, label_format.run(ds, cfg), cfg) == []


def test_strict_geometry_boundaries_are_not_reported(ds, cfg):
    cfg['label_format'].update(overflow_tol=.125, dup_box_iou=1.0, max_box_frac=.25, min_box_px=120)
    ds.label_path('alpha').write_text('0 0 .5 .25 1\n0 0 .5 .25 1\n')
    assert label_format.run(ds, cfg) == []


def test_deletion_precedes_line_work_regardless_of_issue_order(ds, cfg):
    fixes = autofix.fix(ds, [error('BAD_FORMAT', 1), error('CORRUPT_IMAGE'), error('BAD_SIZE')], cfg)
    assert len(fixes) == 1 and fixes[0]['action'] == 'remove_image'
    assert not ds.image_files() and not ds.label_files()


def test_missing_labels_are_logged_on_each_run_without_inventing_a_file(ds, cfg):
    ds.label_path('alpha').unlink()
    issues = [error('MISSING_LABEL_FILE')]
    for _ in range(2):
        assert [f['action'] for f in autofix.fix(ds, issues, cfg)] == ['needs_label']
        assert not ds.label_path('alpha').exists()


def test_rename_preserves_other_yaml_fields_and_is_idempotent(ds, cfg):
    content = yaml.safe_load(ds.yaml_path.read_text())
    content['names'] = ['CAR', 'person', 'truck', 'bus']
    ds.yaml_path.write_text(yaml.safe_dump(content))
    issues = [error('BAD_CLASS_NAME', image='data.yaml')]
    assert len(autofix.fix(ds, issues, cfg)) == 1
    content = yaml.safe_load(ds.yaml_path.read_text())
    assert content['train'] == 'images' and content['path'] == '.'
    assert autofix.fix(ds, issues, cfg) == []


def test_warnings_leave_original_label_bytes_unchanged(ds, cfg):
    ds.label_path('alpha').write_bytes(b'0 .5 .5 .001 .001\n\n')
    before = ds.label_path('alpha').read_bytes()
    assert autofix.fix(ds, [Issue('edge', 'warn', 'BOX_TINY', 'alpha', 'tiny', 1)], cfg) == []
    assert ds.label_path('alpha').read_bytes() == before


def test_original_data_directory_is_rejected_before_any_write(cfg):
    original = Dataset(ROOT / 'data' / 'raw', cfg['classes'])
    with pytest.raises(ValueError, match='bản sao'):
        autofix.fix(original, [], cfg)


def test_empty_predictions_report_original_lines_and_skip_bad_class(ds, cfg):
    ds.label_path('alpha').write_text('0 .5 .5 .2 .2\n\ninf .5 .5 .2 .2\n1 .1 .1 .1 .1\n')
    issues = second_opinion.run(ds, cfg, preds={'alpha': []})
    assert [(i.code, i.line) for i in issues] == [('POSSIBLE_FALSE_POS', 1), ('POSSIBLE_FALSE_POS', 4)]


def test_loose_same_class_wins_over_exact_other_class(ds, cfg):
    ds.label_path('alpha').write_text('0 .5 .5 .3 .3\n2 .5 .5 .2 .2\n')
    issues = second_opinion.run(ds, cfg, preds={'alpha': [[0, .9, .5, .5, .2, .2]]})
    assert [i.code for i in issues] == ['POSSIBLE_LOOSE_BOX']
    assert issues[0].extra['conf'] == .9


def test_warning_order_follows_image_then_prediction_then_label_line(ds, cfg):
    Image.new('RGB', (640, 480), 'white').save(ds.images_dir / 'beta.png')
    ds.label_path('beta').write_text('1 .1 .1 .1 .1\n')
    preds = {'beta': [[2, .9, .8, .8, .2, .2]],
             'alpha': [[1, .9, .1, .1, .1, .1], [2, .9, .8, .8, .2, .2]]}
    issues = second_opinion.run(ds, cfg, preds=preds)
    assert [(i.image, i.code, i.line) for i in issues] == [
        ('alpha', 'POSSIBLE_MISSING', None), ('alpha', 'POSSIBLE_MISSING', None),
        ('alpha', 'POSSIBLE_FALSE_POS', 1), ('beta', 'POSSIBLE_MISSING', None),
        ('beta', 'POSSIBLE_FALSE_POS', 1)]


def test_exact_confidence_and_area_thresholds_are_included(ds, cfg):
    ds.label_path('alpha').write_text('')
    cfg['second_opinion']['min_area_px'] = 640 * 480 * .125 * .125
    conf = cfg['second_opinion']['conf']
    issues = second_opinion.run(ds, cfg, preds={'alpha': [[0, conf, .5, .5, .125, .125]]})
    assert [i.code for i in issues] == ['POSSIBLE_MISSING']


def test_fp_support_does_not_require_same_class_high_confidence_or_large_area(ds, cfg):
    ds.label_path('alpha').write_text('1 .5 .5 .01 .01\n')
    issues = second_opinion.run(ds, cfg, preds={'alpha': [[2, cfg['second_opinion']['fp_conf'], .5, .5, .01, .01]]})
    assert issues == []


def test_gate_uses_unrounded_ratio_to_make_decision(cfg):
    stems = [f'frame-{i}' for i in range(10001)]
    issues = [Issue('edge', 'warn', 'W', s, 'warning') for s in stems[:1000]]
    verdict = gate.decide(issues, stems, cfg)
    assert verdict['warn_ratio'] == .1 and verdict['decision'] == 'Release'


def test_gate_never_hides_dataset_level_errors_or_counts_duplicate_stems(cfg):
    verdict = gate.decide([error('BAD_CLASS_NAME', image='data.yaml')], ['alpha', 'alpha'], cfg, {'alpha'})
    assert verdict['n_images'] == 1 and verdict['n_errors'] == 1 and verdict['decision'] == 'Rework'


def test_read_only_checks_leave_inputs_unchanged(ds, cfg):
    preds = {'alpha': [[0, .9, .5, .5, .2, .2]]}
    original_preds, original_cfg = deepcopy(preds), deepcopy(cfg)
    before = {p.relative_to(ds.root): p.read_bytes() for p in ds.root.rglob('*') if p.is_file()}
    issues = label_format.run(ds, cfg) + second_opinion.run(ds, cfg, preds=preds)
    gate.decide(issues, ['alpha'], cfg)
    after = {p.relative_to(ds.root): p.read_bytes() for p in ds.root.rglob('*') if p.is_file()}
    assert before == after and cfg == original_cfg and preds == original_preds

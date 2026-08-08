import json
import os

import pytest

from donkeycar.config import Config
from donkeycar.parts.image_transformations import (
    ImageTransformations,
    _pipeline_steps,
    build_preprocessing_metadata,
    check_preprocessing_metadata,
    load_config_and_myconfig,
    save_preprocessing_metadata,
)


class TestImageTransformationsDoesNotMutateConfig:
    def test_config_transformations_list_is_left_alone(self):
        # The two-arg form concatenates TRANSFORMATIONS + POST_TRANSFORMATIONS
        # for its own use; doing that with `+=` would extend the config's own
        # list in place, so every later reader (drive-time transformation
        # drift checks, preprocessing metadata) would see a pipeline the user
        # never configured.
        cfg = Config()
        cfg.TRANSFORMATIONS = []
        cfg.POST_TRANSFORMATIONS = ['CROP']
        cfg.ROI_CROP_TOP = 45
        cfg.ROI_CROP_BOTTOM = 0
        cfg.ROI_CROP_LEFT = 0
        cfg.ROI_CROP_RIGHT = 0

        part = ImageTransformations(cfg, 'TRANSFORMATIONS',
                                    'POST_TRANSFORMATIONS')
        assert len(part.transformations) == 1     # the CROP was picked up
        assert cfg.TRANSFORMATIONS == []          # but the config is untouched
        assert cfg.POST_TRANSFORMATIONS == ['CROP']


class TestLoadConfigAndMyconfig:
    def test_defaults_to_local_config_py(self, tmp_path, monkeypatch):
        # The standard `donkey createcar` layout: running an analysis tool
        # from the car directory with no --config must pick up ./config.py
        # (it used to hit os.path.abspath(None) and crash instead).
        (tmp_path / 'config.py').write_text('IMAGE_W = 111\nIMAGE_H = 222\n')
        monkeypatch.chdir(tmp_path)

        cfg = load_config_and_myconfig(None)
        assert cfg.IMAGE_W == 111
        assert cfg.IMAGE_H == 222

    def test_local_myconfig_overrides_config(self, tmp_path, monkeypatch):
        (tmp_path / 'config.py').write_text('IMAGE_W = 111\nIMAGE_H = 222\n')
        (tmp_path / 'myconfig.py').write_text('IMAGE_W = 999\n')
        monkeypatch.chdir(tmp_path)

        cfg = load_config_and_myconfig(None)
        assert cfg.IMAGE_W == 999     # override applied
        assert cfg.IMAGE_H == 222     # base setting retained

    def test_falls_back_to_bundled_template_outside_a_car_dir(
            self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert not os.path.exists('config.py')

        cfg = load_config_and_myconfig(None)
        # cfg_complete.py defines these; the point is simply that we loaded
        # a full base config rather than raising.
        assert cfg.IMAGE_W is not None
        assert cfg.DRIVE_LOOP_HZ is not None


class TestPipelineOrder:
    def test_augmentation_runs_before_crop_in_training(self):
        cfg = Config()
        cfg.TRANSFORMATIONS = []
        cfg.POST_TRANSFORMATIONS = ['CROP']
        cfg.AUGMENTATIONS = ['BRIGHTNESS', 'BLUR']

        training_steps = _pipeline_steps(cfg, include_augmentations=True)
        assert training_steps == ['BRIGHTNESS', 'BLUR', 'CROP']
        assert training_steps.index('CROP') > training_steps.index('BLUR')

    def test_validation_and_driving_never_see_augmentation(self):
        cfg = Config()
        cfg.TRANSFORMATIONS = []
        cfg.POST_TRANSFORMATIONS = ['CROP']
        cfg.AUGMENTATIONS = ['BRIGHTNESS', 'BLUR']

        steps = _pipeline_steps(cfg, include_augmentations=False)
        assert steps == ['CROP']
        assert 'BRIGHTNESS' not in steps
        assert 'BLUR' not in steps


class TestPreprocessingMetadata:
    def crop_cfg(self):
        cfg = Config()
        cfg.IMAGE_W = 160
        cfg.IMAGE_H = 120
        cfg.TRANSFORMATIONS = []
        cfg.POST_TRANSFORMATIONS = ['CROP']
        cfg.ROI_CROP_TOP = 45
        cfg.ROI_CROP_BOTTOM = 0
        cfg.ROI_CROP_LEFT = 0
        cfg.ROI_CROP_RIGHT = 0
        return cfg

    def test_build_metadata_reflects_config(self):
        meta = build_preprocessing_metadata(self.crop_cfg())
        assert meta['image_width'] == 160
        assert meta['image_height'] == 120
        assert meta['roi_crop_top'] == 45
        assert meta['pipeline_steps'] == ['CROP']

    def test_save_then_check_matching_config_does_not_raise(self, tmp_path):
        cfg = self.crop_cfg()
        model_path = str(tmp_path / 'mypilot.h5')
        with open(model_path, 'w') as f:
            f.write('placeholder')
        save_preprocessing_metadata(cfg, model_path)

        sidecar = tmp_path / 'mypilot.preprocessing.json'
        assert sidecar.exists()
        with open(sidecar) as f:
            saved = json.load(f)
        assert saved['roi_crop_top'] == 45

        # must not raise when config matches what was saved
        check_preprocessing_metadata(cfg, model_path)

    def test_check_detects_mismatch(self, tmp_path):
        cfg = self.crop_cfg()
        model_path = str(tmp_path / 'mypilot.h5')
        with open(model_path, 'w') as f:
            f.write('placeholder')
        save_preprocessing_metadata(cfg, model_path)

        drifted_cfg = self.crop_cfg()
        drifted_cfg.ROI_CROP_TOP = 30  # simulates a stale/edited car config
        with pytest.raises(RuntimeError, match='roi_crop_top'):
            check_preprocessing_metadata(drifted_cfg, model_path)

    def test_missing_sidecar_only_warns(self, tmp_path):
        cfg = self.crop_cfg()
        model_path = str(tmp_path / 'never_trained.h5')
        # no sidecar file written at all
        check_preprocessing_metadata(cfg, model_path)  # must not raise

    def test_detects_added_transformation_step(self, tmp_path):
        # The ROI_CROP_* fields are identical on both sides here; only the
        # step list differs, which is exactly what pipeline_steps exists to
        # catch (CANNY keeps the image dimensions, so nothing else would).
        cfg = self.crop_cfg()
        model_path = str(tmp_path / 'mypilot.h5')
        with open(model_path, 'w') as f:
            f.write('placeholder')
        save_preprocessing_metadata(cfg, model_path)

        drifted_cfg = self.crop_cfg()
        drifted_cfg.POST_TRANSFORMATIONS = ['CROP', 'CANNY']
        with pytest.raises(RuntimeError, match='pipeline_steps'):
            check_preprocessing_metadata(drifted_cfg, model_path)

    def test_legacy_sidecar_missing_new_fields_does_not_false_positive(
            self, tmp_path):
        # A sidecar saved before pipeline_steps existed (simulated here by
        # stripping that key) must not be treated as a mismatch just because
        # it lacks a field it predates - only fields it actually recorded
        # should ever be compared.
        cfg = self.crop_cfg()
        model_path = str(tmp_path / 'mypilot.h5')
        with open(model_path, 'w') as f:
            f.write('placeholder')
        save_preprocessing_metadata(cfg, model_path)

        sidecar_path = str(tmp_path / 'mypilot.preprocessing.json')
        with open(sidecar_path) as f:
            saved = json.load(f)
        del saved['pipeline_steps']
        with open(sidecar_path, 'w') as f:
            json.dump(saved, f)

        check_preprocessing_metadata(cfg, model_path)  # must not raise

    def test_skip_keys_excludes_fields_the_caller_reconciles_itself(
            self, tmp_path):
        # The offline analysis path calls check_model_image_size() first,
        # which takes the model file as the authority on its input size and
        # rewrites cfg to match (a documented convenience). Resolution is
        # therefore excluded from this comparison explicitly -- but the crop
        # geometry, which the model file cannot self-describe, must still be
        # enforced.
        cfg = self.crop_cfg()
        model_path = str(tmp_path / 'mypilot.h5')
        with open(model_path, 'w') as f:
            f.write('placeholder')
        save_preprocessing_metadata(cfg, model_path)

        res_only = self.crop_cfg()
        res_only.IMAGE_W = 192
        res_only.IMAGE_H = 108
        # must NOT raise: resolution is reconciled by check_model_image_size
        check_preprocessing_metadata(
            res_only, model_path, skip_keys=('image_width', 'image_height'))
        # ... but it still raises without the exemption
        with pytest.raises(RuntimeError, match='image_width'):
            check_preprocessing_metadata(res_only, model_path)

        # and a real crop mismatch is still caught even with the exemption
        crop_drift = self.crop_cfg()
        crop_drift.ROI_CROP_TOP = 30
        with pytest.raises(RuntimeError, match='roi_crop_top'):
            check_preprocessing_metadata(
                crop_drift, model_path,
                skip_keys=('image_width', 'image_height'))

    def test_context_appears_in_mismatch_message(self, tmp_path):
        cfg = self.crop_cfg()
        model_path = str(tmp_path / 'mypilot.h5')
        with open(model_path, 'w') as f:
            f.write('placeholder')
        save_preprocessing_metadata(cfg, model_path)

        drifted_cfg = self.crop_cfg()
        drifted_cfg.ROI_CROP_TOP = 30
        with pytest.raises(RuntimeError, match="analysis's config"):
            check_preprocessing_metadata(
                drifted_cfg, model_path, context="this analysis's config")

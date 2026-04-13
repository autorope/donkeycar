# Main Python 3.13 Upgrade Plan

Goal: create a clean Python 3.13 upgrade branch from `docgarbanzo/main`,
carry over only the Python 3.13 / TensorFlow LiteRT compatibility work from
`python313-upgrade`, and verify the result with passing tests.

## Scope

This branch should contain only the changes needed to:

- support Python 3.13
- keep TensorFlow-dependent code import-safe when TensorFlow is absent
- support Raspberry Pi inference with `ai-edge-litert`
- keep tests green on the cleaned-up branch

It should **not** pull in unrelated `dev` work from `python313-upgrade`.

## Source branches

- Base branch: `docgarbanzo/main`
- Target branch: `main-py313-upgrade`
- Source of upgrade work: `python313-upgrade`

## Checklist

- [x] Verify whether `docgarbanzo/main` and `autorope/main` are identical
- [x] Fast-forward `docgarbanzo/main` to match `autorope/main` exactly
- [x] Create/reset `main-py313-upgrade` from synced `docgarbanzo/main`
- [x] Select only the Python 3.13 upgrade commits from `python313-upgrade`
- [x] Cherry-pick the selected upgrade commits onto `main-py313-upgrade`
- [x] Resolve any cherry-pick conflicts cleanly
- [x] Review the key resulting diffs against `main`
- [x] Run targeted tests in the `donkey313` conda environment
- [x] Run a broader regression test pass in the `donkey313` conda environment
- [x] Fix any failing tests or branch-specific issues
- [ ] Write a comprehensive Markdown commit message
- [ ] Commit the cleaned-up `main-py313-upgrade` branch
- [ ] Push `main-py313-upgrade` to `docgarbanzo`

## Candidate upgrade commits to port

These are the commits currently believed to be in-scope for the clean branch:

- `af6f141b3` Upgrade to Python 3.13 and update dependencies
- `7b0f37df7` Fix tf.* type annotations that fail when TF is not installed
- `a00dc5ce1` Fix remaining tf.* function signature annotations for Pi compatibility
- `8536a5461` Skip keras tests when TensorFlow is not installed
- `15b133621` Fix Python 3.13 compatibility: ManifestIterator and TF-only test skips
- `cdb72babb` Skip test_drivesim when TensorFlow is not installed
- `916f76854` Implement Step 4: TFLite tensor-API fallback for Python 3.13 compatibility
- `e22dc70a8` Fix output_shapes() to work without TensorFlow (Pi inference)
- `f5e35c111` Fix Pi LiteRT shape handling in keras

## Notes

- `python313-upgrade` contains a large amount of unrelated `dev` work, so we
  must cherry-pick selectively instead of merging the branch.
- The current shell is on the `base` conda environment, not `donkey`.
  Before running Python or pytest, switch to `donkey` using:

  ```zsh
  source /opt/miniconda3/etc/profile.d/conda.sh && conda activate donkey
  ```

- If cherry-picks expose missing prerequisite changes from `main`, capture
  those explicitly here rather than broadening scope implicitly.

## Progress log

- Synced `docgarbanzo/main` to `autorope/main` (`ae588e86e`)
- Reset `main-py313-upgrade` to the synced `docgarbanzo/main`
- Selected and applied the scoped Python 3.13 / LiteRT compatibility changes
  from `python313-upgrade`
- Resolved cherry-pick conflicts by keeping the cleaned-up `main` base and
  re-applying only the upgrade-relevant logic
- Reviewed the key diffs in `setup.cfg`, `interpreter.py`, `keras.py`,
  `training.py`, and the affected tests
- Installed the branch into the `donkey313` environment (`Python 3.13.13`)
- Initial full test run exposed a bad `PipelineGenerator` import in
  `donkeycar/pipeline/training.py`; fixed by restoring the `main` pipeline
  structure and keeping only the upgrade-relevant changes
- Initial full test run also exposed two Keras 3 / LiteRT issues:
  `_tshape()` did not handle `np.integer` scalars and `test_tubplot` still
  saved a `.savedmodel`; both were fixed
- Targeted rerun passed for `test_keras.py` and `test_scripts.py`
- Full test suite now passes on `main-py313-upgrade` in `donkey313`:
  `163 passed, 16 skipped, 1 xfailed`

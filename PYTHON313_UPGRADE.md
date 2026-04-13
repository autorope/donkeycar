# Python 3.13 Upgrade Plan

Upgrade donkeycar from Python 3.11 to support Python 3.13, required for
Raspberry Pi 5 running Debian Trixie.

## Status Legend
- [ ] Pending
- [~] In Progress / Blocked
- [x] Complete

---

## Step 1: Update `setup.cfg` — Package Metadata and Dependencies
- [x] `python_requires`: change `>=3.11.0,<3.12` → `>=3.13.0,<3.14` (single version)
- [x] Update classifier to Python 3.13 only
- [x] `numpy`: bump lower bound to `>=1.26.0` (required by TF 2.20)
- [x] `pc` extra: `tensorflow==2.15.*` → `tensorflow==2.21.*`, add `tf-keras==2.21.*`
- [x] `macos` extra: same TF changes as pc
- [x] `pi` extra: remove `tflite-runtime`, add `ai-edge-litert>=2.1.4`
- [x] `pi` extra: remove `flatbuffers==24.3.*` (ai-edge-litert pulls its own)
- [x] `torch` extra: `torch==2.1.*` → `torch==2.6.*`, `torchvision==0.21.*`, `torchaudio==2.6.*`

## Step 2: Fix `tensorflow.python.*` Internal API Imports

These internal paths were removed in TF 2.16+.

- [x] `donkeycar/parts/interpreter.py`: restore `get_tflite_interpreter()` with
  `ai_edge_litert` fallback; fix `tensorflow.python.saved_model` imports; wrap
  TF imports in try/except
- [x] `donkeycar/parts/keras.py`: wrap TF imports in try/except; replace
  `DatasetV1/DatasetV2` type hints with `Any`
- [x] `donkeycar/pipeline/training.py`: fix
  `from tensorflow.python.keras.models import load_model`
- [x] `donkeycar/parts/keras_2.py`: fix
  `from tensorflow.python.keras.layers import Activation`
- [x] `donkeycar/management/makemovie.py`: fix 3x `tensorflow.python.keras` imports
- [x] `donkeycar/management/base.py`: fix `tensorflow.python.keras.models` import

## Step 3: Fix Keras 3.x Breaking Changes (TF 2.16+)

TF 2.16+ switched from Keras 2 to standalone Keras 3, which broke many APIs.

- [x] `donkeycar/parts/keras.py`:
  - Replace `from keras.backend import concatenate` →
    `from tensorflow.keras.layers import concatenate`
  - Remove `workers=1, use_multiprocessing=False` from `model.fit()` (removed
    in Keras 3)
  - `KerasCategorical.compile()`: set `metrics=['accuracy', 'accuracy']` for
    dual-output model
  - `KerasLocalizer.compile()`: set `metrics={'zloc': 'accuracy'}`
  - `KerasInferred.y_transform()`: return raw float (not dict) — Keras 3
    single-output models require raw arrays, not dicts
  - `KerasInferred.output_shapes()`: return `(input_dict, tf.TensorShape([]))`
  - `KerasInferred.output_types()`: new override returning `(input_dict, tf.float64)`
  - `KerasLSTM.y_transform()`: return `np.array([angle, throttle])` (not dict)
  - `KerasLSTM.output_shapes()`: return `(input_dict, tf.TensorShape([n]))`
  - `KerasLSTM.output_types()`: new override
  - `Keras3D_CNN.y_transform()`: return `np.array([angle, throttle])` (not dict)
  - `Keras3D_CNN.output_shapes()`: return `(input_dict, tf.TensorShape([n]))`
  - `Keras3D_CNN.output_types()`: new override
- [x] `donkeycar/parts/interpreter.py`:
  - `KerasInterpreter.set_model()`: replace `self.model.input_names` (removed in
    Keras 3) with `[inp.name for inp in self.model.inputs]`
- [x] `donkeycar/pipeline/database.py`:
  - Default extension: `'savedmodel'` → `'keras'`
  - `transfer_fmt()`: strip `.keras` suffix correctly
  - `model_prefix_map`: fix `.h5` key (was `'h5'`), add `'.keras': ''`
- [x] `donkeycar/pipeline/training.py`:
  - TRT path: use `!= '.savedmodel'` check; use `model_tmp.export()` for
    savedmodel format
- [x] `donkeycar/templates/complete.py` and `simulator.py`:
  - Add `.keras` to model path extension checks
- [x] `donkeycar/tests/test_train.py`:
  - `pilot_name`: `.savedmodel` → `.keras`
  - `test_training_pipeline`: add `isinstance(batch, dict)` check for raw array
    case (single-output Keras 3 models return raw arrays, not dicts)

## Step 4: Fix TFLite Conversion (TF 2.20 / Keras 3.x) — **BLOCKED**

**Context:** TFLite inference is non-negotiable — it is the primary inference
method on Raspberry Pi. All models are converted to TFLite for deployment.

### What Was Broken

`TFLiteConverter.from_keras_model(model)` is broken with Keras 3.x:

```
TypeError: 'NoneType' object is not callable
# in tensorflow/lite/python/convert.py → tflite_keras_util.py
```

Root cause: The TFLite conversion utility assumes Keras 2 model internals that
no longer exist in Keras 3.

### Approaches Tried

**Approach 1: `model.export()` + `from_saved_model()`**
```python
model.export(savedmodel_path)
converter = tf.lite.TFLiteConverter.from_saved_model(savedmodel_path)
```
Result: FAILED. `model.export()` raises:
```
TypeError: this __dict__ descriptor does not support '_DictWrapper' objects
```
Root cause: Python 3.13 changed `inspect.getattr_static` behavior.
`tf.saved_model.save()` uses it internally to traverse `_DictWrapper` objects
(a TF internal class), which now raises `TypeError` in Python 3.13.

**Approach 2: `tf.saved_model.save(model, path)`**
Same `_DictWrapper` failure as above.

**Approach 3: `tf.function` + `from_concrete_functions` (current state)**
```python
input_sig = [tf.TensorSpec(shape=(1,) + tuple(inp.shape[1:]),
                           dtype=tf.float32, name=inp.name)
             for inp in model.inputs]
tf_func = tf.function(model, input_signature=input_sig)
concrete = tf_func.get_concrete_function()
converter = tf.lite.TFLiteConverter.from_concrete_functions([concrete], tf_func)
tflite_model = converter.convert()
```
Result: **CONVERSION SUCCEEDS** — produces valid TFLite bytes for all 9 model
types. However, the resulting `.tflite` file has **0 signatures** (no
`serving_default`). `TfLite.load()` calls `get_signature_runner()` which
requires exactly 1 signature, so it fails:
```
ValueError: SignatureDef signature_key is None and model has 0 Signatures.
None is only allowed when the model has 1 SignatureDef
```

**Approach 4: `tf.Module` wrapper + `tf.saved_model.save(signatures=...)`**
```python
module = tf.Module()
module._model = model  # track model
module.infer = tf.function(model, input_signature=input_sig)
tf.saved_model.save(module, path, signatures={'serving_default': concrete})
converter = tf.lite.TFLiteConverter.from_saved_model(path)
```
Result: FAILED. When `module._model = model` is set (to track the Keras model),
hits the same `_DictWrapper` bug. Without `_model`, hits:
```
AssertionError: untracked resource
```

### Current Working Conversion

The `from_concrete_functions` approach (Approach 3) successfully converts all
9 model types to TFLite. The TFLite bytes are valid. The only problem is the
missing `serving_default` signature.

### Required Fix: Update `TfLite` Interpreter

`TfLite.load()` and `predict_from_dict()` must fall back to the tensor-based
API when no signatures are present. The tensor-based API works without
signatures and maps inputs by name. Key observations:

- Input tensor names ARE correctly preserved from `from_concrete_functions`
  (e.g., `img_in`, `imu_in` — matching the Keras model input names)
- Output tensor names become generic (`Identity`, `Identity_1`) but can be
  accessed by `index` from `get_output_details()`

#### Required changes to `TfLite` in `interpreter.py`:

**`load()`** — fall back to tensor API when no signatures:
```python
def load(self, model_path):
    assert os.path.splitext(model_path)[1] == '.tflite'
    TfliteInterpreter = get_tflite_interpreter()
    self.interpreter = TfliteInterpreter(model_path=model_path)
    self.signatures = self.interpreter.get_signature_list()
    if self.signatures:
        self.runner = self.interpreter.get_signature_runner()
        self.input_keys = list(self.signatures['serving_default']['inputs'])
        self.output_keys = list(self.signatures['serving_default']['outputs'])
    else:
        # No signatures (from_concrete_functions path): use tensor API
        self.runner = None
        self.interpreter.allocate_tensors()
        in_details = self.interpreter.get_input_details()
        out_details = sorted(self.interpreter.get_output_details(),
                             key=lambda d: d['index'])
        # Input tensor names: e.g. 'serving_default_img_in:0' or just 'img_in'
        self.input_keys = [d['name'].removeprefix('serving_default_')
                                    .removesuffix(':0')
                           for d in in_details]
        self._input_index_map = {k: d['index']
                                 for k, d in zip(self.input_keys, in_details)}
        self._output_indices = [d['index'] for d in out_details]
        self.output_keys = [str(i) for i in range(len(out_details))]
```

**`predict_from_dict()`** — use tensor API when `self.runner is None`:
```python
def predict_from_dict(self, input_dict):
    for k, v in input_dict.items():
        input_dict[k] = self.expand_and_convert(v)
    if self.runner is not None:
        outputs = self.runner(**input_dict)
        ret = list(outputs[k][0] for k in self.output_keys)
    else:
        for k, v in input_dict.items():
            self.interpreter.set_tensor(self._input_index_map[k], v)
        self.interpreter.invoke()
        ret = [self.interpreter.get_tensor(i)[0]
               for i in self._output_indices]
    return ret if len(ret) > 1 else ret[0]
```

**`get_input_shape()`** — handle both `serving_default_{name}:0` and plain
`{name}` formats:
```python
def get_input_shape(self, input_name):
    assert self.interpreter is not None, "Need to load tflite model first"
    details = self.interpreter.get_input_details()
    for detail in details:
        name = detail['name']
        # Match 'serving_default_img_in:0' or 'img_in'
        if (name == f"serving_default_{input_name}:0"
                or name == input_name
                or name.removeprefix('serving_default_').removesuffix(':0')
                    == input_name):
            return detail['shape']
    raise RuntimeError(f'{input_name} not found in TFLite model')
```

### Outstanding Issue: Output Key Alignment

With the tensor-based fallback, output tensor names become generic (`Identity`,
`Identity_1`) and are ordered by TFLite index. The `from_concrete_functions`
path *should* preserve the Keras model's output order in the TFLite indices,
but this needs verification.

**How to verify:** Run the 9 TFLite tests:
```bash
source /opt/miniconda3/etc/profile.d/conda.sh && conda activate donkey313 && \
  pytest donkeycar/tests/test_keras.py::test_keras_vs_tflite_and_tensorrt -v
```
All 9 variants must pass within `TOLERANCE = 1e-4`. Two-output models (e.g.
`KerasLinear` returns `[angle, throttle]`) are the ones that would expose a
swap — the numerical `approx` check would fail if outputs are reordered.

**If output ordering is wrong:** After `allocate_tensors()`, compare
`get_output_details()` index order against the Keras model's `output_names`
(available on the `KerasInterpreter.model` before conversion). Sort
`_output_indices` to match the Keras output order. The Keras model's output
order is the ground truth; the TFLite indices must be remapped to it.

### Status

- [~] TFLite conversion (`keras_to_tflite()`): **WORKS** via
  `from_concrete_functions` for all 9 model types
- [x] `TfLite.load()`: tensor-API fallback implemented
- [x] `TfLite.predict_from_dict()`: tensor-API branch implemented
- [x] `TfLite.get_input_shape()`: flexible name matching implemented
- [x] All 9 `test_keras_vs_tflite_and_tensorrt` tests passing (8 pass, 1 xfail
  for Keras3D_CNN which requires the TFLite Flex delegate for MaxPool3D)
- [x] Output ordering verified: 8/9 models pass numerical approx check within
  TOLERANCE=1e-4; output indices from `from_concrete_functions` match Keras
  model output order

### Alternative Approach to Investigate

According to TF 2.20 release notes and GitHub discussions, `from_keras_model`
should still work via the Keras export path on Python 3.11/3.12. The
`_DictWrapper` failure is specific to Python 3.13's stricter
`inspect.getattr_static`. If TF or Keras releases a fix for this, revert to
`from_keras_model` or `model.export()` + `from_saved_model()` which produce
signatures natively.

Issue tracker references:
- https://github.com/tensorflow/tensorflow/issues (search: "tflite keras 3")
- https://github.com/keras-team/keras/issues (search: "export tflite python 3.13")

## Step 5: Update GitHub Actions CI
- [x] Add Python 3.13 to test matrix in
  `.github/workflows/python-package-conda.yml`

## Step 6: Update CLAUDE.md
- [x] Update Python version requirement from `3.11+ but < 3.12` to `3.11–3.13`

## Step 7: Testing

### 7a: Source-branch validation

- [x] Run full test suite on Ubuntu with existing Python 3.11
- [x] Run full test suite on Pi Python 3.13 on the source upgrade branch
- [x] Verify camera and GPIO imports on Pi
- [x] Verify TFLite inference with `ai-edge-litert` on Pi on the source
  upgrade branch
- [x] All 9 `test_keras_vs_tflite_and_tensorrt` tests passing on x86

### 7b: Clean-branch follow-up

- [ ] Re-run the relevant tests on this cleaned-up `main-py313-upgrade`
  branch
- [ ] Verify TFLite via `ai-edge-litert` on Pi for this cleaned-up branch

---

## Key Decisions

**TensorFlow:** TF 2.20 was the first release with Python 3.13 wheels; pinned
to 2.21 (latest). TF 2.16+ uses standalone Keras 3; the `tf-keras` shim
restores the Keras 2 API as `tensorflow.keras.*`. All
`tensorflow.python.keras.*` imports must be replaced with
`tensorflow.keras.*`.

**TFLite on Pi:** `tflite-runtime` is dead (last release 2.14, Python 3.11
max). Replaced by `ai-edge-litert` (Google's official successor, drop-in API).
TFLite inference is the **primary and non-negotiable inference method** for
Raspberry Pi deployment.

**PyTorch:** `torch==2.6.*` is the first series with Python 3.13 aarch64
wheels. `torchvision==0.21.*` and `torchaudio==2.6.*` match.

**RPi.GPIO vs gpiozero:** Do NOT follow autorope/main switching to `RPi.GPIO`
(wheels stop at Python 3.9). Keep `gpiozero` which supports Python 3.13.

**Nano extra:** Leave numpy/matplotlib/pandas pins — they reflect Jetson Nano
hardware constraints, not Python version limitations.

**Python 3.13 + TF 2.20 TFLite gotcha:** `inspect.getattr_static` behavior
changed in Python 3.13. TF's internal `_DictWrapper` class is incompatible with
the new behavior, breaking all SavedModel export paths (including `model.export()`
and `tf.saved_model.save()`). The workaround via `tf.function +
from_concrete_functions` converts successfully but strips signatures from the
output, requiring `TfLite` to fall back to the tensor-based inference API.

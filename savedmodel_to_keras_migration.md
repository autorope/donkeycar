# SavedModel → .keras Migration Plan

## Definitive Answers to the Three Questions

### Q1: Is the SavedModel format still supported for reading/writing models in TF 2.19?

**It depends on which API layer:**

| API Call                                      | Supported in TF 2.19 / Keras 3? |
| --------------------------------------------- | -------------------------------- |
| `model.save('path.savedmodel')`               | ❌ **No.** Keras 3 requires `.keras` or `.h5` extensions. |
| `keras.models.load_model('path.savedmodel')`  | ❌ **No.** Keras 3 does not recognise SavedModel directories. |
| `model.save('path.keras')`                    | ✅ Yes (new native Keras 3 format). |
| `model.save('path.h5')`                       | ✅ Yes (legacy). |
| `model.export('path.savedmodel')`             | ✅ Yes — produces a SavedModel directory **for deployment / conversion only**. One-way export; the result is NOT a Keras model you can reload. |
| `tf.saved_model.load('path.savedmodel')`      | ✅ Yes at the low TF level — but returns a raw `tf.Module` / trackable object, **not** a Keras model. You lose `.predict()`, `input_names`, `output_names`, training hooks, etc. |

**Evidence in the codebase:**
- `tests/test_keras.py:46` explicit comment: *"Keras 3 requires .keras or .h5 extension"* and uses `model.keras` for the test artefact.
- `pipeline/training.py:187-190` uses `model.export(...savedmodel)` (not `model.save(...)`) when producing a SavedModel intermediate for TRT.
- `parts/interpreter.py:404` still had legacy code calling `keras.models.load_model('...savedmodel')` — this code path was **broken** in Keras 3 and has been removed.

### Q2: Should we be backward compatible with old `.savedmodel` pilot models?

**No.** The reasons are structural, not stylistic:

1. `keras.models.load_model()` — the API `KerasInterpreter.load()` depends on — does not accept SavedModel directories in Keras 3. No monkey-patching changes this.
2. `tf.saved_model.load()` does work, but it returns a raw TF object with no Keras API. Supporting it would require a completely parallel inference code path (no `model.output_names`, no `.compile()`, no `.fit()` for transfer learning, different prediction signature). High maintenance cost for deprecated artefacts.
3. There is no automated way to convert an old `.savedmodel` back into `.keras`: you cannot reconstruct the Keras model graph from a SavedModel in general.
4. Users who have `.savedmodel` models on disk will need to retrain. This is the same break-point the Keras 3 upgrade imposed on the wider ecosystem; we inherit it, we do not work around it.

### Q3: Should we remove SavedModel everywhere?

**Remove from all user-facing places** (UI filters, database strings, path
detection, conversion scripts that consume `.savedmodel`).

**Keep in exactly two internal places**, where SavedModel is never visible to
the user and is only used as a one-shot intermediate:

- `pipeline/training.py` — `model.export(...savedmodel)` to feed TRT converters
  that require SavedModel input.
- `parts/interpreter.py` — `saved_model_to_tensor_rt()` and `TensorRT.load()`
  using `tf.saved_model.load()` on `.trt` (which is itself a SavedModel-format
  directory produced by the TRT converter).

---

## Concrete Changes — COMPLETED ✅

### ✅ 1. `donkeycar/parts/interpreter.py`

**a) `KerasInterpreter.load()` (line 209)**
Updated stale comment: now says output names can be lost when *exporting* to
SavedModel for TRT, not when saving `.keras`.

**b) `TensorRT.load()` (lines 397-420)**
Removed the `ext == '.savedmodel'` branch entirely. It called
`keras.models.load_model()` on a SavedModel directory, which is broken in
Keras 3. The method now only accepts `.trt` inputs via `tf.saved_model.load`.

### ✅ 2. `donkeycar/pipeline/database.py`

**a) `transfer_fmt` function**
Removed `.savedmodel` from the strip chain.

**b) `model_prefix_map`**
Removed the `.savedmodel` entry.

### ✅ 3. `donkeycar/templates/complete.py`

Removed `.savedmodel` from the model-format detection condition.

### ✅ 4. `donkeycar/templates/simulator.py`

Removed `.savedmodel` from the model-format detection condition.

### ✅ 5. `donkeycar/management/ui/car_screen.py`

- Sync buttons updated: `['h5', 'savedmodel', 'tflite', 'trt']`
  → `['h5', 'keras', 'tflite', 'trt']`
- Directory treatment: only `.trt` gets the `/***` rsync suffix now (`.keras`
  is a file, `.savedmodel` removed).

### ✅ 6. `donkeycar/management/ui/train_screen.py`

- `TransferSelector.filters`: `['*.h5', '*.savedmodel']` → `['*.h5', '*.keras']`
- `train_call`: replaced `.savedmodel` path with `.keras`; variable `sm` renamed
  to `keras`; status message updated accordingly.

### ✅ 7. `donkeycar/management/ui/pilot_screen.py`

- `ALL_FILTERS`: `['*.h5', '*.tflite', '*.savedmodel', '*.trt']`
  → `['*.h5', '*.keras', '*.tflite', '*.trt']`
- TensorRT filter: `['*.trt', '*.savedmodel']` → `['*.trt']`
- Default filter: `['*.h5', '*.savedmodel']` → `['*.h5', '*.keras']`

### ✅ 8. `scripts/convert_to_tflite.py`

- Docstring updated to reflect `.keras` (not `.savedmodel`) as accepted input.
- Extension check: `.savedmodel` → `.keras`.
- `keras_model_to_tflite` already calls `keras.models.load_model` which handles
  `.keras` natively; no changes needed to the conversion function itself.

### ✅ 9. `donkeycar/tests/test_keras.py`

Renamed local variable `savedmodel_path` → `keras_path` for clarity.
Removed stale comment about Keras 3 extension requirement (now obvious from name).

### ✅ 10. `donkeycar/pipeline/training.py` (bonus cleanup)

Removed dead guard `if ext != '.savedmodel':` — the model extension is always
`.keras` or `.h5` now, so the export always runs unconditionally.

---

## What Stays (and Why)

| Location                                                  | Why it stays                                                              |
| --------------------------------------------------------- | ------------------------------------------------------------------------- |
| `pipeline/training.py:185-192`                            | `model.export('.savedmodel')` is the correct, supported Keras 3 API for producing the TRT input. Never user-facing. |
| `parts/interpreter.py:saved_model_to_tensor_rt`           | TRT converter consumes a SavedModel directory. Internal only.             |
| `parts/interpreter.py:TensorRT.load` (`.trt` branch)     | `tf.saved_model.load()` reads the TRT-converted graph (also SavedModel-shaped). Not a Keras-level load. |
| `templates/cfg_basic.py` / `cfg_complete.py` `SAVE_MODEL_AS_H5` | Still meaningful: chooses between `.h5` and `.keras`.                |

---

## Testing

- Unit tests in `tests/test_keras.py` already use `.keras`; they should continue
  to pass.
- Manual smoke-test path: train a model → verify it is saved as `.keras` →
  load it via the UI → run inference. Then train with `CREATE_TENSOR_RT=True`
  and verify the intermediate `.savedmodel` is produced and the `.trt` file is
  loadable.
- After the UI filter changes, verify the pilot/train/car screens only list
  `.keras` (and `.h5` where legacy), never `.savedmodel`.

# Python 3.12/3.13 Migration

Donkeycar moved from Python 3.11 + conda to Python 3.12+ + uv. This document
covers every technical decision, all code changes, the new install workflow,
and what the documentation team needs to update.

---

## Python version per platform

| Platform | Python | Reason |
|---|---|---|
| Mac (`[macos]`) | **3.12** | `tensorflow-metal==1.2.0` has no Python 3.13 wheel; TF 2.19 SavedModel export broken on 3.13 |
| PC (`[pc]`) | **3.12** | TF 2.19 SavedModel export broken on 3.13 |
| Raspberry Pi (`[pi]`) | **3.13** | `libcamera`/`picamera2` are Debian system packages for Python 3.13; no pip-installable alternative |

**Why not 3.13 for Mac/PC:** TF's internal `inspect.getattr_static` behavior
changed in 3.13, breaking all SavedModel export paths (`model.export()`,
`tf.saved_model.save()`). The `_DictWrapper` workaround via
`tf.function + from_concrete_functions` produces TFLite with no
`serving_default` signature, requiring a tensor-API fallback in the `TfLite`
interpreter. This is too invasive for the current release cycle.

**Why 3.13 on Pi:** `python3-libcamera` and `python3-picamera2` are Debian
packages installed for the system Python (3.13 on Trixie). The venv must use
the system Python with `--system-site-packages` to access them. A Python 3.12
venv cannot reach these packages even with `--system-site-packages` because
Debian installs them under `/usr/lib/python3/dist-packages`, not under the
custom Python 3.12 tree at `/usr/local`.

---

## Why uv (not conda)

- Single cross-platform tool: same workflow on Pi, Mac, and PC.
- Persistent named venv at a fixed path — `donkey` commands work from any
  directory once the venv is activated in the shell profile.
- `uv pip install` is a drop-in for pip; editable installs (`-e`) work
  unchanged.
- On Pi, the Debian system Python 3.13 is used directly (not uv's bundled
  CPython) because camera libraries are Debian system packages that must be
  visible to the venv via `--system-site-packages`.

---

## TensorFlow version decision

| Platform | TF version | Notes |
|---|---|---|
| Mac (`macos` extra) | `2.19.*` | Highest version compatible with `tensorflow-metal==1.2.0` |
| PC (`pc` extra) | `2.19.*` | Kept in sync with Mac for model format compatibility |
| Pi | — | Pi uses `ai-edge-litert` (TFLite), not TF |

**`tensorflow-metal` compatibility wall:** TF 2.20 changed the internal
`_pywrap_tensorflow_internal.so` rpath, breaking `libmetal_plugin.dylib`.
TF 2.18 and 2.19 both work with `tensorflow-metal==1.2.0` on **Python 3.12
only**. TF 2.20 and 2.21 do not. Check back when Apple releases
tensorflow-metal 1.3+.

**`tensorflow-metal==1.1.0`** (the previous version) has no Python 3.12 wheel.
`1.2.0` is the first release with a `cp312` wheel. There is no `cp313` wheel.

**Inference performance:** TFLite on Pi 5 (aarch64, XNNPACK): **~282 fps**
for a `KerasLinear` 160×120×3 model. No regression vs TF 2.21 on the same
model.

---

## Key dependency changes

| Dependency | Before | After | Reason |
|---|---|---|---|
| Python (Mac/PC) | 3.11 | 3.12 | Stability, TF 2.19 support |
| Python (Pi) | 3.11 | 3.13 | System Python required for Debian camera packages |
| TF (pc/mac) | `2.15.*` | `2.19.*` | Latest compatible with metal |
| `tflite-runtime` | present | **removed** | Dead project (last release Python 3.11) |
| `ai-edge-litert` | absent | `>=2.1.4` | Google's official TFLite successor, drop-in API |
| `tensorflow-metal` | `1.1.0` | `1.2.0` | First release with Python 3.12 wheel |
| `RPi.GPIO` | present | **removed** | No wheels past Python 3.9 |
| `gpiozero` | absent | present | Supports Python 3.12+, covers same hardware |
| `torch` | `2.1.*` | `2.6.*` | First series with Python 3.12+ aarch64 wheels |
| `picamera2` (pi extra) | present | **removed** | Debian system package only; install via `apt` |

---

## Codebase changes

### Package metadata (`pyproject.toml`)

`setup.cfg` and `MANIFEST.in` were deleted. All metadata now lives in
`pyproject.toml`:

- `[project]` — name, dynamic version, authors, license, classifiers,
  `requires-python = ">=3.12.0,<3.14"`, core dependencies
- `[project.optional-dependencies]` — `pi`, `pc`, `macos`, `dev`, and
  `torch` extras
- `[project.scripts]` — `donkey` entry point
- `[tool.setuptools.dynamic]` — `version = {attr = "donkeycar.__version__"}`
- `[tool.setuptools.packages.find]` — `namespaces = true`
- `[tool.setuptools.package-data]` — covers `*.html/ini/txt/kv` plus
  `donkeycar/management/tub_web/static/**/*` (was in MANIFEST.in)

### CI (`.github/workflows/python-package.yml`)

Replaced `python-package-conda.yml`. New workflow:

```yaml
- uses: astral-sh/setup-uv@v5
  with:
    python-version: '3.12'
- run: uv pip install -e ".[pc,dev]"
- run: uv run pytest
```

### TF internal API imports

`tensorflow.python.keras.*` was removed in TF 2.16+. All occurrences replaced
with `tensorflow.keras.*` or wrapped in `try/except ImportError`:

- `donkeycar/parts/interpreter.py`
- `donkeycar/parts/keras.py`
- `donkeycar/pipeline/training.py`
- `donkeycar/parts/keras_2.py`
- `donkeycar/management/makemovie.py`
- `donkeycar/management/base.py`

### Keras 3.x breaking changes (TF 2.16+)

TF 2.16 switched from bundled Keras 2 to standalone Keras 3. The `tf-keras`
package restores the Keras 2 API at `tensorflow.keras.*`:

- `from keras.backend import concatenate` →
  `from tensorflow.keras.layers import concatenate`
- `workers=1, use_multiprocessing=False` removed from `model.fit()` (gone in
  Keras 3)
- `model.input_names` removed in Keras 3 → replaced with
  `[inp.name for inp in model.inputs]`
- Default model save format: `savedmodel` → `keras`
- `model_prefix_map` in `pipeline/database.py` updated for `.keras` extension

### TFLite on Pi (`ai-edge-litert`)

`tflite-runtime` is dead (last release: TF 2.14 / Python 3.11 max). Replaced
by `ai-edge-litert`, which is Google's official successor with a drop-in API.
No inference code changes required — only the import and package name changed.

The `TfLite` interpreter in `interpreter.py` was updated with a tensor-API
fallback for models without `serving_default` signatures (needed when
converting from Keras 3 via `from_concrete_functions`).

---

## Pi: Python 3.13 (system) on Debian Trixie

Pi 5 running Debian 13 (Trixie) ships Python 3.13 as the system default.
Camera support requires `libcamera` and `picamera2`, which are Debian packages
installed for that system Python — they are not available on PyPI. The venv
must therefore use the system Python 3.13 with `--system-site-packages`:

```zsh
sudo apt install python3-libcamera python3-picamera2
uv venv ~/env --python 3.13 --system-site-packages
```

Using `--python 3.12` (custom-built at `/usr/local/bin/python3.12`) will not
work: its `--system-site-packages` only includes
`/usr/local/lib/python3.12/site-packages`, not Debian's
`/usr/lib/python3/dist-packages` where `libcamera` and `picamera2` live.

---

## Install workflow (uv)

### First-time setup — all platforms

```zsh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Raspberry Pi

```zsh
sudo apt install python3-libcamera python3-picamera2
uv venv ~/env --python 3.13 --system-site-packages
echo 'source ~/env/bin/activate' >> ~/.zshrc
source ~/env/bin/activate

# User install (PyPI):
uv pip install donkeycar[pi]

# Developer install (git clone):
uv pip install -e ".[pi,dev]"
```

### Mac

```zsh
uv venv ~/.venvs/donkeycar --python 3.12
echo 'source ~/.venvs/donkeycar/bin/activate' >> ~/.zshrc
source ~/.venvs/donkeycar/bin/activate

# User install (PyPI):
uv pip install donkeycar[macos]

# Developer install (git clone):
uv pip install -e ".[macos,dev]"
```

### PC (Linux / Windows)

```zsh
uv venv ~/.venvs/donkeycar --python 3.12
echo 'source ~/.venvs/donkeycar/bin/activate' >> ~/.zshrc
source ~/.venvs/donkeycar/bin/activate

# User install (PyPI):
uv pip install donkeycar[pc]

# Developer install (git clone):
uv pip install -e ".[pc,dev]"
```

---

## Documentation updates required

The following pages on docs.donkeycar.com need updating before this branch
is merged to main:

| Page | What to change |
|---|---|
| Install — Raspberry Pi | Replace conda/pip steps with uv workflow above; note Pi uses TFLite via `ai-edge-litert`, not full TF |
| Install — Mac | Replace conda steps with uv + `[macos]` extra; note TF 2.19 + Metal GPU |
| Install — PC / Linux | Replace conda steps with uv + `[pc]` extra |
| Software requirements | Update Python version from 3.11 to 3.12 (Mac/PC) or 3.13 (Pi); remove conda prerequisite; add uv install step |
| Upgrade guide | Add section: "Upgrading from conda to uv" — remove old env, install uv, create new venv |
| Training / model formats | Note default save format is now `.keras` (was `.savedmodel`) |
| Pi inference | Update package name from `tflite-runtime` to `ai-edge-litert`; confirm API is identical |
| CI badge in README | Already updated to `python-package.yml` |

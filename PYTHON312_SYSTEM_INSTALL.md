# Python 3.12 System Install on Debian 13 (trixie)

This machine is running Debian GNU/Linux 13 (`trixie`) and already had distro
Python `3.13.5` as the default `python3`.

There is no standard Debian package for Python 3.12 in the configured `apt`
repositories on this host:

- `apt-cache policy python3.12 python3.12-venv python3.12-dev` returned no
  package candidates.
- `apt-cache search '^python3.12($|-)'` returned no matches.

Because of that, Python 3.12 was installed system-wide from source into
`/usr/local` using `make altinstall`, which preserves the distro-managed
`/usr/bin/python3`.

## Host Facts Checked First

The following commands were used to confirm the environment:

```bash
id -u
cat /etc/os-release
command -v apt
python3 --version
sudo -n true
apt-cache policy python3.12 python3.12-venv python3.12-dev
apt-cache search '^python3.12($|-)'
```

Observed results:

- User id was `1000` (non-root user).
- OS was Debian GNU/Linux 13 (`trixie`).
- Package manager was `/usr/bin/apt`.
- Default Python was `Python 3.13.5`.
- `sudo` worked non-interactively.
- No `python3.12` packages were available from `apt`.

## Package Update

```bash
sudo apt-get update
```

During `apt-get update`, a third-party NodeSource repository reported a signing
problem related to SHA-1 policy rejection, but the Debian repositories updated
successfully and this did not block the Python install:

```text
Err:8 https://deb.nodesource.com/node_22.x nodistro InRelease
  Sub-process /usr/bin/sqv returned an error code (1), error message is:
  Signing key on 6F71F525282841EEDAF851B42F59B5F99B1BE0B4 is not bound:
  No binding signature at time 2026-03-30T18:13:34Z because:
  Policy rejected non-revocation signature (PositiveCertification) requiring
  second pre-image resistance because:
  SHA1 is not considered secure since 2026-02-01T00:00:00Z
```

## First Dependency Install Attempt

The first attempt used an incorrect Debian package name:

```bash
sudo apt-get install -y build-essential gdb lcov pkg-config libbz2-dev libffi-dev libgdbm-dev libgdbm-compat-dev liblzma-dev libncurses5-dev libreadline6-dev libsqlite3-dev libssl-dev lzma lzma-dev tk-dev uuid-dev zlib1g-dev libmpdec-dev libexpat1-dev wget
```

That failed with:

```text
E: Unable to locate package lzma-dev
```

## Successful Dependency Install

The install was retried with the correct Debian package names:

```bash
sudo apt-get install -y build-essential pkg-config libbz2-dev libffi-dev libgdbm-dev libgdbm-compat-dev liblzma-dev libncurses-dev libreadline-dev libsqlite3-dev libssl-dev tk-dev uuid-dev zlib1g-dev libmpdec-dev libexpat1-dev wget
```

This completed successfully and provided the libraries needed for a full Python
build, including OpenSSL, sqlite, tkinter, gdbm, libffi, bz2, lzma, readline,
and zlib support.

## Build and Install Commands

Python `3.12.13` was downloaded from `python.org`, built in `/tmp`, and
installed into `/usr/local` with `altinstall`:

```bash
set -e
cd /tmp
rm -rf Python-3.12.13 Python-3.12.13.tar.xz
wget -q https://www.python.org/ftp/python/3.12.13/Python-3.12.13.tar.xz
tar -xf Python-3.12.13.tar.xz
cd Python-3.12.13
./configure --prefix=/usr/local --with-ensurepip=install
make -j"$(nproc)"
sudo make altinstall
```

Notes:

- `--prefix=/usr/local` installs outside the distro-managed `/usr/bin` tree.
- `make altinstall` avoids replacing `/usr/bin/python3`.
- `ensurepip` installed `pip` for Python 3.12 during the install.

## Known `venv` Prompt Bug and Fix

This Python `3.12.13` build generated broken bash activation prompts for new
virtual environments. For example:

```bash
python3.12 -m venv ~/env312
source ~/env312/bin/activate
```

would show:

```text
((env312) ) dirk@host:~ $
```

instead of the expected:

```text
(env312) dirk@host:~ $
```

Root cause:

- `/usr/local/lib/python3.12/venv/__init__.py` sets
  `context.prompt = '(%s) ' % prompt`
- `/usr/local/lib/python3.12/venv/scripts/common/activate` then wraps
  `__VENV_PROMPT__` in parentheses again when building `PS1`

That produces an activation script containing lines like:

```bash
VIRTUAL_ENV_PROMPT='(env312) '
PS1="("'(env312) '") ${PS1:-}"
```

### Fix Existing Installed Python 3.12

Patch the installed stdlib `venv` module so future `python3.12 -m venv ...`
environments use a normal prompt:

```bash
sudo sed -i "s/context.prompt = '(%%s) ' %% prompt/context.prompt = prompt/" /usr/local/lib/python3.12/venv/__init__.py
```

After that change, new environments should generate activation scripts with a
single set of parentheses in the shell prompt.

### Fix an Already-Created Environment

For an existing environment such as `~/env312`, edit `bin/activate` and change:

```bash
VIRTUAL_ENV_PROMPT='(env312) '
PS1="("'(env312) '") ${PS1:-}"
```

to:

```bash
VIRTUAL_ENV_PROMPT=env312
PS1="(${VIRTUAL_ENV_PROMPT}) ${PS1:-}"
```

### Alternative Workaround

If you do not want the activation script to modify the shell prompt at all:

```bash
VIRTUAL_ENV_DISABLE_PROMPT=1 source ~/env312/bin/activate
```

## Resulting Installed Files

Verified installed executables:

- `/usr/local/bin/python3.12`
- `/usr/local/bin/pip3.12`
- `/usr/local/bin/idle3.12`
- `/usr/local/bin/pydoc3.12`
- `/usr/local/bin/2to3-3.12`

## Verification Commands

The following commands were run after installation:

```bash
/usr/local/bin/python3.12 --version
/usr/local/bin/python3.12 -m pip --version
ls -l /usr/local/bin/python3.12 /usr/local/bin/pip3.12 /usr/local/bin/idle3.12 /usr/local/bin/pydoc3.12 /usr/local/bin/2to3-3.12
/usr/local/bin/python3.12 -c 'import ssl,sys; print(sys.version); print(ssl.OPENSSL_VERSION)'
```

Verified results:

- `Python 3.12.13`
- `pip 25.0.1 from /usr/local/lib/python3.12/site-packages/pip (python 3.12)`
- Python build string:
  `3.12.13 (main, Apr 18 2026, 20:56:47) [GCC 14.2.0]`
- SSL runtime:
  `OpenSSL 3.5.5 27 Jan 2026`

## Outcome

Python 3.12 is now installed system-wide as:

```bash
/usr/local/bin/python3.12
```

The distro default `python3` was left unchanged, so Debian continues to use its
own Python `3.13.5` at `/usr/bin/python3`.

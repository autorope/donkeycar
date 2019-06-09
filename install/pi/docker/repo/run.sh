#!/bin/bash

repo="https://github.com/jay-johnson/donkeycar.git"
branch="d1"
repo_dir="/opt/dc"

echo "cloning ${repo} on branch ${branch} to dir: ${repo_dir}"

echo "installing python virtual env and cloning repo" \
  && virtualenv -p /usr/local/bin/python3.7 /opt/venv \
  && echo "activating venv" \
  && . /opt/venv/bin/activate \
  && echo "checking python version:" \
  && python --version \
  && echo "checking python path:" \
  && which python \
  && pyver=$(python --version | grep 3.7 | wc -l) \
  && if [ "${pyver}" = "0" ]; then echo "\nBase image failed setting up virtual env:\nmissing Python 3.7 in virtual env:\n$(which python)\npython version: $(python --version)\n"; exit 1; fi \
  && cd /opt \
  && echo "cloning ${repo}" \
  && git clone ${repo} ${repo_dir} \
  && cd ${repo_dir} \
  && echo "using branch: ${branch}" \
  && git checkout ${branch}

echo "installing initial pips that take a long time: numpy and scipy and pandas" \
  && cd ${repo_dir} \
  && . /opt/venv/bin/activate \
  && echo "which python" \
  && which python \
  && echo "installing numpy" \
  && pip install numpy \
  && echo "installing scipy" \
  && pip install scipy \
  && echo "installing pandas" \
  && pip install pandas

echo "building repo" \
  && . /opt/venv/bin/activate \
  && cd ${repo_dir} \
  && echo "starting pip install pip install --upgrade -e ." \
  && pip install --upgrade -e . \
  && echo "pips:" \
  && pip list --format=columns \
  && echo "checking repo" \
  && ls -l /opt/dc

if [[ ! -e /opt/venv ]]; then
    echo "failed to find python virtual env: /opt/venv as $(whoami)"
    echo "git clone ${repo} ${repo_dir}"
    exit 1
fi

if [[ ! -e /opt/dc ]]; then
    echo "failed to find repository: /opt/dc as $(whoami)"
    echo "virtualenv -p /usr/local/bin/python3.7 /opt/venv"
    exit 1
fi

exit 0

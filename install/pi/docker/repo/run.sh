#!/bin/bash

repo="https://github.com/jay-johnson/donkeycar.git"
branch="d1"
install_dir="/opt/dc"

echo "cloning ${repo} on branch ${branch} to dir: ${install_dir}"

echo "installing source" \
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
  && git clone ${repo} ${install_dir} \
  && cd ${install_dir} \
  && echo "using branch: ${branch}" \
  && git checkout ${branch}

echo "installing initial pips that take a long time: numpy and scipy and pandas" \
  && . /opt/venv/bin/activate \
  && cd ${install_dir} \
  && echo "installing numpy" \
  && pip install numpy -v \
  && echo "installing scipy" \
  && pip install scipy -v
  && echo "installing pandas" \
  && pip install pandas -v

echo "building repo" \
  && . /opt/venv/bin/activate \
  && cd ${install_dir} \
  && echo "starting pip install pip install --upgrade -e ." \
  && pip install --upgrade -e . \
  && echo "pips:" \
  && pip list --format=columns \
  && echo "checking repo" \
  && ls -l /opt/dc

exit 0

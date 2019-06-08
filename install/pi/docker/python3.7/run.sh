#!/bin/bash

echo "installing python 3.7 with a virtual env at: /opt/venv"

echo "" \
  && echo "starting build" \
  && python_version="3.7" \
  && python_build="${python_version}.3" \
  && echo "installing python ${python_version}" \
  && echo "downloading python ${python_build} source: https://www.python.org/ftp/python/${python_build}/Python-${python_build}.tar.xz" \
  && wget https://www.python.org/ftp/python/${python_build}/Python-${python_build}.tar.xz -O /opt/Python-${python_build}.tar.xz -q \
  && echo "extracting tar: Python-${python_build}.tar.xz" \
  && cd /opt \
  && tar xf Python-${python_build}.tar.xz

echo "" \
  && echo "configuring" \
  && python_version="3.7" \
  && python_build="${python_version}.3" \
  && cd /opt/Python-${python_build} \
  && ./configure

echo "" \
  && echo "building" \
  && python_version="3.7" \
  && python_build="${python_version}.3" \
  && cd /opt/Python-${python_build} \
  && echo "building python ${python_build}" \
  && make -j 4 \
  && echo "make -j4 altinstall" \
  && make -j4 altinstall \
  && echo "setting python ${python_build}" \
  && echo "update-alternatives --install /usr/bin/python python /usr/local/bin/python${python_version} 50" \
  && update-alternatives --install /usr/bin/python python /usr/local/bin/python${python_version} 50 \
  && echo "removing /opt/Python-${python_build}" \
  && rm -rf /opt/Python-${python_build} \
  && echo "removing /opt/Python-${python_build}.tar.xz" \
  && rm -f /opt/Python-${python_build}.tar.xz

echo "" \
  && python_version="3.7" \
  && echo "creating virtualenv using: ${python_version}: /opt/venv using python runtime: /usr/local/bin/python${python_verison}" \
  && sudo -u pi /bin/sh -c "virtualenv -p /usr/local/bin/python3.7 /opt/venv" \
  && echo "upgrading setuptools and pip" \
  && sudo -u pi /bin/sh -c ". /opt/venv/bin/activate && pip install --upgrade setuptools pip" \
  && echo "python runtime details: . /opt/venv/bin/activate" \
  && sudo -u pi /bin/sh -c ". /opt/venv/bin/activate && pip list --format=columns && which python && python --version && ls -l $(ls -l $(which python) | awk '{print $NF}')"

exit 0

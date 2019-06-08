FROM jayjohnson/arm32v7-base:latest

RUN echo "" \
  && echo "starting build" \
  && python_version="3.7" \
  && python_build="${python_version}.3" \
  && echo "installing python ${python_version}" \
  && echo "downloading python ${python_build} source: https://www.python.org/ftp/python/${python_build}/Python-${python_build}.tar.xz" \
  && wget https://www.python.org/ftp/python/${python_build}/Python-${python_build}.tar.xz -O /opt/Python-${python_build}.tar.xz -q \
  && echo "extracting tar: Python-${python_build}.tar.xz" \
  && cd /opt \
  && tar xf Python-${python_build}.tar.xz

RUN echo "" \
  && echo "configuring" \
  && python_version="3.7" \
  && python_build="${python_version}.3" \
  && cd /opt/Python-${python_build} \
  && ./configure

RUN echo "" \
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

RUN echo "" \
  && python_version="3.7" \
  && echo "creating virtualenv using: ${python_version}: /opt/venv using python runtime: /usr/local/bin/python${python_verison}" \
  && echo "virtualenv -p /usr/local/bin/python3.7 /opt/venv" \
  && virtualenv -p /usr/local/bin/python3.7 /opt/venv \
  && echo "upgrading setuptools and pip" \
  && . /opt/venv/bin/activate && pip install --upgrade setuptools pip \
  && echo "python runtime details: . /opt/venv/bin/activate" \
  && . /opt/venv/bin/activate && pip list --format=columns && which python && python --version && which python

ENV VENV="/opt/venv"

ENTRYPOINT . /opt/venv/bin/activate \
  && ls -l /opt/dc

FROM jayjohnson/arm32v7-python37-venv:latest

RUN echo "installing python virtual env and cloning repo" \
  && virtualenv -p /usr/local/bin/python3.7 /opt/venv \
  && repo="https://github.com/jay-johnson/donkeycar.git" \
  && branch="d1" \
  && repo_dir="/opt/dc" \
  && echo "activating venv" \
  && . /opt/venv/bin/activate \
  && echo "checking python version:" \
  && python --version \
  && echo "checking python path:" \
  && which python \
  && pyver=$(python --version | grep 3.7 | wc -l) \
  && if [ "${pyver}" = "0" ]; then echo "\nBase image failed setting up virtual env:\nmissing Python 3.7 in virtual env:\n$(which python)\npython version: $(python --version)\n"; exit 1; fi \
  && cd /opt \
  && echo "cloning: ${repo} on branch ${branch} to ${repo_dir}" \
  && git clone ${repo} ${repo_dir} \
  && cd ${repo_dir} \
  && echo "using branch: ${branch}" \
  && git checkout ${branch}

RUN echo "installing initial pips that take a long time: numpy and scipy and pandas" \
  && repo_dir="/opt/dc" \
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

RUN echo "building repo" \
  && repo_dir="/opt/dc" \
  && . /opt/venv/bin/activate \
  && echo "starting pip install pip install --upgrade -e ." \
  && pip install --upgrade -e . \
  && echo "pips:" \
  && pip list --format=columns \
  && echo "checking repo" \
  && ls -l ${repo_dir} \
  && echo "installing rc files" \
  && cp ${repo_dir}/install/pi/files/bashrc /root/.bashrc \
  && cp ${repo_dir}/install/pi/files/vimrc /root/.vimrc \
  && cp ${repo_dir}/install/pi/files/gitconfig /root/.gitconfig

WORKDIR /opt/dc

ENTRYPOINT echo "starting container" \
  && . /opt/venv/bin/activate \
  && echo "" \
  && echo "/opt/dc contents:" \
  && ls -l /opt/dc \
  && cd /opt/dc \
  && echo "" \
  && echo "git log -1:" \
  && git log -1 \
  && echo "" \
  && echo "git status:" \
  && git status \
  && echo "" \
  && echo "pip list:" \
  && pip list

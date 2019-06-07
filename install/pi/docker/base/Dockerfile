FROM arm32v7/python:3.7.3-stretch

RUN apt-get update -y -o "Dpkg::Options::=--force-confdef" -o "Dpkg::Options::=--force-confold" \
  && apt-get install -y \
    autoconf \
    build-essential \
    cmake \
    curl \
    gcc \
    gfortran \
    git \
    libblas-dev \
    libcurl4-openssl-dev \
    libffi6 \
    libffi-dev \
    libhdf5-serial-dev \
    liblapack-dev \
    libncurses5-dev \
    libncursesw5-dev \
    libreadline-dev \
    libsqlite3-dev \
    libssl-dev \
    liblzma-dev \
    libbz2-dev \
    llvm \
    lsof \
    make \
    mlocate \
    ncdu \
    netcat \
    net-tools \
    openssl \
    pandoc \
    python3 \
    python3-dev \
    python3-pip \
    python3-tk \
    python-setuptools \
    python-virtualenv \
    python-pip \
    redis-tools \
    s3cmd \
    software-properties-common \
    strace \
    telnet \
    tk-dev \
    unzip \
    uuid-runtime \
    vim \
    wget \
    xz-utils \
    zlib1g-dev

WORKDIR /opt/dc

ENTRYPOINT . /opt/venv/bin/activate \
  && ls -l /opt/dc

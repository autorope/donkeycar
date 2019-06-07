#!/bin/bash

echo "updating all packages"

apt-get update -y -o "Dpkg::Options::=--force-confdef" -o "Dpkg::Options::=--force-confold"
if [[ "$?" != "0" ]]; then
    echo "failed - updating"
    exit 1
fi

apt-get install -y \
    autoconf \
    build-essential \
    cmake \
    curl \
    gcc \
    gfortran \
    git \
    libblas-dev \
    libcurl4-openssl-dev \
    liblapack-dev \
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

if [[ "$?" != "0" ]]; then
    echo "failed - installing"
    exit 1
fi

exit 0

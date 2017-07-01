#!/bin/bash -x

# $1 comma separated list of session names (2017_06_03__12_31_52_AM, ...)
# $2 model name (tX)

cwd=$(pwd)

source /disk1/marcow/tf/bin/activate

export PYTHONPATH=$cwd

exec python3 scripts/train.py --sessions=$1 --name=$2

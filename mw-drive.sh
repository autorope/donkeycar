#!/bin/bash -x

# Does not need any arguments

cwd=$(pwd)
ip=$(echo $SSH_CLIENT | awk '{ print $1; }')

source env/bin/activate

export PYTHONPATH=$cwd

exec python  scripts/drive.py --remote http://$ip:8887

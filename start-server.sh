#!/bin/sh

docker build -t donkey . && docker run -p 8887:8887 donkey

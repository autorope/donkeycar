#!/bin/bash

if [[ "REPLACE_DOCKER_ENABLED" == "1" ]]; then
    echo "shell ${USER} - trying logging into docker registry: REPLACE_DC_DOCKER_USER@REPLACE_DC_DOCKER_REGISTRY"
    echo "REPLACE_DC_DOCKER_PASSWORD" | docker login --username REPLACE_DC_DOCKER_USER --password-stdin REPLACE_DC_DOCKER_REGISTRY
    exit $?
else
    exit 0
fi

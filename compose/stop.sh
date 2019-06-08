#!/bin/bash

export DCPATH=/opt/dc
if [[ -e ${DCPATH}/install/pi/files/bash_colors.sh ]]; then
    source ${DCPATH}/install/pi/files/bash_colors.sh
fi

compose_files=""

# argument parsing code from:
# https://medium.com/@Drew_Stokes/bash-argument-parsing-54f3b81a6a8f
PARAMS=""
args="$@"
while (( "$#" )); do
    case "$1" in
        -d|--debug)
            export DCDEBUG="1"
            shift 1
            ;;
        -P|--PATH)
            export DCPATH="${2}"
            shift 2
            ;;
        -s|--splunk)
            if [[ ! -e ${2} ]]; then
                err "missing docker compose file for: splunk at: ${2}"
                exit 1
            fi
            if [[ "${compose_files}" == "" ]]; then
                compose_files="${2}"
            else
                compose_files="${compose_files} ${2}"
            fi
            shift 2
            ;;
        -r|--registry)
            if [[ ! -e ${2} ]]; then
                err "missing docker compose file for: registry at: ${2}"
                exit 1
            fi
            if [[ "${compose_files}" == "" ]]; then
                compose_files="${2}"
            else
                compose_files="${compose_files} ${2}"
            fi
            shift 2
            ;;
        -f|--fluentd)
            if [[ "${2}" == "" ]]; then
                err "missing docker compose file for: fluentd at: ${2}"
                exit 1
            fi
            if [[ "${compose_files}" == "" ]]; then
                compose_files="${2}"
            else
                compose_files="${compose_files} ${2}"
            fi
            shift 2
            ;;
        -m|--minio)
            if [[ "${2}" == "" ]]; then
                err "missing docker compose file for: minio at: ${2}"
                exit 1
            fi
            if [[ "${compose_files}" == "" ]]; then
                compose_files="${2}"
            else
                compose_files="${compose_files} ${2}"
            fi
            if [[ "${MINIO_ACCESS_KEY}" == "" ]]; then
                export MINIO_ACCESS_KEY=dcpi
            fi
            if [[ "${MINIO_SECRET_KEY}" == "" ]]; then
                export MINIO_SECRET_KEY=raspberry
            fi
            shift 2
            ;;
        -c|--camera-rec)
            if [[ ! -e ${2} ]]; then
                err "missing docker compose file for: camera recorder at: ${2}"
                exit 1
            fi
            if [[ "${compose_files}" == "" ]]; then
                compose_files="${2}"
            else
                compose_files="${compose_files} ${2}"
            fi
            shift 2
            ;;
        -T|--run-tests-on-donkey-car)
            compose_files="${compose_files} /opt/dc/compose/dc/test_fluent_bit/test_fluent_bit.yaml"
            shift 1
            ;;
        --) # end argument parsing
            shift
            break
            ;;
        -*|--*=) # unsupported flag detected
            err "usage error: unsupported flag ${1} detected"
            err ""
            err "Debug with:"
            err "usage: ./just-deploy-build-to-sd-card.sh -d"
            err ""
            exit 1
            ;;
        *) # preserve positional arguments
            PARAMS="$PARAMS $1"
            shift
        ;;
    esac
done
# set positional arguments in their proper place
eval set -- "$PARAMS"

if [[ "${compose_files}" == "" ]]; then
    err "please set at least 1 compose file to stop"
    exit 1
fi

anmt "stopping compose files in order: ${compose_files}"
date +"%Y-%m-%d %H:%M:%S"

for c in ${compose_files}; do
    anmt "stopping: ${c}"
    echo "docker-compose -f ${c} down"
    docker-compose -f ${c} down
    echo ""
done
anmt "done - stopping compose files: ${compose_files}"
echo ""

anmt "checking docker containers:"
docker ps
echo ""

date +"%Y-%m-%d %H:%M:%S"
good "done"

EXITVALUE=0
exit $EXITVALUE

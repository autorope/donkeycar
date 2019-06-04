#!/bin/bash

export DCPATH=/opt/dc
if [[ -e ${DCPATH}/install/pi/files/bash_colors.sh ]]; then
    source ${DCPATH}/install/pi/files/bash_colors.sh
fi

compose_files=""

if [[ "${DCDOCKERUSER}" == "" ]]; then
    export DCDOCKERUSER="pi"
fi
if [[ "${DCDOCKERPASSWORD}" == "" ]]; then
    export DCDOCKERPASSWORD="123321"
fi

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
            if [[ "${2}" == "" ]]; then
                err "missing docker compose file for: splunk at: ${2}"
                exit 1
            fi
            if [[ "${compose_files}" == "" ]]; then
                compose_files="${2}"
            else
                compose_files="${compose_files} ${2}"
            fi
            if [[ ! -e /opt/docker_data/splunk ]]; then
                mkdir -p -m 777 /opt/docker_data/splunk
                if [[ "$?" != "0" ]]; then
                    err "failed to create /opt/docker_data/splunk directory - please confirm permissions are correct:"
                    echo ""
                    echo "ls -l /opt | grep docker_data"
                    ls -l /opt | grep docker_data
                    echo ""
                    echo "ls -l /opt/docker_data"
                    ls -l /opt/docker_data
                    echo ""
                    exit 1
                fi
            fi
            shift 2
            ;;
        -r|--registry)
            if [[ "${2}" == "" ]]; then
                err "missing docker compose file for: registry at: ${2}"
                exit 1
            fi
            if [[ "${compose_files}" == "" ]]; then
                compose_files="${2}"
            else
                compose_files="${compose_files} ${2}"
            fi
            if [[ ! -e /opt/docker_data/registry ]]; then
                mkdir -p -m 777 /opt/docker_data/registry
                if [[ "$?" != "0" ]]; then
                    err "failed to create /opt/docker_data/registry directory - please confirm permissions are correct:"
                    echo ""
                    echo "ls -l /opt | grep docker_data"
                    ls -l /opt | grep docker_data
                    echo ""
                    echo "ls -l /opt/docker_data"
                    ls -l /opt/docker_data
                    echo ""
                    exit 1
                fi
            fi
            anmt "adding registry credentials for ${DCDOCKERUSER} user: /opt/docker_data/registry/auth/htpasswd"
            docker run --entrypoint htpasswd registry:2 -Bbn ${DCDOCKERUSER} ${DCDOCKERPASSWORD} > /opt/docker_data/registry/auth/htpasswd
            anmt "please login to the registry with:"
            anmt "echo \"DOCKER_PASSWORD\" | docker login --username ${DCDOCKERUSER} --password-stdin 0.0.0.0:5000"
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
        -c|--camera-rec)
            if [[ "${2}" == "" ]]; then
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
        -e|--docker-user)
            if [[ "${2}" == "" ]]; then
                err "missing docker user for private registry"
                exit 1
            fi
            export DCDOCKERUSER="${2}"
            shift 2
            ;;
        -w|--docker-password)
            if [[ "${2}" == "" ]]; then
                err "missing docker password for private registry"
                exit 1
            fi
            export DCDOCKERPASSWORD="${2}"
            shift 2
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
    err "please set at least 1 compose file to start"
    exit 1
fi

anmt "starting compose files in order: ${compose_files}"
date +"%Y-%m-%d %H:%M:%S"

for c in ${compose_files}; do
    anmt "deploying: ${c}"
    echo "docker-compose -f ${c} up -d"
    docker-compose -f ${c} up -d
    echo ""
done
anmt "done - starting compose files: ${compose_files}"
echo ""

anmt "checking docker containers:"
docker ps
echo ""

date +"%Y-%m-%d %H:%M:%S"
good "done"

EXITVALUE=0
exit $EXITVALUE

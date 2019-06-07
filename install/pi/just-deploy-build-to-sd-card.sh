#!/bin/bash

if [[ "${DCPATH}" == "" ]]; then
    export DCPATH="."
fi
if [[ -e ${DCPATH}/files/bash_colors.sh ]]; then
    source ${DCPATH}/files/bash_colors.sh
fi

if [[ "$(whoami)" != "root" ]]; then
    err "please run as root"
    exit 1
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
    # download from a custom image zip from google drive by this file id
    -f|--google-fileid)
        if [[ "${2}" == "" ]]; then
            err "missing google file id"
            exit 1
        fi
        export DCGID="${2}"
        shift 2
        ;;
    # during image backup, you can name the zipped up image,
    # please use it again to ensure
    # the unzipped file image is correct
    -x|--extracted-image-name)
        if [[ "${2}" == "" ]]; then
            err "missing extracted image name"
            exit 1
        fi
        export DCIMAGENAME="${2}"
        shift 2
        ;;
    -t|--docker-registry-url)
        if [[ "${2}" == "" ]]; then
            err "missing docker private registry url"
            exit 1
        fi
        export DCDOCKERREGISTRY="${2}"
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
    -S|--splunk-host)
        if [[ "${2}" == "" ]]; then
            err "missing splunk host"
            exit 1
        fi
        export DCSPLUNKHOST="${2}"
        shift 2
        ;;
    -r|--rclocal-path)
        if [[ ! -e ${2} ]]; then
            err "unable to find rc.local path to -r <file>: ${2}"
            exit 1
        fi
        export DCSTARTUP="${2}"
        shift 2
        ;;
    -g|--gitrepo)
        if [[ ${2} == "" ]]; then
            err "missing github repo arg: -g https://github.com/jay-johnson/donkeycar.git"
            exit 1
        fi
        export DCREPO="${2}"
        shift 2
        ;;
    -b|--gitbranch)
        if [[ ${2} == "" ]]; then
            err "missing github branch arg: -b dev"
            exit 1
        fi
        dcbranch="${2}"
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

anmt "starting redeploy"
anmt "${DCPATH}/burn-image-to-sd-card.sh ${args} -i"
${DCPATH}/burn-image-to-sd-card.sh -i ${args}
if [[ "$?" != "0" ]]; then
    err "failed to redeploy with: ${DCPATH}/burn-image-to-sd-card.sh ${args} -i"
    exit 1
fi

date +"%Y-%m-%d %H:%M:%S"
good "donkey car image - redeploy complete"

exit 0

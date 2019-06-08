#!/bin/bash

log_file=/tmp/docker.log

echo "starting docker build in the background"

start_date=$(date +"%Y-%m-%d %H:%M:%S")
echo "starting new docker build at: ${start_date} from dir: $(pwd)" > ${log_file}
if [[ "${DOCKER_USER}" != "" ]] && [[ "${DOCKER_PASSWORD}" != "" ]] && [[ "${DOCKER_REGISTRY}" != "" ]]; then
    echo "" >> ${log_file}
    echo "detected docker push enabled" >> ${log_file}
    echo "" >> ${log_file}
    echo "testing login before starting" >> ${log_file}
    echo "${DOCKER_PASSWORD}" | docker login --username ${DOCKER_USER} --password-stdin ${DOCKER_REGISTRY}
    if [[ "$?" != "0" ]]; then
        echo "failed logging into docker with ${DOCKER_USER}@${DOCKER_REGISTRY}"
        echo "please confirm these values are correct and try again:"
        echo "" >> ${log_file}
        echo "export DOCKER_USER=DOCKER_USERNAME" >> ${log_file}
        echo "export DOCKER_PASSWORD=DOCKER_PASSWORD" >> ${log_file}
        echo "export DOCKER_REGISTRY=REGISTRY_ADDRESS_OR_DOCKER_HUB_WITH_docker.io" >> ${log_file}
        echo "" >> ${log_file}
        echo "stopping build" >> ${log_file}

        echo "---------------------------"
        echo "${log_file} contents:"
        cat ${log_file}
        echo "---------------------------"
        popd >> /dev/null 2>&1
        exit 1
    fi
fi

echo "" >> ${log_file}
echo "backgrounding with command:" >> ${log_file}
echo "nohup ./build.sh >> ${log_file} 2>&1 &" >> ${log_file}
nohup ./build.sh push >> ${log_file} 2>&1 &
echo "" >> ${log_file}

echo "---------------------------"
echo "${log_file} contents:"
cat ${log_file}
echo "---------------------------"

echo ""
echo "watch the build logs with:"
echo "tail -f ${log_file}"
echo ""
exit 0

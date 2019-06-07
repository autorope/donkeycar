#!/bin/bash

maintainer=jayjohnson
imagename=arm32v7-base
start_date=$(date +"%Y-%m-%d %H:%M:%S")

print_env_diagnostics() {
    echo ""
    echo "os details:"
    echo "$(uname -a)"
    echo ""
    echo "git status:"
    echo "$(git status)"
    echo ""
    echo "docker version:"
    echo "$(docker version)"
    echo ""
    echo "free space:"
    echo "$(df -h)"
    echo ""
}

handle_end() {
    exit_code=0
    if [[ "${1}" != "" ]]; then
        exit_code=$1
    fi
    end_date=$(date +"%Y-%m-%d %H:%M:%S")
    echo "started: ${start_date} from dir: $(pwd)"
    echo "ended:   ${end_date}"
    echo ""
    if [[ "${exit_code}" == "0" ]]; then
        echo "build was successful with exit: ${exit_code}"
    else
        echo "build failed with exit: ${exit_code}"
    fi
    popd >> /dev/null 2>&1
    exit ${exit_code}
}

pushd /opt/dc/install/pi/docker >> /dev/null 2>&1
echo "starting new docker build at: ${start_date} from dir: $(pwd)"
print_env_diagnostics

tag=$(cat ../../../setup.py | grep "version=" | sed -e 's/"/ /g' | awk '{print $2}')

echo ""
echo "--------------------------------------------------------"
echo "building new base image: ${maintainer}/${imagename}"
base_image="$maintainer/$imagename"
docker build -f ./base/Dockerfile --rm -t ${base_image} .
last_status=$?
if [[ "${last_status}" != "0" ]]; then
    echo ""
    echo "failed to build base image: ${base_image}"
    echo "docker build -f ./repo/Dockerfile --rm -t ${base_image} ."
    echo ""
    handle_end 1
fi

imagename=arm32v7-python37-venv
repo_image="$maintainer/$imagename"
docker build -f ./python3.7/Dockerfile --rm -t ${repo_image} .
last_status=$?
if [[ "${last_status}" != "0" ]]; then
    echo ""
    echo "failed to build python image: ${repo_image}"
    echo "docker build -f ./python3.7/Dockerfile --rm -t ${repo_image} ."
    echo ""
    handle_end 1
fi

imagename=arm32v7-python37-repo-base
repo_image="$maintainer/$imagename"
docker build -f ./repo/Dockerfile --rm -t ${repo_image} .
last_status=$?
if [[ "${last_status}" != "0" ]]; then
    echo ""
    echo "failed to build repo image: ${repo_image}"
    echo "docker build -f ./repo/Dockerfile --rm -t ${repo_image} ."
    echo ""
    handle_end 1
fi
if [[ "${last_status}" == "0" ]]; then
    echo ""
    if [[ "${tag}" != "" ]]; then
        image_csum=$(docker images | grep "${maintainer}/${imagename} " | grep latest | awk '{print $3}')
        if [[ "${image_csum}" != "" ]]; then
            docker tag $image_csum $maintainer/$imagename:$tag
            last_status=$?
            if [[ "${last_status}" != "0" ]]; then
                echo "failed to tag image(${imagename}) with tag(${tag})"
                echo ""
                handle_end 1
            else
                echo "build successful tagged image(${imagename}) with tag(${tag})"
            fi

            if [[ "${DOCKER_USER}" != "" ]] && [[ "${DOCKER_PASSWORD}" != "" ]] && [[ "${DOCKER_REGISTRY}" != "" ]]; then
                echo "pushing ${maintainer}/${imagename}:${tag} with image id: ${image_csum} docker registry: ${DOCKER_REGISTRY}"
                echo "testing login"
                echo "${DOCKER_PASSWORD}" | docker login --username ${DOCKER_USER} --password-stdin ${DOCKER_REGISTRY}
                if [[ "$?" != "0" ]]; then
                    echo "failed logging into docker with ${DOCKER_USER}@${DOCKER_REGISTRY}"
                    echo "please confirm these values are correct and try again:"
                    echo ""
                    echo "export DOCKER_USER=DOCKER_USERNAME"
                    echo "export DOCKER_PASSWORD=DOCKER_PASSWORD"
                    echo "export DOCKER_REGISTRY=REGISTRY_ADDRESS_OR_DOCKER_HUB_WITH_docker.io"
                    echo ""
                    echo "stopping build - did not push"
                    handle_end 1
                fi
                echo "docker push ${DOCKER_REGISTRY}/${imagename}"
                docker push ${DOCKER_REGISTRY}/${imagename}
                last_status=$?
                if [[ "${last_status}" != "0" ]]; then
                    echo "build worked - but failed to push to docker regsitry"
                    handle_end 1
                else
                    echo "build successful - pushed to registry"
                fi
            fi
            echo ""
            handle_end 0
        else
            echo ""
            echo "build failed to find latest image(${imagename}) with tag(${tag})"
            echo ""
            handle_end 1
        fi
    else
        echo "build successful - no tag and not pushed - only locally available"
        echo ""
        handle_end 0
    fi
    echo ""
else
    echo ""
    echo "build failed with exit code: ${last_status}"
    echo ""
    handle_end 1
fi

handle_end 0

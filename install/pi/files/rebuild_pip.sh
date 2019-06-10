#!/bin/bash

repo_dir="/opt/dc"
if [[ "${DCPATH}" != "" ]]; then
    repo_dir="${DCPATH}"
fi
repo="https://github.com/jay-johnson/donkeycar.git"
if [[ "${DCREPO}" != "" ]]; then
    repo="${DCREPO}"
fi
branch="d1"
if [[ "${DCBRANCH}" != "" ]]; then
    branch="${DCBRANCH}"
fi
venvpath="/opt/venv"
if [[ "${DCVENVDIR}" != "" ]]; then
    venvpath="${DCVENVDIR}"
fi
python_version="3.7"
if [[ "${DCPYTHONVERSION}" != "" ]]; then
    python_version="${DCPYTHONVERSION}"
fi
export DCPYTHONVERSION="${python_version}"

echo ""
echo "starting install: $(date +'%Y-%m-%d %H:%M:%S')"

if [[ ! -e ${repo_dir} ]]; then
    not_done="1"
    num_clone_attempts=0
    while [[ "${not_done}" == "1" ]]; do
        echo "cloning ${repo} to ${repo_dir}"
        git clone ${repo} ${repo_dir}
        if [[ "$?" == "0" ]]; then
            not_done="0"
        else
            echo " - sleeping for 10 seconds before retrying - git clone"
            num_clone_attempts=$((num_clone_attempts++))
            if [[ ${num_clone_attempts} -gt 10000000 ]]; then
                echo "failed after 10000000 attempts"
                exit 1
            else
                if [[ -e ~/.ssh/id_rsa.pub ]]; then
                    echo "please check the ssh key is supported for cloning the repo:"
                    cat ~/.ssh/id_rsa.pub
                else
                    echo "no public ssh key detected in ~/.ssh/id_rsa.pub - please confirm the repo supports public reads"
                fi
            fi
            sleep 10
        fi
    done
    cd ${repo_dir}
    echo "${repo} in ${repo_dir} checking out branch: ${branch}"
    git checkout ${branch}
    if [[ "$?" != "0" ]]; then
        echo "failed to checkout ${repo} branch: ${branch} in ${repo_dir}"
        ls -l ${repo_dir}/*
        exit 1
    fi
fi

if [[ ! -e ${repo_dir} ]]; then
    echo "failed to find ${repo_dir} after clone attempts"
    echo "git clone ${repo} ${repo_dir}"
    if [[ -e ~/.ssh/id_rsa.pub ]]; then
        echo ""
        echo "please confirm this ssh key has access to pull this repo: ${repo}"
        cat ~/.ssh/id_rsa.pub
        echo ""
    else
        echo ""
        echo "did not find a public ssh key ~/.ssh/id_rsa.pub - please confirm this user has a private ssh key that can clone the repo: ${repo}"
        echo ""
    fi
    exit 1
else
    pushd ${repo_dir} >> /dev/null 2>&1
    echo "checking repo status: ${repo_dir}"
    git status
    num_fetch_attempts=0
    not_done="1"
    while [[ "${not_done}" == "1" ]]; do
        echo "fetching the latest from $(cat ${repo_dir}/.git/config | grep url | awk '{print $NF}')"
        git fetch
        if [[ "$?" == "0" ]]; then
            not_done="0"
        else
            echo " - sleeping for 10 seconds before retrying - pulling the latest for repo: ${repo}"
            num_fetch_attempts=$((num_fetch_attempts++))
            if [[ ${num_fetch_attempts} -gt 180 ]]; then
                sleep 10
            else
                echo "did not have a successful git pull after 180 attempts"
                not_done="0"
            fi
        fi
    done
    echo "${repo} in ${repo_dir} checking out branch: ${branch}"
    git checkout ${branch}
    if [[ "$?" != "0" ]]; then
        echo "failed to checkout ${repo} branch: ${branch} in ${repo_dir}"
        ls -l ${repo_dir}/*
    fi
    num_pull_attempts=0
    not_done="1"
    while [[ "${not_done}" == "1" ]]; do
        echo "pulling the latest from $(cat ${repo_dir}/.git/config | grep url | awk '{print $NF}')"
        git pull
        if [[ "$?" == "0" ]]; then
            not_done="0"
        else
            echo " - sleeping for 10 seconds before retrying - pulling the latest for repo: ${repo}"
            num_pull_attempts=$((num_pull_attempts++))
            if [[ ${num_pull_attempts} -gt 180 ]]; then
                sleep 10
            else
                echo "did not have a successful git pull after 180 attempts"
                not_done="0"
            fi
        fi
    done
    popd >> /dev/null 2>&1
fi

lg() {
    echo "$@"
}
inf() {
    lg "$@"
}
anmt() {
    lg "$@"
}
good() {
    lg "$@"
}
err() {
    lg "$@"
}
critical() {
    lg "$@"
}
warn() {
    lg "$@"
}
if [[ -e ${repo_dir}/install/pi/files/bash_colors.sh ]]; then
    source ${repo_dir}/install/pi/files/bash_colors.sh
fi

if [[ ! -e /usr/local/bin/python${python_version} ]]; then
    anmt "installing python_version: ${python_version}"
    if [[ ! -e /opt/dc/install/pi/docker/python${python_version}/run.sh ]]; then
        err "unsupported python version: ${python_version}"
        exit 1
    else
        sudo /opt/dc/install/pi/docker/python${python_version}/run.sh
        if [[ "$?" != "0" ]]; then
            err "Failed to install python with: sudo /opt/dc/install/pi/docker/python${python_version}/run.sh"
            exit 1
        else
            good "${python_version} - installed"
        fi
    fi
fi

if [[ ! -e ${venvpath}/bin/activate ]]; then
    anmt "creating venv: ${venvpath} python runtime: $(ls -l /usr/local/bin/python3.7 | awk '{print $NF}')"
    virtualenv -p /usr/local/bin/python3.7 ${venvpath}
    if [[ "$?" != "0" ]]; then
        err "unable to create virtual env for python 3.7 with command:"
        virtualenv -p /usr/local/bin/python3.7 ${venvpath}
        exit 1
    fi
fi

if [[ -e ${venvpath}/bin/activate ]]; then
    anmt "$(whoami) is activating venv: ${venvpath}"
    source ${venvpath}/bin/activate

    not_done="1"
    num_attempts=0
    while [[ "${not_done}" == "1" ]]; do
        anmt "upgrading pip and setuptools: $(date +'%Y-%m-%d %H:%M:%S')"
        pip install --upgrade pip setuptools
        if [[ "$?" == "0" ]]; then
            not_done="0"
        else
            anmt " - sleeping for 10 seconds before retrying"
            num_attempts=$((num_attempts++))
            if [[ ${num_attempts} -gt 180 ]]; then
                sleep 10
            else
                err "did not install pip and setuptools correctly after 180 attempts"
                not_done="0"
            fi
        fi
    done

    if [[ -e ${repo_dir} ]]; then
        pushd ${repo_dir} >> /dev/null 2>&1
        not_done="1"
        num_attempts=0
        while [[ "${not_done}" == "1" ]]; do
            anmt "installing pips $(date +'%Y-%m-%d %H:%M:%S'): pip install --upgrade -e ."
            pip install --upgrade -e .
            if [[ "$?" == "0" ]]; then
                not_done="0"
            else
                anmt " - sleeping for 10 seconds before retrying - install + upgrading the pips"
                num_attempts=$((num_attempts++))
                if [[ ${num_attempts} -gt 180 ]]; then
                    sleep 10
                else
                    err "did not install pip install --upgrade -e . correctly after 180 attempts"
                    not_done="0"
                fi
            fi
        done
        popd >> /dev/null 2>&1
    else
        err "did not find repo_dir: ${repo_dir}"
        exit 1
    fi
else
    err "failed to find a valid virtual environment at path: ${venvpath}"
    err "checking permissions on parent directory:"
    ls -l ${venvpath}/.. | grep $(dirname $venvpath)
    if [[ -e ${venvpath} ]]; then
        err "checking permissions on ${venvpath} directory:"
        ls -l $venvpath
    fi
    exit 1
fi

date +"%Y-%m-%d %H:%M:%S"
good "done - rebuild pip: ${repo_dir}"

exit 0

#!/bin/bash

repo_dir="/opt/dc"
if [[ "${DCPATH}" != "" ]]; then
    repo_dir="${DCPATH}"
fi
if [[ -e ${repo_dir}/install/pi/files/bash_colors.sh ]]; then
    source ${repo_dir}/install/pi/files/bash_colors.sh
fi
venvpath="/opt/venv"
if [[ "${DCVENVDIR}" != "" ]]; then
    venvpath="${DCVENVDIR}"
fi

if [[ ! -e ${venvpath}/bin/activate ]]; then
    anmt "creating venv: ${venvpath}"
    virtualenv -p /usr/bin/python3 ${venvpath}
fi

if [[ -e ${venvpath}/bin/activate ]]; then
    anmt "activating venv: ${venvpath}"
    source ${venvpath}/bin/activate

    anmt "upgrading pip and setuptools:"
    pip install --upgrade pip setuptools

    upgrade_scipy=""
    test_scipy=$(pip list --format columns | grep scipy | wc -l)
    if [[ "${test_scipy}" == "0" ]]; then
        scipy_version="scipy-1.2.1-cp35-cp35m-linux_armv7l.whl"
        if [[ "${upgrade_scipy}" != "" ]]; then
            scipy_version="${upgrade_scipy}"
        fi
        scipy_download_file="/opt/downloads/pip/${scipy_version}"
        scipy_url="https://www.piwheels.org/simple/scipy/${scipy_version}#sha256=270be300233af556e6ee3f55a0ae237df0cb65ac85d47559010d7a9071f2e878"
        if [[ ! -e ${scipy_download_file} ]]; then
            anmt "downloading scipy: ${scipy_version} from ${scipy_url}"
            wget "${scipy_url}" -O ${scipy_download_file}
        fi
        if [[ ! -e ${scipy_download_file} ]]; then
            err "failed to download scipy update to version: ${scipy_download_file} with:"
            err "wget \"${scipy_url}\" -O ${scipy_download_file}"
            exit 1
        fi
        anmt "installing scipy: ${scipy_download_file}"
        pip install ${scipy_download_file}
        if [[ "$?" != "0" ]]; then
            err "failed to install ${scipy_download_file} with command:"
            err "pip install ${scipy_download_file}"
            exit 1
        fi
    fi

    if [[ -e ${repo_dir} ]]; then
        pushd ${repo_dir} >> /dev/null 2>&1
        anmt "checking repo status: ${repo_dir}"
        git status 
        anmt "pulling the latest from $(cat ${repo_dir}/.git/config | grep url | awk '{print $NF}')"
        git pull 
        anmt "installing pips: pip install --upgrade -e ."
        pip install --upgrade -e .
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

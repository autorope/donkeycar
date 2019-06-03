#!/bin/bash

if [[ "${DCPATH}" == "" ]]; then
    export DCPATH="."
fi
if [[ -e ${DCPATH}/files/bash_colors.sh ]]; then
    source ${DCPATH}/files/bash_colors.sh
fi

# latest donkey car image id:
latest_image="donkey_2.5.0_pi3.img"
fileid="1vr4nEXLEh4xByKAXik8KhK3o-XWgo2fQ"
if [[ "${DCGID}" != "" ]]; then
    fileid="${DCGID}"
fi
dc_base_image="$(dirname ${DCIMAGE})/${latest_image}"

if [[ ! -e ${DCIMAGE} ]]; then
    anmt "getting cookies from:"
    anmt "curl -c ./cookie -s -L \"https://drive.google.com/uc?export=download&id=${fileid}\""
    curl -c ./cookie -s -L "https://drive.google.com/uc?export=download&id=${fileid}" > /dev/null
fi

if [[ ! -e ${DCGDOWNLOADPATH} ]]; then
    anmt "downloading ${fileid} to ${DCGDOWNLOADPATH}:"
    anmt "curl -s -Lb ./cookie \"https://drive.google.com/uc?export=download&confirm=$(awk '/download/ {print $NF}' ./cookie)&id=${fileid}\" -o ${DCGDOWNLOADPATH}"
    if [[ "${DCDEBUG}" == "1" ]]; then
        curl -Lb ./cookie "https://drive.google.com/uc?export=download&confirm=`awk '/download/ {print $NF}' ./cookie`&id=${fileid}" -o ${DCGDOWNLOADPATH}
    else
        curl -s -Lb ./cookie "https://drive.google.com/uc?export=download&confirm=`awk '/download/ {print $NF}' ./cookie`&id=${fileid}" -o ${DCGDOWNLOADPATH}
    fi

    if [[ "$?" != "0" ]]; then
        err "failed to download ${fileid}"
        exit 1
    fi
else
    good " - found previous download zip: ${DCGDOWNLOADPATH}"
fi

if [[ ! -e ${DCGDOWNLOADPATH} ]]; then
    err "failed to find downloaded file: ${DCGDOWNLOADPATH}"
    exit 1
fi

if [[ ! -e ${dc_base_image} ]]; then
    anmt "extracting ${DCGDOWNLOADPATH} to image: ${dc_base_image}"
    chmod 666 ${DCGDOWNLOADPATH}
    unzip ${DCGDOWNLOADPATH} -d $(dirname ${DCIMAGE})
    output_file="$(dirname ${DCIMAGE})/donkey_2.5.0_pi3.img"
    if [[ "$?" != "0" ]]; then
        err "failed to unzip ${DCGDOWNLOADPATH} to ${DCIMAGE}"
        exit 1
    fi
else
    good " - found existing base image: ${dc_base_image}"
fi

if [[ ! -e ${output_file} ]]; then
    unzip ${DCGDOWNLOADPATH} -d $(dirname ${DCIMAGE})
    output_file="$(dirname ${DCIMAGE})/donkey_2.5.0_pi3.img"
    if [[ ! -e ${output_file} ]]; then
        err "failed to find unzipped file: ${output_file}"
        exit 1
    fi
fi

if [[ ! -e ${DCIMAGE} ]]; then
    anmt "renaming ${output_file} to ${DCIMAGE}"
    mv ${output_file} ${DCIMAGE}
    if [[ ! -e ${DCIMAGE} ]]; then
        err "failed to find unzipped file: ${DCIMAGE}"
        exit 1
    fi
    chmod 666 ${DCIMAGE}
else
    good " - found existing renamed image file to use: ${DCIMAGE}"
fi

if [[ -e ./cookie ]]; then
    rm -f ./cookie
fi

exit 0

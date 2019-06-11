#!/bin/bash

# test zip url here is a zipped file holding an empty img file for quickly testing
# https://drive.google.com/file/d/10QoJkleQOXRvEOYKLDF89EGoF4wWep74/view?usp=sharing
# export DCGID=10QoJkleQOXRvEOYKLDF89EGoF4wWep74
# or
# download-google-drive-dc-img.sh 10QoJkleQOXRvEOYKLDF89EGoF4wWep74 /tmp/donkey.img

if [[ "${DCPATH}" == "" ]]; then
    export DCPATH="."
fi
if [[ -e ${DCPATH}/files/bash_colors.sh ]]; then
    source ${DCPATH}/files/bash_colors.sh
fi

# latest donkey car image id:
fileid="1vr4nEXLEh4xByKAXik8KhK3o-XWgo2fQ"
dc_extracted_image="donkey_2.5.0_pi3.img"
dc_base_image="${dc_extracted_image}"
if [[ "${DCGID}" != "" ]]; then
    fileid="${DCGID}"
fi
if [[ "${DCIMAGENAME}" != "" ]]; then
    dc_extracted_image="${DCIMAGENAME}"
    dc_base_image="$(dirname ${DCIMAGENAME})/${dc_extracted_image}"
fi
output_dir="${DCPATH}/files"
if [[ "${DCSTORAGEDIR}" != "" ]]; then
    output_dir="${DCSTORAGEDIR}"
fi
dc_image_file="${dc_extracted_image}"
if [[ "${DCIMAGE}" != "" ]]; then
    dc_image_file="${DCIMAGE}"
fi
download_path=$(echo "${output_dir}/${dc_image_file}" | sed -e 's|\.img|\.zip|g')
if [[ "${DCGDOWNLOADPATH}" != "" ]]; then
    download_path=$(echo "${DCGDOWNLOADPATH}" | sed -e 's|\.img|\.zip|g')
fi

# command line args override env vars
if [[ "$1" != "" ]]; then
    fileid="${1}"
fi
final_moved_location="${output_dir}/${dc_image_file}"
if [[ "$2" != "" ]]; then
    dc_image_file="${2}"
    final_moved_location="${dc_image_file}"
fi

if [[ -e ./cookie ]]; then
    rm -f ./cookie
fi

if [[ ! -e ${dc_image_file} ]]; then
    anmt "getting cookies from:"
    anmt "curl -c ./cookie -s -L \"https://drive.google.com/uc?export=download&id=${fileid}\""
    curl -c ./cookie -s -L "https://drive.google.com/uc?export=download&id=${fileid}" > /dev/null
fi

if [[ ! -e ${download_path} ]]; then
    anmt "$(date +'%Y-%m-%d %H:%M:%S') - downloading ${fileid} to ${download_path}:"
    anmt "curl -s -Lb ./cookie \"https://drive.google.com/uc?export=download&confirm=$(awk '/download/ {print $NF}' ./cookie)&id=${fileid}\" -o ${download_path}"
    if [[ "${DCDEBUG}" == "1" ]]; then
        curl -Lb ./cookie "https://drive.google.com/uc?export=download&confirm=`awk '/download/ {print $NF}' ./cookie`&id=${fileid}" -o ${download_path}
    else
        curl -s -Lb ./cookie "https://drive.google.com/uc?export=download&confirm=`awk '/download/ {print $NF}' ./cookie`&id=${fileid}" -o ${download_path}
    fi

    if [[ "$?" != "0" ]]; then
        err "failed to download ${fileid}"
        exit 1
    fi
else
    good "$(date +'%Y-%m-%d %H:%M:%S') -  - found previous download zip: ${download_path}"
fi

if [[ ! -e ${download_path} ]]; then
    err "failed to find downloaded file: ${download_path}"
    exit 1
fi

found_img_file_in_zip=$(unzip -l ${download_path} | grep img | awk '{print $NF}' | head -1)
if [[ "${found_img_file_in_zip}" == "" ]]; then
    err "failed to find an img file in the downloaded zip: ${download_path}"
    exit 1
else
    export DCIMAGENAME="${download_path}"
    dc_extracted_image="${found_img_file_in_zip}"
    anmt "found file in zip: ${found_img_file_in_zip}"
fi
dc_base_image="${output_dir}/${found_img_file_in_zip}"

if [[ ! -e ${dc_base_image} ]]; then
    anmt "extracting ${download_path} to image: ${dc_base_image}"
    chmod 666 ${download_path}
    unzip -n ${download_path} -d ${output_dir}
    output_file="${found_img_file_in_zip}"
    if [[ "$?" != "0" ]]; then
        err "failed to unzip ${download_path} to directory: ${output_dir}"
        exit 1
    fi
else
    good " - found existing base image: ${dc_base_image}"
fi

if [[ ! -e ${output_file} ]]; then
    unzip -n ${download_path} -d ${output_dir}
    output_file="${output_dir}/${dc_extracted_image}"
    if [[ ! -e ${output_file} ]]; then
        err "failed to find unzipped file: ${output_file}"
        exit 1
    fi
fi

if [[ "${final_moved_location}" != "${output_file}" ]]; then
    if [[ ! -e ${final_moved_location} ]]; then
        anmt "renaming ${output_file} to ${final_moved_location}"
        anmt "mv ${output_file} ${final_moved_location}"
        mv ${output_file} ${final_moved_location}
        if [[ ! -e ${final_moved_location} ]]; then
            err "failed to find renamed file: ${final_moved_location}"
            exit 1
        fi
        chmod 666 ${final_moved_location}
    else
        anmt " - found existing renamed image file to use: ${final_moved_location}"
    fi
fi

if [[ ! -e ${final_moved_location} ]]; then
    err "failed to find imamge file after moving to final location: ${final_moved_location}"
    exit 1
fi

if [[ -e ./cookie ]]; then
    rm -f ./cookie
fi

good "$(date +'%Y-%m-%d %H:%M:%S') - downloaded https://drive.google.com/uc?export=download&id=${fileid} as the extracted image file: ${final_moved_location}"

exit 0

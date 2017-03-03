FROM python:3

RUN apt-get -y update
RUN apt-get -y upgrade
RUN apt-get -y install git
RUN apt-get -y install xsel xclip libxml2-dev libxslt-dev libzmq-dev libspatialindex-dev virtualenv
RUN apt-get -y install python3-lxml python3-h5py python3-numexpr python3-dateutil python3-tz python3-bs4 python3-xlrd python3-tables python3-sqlalchemy python3-xlsxwriter python3-httplib2 python3-zmq
RUN apt-get -y install python3-numpy python3-matplotlib python3-scipy python3-pandas python3-skimage python3-yaml
RUN apt-get -y install python3-skimage

RUN pip install numpy
RUN pip install tensorflow

# First copy only setup.py, run pip install, and then copy the whole donkey dir.
# This is so only changes to setup.py trigger a pip install.
COPY ./setup.py /donkey/setup.py
RUN pip install -e /donkey/[server]
COPY . /donkey/

# Change workdir and run scripts/setup.py
WORKDIR /donkey
RUN python /donkey/scripts/setup.py

EXPOSE 8886
EXPOSE 8887

# Run the server
ENTRYPOINT ["python", "/donkey/scripts/serve.py"]
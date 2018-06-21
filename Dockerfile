FROM python:3

WORKDIR /app

ADD . /app
RUN pip install -e .

EXPOSE 8887

# syntax=docker/dockerfile:1
FROM python:3.8-slim-buster

WORKDIR /WebCrawler
COPY . /WebCrawler/

ENV RUN_IN_DOCKER_CONTAINER Yes

RUN pip install --upgrade pip

RUN pip install -r requirements.txt

CMD [ "python", "main.py"]

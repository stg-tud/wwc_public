# syntax=docker/dockerfile:1
FROM python:3.8-slim-buster

WORKDIR /Analysis
COPY ./analysis/ /Analysis/
COPY ./database/database_manager.py /Analysis/database/
COPY ./utility/website_data.py /Analysis/utility/
COPY ./utility/input_reader.py /Analysis/utility/
COPY ./requirements.txt /Analysis/
COPY ./config.yml /Analysis/

ENV RUN_IN_DOCKER_CONTAINER Yes

RUN pip install --upgrade pip

RUN pip install -r requirements.txt

CMD [ "python", "main_analysis.py"]

FROM python:3.10.0-slim
# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /opt/app

RUN apt update \
    && apt install -y gcc libgeos-dev git netcat \
    && pip install --upgrade pip \
    && apt-get autoclean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /opt/app/requirements.txt
RUN pip install --no-cache-dir -r /opt/app/requirements.txt

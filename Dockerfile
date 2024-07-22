FROM python:3.11-slim

RUN adduser avala

RUN mkdir /app && chown avala /app

USER avala

RUN pip install requests loguru pyyaml sqlalchemy psycopg2-binary pyparsing jsonschema fastapi uvicorn APScheduler==3.10.1 addict pika aio_pika click broadcaster

COPY server /app/server
COPY client /app/client
COPY shared /app/shared
COPY setup.py /app/

WORKDIR /home/avala/workspace

RUN pip install -e /app/

ENV PATH="/home/avala/.local/bin:${PATH}"

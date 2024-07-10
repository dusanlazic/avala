FROM python:3.11-slim AS build

RUN adduser avala

RUN mkdir /app && chown avala /app

USER avala

COPY server /app/server
COPY client /app/client
COPY shared /app/shared
COPY setup.py /app/

WORKDIR /home/avala/workspace

RUN pip install -e /app/

ENV PATH="/home/avala/.local/bin:${PATH}"

CMD ["sh"]

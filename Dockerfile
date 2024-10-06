FROM node:22-slim AS build-frontend
WORKDIR /app
ADD web /app/
RUN rm -rf /app/node_modules || true
RUN npm install
RUN npm run build

FROM python:3.11-alpine AS build-package
WORKDIR /app
COPY server /app/server
RUN rm /app/server/avala/shared
COPY shared /app/server/avala/shared
COPY --from=build-frontend /app/dist /app/server/avala/static/dist
RUN cd /app/server && python setup.py sdist

FROM python:3.11-slim
RUN adduser avala
USER avala
WORKDIR /home/avala/workspace
COPY --from=build-package /app/server/dist/*.tar.gz avala.tar.gz
RUN pip install avala.tar.gz pwntools
ENV PATH="/home/avala/.local/bin:${PATH}"

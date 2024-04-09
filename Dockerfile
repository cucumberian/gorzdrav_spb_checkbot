FROM python:3.11.9-alpine3.19

ENV HOMEDIR=/home/app/
ENV APPDIR=${HOMEDIR}/src/

RUN mkdir -p ${APPDIR}
WORKDIR ${APPDIR}

COPY . ${APPDIR}

RUN pip3 install --no-cache-dir -r requirements.txt

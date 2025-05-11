FROM python:3.12-alpine

ENV HOMEDIR=/home/app
ENV APPDIR=${HOMEDIR}/src/

RUN mkdir -p ${APPDIR}
WORKDIR ${APPDIR}

COPY . ${APPDIR}

RUN pip3 install --no-cache-dir -r requirements.txt

CMD ["python3", "app.py"]

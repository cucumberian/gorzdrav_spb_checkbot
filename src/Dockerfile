FROM python:3.12-alpine

ENV HOMEDIR=/home/app
ENV APPDIR=${HOMEDIR}/src/

RUN mkdir -p ${APPDIR}
WORKDIR ${APPDIR}

COPY requirements.txt ${APPDIR}
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . ${APPDIR}

CMD ["python3", "app.py"]

FROM python:3.12-alpine3.21

ENV HOMEDIR=/home/app/
ENV APPDIR=${HOMEDIR}/src/

RUN mkdir -p ${APPDIR}
WORKDIR ${APPDIR}

COPY . ${APPDIR}

RUN pip3 install --no-cache-dir -r requirements.txt

RUN addgroup --system app && adduser --system -G app app
RUN chown -R app:app ${HOMEDIR}
USER app

CMD ["python3", "app.py"]

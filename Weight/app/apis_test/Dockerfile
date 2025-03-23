FROM python:3.12-alpine

WORKDIR /app

COPY ./app/requierments.txt ./requierments.txt

RUN pip install -r requierments.txt && \
    apk add --no-cache shadow && \
    useradd -m test-user

USER test-user

COPY ./app/apis_test/ ./tests
COPY ./app/weight.py ./app/db.py ./
COPY ./app/in/ ./app/in/

CMD [ "pytest", "-q", "--disable-warnings", "./tests" ]
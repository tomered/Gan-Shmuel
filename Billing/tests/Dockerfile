FROM python:3.12-alpine

WORKDIR /app

COPY ../app/requirements.txt .

RUN pip install -r requirements.txt && \
    apk add --no-cache shadow && \
    useradd -m test-user

USER test-user

COPY test_billing.py .


CMD [ "python", "test_billing.py" ]
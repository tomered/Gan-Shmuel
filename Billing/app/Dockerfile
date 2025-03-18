FROM python:3.12-alpine

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt && \
    apk add --no-cache shadow && \
    useradd -m app-user

USER app-user

COPY  app.py .

CMD ["python", "app.py"]

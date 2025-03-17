FROM python:3.12.7

WORKDIR /ci
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt && \
    apt-get update && \
    apt-get install -y docker.io

COPY ci.py .
ENV FLASK_APP=ci.py
ENV FLASK_RUN_HOST=0.0.0.0

EXPOSE 5000
CMD [ "flask", "run" ]
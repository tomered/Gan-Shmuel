FROM python:3.12.7-slim

RUN apt update && apt install -y --no-install-recommends \
    curl \
    ca-certificates \
    git \
    && curl -fsSL https://get.docker.com | bash \
    && curl -L "https://github.com/docker/compose/releases/download/$(curl -s https://api.github.com/repos/docker/compose/releases/latest | jq -r .tag_name)/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose \
    && chmod +x /usr/local/bin/docker-compose \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /ci

# Copy the requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Clone the repository inside the container
RUN git clone https://github.com/tomered/Gan-Shmuel.git /Gan-Shmuel
# RUN apt update && apt install -y --no-install-recommends docker.io \
#     git && \
#     pip install  --no-cache-dir -r requirements.txt && \
#     rm -rf /var/lib/apt/lists/*


# RUN git clone https://github.com/tomered/Gan-Shmuel.git /Gan-Shmuel

COPY ci.py .

WORKDIR /Gan-Shmuel

ENV FLASK_APP=/ci/ci.py \
    FLASK_RUN_HOST=0.0.0.0 \
    PYTHONUNBUFFERED=1

EXPOSE 5000

CMD [ "flask", "run" ]
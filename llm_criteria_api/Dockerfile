FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

ARG APP_IMAGE_TAG=local
ARG PIPELINE_VERSION=complete-jd-candidate-extraction-v2
ARG GIT_COMMIT_HASH=local-build

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/runpod-volume/huggingface \
    TRANSFORMERS_CACHE=/runpod-volume/huggingface \
    APP_IMAGE_TAG=${APP_IMAGE_TAG} \
    IMAGE_TAG=${APP_IMAGE_TAG} \
    PIPELINE_VERSION=${PIPELINE_VERSION} \
    GIT_COMMIT_HASH=${GIT_COMMIT_HASH}

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3 /usr/local/bin/python \
    && ln -sf /usr/bin/pip3 /usr/local/bin/pip

COPY requirements.txt .
RUN python -m pip install --index-url https://download.pytorch.org/whl/cu121 torch==2.5.1+cu121 \
    && python -m pip install -r requirements.txt

COPY app ./app
COPY runpod_handler.py .

# The RunPod worker imports this module once, then keeps the model in memory
# for the lifetime of the worker process.
CMD ["python", "-u", "runpod_handler.py"]

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
RUN pip install paho-mqtt==2.1.0
COPY publish_mqtt.py ./
CMD ["python", "publish_mqtt.py"]

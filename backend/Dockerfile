FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    YOLO_CONFIG_DIR=/tmp/ultralytics

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --system app && adduser --system --ingroup app app

COPY requirements.txt ./
RUN python -m pip install --upgrade pip && \
    python -m pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu && \
    python -m pip uninstall -y polars matplotlib pandas seaborn scipy fonttools six \
                    contourpy cycler kiwisolver pyparsing python-dateutil polars-runtime-32

COPY --chown=app:app . .
RUN install -d -m 775 -o app -g app /app/logs

USER app

EXPOSE 5762

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5762"]
# Se construye desde la RAIZ del repositorio (ver docker-compose.yml): asi el
# agente copia el mismo app/models/best.pt que usa el backend, y no pueden
# quedar desplegados dos modelos distintos.
FROM python:3.10-bookworm

WORKDIR /app

RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    ffmpeg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY agente/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY agente/sentinel_agent.py .
COPY app/models/best.pt .

CMD ["python", "sentinel_agent.py"]

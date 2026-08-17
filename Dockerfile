FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV YOLO_CONFIG_DIR=/tmp/Ultralytics

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ultralytics declara como dependencia opencv-python (la variante con GUI), asi
# que pip la instala AUNQUE requirements.txt pida opencv-python-headless, y esa
# variante es la que gana al importar cv2. Es la que exige libGL/libxcb y obliga
# a instalar libgl1, libglib2.0-0 y ffmpeg via apt.
#
# Dejando solo la variante headless, cv2 funciona sin ninguna libreria de
# sistema: la imagen adelgaza y el build deja de depender de que
# deb.debian.org sea alcanzable.
RUN pip uninstall -y opencv-python \
    && pip install --no-cache-dir --force-reinstall opencv-python-headless==4.10.0.84

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
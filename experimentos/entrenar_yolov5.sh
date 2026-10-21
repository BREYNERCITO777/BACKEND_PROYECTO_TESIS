#!/bin/sh
set -e
pip install -q yolov5
pip uninstall -y opencv-python
pip install -q --no-cache-dir --force-reinstall opencv-python-headless==4.10.0.84

python -m yolov5.train \
  --weights yolov5s.pt \
  --data /eval/data_combinado.yaml \
  --epochs 20 \
  --batch-size 16 \
  --imgsz 640 \
  --device 0 \
  --patience 8 \
  --project /salida \
  --name yolov5s_comparacion \
  --exist-ok

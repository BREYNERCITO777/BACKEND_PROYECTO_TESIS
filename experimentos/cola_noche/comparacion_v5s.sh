#!/bin/sh
set -e
pip install -q yolov5==7.0.14
pip uninstall -y -q opencv-python
pip install -q --no-deps --force-reinstall opencv-python-headless==4.10.0.84
python /eval/evaluar_yolov5.py
python /eval/benchmark_latencia.py

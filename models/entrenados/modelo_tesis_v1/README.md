# Entrenamiento v1 (histórico)

Primer entrenamiento sobre el corpus completo: YOLOv8n desde COCO, en **CPU**, batch 4,
640 px, previsto para 10 épocas y **detenido en la 7** sin converger (mAP50 de validación
interna 0.778 en la última época, `results.csv`). Además, su configuración desactivaba el
mosaico desde la primera época.

Es la fila **v1** de la Tabla 2 del artículo. Se conserva solo como evidencia de esa
cronología: no es el modelo desplegado (ese es `app/models/best.pt`, v5, YOLOv8s) ni el
prototipo de 20 épocas de la versión inicial del manuscrito.

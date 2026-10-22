# Diagramas del artículo (figuras 2, 4, 5, 6 y 7)

Redibujados para la revisión de Frontiers con los datos verificados en el código:
agente local entre las cámaras y el backend, YOLOv8s (v5), 28 endpoints HTTP y 1
WebSocket, WebSocket nativo en el panel y despliegue del agente en la municipalidad.

Cada figura es un HTML con cajas posicionadas (`base.css`) y flechas dibujadas en SVG
(`base.js`). Para regenerar el PNG (escala 2) con Edge o Chrome en modo headless:

```bash
sh render.sh fig2 1500 985
sh render.sh fig4 1500 820
sh render.sh fig5 1500 850
sh render.sh fig6 1500 885
sh render.sh fig7 1500 745
```

`render.sh` usa la ruta de Edge en Windows; en otro sistema, cambiar el ejecutable.

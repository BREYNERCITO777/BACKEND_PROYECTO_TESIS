# Evaluación ciega de v5 en YouTube-GDD — protocolo fijado antes de evaluar

Escrito: 2026-10-29T20:27:42Z (UTC), antes de ejecutar ninguna inferencia sobre este conjunto.

- Conjunto: split de test oficial de YouTube-GDD (Gu et al., 2022; fold 7), 500 imágenes de
  fotogramas de vídeos de YouTube. Nunca se usó para entrenar, validar ni elegir ningún modelo.
- Etiquetas: clase "gun" (1) -> arma_fuego (0); "person" se descarta. 497 imágenes con arma, 879 cajas.
- Deduplicación: dHash 64 bits, Hamming <= 6, contra las 6 fuentes que vio v5 (42,866 imágenes);
  3 candidatos, ninguno pasa la comprobación de píxel (MAD >= 25.96 frente al umbral 4). 0 duplicados.
- Modelo: v5 desplegado, SHA-256 1aec8d3c923cc0a0…, sin ningún cambio.
- Métricas: m.val(conf=0.001, iou=0.5, batch=8, workers=2, imgsz=640), igual que la Tabla 4.
  Se reportan precisión, recall, AP@0.5 y AP@0.5:0.95 de arma_fuego, y la fracción de imágenes
  con arma que disparan alerta al umbral de operación 0.65 (cualquier clase).
- Una sola ejecución. El resultado se reporta tal como salga; no se ajusta umbral, modelo ni conjunto.

---
Nota añadida DESPUÉS de la evaluación (29 oct 2026): el total de imágenes de entrenamiento
comparadas es 43,266 (21,534 + 5,386 + 900 + 5,934 + 1,272 + 8,240), no 42,866; fue un error de
suma al escribir este protocolo. Las fuentes comparadas y el resultado de la deduplicación no
cambian. Lo demás del protocolo se cumplió tal cual: una sola ejecución, sin cambios posteriores.

"""Entrenamiento ORIGINAL del modelo (v1), conservado como registro histórico.

Con epochs=10 en CPU se interrumpió en la época 7 sin converger; es la
discrepancia de épocas que señaló la revisión. Los entrenamientos reales
(v2 a v5) y su protocolo están en experimentos/ y en
ESTADO_CORRECCIONES_FRONTIERS.md. No usar para reproducir los resultados.
"""

from ultralytics import YOLO
import shutil
import os

def entrenar_modelo():
    print("🚀 CARGANDO EL CEREBRO DE LA IA (YOLOv8)...")
    
    # Usamos el modelo nano
    model = YOLO('yolov8n.pt') 
    
    print("🏋️ INICIANDO ENTRENAMIENTO (MODO SEGURO)...")
    print("ℹ️  Configuración optimizada para evitar crash por memoria.")
    
    try:
        results = model.train(
            data='/app/data/dataset_final/data.yaml',
            epochs=10,       # Mantenemos 10 épocas
            imgsz=640,
            
            # --- CAMBIOS CRÍTICOS PARA QUE NO SE CIERRE ---
            batch=4,         # Procesamos solo 4 fotos a la vez (antes 16)
            cache=False,     # ¡IMPORTANTE! Leer de disco, no llenar la RAM
            workers=0,       # Un solo trabajador para máxima estabilidad
            # ----------------------------------------------
            
            project='/app/models/entrenados',
            name='modelo_tesis_v1',
            exist_ok=True
        )
        
        print("✅ ENTRENAMIENTO FINALIZADO CON ÉXITO")
        
        # Guardar resultado
        ruta_origen = '/app/models/entrenados/modelo_tesis_v1/weights/best.pt'
        ruta_destino = '/app/models/best.pt'
        
        if os.path.exists(ruta_origen):
            shutil.copy(ruta_origen, ruta_destino)
            print(f"🏆 MEJOR MODELO GUARDADO EN: {ruta_destino}")
            
            print("📦 Exportando a formato ONNX...")
            model.export(format='onnx')
        else:
            print("❌ No se generó el archivo de pesos final.")
            
    except Exception as e:
        print(f"❌ ERROR FATAL DURANTE EL ENTRENAMIENTO: {e}")

if __name__ == "__main__":
    entrenar_modelo()
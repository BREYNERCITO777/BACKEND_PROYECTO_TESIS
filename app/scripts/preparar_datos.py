"""Partición ORIGINAL 70/20/10 del dataset (v1), conservada como registro histórico.

Los modelos actuales usan la partición 80/20 descrita en
ESTADO_CORRECCIONES_FRONTIERS.md (puntos 7 y 8).
"""

import os
import shutil
import random
import yaml
from pathlib import Path

# --- CONFIGURACIÓN ---
BASE_DIR = Path("/app/data")
RAW_DIR = BASE_DIR / "raw"
DATASET_DIR = BASE_DIR / "dataset_final"

# Mapeo: Pistolas = 0, Cuchillos = 1
CLASES = {
    "armas_fuego": 0,
    "armas_blanca": 1
}

def procesar_datos():
    print("🚀 INICIANDO ORGANIZACIÓN DEL DATASET...")
    
    # 1. Limpiar carpeta de destino si ya existe
    if DATASET_DIR.exists():
        shutil.rmtree(DATASET_DIR)
    
    # 2. Crear estructura de carpetas YOLO
    for split in ['train', 'val', 'test']:
        (DATASET_DIR / split / 'images').mkdir(parents=True, exist_ok=True)
        (DATASET_DIR / split / 'labels').mkdir(parents=True, exist_ok=True)

    total_imgs = 0

    # 3. Procesar cada clase
    for carpeta_nombre, id_clase in CLASES.items():
        ruta_origen = RAW_DIR / carpeta_nombre
        
        if not ruta_origen.exists():
            print(f"⚠️  ALERTA: No encuentro la carpeta {carpeta_nombre}")
            continue

        # Buscar todas las imágenes
        imagenes = list(ruta_origen.glob("*.jpg")) + list(ruta_origen.glob("*.png")) + list(ruta_origen.glob("*.jpeg"))
        random.shuffle(imagenes) # Mezclar para que sea aleatorio
        
        # Calcular división (70% Entrenar, 20% Validar, 10% Test)
        n = len(imagenes)
        n_train = int(n * 0.7)
        n_val = int(n * 0.2)
        
        splits = {
            'train': imagenes[:n_train],
            'val': imagenes[n_train:n_train+n_val],
            'test': imagenes[n_train+n_val:]
        }
        
        print(f"   📂 Procesando '{carpeta_nombre}' -> ID {id_clase}: {n} imágenes encontradas.")

        for split, imgs in splits.items():
            for img_path in imgs:
                # Copiar imagen
                shutil.copy(img_path, DATASET_DIR / split / 'images' / img_path.name)
                
                # Procesar etiqueta (corregir ID de clase)
                txt_path = img_path.with_suffix('.txt')
                if txt_path.exists():
                    with open(txt_path, 'r') as f:
                        lines = f.readlines()
                    
                    new_lines = []
                    for line in lines:
                        parts = line.strip().split()
                        if parts:
                            # AQUÍ OCURRE LA MAGIA: Forzamos el ID correcto
                            parts[0] = str(id_clase) 
                            new_lines.append(" ".join(parts))
                    
                    with open(DATASET_DIR / split / 'labels' / txt_path.name, 'w') as f:
                        f.write("\n".join(new_lines))
        
        total_imgs += n

    # 4. Crear archivo de configuración data.yaml
    yaml_data = {
        'path': str(DATASET_DIR.absolute()),
        'train': 'train/images',
        'val': 'val/images',
        'test': 'test/images',
        'nc': 2,
        'names': ['arma_fuego', 'arma_blanca']
    }
    
    with open(DATASET_DIR / 'data.yaml', 'w') as f:
        yaml.dump(yaml_data, f)

    print("-" * 30)
    print(f"✅ ¡ÉXITO! Dataset listo con {total_imgs} imágenes.")
    print(f"📍 Ubicación: {DATASET_DIR}")

if __name__ == "__main__":
    procesar_datos()
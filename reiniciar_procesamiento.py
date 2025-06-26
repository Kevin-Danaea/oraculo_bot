#!/usr/bin/env python3
"""
Script para reiniciar el procesamiento histórico desde donde se quedó.
"""

import subprocess
import sys
import os
import time

def process_single_file(file_path, file_name):
    """
    Procesa un solo archivo .zst y lo elimina al completar.
    Incluye fallback automático si hay problemas de memoria.
    
    Returns:
        bool: True si se procesó exitosamente, False si falló
    """
    print(f"📊 Procesando archivo: {file_name}")
    print("🚀 Iniciando procesamiento...")
    
    try:
        # Intentar procesamiento normal primero
        result = subprocess.run([sys.executable, "procesador_historico.py", file_path], 
                              capture_output=True, text=True, check=True)
        print("✅ Procesamiento completado exitosamente")
        
    except subprocess.CalledProcessError as e:
        # Verificar si es error de memoria
        error_output = e.stderr.lower() if e.stderr else ""
        if "memory" in error_output or "frame requires too much memory" in error_output:
            print("⚠️  Error de memoria detectado en procesador principal")
            print("🔧 Cambiando automáticamente al procesador externo...")
            
            try:
                # Fallback al procesador externo
                result = subprocess.run([sys.executable, "procesador_externo.py", file_path], 
                                      capture_output=True, text=True, check=True)
                print("✅ Procesamiento externo completado exitosamente")
            except subprocess.CalledProcessError as fallback_error:
                print(f"❌ También falló el procesador externo: {fallback_error}")
                return False
        else:
            print(f"❌ Error en procesamiento principal: {e}")
            return False
    
    try:
        
        # Mover el archivo procesado en lugar de eliminarlo (más seguro)
        print(f"📦 Moviendo archivo procesado: {file_name}")
        
        # Esperar un momento para que se liberen los handles del archivo
        time.sleep(2)
        
        # Mover a carpeta "procesados" en lugar de eliminar
        processed_dir = os.path.join(os.path.dirname(file_path), "procesados")
        os.makedirs(processed_dir, exist_ok=True)
        
        processed_path = os.path.join(processed_dir, file_name)
        
        # Intentar mover con reintentos
        for attempt in range(3):
            try:
                os.rename(file_path, processed_path)
                print(f"✅ Archivo movido a: {processed_path}")
                return True
            except OSError as e:
                if attempt < 2:  # No es el último intento
                    print(f"⏳ Intento {attempt + 1} falló, esperando 3 segundos...")
                    time.sleep(3)
                else:
                    # Último intento falló
                    print(f"⚠️  Procesamiento exitoso pero no se pudo mover el archivo: {e}")
                    print(f"📁 Puedes moverlo manualmente: {file_path}")
                    return True  # Consideramos exitoso aunque no se pudo mover
                    
    except subprocess.CalledProcessError:
        print("❌ El procesamiento falló - revisa los logs")
        print(f"📁 El archivo {file_name} se mantiene para reintento")
        return False

def main():
    # Verificar si existe el archivo del procesador
    if not os.path.exists("procesador_historico.py"):
        print("❌ Error: No se encontró procesador_historico.py")
        sys.exit(1)
    
    # Verificar si existe un checkpoint
    checkpoint_file = "procesamiento_checkpoint.txt"
    if os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, 'r') as f:
                line_number = int(f.read().strip())
            print(f"🔄 Checkpoint encontrado: reanudará desde línea {line_number:,}")
        except:
            print("⚠️  Checkpoint encontrado pero no se pudo leer")
    else:
        print("🚀 No hay checkpoint - iniciará desde el principio")
    
    # Verificar URLs procesadas
    urls_file = "urls_procesadas.txt"
    if os.path.exists(urls_file):
        try:
            with open(urls_file, 'r', encoding='utf-8') as f:
                url_count = sum(1 for line in f if line.strip())
            print(f"📝 URLs ya procesadas: {url_count:,} (se saltarán para evitar duplicados)")
        except:
            print("⚠️  Archivo de URLs procesadas encontrado pero no se pudo leer")
    else:
        print("🆕 No hay URLs procesadas - analizará todos los posts")
    
    submissions_dir = r'C:\Users\USER\OneDrive\Documents\Proyectos\trading_crypto\Datasets\reddit\submissions'
    
    # Procesar todos los archivos .zst automáticamente
    total_processed = 0
    total_failed = 0
    
    print("🤖 MODO AUTOMATIZADO: Procesando todos los archivos .zst secuencialmente")
    print("=" * 60)
    
    while True:
        # Buscar archivos .zst disponibles
        try:
            zst_files = [f for f in os.listdir(submissions_dir) if f.endswith('.zst')]
        except FileNotFoundError:
            print(f"❌ Error: No se encontró el directorio {submissions_dir}")
            sys.exit(1)
        
        if not zst_files:
            print(f"🎉 ¡PROCESAMIENTO COMPLETADO! No quedan archivos .zst por procesar")
            print(f"📊 RESUMEN FINAL:")
            print(f"   ✅ Archivos procesados exitosamente: {total_processed}")
            print(f"   ❌ Archivos que fallaron: {total_failed}")
            print("=" * 60)
            break
        
        # Ordenar archivos para procesamiento secuencial (opcional)
        zst_files.sort()
        
        # Tomar el primer archivo disponible
        current_file = zst_files[0]
        file_path = os.path.join(submissions_dir, current_file)
        
        print(f"📂 Archivos restantes: {len(zst_files)}")
        print(f"📄 Procesando ahora: {current_file}")
        
        # Procesar el archivo
        success = process_single_file(file_path, current_file)
        
        if success:
            total_processed += 1
            print(f"✅ Archivo {current_file} completado ({total_processed} de {total_processed + len(zst_files) - 1})")
        else:
            total_failed += 1
            print(f"❌ Archivo {current_file} falló. Deteniéndose.")
            print(f"📊 RESUMEN PARCIAL:")
            print(f"   ✅ Archivos procesados: {total_processed}")
            print(f"   ❌ Archivos fallidos: {total_failed}")
            sys.exit(1)
        
        print("=" * 60)
        
        # Pequeña pausa entre archivos para no sobrecargar el sistema
        if len(zst_files) > 1:  # Si hay más archivos por procesar
            print("⏳ Pausa de 5 segundos antes del siguiente archivo...")
            time.sleep(5)

if __name__ == "__main__":
    main() 
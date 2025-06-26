#!/usr/bin/env python3
"""
Script para reiniciar el procesamiento histórico desde donde se quedó.
Actualizado para funcionar con procesador_historico.py y mostrar logs en tiempo real.
"""

import subprocess
import sys
import os
import time

def process_single_file(file_path, file_name):
    """
    Procesa un solo archivo .zst y lo mueve al completar.
    Muestra logs en tiempo real del procesador.
    
    Returns:
        bool: True si se procesó exitosamente, False si falló
    """
    print(f"📊 Procesando archivo: {file_name}")
    print("🚀 Iniciando procesamiento con logs en tiempo real...")
    print("=" * 60)
    
    try:
        # Ejecutar el procesador sin capturar output para ver logs en tiempo real
        # stdout=None, stderr=None permite que los logs se muestren directamente
        result = subprocess.run(
            [sys.executable, "procesador_historico.py", file_path], 
            stdout=None,  # Permitir que los logs se muestren en tiempo real
            stderr=None,  # Permitir que los errores se muestren en tiempo real
            check=True
        )
        
        print("=" * 60)
        print("✅ Procesamiento completado exitosamente")
        
    except subprocess.CalledProcessError as e:
        print("=" * 60)
        print(f"❌ Error en procesamiento: código de salida {e.returncode}")
        print("📋 Revisa los logs arriba para más detalles sobre el error")
        return False
    except KeyboardInterrupt:
        print("\n⏹️  Procesamiento interrumpido por el usuario")
        return False
    
    # Mover el archivo procesado (más seguro que eliminarlo)
    try:
        print(f"📦 Moviendo archivo procesado: {file_name}")
        
        # Esperar un momento para que se liberen los handles del archivo
        time.sleep(2)
        
        # Crear carpeta "procesados" si no existe
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
                    
    except Exception as e:
        print(f"⚠️  Error moviendo archivo: {e}")
        print(f"📁 El archivo permanece en: {file_path}")
        return True  # Consideramos exitoso el procesamiento

def check_prerequisites():
    """Verifica que todos los requisitos estén disponibles."""
    print("🔍 Verificando prerequisitos...")
    
    # Verificar procesador principal
    if not os.path.exists("procesador_historico.py"):
        print("❌ Error: No se encontró procesador_historico.py")
        return False
    print("✅ procesador_historico.py encontrado")
    
    # Verificar comando zstd
    try:
        subprocess.run(['zstd', '--version'], capture_output=True, check=True)
        print("✅ Comando zstd disponible")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Error: Comando 'zstd' no encontrado")
        print("💡 Instala zstd: winget install facebook.zstd")
        return False
    
    return True

def show_current_status():
    """Muestra el estado actual del procesamiento."""
    print("📊 ESTADO ACTUAL DEL PROCESAMIENTO:")
    print("-" * 40)
    
    # Verificar checkpoint
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
            print(f"📝 URLs ya procesadas: {url_count:,} (se saltarán duplicados)")
        except:
            print("⚠️  Archivo de URLs procesadas encontrado pero no se pudo leer")
    else:
        print("🆕 No hay URLs procesadas - analizará todos los posts")

def main():
    print("🤖 REINICIADOR DE PROCESAMIENTO HISTÓRICO")
    print("=" * 60)
    
    # Verificar prerequisitos
    if not check_prerequisites():
        print("\n❌ Faltan prerequisitos. Terminando script.")
        sys.exit(1)
    
    # Mostrar estado actual
    show_current_status()
    
    # Directorio de archivos
    submissions_dir = r'C:\Users\USER\Downloads\reddit\submissions'
    
    # Verificar que el directorio existe
    if not os.path.exists(submissions_dir):
        print(f"\n❌ Error: No se encontró el directorio {submissions_dir}")
        sys.exit(1)
    
    # Procesar todos los archivos .zst automáticamente
    total_processed = 0
    total_failed = 0
    
    print("\n🤖 MODO AUTOMATIZADO: Procesando archivos .zst secuencialmente")
    print("💡 Los logs del procesador se mostrarán en tiempo real")
    print("⏹️  Usa Ctrl+C para interrumpir si es necesario")
    print("=" * 60)
    
    while True:
        # Buscar archivos .zst disponibles
        try:
            zst_files = [f for f in os.listdir(submissions_dir) if f.endswith('.zst')]
        except Exception as e:
            print(f"❌ Error accediendo al directorio: {e}")
            break
        
        if not zst_files:
            print(f"\n🎉 ¡PROCESAMIENTO COMPLETADO!")
            print(f"📊 RESUMEN FINAL:")
            print(f"   ✅ Archivos procesados exitosamente: {total_processed}")
            print(f"   ❌ Archivos que fallaron: {total_failed}")
            print("=" * 60)
            break
        
        # Ordenar archivos cronológicamente (por nombre)
        zst_files.sort()
        
        # Tomar el primer archivo disponible
        current_file = zst_files[0]
        file_path = os.path.join(submissions_dir, current_file)
        
        print(f"\n📂 Archivos restantes: {len(zst_files)}")
        print(f"📄 Archivo actual: {current_file}")
        
        # Procesar el archivo
        success = process_single_file(file_path, current_file)
        
        if success:
            total_processed += 1
            print(f"\n✅ Archivo {current_file} completado exitosamente")
            print(f"📈 Progreso: {total_processed} completados, {len(zst_files)-1} restantes")
        else:
            total_failed += 1
            print(f"\n❌ Archivo {current_file} falló.")
            
            # Preguntar si continuar o detenerse
            print(f"📊 ESTADO ACTUAL:")
            print(f"   ✅ Procesados: {total_processed}")
            print(f"   ❌ Fallidos: {total_failed}")
            print(f"   📄 Restantes: {len(zst_files)-1}")
            
            response = input("\n¿Continuar con el siguiente archivo? (s/N): ").strip().lower()
            if response != 's' and response != 'sí' and response != 'si':
                print("🛑 Procesamiento detenido por el usuario")
                break
        
        # Pequeña pausa entre archivos
        if len(zst_files) > 1:  # Si hay más archivos por procesar
            print("\n⏳ Pausa de 3 segundos antes del siguiente archivo...")
            time.sleep(3)
    
    print(f"\n📊 RESUMEN FINAL:")
    print(f"   ✅ Archivos procesados: {total_processed}")
    print(f"   ❌ Archivos fallidos: {total_failed}")
    print("🏁 Script terminado")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Script interrumpido por el usuario")
        print("🔄 Los checkpoints se mantienen para reanudar después")
        sys.exit(0) 
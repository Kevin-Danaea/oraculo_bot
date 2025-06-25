#!/usr/bin/env python3
"""
Script para reiniciar el procesamiento histórico desde donde se quedó.
"""

import subprocess
import sys
import os

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
    
    # Buscar archivos .zst en el directorio actual
    zst_files = [f for f in os.listdir('.') if f.endswith('.zst')]
    
    if not zst_files:
        print("❌ Error: No se encontraron archivos .zst en el directorio actual")
        print("   Copia el archivo de Reddit .zst a este directorio")
        sys.exit(1)
    
    if len(zst_files) > 1:
        print("📁 Se encontraron múltiples archivos .zst:")
        for i, f in enumerate(zst_files):
            print(f"   {i+1}. {f}")
        choice = input("Selecciona el número del archivo a procesar: ")
        try:
            selected_file = zst_files[int(choice) - 1]
        except (ValueError, IndexError):
            print("❌ Selección inválida")
            sys.exit(1)
    else:
        selected_file = zst_files[0]
    
    print(f"📊 Procesando archivo: {selected_file}")
    print("🚀 Iniciando procesamiento...")
    
    # Ejecutar el procesador
    try:
        subprocess.run([sys.executable, "procesador_historico.py", selected_file], check=True)
        print("✅ Procesamiento completado exitosamente")
    except subprocess.CalledProcessError:
        print("❌ El procesamiento falló - revisa los logs")
        sys.exit(1)

if __name__ == "__main__":
    main() 
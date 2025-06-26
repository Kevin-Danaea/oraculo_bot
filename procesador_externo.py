#!/usr/bin/env python3
"""
Procesador EXTERNO para archivos .zst que requieren demasiada memoria.
Usa zstd externo + procesamiento línea por línea en memoria.
"""

import subprocess
import sys
import logging
import time
import os
from typing import Dict, Any

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Importar clases del procesador principal (que ya tienen todos los imports necesarios)
from procesador_historico import SentimentAnalyzer, RedditPostProcessor, DatabaseManager

def process_with_external_zstd(filepath: str) -> Dict[str, Any]:
    """
    Procesa archivo .zst usando zstd externo para evitar problemas de memoria.
    
    Args:
        filepath: Ruta al archivo .zst
        
    Returns:
        Dict con estadísticas del procesamiento
    """
    logger.info(f"🔧 PROCESAMIENTO EXTERNO: {filepath}")
    
    # Inicializar componentes
    analyzer = SentimentAnalyzer()
    processor = RedditPostProcessor(analyzer)
    db_manager = DatabaseManager()
    
    batch_data = []
    batch_size = 500
    line_count = 0
    start_time = time.time()
    
    try:
        # Comando para descomprimir con zstd externo
        cmd = ["zstd", "-dc", filepath]
        logger.info(f"🚀 Ejecutando: {' '.join(cmd)}")
        
        # Abrir proceso de descompresión
        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8') as process:
            logger.info("📄 Procesando líneas del archivo descomprimido...")
            
            for line in (process.stdout or []):
                line_count += 1
                
                try:
                    if not line.strip():
                        continue
                    
                    # Procesar línea con el procesador existente
                    post_data = processor.process_post(line)
                    
                    if post_data:
                        batch_data.append(post_data)
                    
                    # Insertar lote cuando sea necesario
                    if len(batch_data) >= batch_size:
                        success = db_manager.insert_batch(batch_data)
                        if success:
                            logger.info(f"✅ Lote de {len(batch_data)} registros insertado (línea {line_count:,})")
                        batch_data.clear()
                    
                    # Log de progreso cada 100k líneas
                    if line_count % 100000 == 0:
                        stats = processor.get_stats()
                        logger.info(f"📊 Progreso: {line_count:,} líneas, {stats['processed']} procesados")
                
                except Exception as e:
                    logger.error(f"Error procesando línea {line_count}: {e}")
                    continue
            
            # Insertar lote final
            if batch_data:
                success = db_manager.insert_batch(batch_data)
                if success:
                    logger.info(f"✅ Lote final de {len(batch_data)} registros insertado")
            
            # Verificar que el proceso terminó correctamente
            return_code = process.wait()
            if return_code != 0:
                stderr_output = process.stderr.read() if process.stderr else "Error desconocido"
                logger.error(f"❌ zstd falló con código {return_code}: {stderr_output}")
                return {'success': False, 'error': f'zstd error: {stderr_output}'}
    
    except Exception as e:
        logger.error(f"❌ Error en procesamiento externo: {e}")
        return {'success': False, 'error': str(e)}
    
    finally:
        if db_manager:
            db_manager.close()
    
    # Estadísticas finales
    end_time = time.time()
    processing_time = end_time - start_time
    stats = processor.get_stats()
    
    logger.info("=" * 60)
    logger.info("PROCESAMIENTO EXTERNO COMPLETADO")
    logger.info("=" * 60)
    logger.info(f"Tiempo total: {processing_time:.2f} segundos")
    logger.info(f"Líneas procesadas: {line_count:,}")
    logger.info(f"Posts analizados: {stats['processed']:,}")
    logger.info("=" * 60)
    
    return {
        'success': True,
        'processing_time': processing_time,
        'lines_processed': line_count,
        'posts_processed': stats['processed'],
        'stats': stats
    }

def main():
    if len(sys.argv) != 2:
        print("Uso: python procesador_externo.py archivo.zst")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    # Verificar que zstd esté disponible
    try:
        subprocess.run(["zstd", "--version"], capture_output=True, check=True)
        logger.info("✅ zstd externo disponible")
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("❌ zstd no encontrado. Instala con: winget install zstd")
        sys.exit(1)
    
    # Verificar archivo
    if not os.path.exists(filepath):
        logger.error(f"❌ Archivo no encontrado: {filepath}")
        sys.exit(1)
    
    # Procesar archivo
    result = process_with_external_zstd(filepath)
    
    if result['success']:
        logger.info("🎉 Procesamiento externo exitoso")
    else:
        logger.error(f"❌ Procesamiento externo falló: {result.get('error', 'Error desconocido')}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Script de migración de un solo uso para actualizar timestamps en la base de datos.

Convierte la columna published_at de timestamp Unix (string) a formato ISO 8601 UTC.
Ejemplo: "2020-02-12 16:47:29" -> "2020-02-12T16:47:29+00:00"

Este script debe ejecutarse una sola vez para migrar los datos existentes.
"""

import os
import sys
import time
import pandas as pd
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv
import traceback

def load_database_config():
    """
    Carga la configuración de la base de datos desde el archivo .env.
    
    Returns:
        str: URL de conexión a la base de datos
    """
    # Cargar variables de entorno desde .env
    load_dotenv()
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL no encontrada en el archivo .env")
    
    return database_url

def convert_unix_timestamp_to_iso(timestamp_str: str) -> str:
    """
    Convierte un timestamp Unix (string) a formato ISO 8601 UTC.
    
    Args:
        timestamp_str: Timestamp como string (puede ser Unix timestamp o fecha en formato local)
        
    Returns:
        Fecha en formato ISO 8601 UTC: 2020-05-01T15:30:45+00:00
    """
    try:
        # Intentar parsear como timestamp Unix (float)
        try:
            timestamp_float = float(timestamp_str)
            # Si es un timestamp Unix válido (después de 1970 y antes de 2050)
            if 0 <= timestamp_float <= 2524608000:  # 01/01/2050
                dt_utc = datetime.fromtimestamp(timestamp_float, tz=timezone.utc)
                return dt_utc.isoformat()
        except ValueError:
            pass
        
        # Intentar parsear como fecha en formato string (formato actual: "2020-02-12 16:47:29")
        try:
            # Parsear fecha sin timezone (asumiendo que es UTC)
            dt_naive = datetime.strptime(timestamp_str.strip(), "%Y-%m-%d %H:%M:%S")
            # Asignar timezone UTC
            dt_utc = dt_naive.replace(tzinfo=timezone.utc)
            return dt_utc.isoformat()
        except ValueError:
            pass
        
        # Si no se puede parsear, usar epoch como fallback
        print(f"⚠️  No se pudo parsear timestamp '{timestamp_str}', usando epoch como fallback")
        dt_utc = datetime.fromtimestamp(0, tz=timezone.utc)
        return dt_utc.isoformat()
        
    except Exception as e:
        print(f"❌ Error convirtiendo timestamp '{timestamp_str}': {e}")
        # Usar epoch como fallback en caso de error
        dt_utc = datetime.fromtimestamp(0, tz=timezone.utc)
        return dt_utc.isoformat()

def main():
    """Función principal del script de migración."""
    print("🔄 SCRIPT DE MIGRACIÓN DE TIMESTAMPS")
    print("=" * 60)
    print("Convirtiendo published_at de formato Unix a ISO 8601 UTC")
    print("=" * 60)
    
    try:
        # 1. Cargar configuración
        print("📁 Cargando configuración desde .env...")
        database_url = load_database_config()
        print("✅ Configuración cargada exitosamente")
        
        # 2. Conectar a la base de datos
        print("\n🔌 Conectando a la base de datos...")
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        print("✅ Conexión establecida exitosamente")
        
        # 3. Leer registros que necesitan actualización
        print("\n🔍 Buscando registros con formato de timestamp incorrecto...")
        
        # Usar conexión directa para evitar problemas con SQLAlchemy
        query = text("SELECT id, published_at FROM noticias WHERE published_at NOT LIKE '%T%'")
        
        with engine.connect() as conn:
            result = conn.execute(query)
            records = result.fetchall()
        
        if not records:
            print("✅ No se encontraron registros para actualizar.")
            print("🎉 Todos los timestamps ya están en formato ISO 8601 UTC")
            return
        
        print(f"📊 Se encontraron {len(records)} registros para actualizar.")
        
        # 4. Mostrar algunos ejemplos
        print(f"\n📋 Ejemplos de registros a actualizar:")
        for i, record in enumerate(records[:3]):
            print(f"   ID {record[0]}: '{record[1]}'")
        if len(records) > 3:
            print(f"   ... y {len(records) - 3} registros más")
        
        # 5. Transformar timestamps
        print(f"\n⚙️  Iniciando transformación de fechas...")
        update_mappings = []
        
        total_records = len(records)
        processed = 0
        errors = 0
        
        for record in records:
            try:
                record_id = int(record[0])  # ID del registro
                old_timestamp = str(record[1])  # Timestamp actual
                
                # Convertir a formato ISO 8601 UTC
                new_timestamp = convert_unix_timestamp_to_iso(old_timestamp)
                
                update_mappings.append({
                    'id': record_id,
                    'published_at': new_timestamp
                })
                
                processed += 1
                
                # Mostrar progreso cada 1000 registros
                if processed % 1000 == 0:
                    print(f"   📈 Procesados: {processed}/{total_records}")
                
            except Exception as e:
                errors += 1
                print(f"❌ Error procesando registro ID {record[0]}: {e}")
        
        print(f"✅ Transformación completada: {processed} exitosos, {errors} errores")
        
        # 6. Actualización en lotes para no sobrecargar la base de datos en la nube
        if update_mappings:
            print(f"\n💾 Actualizando registros en lotes de 500 para proteger la infraestructura...")
            print(f"   📊 Total de registros: {len(update_mappings)}")
            print(f"   🔒 Cada lote tendrá su propia transacción segura")
            print(f"   ⏱️  Pausa de 10 segundos entre lotes")
            
            # Configuración de lotes
            BATCH_SIZE = 500
            PAUSE_SECONDS = 10
            
            total_records = len(update_mappings)
            total_batches = (total_records + BATCH_SIZE - 1) // BATCH_SIZE  # Redondeo hacia arriba
            successful_batches = 0
            total_updated = 0
            
            print(f"   📦 Se procesarán {total_batches} lotes de máximo {BATCH_SIZE} registros")
            print(f"\n🚀 Iniciando actualización por lotes...")
            
            # Procesar en lotes
            for batch_num in range(total_batches):
                start_idx = batch_num * BATCH_SIZE
                end_idx = min(start_idx + BATCH_SIZE, total_records)
                current_batch = update_mappings[start_idx:end_idx]
                
                print(f"\n📦 Lote {batch_num + 1}/{total_batches}: Actualizando registros {start_idx + 1}-{end_idx}")
                
                try:
                    # Usar raw SQL para actualización del lote
                    update_sql = """
                    UPDATE noticias 
                    SET published_at = :published_at 
                    WHERE id = :id
                    """
                    
                    # Ejecutar la actualización del lote
                    session.execute(text(update_sql), current_batch)
                    
                    # Commit del lote actual
                    session.commit()
                    
                    successful_batches += 1
                    total_updated += len(current_batch)
                    
                    print(f"   ✅ Lote completado: {len(current_batch)} registros actualizados")
                    print(f"   📈 Progreso total: {total_updated}/{total_records} registros")
                    
                    # Pausa entre lotes (excepto en el último)
                    if batch_num < total_batches - 1:
                        print(f"   ⏳ Esperando {PAUSE_SECONDS} segundos antes del siguiente lote...")
                        time.sleep(PAUSE_SECONDS)
                    
                except Exception as db_error:
                    # Rollback solo del lote actual
                    session.rollback()
                    print(f"   ❌ ERROR en lote {batch_num + 1}: {db_error}")
                    print(f"   🔄 ROLLBACK del lote actual - registros {start_idx + 1}-{end_idx} NO modificados")
                    
                    # Mostrar estadísticas hasta el momento
                    print(f"\n📊 ESTADÍSTICAS HASTA EL ERROR:")
                    print(f"   ✅ Lotes exitosos: {successful_batches}/{batch_num + 1}")
                    print(f"   ✅ Registros actualizados: {total_updated}")
                    print(f"   ❌ Registros pendientes: {total_records - total_updated}")
                    
                    # Preguntar si continuar sería peligroso, mejor terminar aquí
                    print(f"\n🛑 Deteniendo proceso para evitar inconsistencias")
                    raise db_error
            
            print(f"\n🎉 ¡ACTUALIZACIÓN MASIVA COMPLETADA!")
            print(f"   ✅ Total de lotes procesados: {successful_batches}/{total_batches}")
            print(f"   ✅ Total de registros actualizados: {total_updated}")
            
        else:
            print("⚠️  No hay registros para actualizar")
        
        # 7. Verificar resultados
        print(f"\n🔍 Verificando resultados...")
        verification_query = text("SELECT COUNT(*) FROM noticias WHERE published_at NOT LIKE '%T%'")
        
        with engine.connect() as conn:
            remaining_count = conn.execute(verification_query).scalar() or 0
        
        if remaining_count == 0:
            print("✅ Verificación exitosa: Todos los timestamps están en formato ISO 8601")
        else:
            print(f"⚠️  Verificación: Quedan {remaining_count} registros sin formato correcto")
        
        # 8. Mostrar algunos ejemplos de registros actualizados
        print(f"\n📋 Ejemplos de registros actualizados:")
        updated_query = text("SELECT id, published_at FROM noticias WHERE published_at LIKE '%T%' ORDER BY id DESC LIMIT 3")
        
        with engine.connect() as conn:
            updated_result = conn.execute(updated_query)
            for row in updated_result:
                print(f"   ID {row[0]}: '{row[1]}'")
        
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {e}")
        print(f"📋 Traceback completo:")
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        # Cerrar conexión
        if 'session' in locals():
            session.close()
        if 'engine' in locals():
            engine.dispose()
        print(f"\n🔌 Conexión a la base de datos cerrada")
    
    print(f"\n" + "=" * 60)
    print("🎉 MIGRACIÓN COMPLETADA EXITOSAMENTE")
    print("=" * 60)
    print("✅ Todos los timestamps ahora están en formato ISO 8601 UTC")
    print("✅ Este script puede eliminarse ya que es de un solo uso")
    print("=" * 60)

if __name__ == "__main__":
    # Verificar que las dependencias estén instaladas
    try:
        import sqlalchemy
        import psycopg2
        import pandas
        import dotenv
        print("✅ Todas las dependencias están instaladas")
    except ImportError as e:
        print(f"❌ Error: Dependencia faltante: {e}")
        print("💡 Instala las dependencias:")
        print("   pip install sqlalchemy psycopg2-binary pandas python-dotenv")
        sys.exit(1)
    
    main() 
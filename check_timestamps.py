#!/usr/bin/env python3
"""
Script auxiliar para verificar el estado de los timestamps antes de la migración.
"""

import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

def main():
    """Verifica el estado actual de los timestamps en la base de datos."""
    print("🔍 VERIFICACIÓN DE TIMESTAMPS EN LA BASE DE DATOS")
    print("=" * 60)
    
    # Cargar configuración
    load_dotenv()
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL no encontrada en .env")
        return
    
    # Conectar a la base de datos
    engine = create_engine(database_url)
    
    try:
        # Verificar registros con formato incorrecto
        print("\n📊 Analizando formatos de timestamp...")
        
        # Query simple para contar registros sin formato ISO 8601
        incorrect_query = text("SELECT COUNT(*) FROM noticias WHERE published_at NOT LIKE '%T%'")
        correct_query = text("SELECT COUNT(*) FROM noticias WHERE published_at LIKE '%T%'")
        total_query = text("SELECT COUNT(*) FROM noticias")
        
        # Ejecutar consultas usando connection
        with engine.connect() as conn:
            incorrect_count = conn.execute(incorrect_query).scalar() or 0
            correct_count = conn.execute(correct_query).scalar() or 0
            total_count = conn.execute(total_query).scalar() or 0
        
        print(f"📈 Total de registros: {total_count}")
        print(f"✅ Formato correcto (ISO 8601): {correct_count}")
        print(f"❌ Formato incorrecto (necesita migración): {incorrect_count}")
        
        if incorrect_count > 0:
            print(f"\n📋 Ejemplos de registros que necesitan migración:")
            
            # Obtener algunos ejemplos
            sample_query = text("SELECT id, published_at FROM noticias WHERE published_at NOT LIKE '%T%' LIMIT 5")
            with engine.connect() as conn:
                result = conn.execute(sample_query)
                for row in result:
                    print(f"   ID {row[0]}: '{row[1]}'")
            
            print(f"\n💡 Ejecuta 'python update_timestamps.py' para migrar estos registros")
        else:
            print(f"\n🎉 ¡Todos los timestamps ya están en formato ISO 8601 UTC!")
            print(f"✅ No es necesario ejecutar la migración")
    
    except Exception as e:
        print(f"❌ Error ejecutando verificación: {e}")
    finally:
        engine.dispose()
    
    print("=" * 60)

if __name__ == "__main__":
    main() 
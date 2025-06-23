#!/usr/bin/env python3
"""
Migración SQLAlchemy - Grid Bot V2.0
Usa la infraestructura existente (models.py + session.py) para migrar la DB
"""

import sys
sys.path.append('.')

from sqlalchemy import inspect, text
from shared.database.session import get_db_session, engine
from shared.database.models import Base, GridBotConfig, GridBotState
from shared.services.logging_config import get_logger

logger = get_logger(__name__)

def check_table_structure():
    """Revisa la estructura actual usando SQLAlchemy"""
    try:
        inspector = inspect(engine)
        
        # Verificar si las tablas existen
        existing_tables = inspector.get_table_names()
        print('📊 TABLAS EXISTENTES:')
        for table in existing_tables:
            print(f'• {table}')
        
        # Verificar estructura de grid_bot_config
        if 'grid_bot_config' in existing_tables:
            columns = inspector.get_columns('grid_bot_config')
            print(f'\n🔍 COLUMNAS EN grid_bot_config:')
            column_names = []
            for col in columns:
                column_names.append(col['name'])
                print(f'• {col["name"]} - {col["type"]} - {"NOT NULL" if not col.get("nullable", True) else "NULL"}')
            
            # Verificar columnas V2
            v2_columns = ['stop_loss_percent', 'enable_stop_loss', 'enable_trailing_up']
            missing_columns = [col for col in v2_columns if col not in column_names]
            
            print(f'\n🎯 ANÁLISIS V2:')
            print(f'• Columnas V2 faltantes: {missing_columns if missing_columns else "Ninguna - Ya está V2.0"}')
            
            return len(missing_columns) > 0, missing_columns
        else:
            print('❌ Tabla grid_bot_config no existe')
            return True, []
            
    except Exception as e:
        print(f'❌ Error revisando estructura: {e}')
        return True, []

def migrate_with_sqlalchemy():
    """Migra usando SQLAlchemy - Crea tablas faltantes automáticamente"""
    try:
        print('\n🚀 MIGRANDO CON SQLALCHEMY')
        print('=' * 50)
        
        # 1. Crear todas las tablas definidas en models.py
        print('📋 Creando/actualizando tablas desde models.py...')
        
        # Esto crea todas las tablas que no existen, pero NO agrega columnas a tablas existentes
        Base.metadata.create_all(bind=engine)
        print('✅ Tablas base verificadas')
        
        # 2. Para columnas faltantes, necesitamos ALTER TABLE manual
        print('\n🔧 Verificando columnas V2 en tabla existente...')
        
        needs_migration, missing_columns = check_table_structure()
        
        if not missing_columns:
            print('✅ Tabla ya tiene todas las columnas V2')
            return True
        
        # 3. Agregar columnas faltantes manualmente
        print(f'📋 Agregando {len(missing_columns)} columnas V2...')
        
        with get_db_session() as db:
            for column in missing_columns:
                try:
                    if column == 'stop_loss_percent':
                        db.execute(text("""
                            ALTER TABLE grid_bot_config 
                            ADD COLUMN stop_loss_percent FLOAT DEFAULT 5.0
                        """))
                        print('✅ stop_loss_percent agregada')
                    
                    elif column == 'enable_stop_loss':
                        db.execute(text("""
                            ALTER TABLE grid_bot_config 
                            ADD COLUMN enable_stop_loss BOOLEAN DEFAULT 1
                        """))
                        print('✅ enable_stop_loss agregada')
                    
                    elif column == 'enable_trailing_up':
                        db.execute(text("""
                            ALTER TABLE grid_bot_config 
                            ADD COLUMN enable_trailing_up BOOLEAN DEFAULT 1
                        """))
                        print('✅ enable_trailing_up agregada')
                        
                except Exception as e:
                    if 'duplicate column name' in str(e):
                        print(f'ℹ️ Columna {column} ya existe')
                    else:
                        print(f'❌ Error agregando {column}: {e}')
                        raise e
            
            # 4. Actualizar registros existentes
            print('\n📋 Actualizando configuraciones existentes...')
            
            # Consultar configuraciones sin valores V2
            configs_to_update = db.execute(text("""
                SELECT id, total_capital 
                FROM grid_bot_config 
                WHERE stop_loss_percent IS NULL OR stop_loss_percent = 0
            """)).fetchall()
            
            for config in configs_to_update:
                config_id, capital = config
                
                # Asignar stop-loss inteligente basado en capital
                if capital < 50:
                    stop_loss = 3.0
                elif capital < 100:
                    stop_loss = 4.0
                elif capital < 500:
                    stop_loss = 5.0
                else:
                    stop_loss = 6.0
                
                db.execute(text("""
                    UPDATE grid_bot_config 
                    SET 
                        stop_loss_percent = :stop_loss,
                        enable_stop_loss = 1,
                        enable_trailing_up = 1
                    WHERE id = :config_id
                """), {
                    'stop_loss': stop_loss,
                    'config_id': config_id
                })
            
            db.commit()
            print(f'✅ {len(configs_to_update)} configuraciones actualizadas')
        
        return True
        
    except Exception as e:
        print(f'❌ Error en migración SQLAlchemy: {e}')
        return False

def verify_final_structure():
    """Verifica que la migración fue exitosa"""
    try:
        print('\n🔍 VERIFICACIÓN FINAL')
        print('=' * 40)
        
        with get_db_session() as db:
            # 1. Verificar estructura
            inspector = inspect(engine)
            columns = inspector.get_columns('grid_bot_config')
            column_names = [col['name'] for col in columns]
            
            v2_columns = ['stop_loss_percent', 'enable_stop_loss', 'enable_trailing_up']
            success = all(col in column_names for col in v2_columns)
            
            if success:
                print('✅ Estructura V2.0 verificada')
                
                # 2. Mostrar configuraciones existentes
                result = db.execute(text("""
                    SELECT pair, total_capital, stop_loss_percent, enable_stop_loss, enable_trailing_up, is_active
                    FROM grid_bot_config 
                    ORDER BY created_at DESC
                    LIMIT 5
                """)).fetchall()
                
                print(f'\n📊 CONFIGURACIONES EXISTENTES ({len(result)}):')
                print('-' * 80)
                print('Par       | Capital | Stop-Loss | SL_ON | TU_ON | Activa')
                print('-' * 80)
                
                for config in result:
                    pair, capital, sl_percent, sl_on, tu_on, active = config
                    print(f'{pair:8} | ${capital:6.0f} | {sl_percent:8.1f}% | {sl_on:5} | {tu_on:5} | {active}')
                
                return True
            else:
                print('❌ Faltan columnas V2')
                return False
                
    except Exception as e:
        print(f'❌ Error en verificación: {e}')
        return False

def main():
    """Función principal de migración SQLAlchemy"""
    print('🔮 MIGRACIÓN SQLALCHEMY - GRID BOT V2.0')
    print('=' * 60)
    
    try:
        # 1. Verificar estado actual
        needs_migration, missing_columns = check_table_structure()
        
        if not needs_migration:
            print('\n✅ Base de datos ya está actualizada a V2.0')
            verify_final_structure()
            return
        
        print(f'\n⚠️ Se necesita agregar columnas: {missing_columns}')
        
        # 2. Ejecutar migración automática
        success = migrate_with_sqlalchemy()
        
        if success:
            # 3. Verificar resultado
            final_success = verify_final_structure()
            
            if final_success:
                print('\n🎉 ¡MIGRACIÓN SQLALCHEMY EXITOSA!')
                print('✅ Base de datos V2.0 lista')
                print('✅ Compatibilidad con VPS mantenida')
                print('\n🚀 PRÓXIMOS PASOS:')
                print('1. Subir a VPS y ejecutar: python migrate_sqlalchemy_v2.py')
                print('2. Reiniciar servicio grid: sudo systemctl restart oraculo-grid')
                print('3. Usar /config en Telegram para probar')
            else:
                print('\n❌ Verificación final falló')
        else:
            print('\n❌ Migración falló')
            
    except Exception as e:
        print(f'❌ Error crítico: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main() 
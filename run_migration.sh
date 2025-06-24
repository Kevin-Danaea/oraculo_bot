#!/bin/bash

# Script de ejecución de migración - Análisis Enriquecido de Noticias
# ===================================================================
# 
# Este script facilita la ejecución de la migración de base de datos
# tanto en desarrollo como en producción (VPS).
#
# Uso:
#   chmod +x run_migration.sh
#   ./run_migration.sh

echo "🔧 Migración de Base de Datos - Análisis Enriquecido"
echo "=================================================="

# Verificar que Python está disponible
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python3 no está instalado o no está en el PATH"
    exit 1
fi

# Verificar que el script de migración existe
if [ ! -f "migrate_news_fields.py" ]; then
    echo "❌ Error: No se encontró el archivo migrate_news_fields.py"
    echo "   Asegúrate de ejecutar este script desde el directorio raíz del proyecto"
    exit 1
fi

# Verificar que requirements.txt existe e instalar dependencias si es necesario
if [ -f "requirements.txt" ]; then
    echo "📦 Verificando dependencias..."
    pip install -r requirements.txt > /dev/null 2>&1
fi

echo "🚀 Ejecutando migración..."
echo "========================="

# Ejecutar la migración
python3 migrate_news_fields.py

# Capturar el código de salida
exit_code=$?

echo ""
if [ $exit_code -eq 0 ]; then
    echo "✅ ¡Migración completada exitosamente!"
    echo ""
    echo "📝 Próximos pasos:"
    echo "1. Reiniciar los servicios de news:"
    echo "   sudo systemctl restart oraculo-news"
    echo ""
    echo "2. Verificar que todo funcione:"
    echo "   sudo systemctl status oraculo-news"
    echo ""
    echo "3. Eliminar los archivos de migración:"
    echo "   rm migrate_news_fields.py run_migration.sh"
    echo ""
else
    echo "❌ La migración falló con código de salida: $exit_code"
    echo "Revisa los logs para más información"
fi

exit $exit_code 
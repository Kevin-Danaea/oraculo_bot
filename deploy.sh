#!/bin/bash

# ==============================================================================
# Script de Despliegue Simplificado - Oráculo Bot
# ==============================================================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "🚀 Iniciando despliegue del Oráculo Bot..."

# Verificar archivo .env
if [ ! -f .env ]; then
    echo "❌ Error: Archivo .env no encontrado"
    echo "📝 Copia .env.example a .env y configura las variables"
    exit 1
fi

print_success "✅ Archivo .env encontrado"

# Crear directorio de logs
if [ ! -d logs ]; then
    mkdir -p logs
    print_success "✅ Directorio de logs creado"
fi

# Limpiar contenedores previos
echo "🧹 Limpiando contenedores previos..."
docker-compose down --remove-orphans

# Construir imágenes
echo "🔨 Construyendo imágenes..."
docker-compose build --no-cache

# Verificar que TA-Lib se instaló correctamente en Brain
echo "🔍 Verificando TA-Lib en Brain..."
docker-compose run --rm brain python -c "import talib; print('✅ TA-Lib version:', talib.__version__)"

if [ $? -eq 0 ]; then
    echo "✅ TA-Lib instalado correctamente"
else
    echo "❌ Error con TA-Lib"
    echo "📋 Revisando logs de construcción..."
    docker-compose logs brain
    exit 1
fi

# Levantar servicios
echo "🚀 Levantando servicios..."
docker-compose up -d

# Esperar un momento para que los servicios se inicien
echo "⏳ Esperando que los servicios se inicien..."
sleep 15

# Verificar estado de los servicios
echo "📊 Estado de los servicios:"
docker-compose ps

# Verificar logs de Brain
echo "📋 Logs del servicio Brain:"
docker-compose logs brain --tail=20

echo "✅ Despliegue completado!"
echo "🌐 Servicios disponibles:"
echo "   - Brain: http://localhost:8001"
echo "   - Grid: http://localhost:8002"
echo "   - News: http://localhost:8003"
echo "   - Hype: http://localhost:8004"
echo ""
print_status "Comandos útiles:"
echo "  docker-compose logs -f          # Ver logs en tiempo real"
echo "  docker-compose down             # Detener servicios"
echo "  docker-compose restart brain    # Reiniciar brain"
echo "  docker-compose ps               # Ver estado de servicios" 
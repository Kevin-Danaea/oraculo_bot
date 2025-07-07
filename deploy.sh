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

echo "🚀 Despliegue Simplificado - Oráculo Bot"
echo ""

# Verificar archivo .env
if [ ! -f .env ]; then
    print_error "Archivo .env no encontrado"
    print_status "Copiando .env.example a .env..."
    cp .env.example .env
    print_warning "Por favor edita el archivo .env con tus credenciales antes de continuar"
    exit 1
fi

print_success "✅ Archivo .env encontrado"

# Crear directorio de logs
if [ ! -d logs ]; then
    mkdir -p logs
    print_success "✅ Directorio de logs creado"
fi

# Limpiar contenedores anteriores
print_status "Limpiando contenedores anteriores..."
docker-compose down 2>/dev/null || true

# Construir y ejecutar
print_status "Construyendo y ejecutando servicios..."
docker-compose up --build -d

# Esperar a que los servicios se inicien
print_status "Esperando a que los servicios se inicien..."
sleep 15

# Verificar estado
print_status "Verificando estado de los servicios..."
docker-compose ps

# Verificar TA-Lib
print_status "Verificando TA-Lib..."
if docker-compose exec brain python -c "import talib; print('✅ TA-Lib funciona')" 2>/dev/null; then
    print_success "✅ TA-Lib instalado correctamente"
else
    print_warning "⚠️  TA-Lib no funciona, revisando logs..."
    docker-compose logs brain | tail -20
fi

echo ""
print_success "✅ Despliegue completado"
echo ""
print_status "Servicios disponibles:"
echo "  📰 News Service: http://localhost:8000"
echo "  🧠 Brain Service: http://localhost:8001"
echo "  📊 Grid Service: http://localhost:8002"
echo "  🔥 Hype Service: http://localhost:8003"
echo ""
print_status "Comandos útiles:"
echo "  docker-compose logs -f          # Ver logs en tiempo real"
echo "  docker-compose down             # Detener servicios"
echo "  docker-compose restart brain    # Reiniciar brain"
echo "  docker-compose ps               # Ver estado de servicios" 
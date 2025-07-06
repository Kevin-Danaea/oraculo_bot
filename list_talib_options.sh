#!/bin/bash

# ==============================================================================
# Script para Listar Opciones de TA-Lib Disponibles
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

echo "📋 Opciones de TA-Lib Disponibles"
echo "=================================="
echo ""

# Verificar archivos de Dockerfile
print_status "Dockerfiles disponibles:"

if [ -f "services/brain/Dockerfile" ]; then
    print_success "✅ services/brain/Dockerfile (original)"
else
    print_error "❌ services/brain/Dockerfile (original) - NO ENCONTRADO"
fi

if [ -f "services/brain/Dockerfile.conda" ]; then
    print_success "✅ services/brain/Dockerfile.conda (con conda)"
else
    print_error "❌ services/brain/Dockerfile.conda (con conda) - NO ENCONTRADO"
fi

if [ -f "services/brain/Dockerfile.no-conda" ]; then
    print_success "✅ services/brain/Dockerfile.no-conda (sin conda)"
else
    print_error "❌ services/brain/Dockerfile.no-conda (sin conda) - NO ENCONTRADO"
fi

if [ -f "services/brain/Dockerfile.alternative" ]; then
    print_success "✅ services/brain/Dockerfile.alternative (alternativo)"
else
    print_error "❌ services/brain/Dockerfile.alternative (alternativo) - NO ENCONTRADO"
fi

echo ""

# Verificar archivos de requirements
print_status "Archivos de requirements disponibles:"

if [ -f "services/brain/requirements.txt" ]; then
    print_success "✅ services/brain/requirements.txt (original)"
else
    print_error "❌ services/brain/requirements.txt (original) - NO ENCONTRADO"
fi

if [ -f "services/brain/requirements.wheel.txt" ]; then
    print_success "✅ services/brain/requirements.wheel.txt (wheel precompilado)"
else
    print_error "❌ services/brain/requirements.wheel.txt (wheel precompilado) - NO ENCONTRADO"
fi

if [ -f "services/brain/requirements.talib_test.txt" ]; then
    print_success "✅ services/brain/requirements.talib_test.txt (sin versión específica)"
else
    print_error "❌ services/brain/requirements.talib_test.txt (sin versión específica) - NO ENCONTRADO"
fi

echo ""

# Verificar scripts
print_status "Scripts disponibles:"

if [ -f "fix_talib.sh" ]; then
    print_success "✅ fix_talib.sh (reparación automática)"
else
    print_error "❌ fix_talib.sh (reparación automática) - NO ENCONTRADO"
fi

if [ -f "deploy_ubuntu_no_conda.sh" ]; then
    print_success "✅ deploy_ubuntu_no_conda.sh (Ubuntu sin conda)"
else
    print_error "❌ deploy_ubuntu_no_conda.sh (Ubuntu sin conda) - NO ENCONTRADO"
fi

if [ -f "install_talib_manual.sh" ]; then
    print_success "✅ install_talib_manual.sh (instalación manual)"
else
    print_error "❌ install_talib_manual.sh (instalación manual) - NO ENCONTRADO"
fi

if [ -f "verify_talib.sh" ]; then
    print_success "✅ verify_talib.sh (verificación TA-Lib)"
else
    print_error "❌ verify_talib.sh (verificación TA-Lib) - NO ENCONTRADO"
fi

echo ""

print_status "Comandos para usar cada opción:"

echo ""
echo "🔧 Opción 1: Dockerfile con Conda (RECOMENDADO)"
echo "   cp services/brain/Dockerfile.conda services/brain/Dockerfile"
echo "   docker-compose build --no-cache brain"

echo ""
echo "🔧 Opción 2: Dockerfile sin Conda"
echo "   cp services/brain/Dockerfile.no-conda services/brain/Dockerfile"
echo "   docker-compose build --no-cache brain"

echo ""
echo "🔧 Opción 3: Wheel Precompilado"
echo "   cp services/brain/requirements.wheel.txt services/brain/requirements.txt"
echo "   docker-compose build --no-cache brain"

echo ""
echo "🔧 Opción 4: Sin Versión Específica"
echo "   cp services/brain/requirements.talib_test.txt services/brain/requirements.txt"
echo "   docker-compose build --no-cache brain"

echo ""
echo "🔧 Opción 5: Instalación Manual"
echo "   ./install_talib_manual.sh"

echo ""
echo "🔧 Opción 6: Script Automático"
echo "   ./fix_talib.sh"

echo ""
echo "🔧 Opción 7: Ubuntu Sin Conda"
echo "   ./deploy_ubuntu_no_conda.sh"

echo ""
print_status "Verificación después de cualquier opción:"
echo "   ./verify_talib.sh"
echo "   docker-compose exec brain python -c 'import talib; print(talib.__version__)'"

echo ""
print_success "✅ Listado completado"
print_status "💡 Recomendación: Probar Opción 1 (Conda) primero, luego Opción 2 (sin conda)" 
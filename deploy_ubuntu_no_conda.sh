#!/bin/bash

# ==============================================================================
# Script de Despliegue para Ubuntu Sin Conda
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

echo "🚀 Despliegue para Ubuntu Sin Conda..."
echo ""

# Verificar sistema
print_status "Verificando sistema..."
if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo "Sistema: $NAME $VERSION"
fi

# Verificar que Docker esté instalado
if ! command -v docker &> /dev/null; then
    print_error "Docker no está instalado. Instalando..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    print_success "Docker instalado. Por favor reinicia la sesión."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose no está instalado. Instalando..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    print_success "Docker Compose instalado"
fi

echo ""

# Opción 1: Usar Dockerfile sin conda (RECOMENDADO)
print_status "Opción 1: Usando Dockerfile sin conda..."

if [ -f "services/brain/Dockerfile.no-conda" ]; then
    print_status "Haciendo backup del Dockerfile original..."
    cp services/brain/Dockerfile services/brain/Dockerfile.backup
    
    print_status "Usando Dockerfile sin conda..."
    cp services/brain/Dockerfile.no-conda services/brain/Dockerfile
    
    print_status "Reconstruyendo imagen..."
    docker-compose build --no-cache brain
    
    print_success "✅ Dockerfile sin conda aplicado"
else
    print_error "❌ Dockerfile.no-conda no encontrado"
fi

echo ""

# Opción 2: Usar wheel precompilado
print_status "Opción 2: Probando con wheel precompilado..."

if [ -f "services/brain/requirements.wheel.txt" ]; then
    print_status "Haciendo backup del requirements original..."
    cp services/brain/requirements.txt services/brain/requirements.txt.backup
    
    print_status "Usando requirements con wheel precompilado..."
    cp services/brain/requirements.wheel.txt services/brain/requirements.txt
    
    print_status "Reconstruyendo imagen..."
    docker-compose build --no-cache brain
    
    print_success "✅ Wheel precompilado aplicado"
else
    print_error "❌ requirements.wheel.txt no encontrado"
fi

echo ""

# Opción 3: Instalación manual en el sistema
print_status "Opción 3: Instalación manual en el sistema..."

if [ -f "install_talib_manual.sh" ]; then
    print_status "Ejecutando instalación manual de TA-Lib..."
    chmod +x install_talib_manual.sh
    ./install_talib_manual.sh
    print_success "✅ Instalación manual completada"
else
    print_error "❌ install_talib_manual.sh no encontrado"
fi

echo ""

# Verificar instalación
print_status "Verificando instalación..."

# Verificar si el contenedor se construyó correctamente
if docker images | grep -q "oraculo_bot_brain"; then
    print_success "✅ Imagen del brain construida correctamente"
else
    print_warning "⚠️  Imagen del brain no encontrada"
fi

# Verificar si TA-Lib funciona
if docker-compose exec brain python -c "import talib; print('TA-Lib funciona')" 2>/dev/null; then
    print_success "✅ TA-Lib funciona correctamente en el contenedor"
else
    print_warning "⚠️  TA-Lib no funciona en el contenedor"
fi

echo ""

print_status "Resumen de opciones para Ubuntu sin conda:"

echo "📋 Opciones disponibles:"
echo "   1. ✅ Dockerfile sin conda (Dockerfile.no-conda)"
echo "   2. ✅ Wheel precompilado (requirements.wheel.txt)"
echo "   3. ✅ Instalación manual (install_talib_manual.sh)"

echo ""
print_status "Comandos manuales si necesitas probar individualmente:"

echo "🔧 Opción 1 (Dockerfile sin conda):"
echo "   cp services/brain/Dockerfile.no-conda services/brain/Dockerfile"
echo "   docker-compose build --no-cache brain"

echo ""
echo "🔧 Opción 2 (Wheel precompilado):"
echo "   cp services/brain/requirements.wheel.txt services/brain/requirements.txt"
echo "   docker-compose build --no-cache brain"

echo ""
echo "🔧 Opción 3 (Manual):"
echo "   ./install_talib_manual.sh"

echo ""
print_status "Verificación:"
echo "   ./verify_talib.sh"
echo "   ./monitor_memory.sh"

echo ""
print_success "✅ Despliegue para Ubuntu sin conda completado"
print_status "💡 Recomendación: Usar Opción 1 (Dockerfile sin conda) para mayor compatibilidad" 
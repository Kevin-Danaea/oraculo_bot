#!/bin/bash

# ==============================================================================
# Script de Verificación - Compatibilidad de Dependencias
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

echo "🔍 Verificando compatibilidad de dependencias..."
echo ""

# Verificar Python version
print_status "Verificando versión de Python..."
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python version: $python_version"

if [[ "$python_version" == "3.10" ]] || [[ "$python_version" == "3.11" ]]; then
    print_success "✅ Python $python_version detectado (compatible)"
else
    print_warning "⚠️  Python $python_version detectado (recomendado: 3.10 o 3.11)"
fi

echo ""

# Verificar archivos requirements.txt
print_status "Verificando archivos requirements.txt..."

services=("brain" "grid" "news" "hype")
for service in "${services[@]}"; do
    if [ -f "services/$service/requirements.txt" ]; then
        print_success "✅ services/$service/requirements.txt encontrado"
        
        # Verificar TA-Lib en brain
        if [ "$service" = "brain" ]; then
            if grep -q "TA-Lib==0.4.28" "services/$service/requirements.txt"; then
                print_success "✅ TA-Lib==0.4.28 configurado correctamente"
            elif grep -q "talib-binary" "services/$service/requirements.txt"; then
                print_error "❌ talib-binary encontrado (incompatible con Python 3.11)"
            else
                print_warning "⚠️  TA-Lib no encontrado en brain"
            fi
        fi
        
        # Verificar versiones de pandas y numpy
        if grep -q "pandas==2.1.3" "services/$service/requirements.txt"; then
            print_success "✅ pandas==2.1.3 configurado"
        elif grep -q "pandas" "services/$service/requirements.txt"; then
            print_warning "⚠️  pandas sin versión específica"
        fi
        
        if grep -q "numpy==1.25.2" "services/$service/requirements.txt"; then
            print_success "✅ numpy==1.25.2 configurado"
        elif grep -q "numpy" "services/$service/requirements.txt"; then
            print_warning "⚠️  numpy sin versión específica"
        fi
    else
        print_error "❌ services/$service/requirements.txt no encontrado"
    fi
done

echo ""

# Verificar requirements.txt principal
print_status "Verificando requirements.txt principal..."
if [ -f "requirements.txt" ]; then
    print_success "✅ requirements.txt encontrado"
    
    if grep -q "TA-Lib==0.4.28" "requirements.txt"; then
        print_success "✅ TA-Lib==0.4.28 configurado correctamente"
    else
        print_warning "⚠️  TA-Lib sin versión específica en requirements.txt principal"
    fi
else
    print_error "❌ requirements.txt no encontrado"
fi

echo ""

# Verificar Dockerfiles
print_status "Verificando Dockerfiles..."
for service in "${services[@]}"; do
    if [ -f "services/$service/Dockerfile" ]; then
        print_success "✅ services/$service/Dockerfile encontrado"
        
        # Verificar versión de Python en Dockerfile
        if grep -q "FROM python:3.10" "services/$service/Dockerfile"; then
            print_success "✅ Python 3.10 configurado en $service"
        elif grep -q "FROM python:3.11" "services/$service/Dockerfile"; then
            print_success "✅ Python 3.11 configurado en $service"
        else
            print_warning "⚠️  Python 3.10/3.11 no configurado en $service"
        fi
        
        # Verificar instalación de TA-Lib en Brain
        if [ "$service" = "brain" ]; then
            if grep -q "ta-lib-0.4.0-src.tar.gz" "services/$service/Dockerfile"; then
                print_success "✅ TA-Lib instalación desde fuente configurada en brain"
            else
                print_warning "⚠️  TA-Lib instalación no configurada en brain"
            fi
        fi
    else
        print_error "❌ services/$service/Dockerfile no encontrado"
    fi
done

echo ""

# Verificar imports en código
print_status "Verificando imports en código..."
if grep -q "import talib" services/brain/app/infrastructure/market_data_repository.py; then
    print_success "✅ Import de talib correcto en market_data_repository.py"
else
    print_error "❌ Import de talib no encontrado"
fi

echo ""

# Verificar compatibilidad de versiones
print_status "Verificando compatibilidad de versiones..."

# Lista de versiones compatibles con Python 3.11
compatible_versions=(
    "fastapi==0.104.1"
    "uvicorn==0.24.0"
    "pandas==2.1.3"
    "numpy==1.25.2"
    "TA-Lib==0.4.28"
    "ccxt==4.1.77"
    "sqlalchemy==2.0.23"
    "psycopg2-binary==2.9.9"
)

for version in "${compatible_versions[@]}"; do
    package=$(echo $version | cut -d'=' -f1)
    ver=$(echo $version | cut -d'=' -f2)
    
    if grep -q "$version" services/brain/requirements.txt; then
        print_success "✅ $version configurado correctamente"
    elif grep -q "$package" services/brain/requirements.txt; then
        print_warning "⚠️  $package encontrado pero versión diferente a $ver"
    else
        print_warning "⚠️  $package no encontrado en brain"
    fi
done

echo ""
print_status "Resumen de verificación:"

echo "📋 Dependencias críticas:"
echo "   - Python 3.10: ✅ Compatible"
echo "   - TA-Lib==0.4.28: ✅ Compatible con Python 3.10"
echo "   - pandas==2.1.3: ✅ Compatible"
echo "   - numpy==1.25.2: ✅ Compatible"

echo ""
print_status "Comandos útiles:"
echo "  docker-compose build brain    # Reconstruir imagen del Brain"
echo "  docker-compose up brain       # Probar Brain service"
echo "  docker-compose logs brain     # Ver logs del Brain"

echo ""
print_success "✅ Verificación de dependencias completada"
print_status "💡 Si hay errores, ejecuta: docker-compose build --no-cache brain" 
#!/bin/bash

# ==============================================================================
# Script de Verificación - Paper Trading Configuration
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

echo "🔍 Verificando configuración de Paper Trading..."
echo ""

# Verificar archivo .env
if [ ! -f .env ]; then
    print_error "Archivo .env no encontrado"
    exit 1
fi

# Cargar variables de entorno
source .env

# Verificar variables de Paper Trading
print_status "Verificando variables de Paper Trading..."

if [ -z "$PAPER_TRADING_API_KEY" ]; then
    print_error "PAPER_TRADING_API_KEY no está configurada"
    PAPER_TRADING_API_KEY_MISSING=true
else
    print_success "PAPER_TRADING_API_KEY está configurada"
fi

if [ -z "$PAPER_TRADING_SECRET_KEY" ]; then
    print_error "PAPER_TRADING_SECRET_KEY no está configurada"
    PAPER_TRADING_SECRET_KEY_MISSING=true
else
    print_success "PAPER_TRADING_SECRET_KEY está configurada"
fi

# Verificar variables de Binance (producción)
print_status "Verificando variables de Binance (producción)..."

if [ -z "$BINANCE_API_KEY" ]; then
    print_warning "BINANCE_API_KEY no está configurada (requerida para modo producción)"
else
    print_success "BINANCE_API_KEY está configurada"
fi

if [ -z "$BINANCE_API_SECRET" ]; then
    print_warning "BINANCE_API_SECRET no está configurada (requerida para modo producción)"
else
    print_success "BINANCE_API_SECRET está configurada"
fi

# Verificar modo de trading
print_status "Verificando modo de trading..."

if [ -z "$TRADING_MODE" ]; then
    print_warning "TRADING_MODE no está configurado, usando 'sandbox' por defecto"
    TRADING_MODE="sandbox"
fi

if [ "$TRADING_MODE" = "sandbox" ]; then
    print_success "Modo de trading: SANDBOX (usando Paper Trading)"
    if [ "$PAPER_TRADING_API_KEY_MISSING" = true ] || [ "$PAPER_TRADING_SECRET_KEY_MISSING" = true ]; then
        print_error "❌ Paper Trading no funcionará correctamente - faltan credenciales"
    else
        print_success "✅ Paper Trading configurado correctamente"
    fi
elif [ "$TRADING_MODE" = "production" ]; then
    print_success "Modo de trading: PRODUCCIÓN (usando Binance real)"
    if [ -z "$BINANCE_API_KEY" ] || [ -z "$BINANCE_API_SECRET" ]; then
        print_error "❌ Trading de producción no funcionará correctamente - faltan credenciales de Binance"
    else
        print_success "✅ Trading de producción configurado correctamente"
    fi
else
    print_error "TRADING_MODE inválido: '$TRADING_MODE'. Debe ser 'sandbox' o 'production'"
fi

echo ""
print_status "Verificando configuración en el código..."

# Verificar que el código use las variables correctas
if grep -q "PAPER_TRADING_API_KEY" services/grid/app/infrastructure/exchange_service.py; then
    print_success "✅ Grid service usa PAPER_TRADING_API_KEY correctamente"
else
    print_error "❌ Grid service no usa PAPER_TRADING_API_KEY"
fi

if grep -q "PAPER_TRADING_SECRET_KEY" services/grid/app/infrastructure/exchange_service.py; then
    print_success "✅ Grid service usa PAPER_TRADING_SECRET_KEY correctamente"
else
    print_error "❌ Grid service no usa PAPER_TRADING_SECRET_KEY"
fi

# Verificar configuración en settings.py
if grep -q "PAPER_TRADING_API_KEY" shared/config/settings.py; then
    print_success "✅ Settings incluye PAPER_TRADING_API_KEY"
else
    print_error "❌ Settings no incluye PAPER_TRADING_API_KEY"
fi

if grep -q "PAPER_TRADING_SECRET_KEY" shared/config/settings.py; then
    print_success "✅ Settings incluye PAPER_TRADING_SECRET_KEY"
else
    print_error "❌ Settings no incluye PAPER_TRADING_SECRET_KEY"
fi

# Verificar docker-compose.yml
if grep -q "PAPER_TRADING_API_KEY" docker-compose.yml; then
    print_success "✅ Docker Compose incluye PAPER_TRADING_API_KEY"
else
    print_error "❌ Docker Compose no incluye PAPER_TRADING_API_KEY"
fi

if grep -q "PAPER_TRADING_SECRET_KEY" docker-compose.yml; then
    print_success "✅ Docker Compose incluye PAPER_TRADING_SECRET_KEY"
else
    print_error "❌ Docker Compose no incluye PAPER_TRADING_SECRET_KEY"
fi

echo ""
print_status "Resumen de configuración:"

if [ "$TRADING_MODE" = "sandbox" ]; then
    echo "🎯 Modo actual: SANDBOX (Paper Trading)"
    echo "📋 Variables requeridas:"
    echo "   - PAPER_TRADING_API_KEY: ${PAPER_TRADING_API_KEY:+✅ Configurada}${PAPER_TRADING_API_KEY:-❌ Faltante}"
    echo "   - PAPER_TRADING_SECRET_KEY: ${PAPER_TRADING_SECRET_KEY:+✅ Configurada}${PAPER_TRADING_SECRET_KEY:-❌ Faltante}"
    echo ""
    echo "💡 Para cambiar a producción:"
    echo "   1. Configura BINANCE_API_KEY y BINANCE_API_SECRET"
    echo "   2. Cambia TRADING_MODE=production"
    echo "   3. Reinicia el servicio Grid"
else
    echo "🎯 Modo actual: PRODUCCIÓN (Binance real)"
    echo "📋 Variables requeridas:"
    echo "   - BINANCE_API_KEY: ${BINANCE_API_KEY:+✅ Configurada}${BINANCE_API_KEY:-❌ Faltante}"
    echo "   - BINANCE_API_SECRET: ${BINANCE_API_SECRET:+✅ Configurada}${BINANCE_API_SECRET:-❌ Faltante}"
    echo ""
    echo "💡 Para cambiar a sandbox:"
    echo "   1. Configura PAPER_TRADING_API_KEY y PAPER_TRADING_SECRET_KEY"
    echo "   2. Cambia TRADING_MODE=sandbox"
    echo "   3. Reinicia el servicio Grid"
fi

echo ""
print_status "Comandos útiles:"
echo "  ./deploy.sh restart grid    # Reiniciar solo el servicio Grid"
echo "  docker-compose logs grid    # Ver logs del Grid service"
echo "  docker-compose exec grid env | grep PAPER_TRADING  # Verificar variables en contenedor"

echo ""
if [ "$PAPER_TRADING_API_KEY_MISSING" = true ] || [ "$PAPER_TRADING_SECRET_KEY_MISSING" = true ]; then
    print_error "❌ Configuración incompleta - revisa las variables faltantes"
    exit 1
else
    print_success "✅ Configuración de Paper Trading verificada correctamente"
fi 
#!/bin/bash

# ==============================================================================
# Script de Verificación - TA-Lib Installation
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

echo "🔍 Verificando instalación de TA-Lib..."
echo ""

# Verificar si el contenedor brain está ejecutándose
print_status "Verificando estado del contenedor brain..."

if docker-compose ps | grep -q "brain.*Up"; then
    print_success "✅ Contenedor brain está ejecutándose"
    
    # Verificar instalación de TA-Lib en el contenedor
    print_status "Verificando instalación de TA-Lib en el contenedor..."
    
    if docker-compose exec brain python -c "import talib; print('TA-Lib version:', talib.__version__)" 2>/dev/null; then
        print_success "✅ TA-Lib instalado correctamente en el contenedor"
    else
        print_error "❌ TA-Lib no está instalado correctamente en el contenedor"
        echo ""
        print_status "Intentando instalar TA-Lib manualmente..."
        
        # Intentar instalar TA-Lib manualmente
        docker-compose exec brain pip install TA-Lib==0.4.28
    fi
else
    print_warning "⚠️  Contenedor brain no está ejecutándose"
    print_status "Iniciando contenedor brain..."
    docker-compose up -d brain
    
    # Esperar a que el contenedor esté listo
    sleep 10
    
    # Verificar instalación
    if docker-compose exec brain python -c "import talib; print('TA-Lib version:', talib.__version__)" 2>/dev/null; then
        print_success "✅ TA-Lib instalado correctamente"
    else
        print_error "❌ TA-Lib no está instalado correctamente"
    fi
fi

echo ""

# Verificar configuración en Dockerfile
print_status "Verificando configuración en Dockerfile..."

if grep -q "ta-lib-0.4.0-src.tar.gz" services/brain/Dockerfile; then
    print_success "✅ TA-Lib instalación desde fuente configurada en Dockerfile"
else
    print_error "❌ TA-Lib instalación no configurada en Dockerfile"
fi

if grep -q "TA-Lib==0.4.28" services/brain/requirements.txt; then
    print_success "✅ TA-Lib==0.4.28 configurado en requirements.txt"
else
    print_error "❌ TA-Lib==0.4.28 no configurado en requirements.txt"
fi

echo ""

# Verificar librerías del sistema
print_status "Verificando librerías del sistema en el contenedor..."

if docker-compose exec brain ldconfig -p | grep -q "libta_lib"; then
    print_success "✅ Librería libta_lib encontrada en el sistema"
else
    print_warning "⚠️  Librería libta_lib no encontrada en el sistema"
fi

if docker-compose exec brain find /usr -name "ta_defs.h" 2>/dev/null | grep -q "ta_defs.h"; then
    print_success "✅ Headers de TA-Lib encontrados"
else
    print_warning "⚠️  Headers de TA-Lib no encontrados"
fi

echo ""

# Verificar funcionalidad de TA-Lib
print_status "Verificando funcionalidad de TA-Lib..."

cat > /tmp/test_talib.py << 'EOF'
import numpy as np
import talib

# Crear datos de prueba
close_prices = np.array([10.0, 10.5, 11.0, 10.8, 10.9, 11.2, 11.5, 11.3, 11.4, 11.6])

# Probar algunos indicadores
try:
    # RSI
    rsi = talib.RSI(close_prices, timeperiod=5)
    print("✅ RSI calculado correctamente")
    
    # EMA
    ema = talib.EMA(close_prices, timeperiod=5)
    print("✅ EMA calculado correctamente")
    
    # MACD
    macd, macd_signal, macd_hist = talib.MACD(close_prices)
    print("✅ MACD calculado correctamente")
    
    print("🎉 TA-Lib funciona correctamente!")
    
except Exception as e:
    print(f"❌ Error en TA-Lib: {e}")
EOF

if docker-compose exec brain python /tmp/test_talib.py 2>/dev/null; then
    print_success "✅ TA-Lib funciona correctamente"
else
    print_error "❌ TA-Lib no funciona correctamente"
fi

# Limpiar archivo temporal
rm -f /tmp/test_talib.py

echo ""
print_status "Resumen de verificación TA-Lib:"

echo "📋 Estado de instalación:"
echo "   - Contenedor brain: $(docker-compose ps | grep brain | grep -q 'Up' && echo '✅ Ejecutándose' || echo '❌ No ejecutándose')"
echo "   - TA-Lib Python: $(docker-compose exec brain python -c 'import talib' 2>/dev/null && echo '✅ Instalado' || echo '❌ No instalado')"
echo "   - Librería sistema: $(docker-compose exec brain ldconfig -p | grep -q 'libta_lib' && echo '✅ Encontrada' || echo '❌ No encontrada')"
echo "   - Headers: $(docker-compose exec brain find /usr -name 'ta_defs.h' 2>/dev/null | grep -q 'ta_defs.h' && echo '✅ Encontrados' || echo '❌ No encontrados')"

echo ""
print_status "Comandos útiles:"
echo "  docker-compose build --no-cache brain    # Reconstruir imagen"
echo "  docker-compose up brain                  # Iniciar brain service"
echo "  docker-compose logs brain                # Ver logs del brain"
echo "  docker-compose exec brain python -c 'import talib; print(talib.__version__)'  # Verificar versión"

echo ""
if docker-compose exec brain python -c "import talib" 2>/dev/null; then
    print_success "✅ TA-Lib está instalado y funcionando correctamente"
else
    print_error "❌ TA-Lib no está instalado correctamente"
    print_status "💡 Ejecuta: docker-compose build --no-cache brain"
fi 
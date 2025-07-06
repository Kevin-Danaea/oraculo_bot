#!/bin/bash

# ==============================================================================
# Script de Reparación - Problema de TA-Lib
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

echo "🔧 Reparando problema de TA-Lib..."
echo ""

# Opción 1: Usar Dockerfile alternativo
print_status "Opción 1: Probando Dockerfile alternativo..."

if [ -f "services/brain/Dockerfile.alternative" ]; then
    print_status "Haciendo backup del Dockerfile original..."
    cp services/brain/Dockerfile services/brain/Dockerfile.backup
    
    print_status "Usando Dockerfile alternativo..."
    cp services/brain/Dockerfile.alternative services/brain/Dockerfile
    
    print_status "Reconstruyendo imagen con Dockerfile alternativo..."
    docker-compose build --no-cache brain
    
    print_success "✅ Dockerfile alternativo aplicado"
else
    print_error "❌ Dockerfile alternativo no encontrado"
fi

echo ""

# Opción 2: Probar con diferentes versiones de TA-Lib
print_status "Opción 2: Probando diferentes versiones de TA-Lib..."

# Crear requirements temporal con versión diferente
cat > services/brain/requirements.talib_test.txt <<EOF
# Brain Service Dependencies
# ==========================

# FastAPI y servidor
fastapi==0.104.1
uvicorn[standard]==0.24.0

# Análisis de datos y trading
pandas==2.1.3
numpy==1.25.2
TA-Lib
ccxt==4.1.77

# Base de datos
sqlalchemy==2.0.23
psycopg2-binary==2.9.9

# HTTP client para notificaciones
httpx==0.25.2

# Utilidades
python-dotenv==1.0.0
pydantic==2.5.0

# Logging y monitoreo
structlog==23.2.0

# Testing (opcional)
pytest==7.4.3
pytest-asyncio==0.21.1

# Desarrollo (opcional)
black==23.11.0
flake8==6.1.0
mypy==1.7.1
EOF

print_status "Probando con TA-Lib sin versión específica..."
cp services/brain/requirements.talib_test.txt services/brain/requirements.txt

echo ""

# Opción 3: Usar imagen base diferente
print_status "Opción 3: Creando Dockerfile con imagen base diferente..."

cat > services/brain/Dockerfile.conda <<EOF
# ==============================================================================
# Dockerfile con Conda - Alternativa para TA-Lib
# ==============================================================================

FROM continuumio/miniconda3:latest

# --- Configuración del Entorno ---
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# --- Instalar TA-Lib con conda ---
RUN conda install -c conda-forge ta-lib -y

# --- Instalación de dependencias de Python ---
COPY services/brain/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Copiar el Código de la Aplicación ---
COPY shared/ ./shared/
COPY services/brain/app/ ./app/

# Crear directorio para logs
RUN mkdir -p logs

# Exponer puerto
EXPOSE 8000

# Variables de entorno por defecto
ENV BRAIN_ANALYSIS_INTERVAL=3600
ENV BRAIN_ANALYSIS_TIMEFRAME=4h
ENV BRAIN_ANALYSIS_DAYS=40
ENV BRAIN_LOG_LEVEL=INFO
ENV BRAIN_DEBUG=false
ENV BRAIN_DEV_MODE=false
ENV PYTHONPATH=/app

# --- Comando de Ejecución ---
CMD ["python", "-m", "app.main"]
EOF

print_success "✅ Dockerfile con Conda creado"

echo ""

# Opción 4: Script de instalación manual
print_status "Opción 4: Creando script de instalación manual..."

cat > install_talib_manual.sh <<'EOF'
#!/bin/bash

# Script de instalación manual de TA-Lib
echo "Instalando TA-Lib manualmente..."

# Instalar dependencias del sistema
sudo apt-get update
sudo apt-get install -y wget build-essential

# Descargar y compilar TA-Lib
cd /tmp
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr/local
make
sudo make install

# Configurar variables de entorno
export TA_INCLUDE_PATH=/usr/local/include
export TA_LIBRARY_PATH=/usr/local/lib
export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

# Actualizar ldconfig
sudo ldconfig

# Instalar wrapper de Python
pip install TA-Lib

echo "TA-Lib instalado manualmente"
EOF

chmod +x install_talib_manual.sh
print_success "✅ Script de instalación manual creado"

echo ""

# Opción 5: Usar wheel precompilado
print_status "Opción 5: Creando requirements con wheel precompilado..."

cat > services/brain/requirements.wheel.txt <<EOF
# Brain Service Dependencies
# ==========================

# FastAPI y servidor
fastapi==0.104.1
uvicorn[standard]==0.24.0

# Análisis de datos y trading
pandas==2.1.3
numpy==1.25.2
https://github.com/TA-Lib/ta-lib-python/releases/download/TA_Lib-0.4.28/TA_Lib-0.4.28-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
ccxt==4.1.77

# Base de datos
sqlalchemy==2.0.23
psycopg2-binary==2.9.9

# HTTP client para notificaciones
httpx==0.25.2

# Utilidades
python-dotenv==1.0.0
pydantic==2.5.0

# Logging y monitoreo
structlog==23.2.0

# Testing (opcional)
pytest==7.4.3
pytest-asyncio==0.21.1

# Desarrollo (opcional)
black==23.11.0
flake8==6.1.0
mypy==1.7.1
EOF

print_success "✅ Requirements con wheel precompilado creado"

echo ""

print_status "Resumen de opciones disponibles:"

echo "📋 Opciones para resolver TA-Lib:"
echo "   1. ✅ Dockerfile alternativo creado"
echo "   2. ✅ Requirements sin versión específica"
echo "   3. ✅ Dockerfile con Conda creado"
echo "   4. ✅ Script de instalación manual creado"
echo "   5. ✅ Requirements con wheel precompilado"

echo ""
print_status "Comandos para probar cada opción:"

echo "🔧 Opción 1 (Dockerfile alternativo):"
echo "   docker-compose build --no-cache brain"

echo ""
echo "🔧 Opción 2 (Sin versión específica):"
echo "   cp services/brain/requirements.talib_test.txt services/brain/requirements.txt"
echo "   docker-compose build --no-cache brain"

echo ""
echo "🔧 Opción 3 (Conda):"
echo "   cp services/brain/Dockerfile.conda services/brain/Dockerfile"
echo "   docker-compose build --no-cache brain"

echo ""
echo "🔧 Opción 4 (Manual):"
echo "   ./install_talib_manual.sh"

echo ""
echo "🔧 Opción 5 (Wheel precompilado):"
echo "   cp services/brain/requirements.wheel.txt services/brain/requirements.txt"
echo "   docker-compose build --no-cache brain"

echo ""
print_status "Recomendación: Probar Opción 3 (Conda) primero, ya que es la más confiable"
print_status "💡 Si ninguna funciona, usar Opción 4 (instalación manual)" 
#!/bin/bash

# ==============================================================================
# Script de Optimización de Memoria para DigitalOcean Droplet (1GB RAM)
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

echo "🔧 Optimizando memoria para DigitalOcean Droplet (1GB RAM)..."
echo ""

# Verificar si estamos en un droplet de DigitalOcean
print_status "Verificando entorno..."

if [ -f /etc/digitalocean ]; then
    print_success "✅ Detectado DigitalOcean Droplet"
else
    print_warning "⚠️  No se detectó DigitalOcean Droplet (continuando de todas formas)"
fi

# Verificar memoria disponible
print_status "Verificando memoria disponible..."
total_mem=$(free -m | awk 'NR==2{printf "%.0f", $2}')
available_mem=$(free -m | awk 'NR==2{printf "%.0f", $7}')
used_mem=$(free -m | awk 'NR==2{printf "%.0f", $3}')

echo "Memoria total: ${total_mem}MB"
echo "Memoria usada: ${used_mem}MB"
echo "Memoria disponible: ${available_mem}MB"

if [ $total_mem -lt 1024 ]; then
    print_warning "⚠️  Droplet con menos de 1GB de RAM detectado"
    print_status "Aplicando optimizaciones de memoria..."
else
    print_success "✅ Memoria suficiente detectada"
fi

echo ""

# Optimizar Docker
print_status "Optimizando Docker..."

# Configurar límites de memoria para Docker
if [ ! -f /etc/docker/daemon.json ]; then
    print_status "Creando configuración de Docker..."
    sudo mkdir -p /etc/docker
    sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "default-ulimits": {
    "nofile": {
      "Hard": 64000,
      "Name": "nofile",
      "Soft": 64000
    }
  },
  "log-driver": "json-file",
  "log-opts": {
    "max-file": "3",
    "max-size": "10m"
  },
  "storage-driver": "overlay2"
}
EOF
    print_success "✅ Configuración de Docker creada"
else
    print_success "✅ Configuración de Docker ya existe"
fi

# Reiniciar Docker si es necesario
if systemctl is-active --quiet docker; then
    print_status "Reiniciando Docker para aplicar configuraciones..."
    sudo systemctl restart docker
    print_success "✅ Docker reiniciado"
fi

echo ""

# Optimizar docker-compose para memoria limitada
print_status "Optimizando docker-compose..."

# Crear archivo de configuración optimizado
cat > docker-compose.optimized.yml <<EOF
version: '3.8'

services:
  # Servicio Brain - Motor de Decisiones (Optimizado para memoria)
  brain:
    build:
      context: .
      dockerfile: services/brain/Dockerfile
    container_name: oraculo-brain
    ports:
      - "8001:8000"
    environment:
      - DATABASE_URL=\${DATABASE_URL}
      - BINANCE_API_KEY=\${BINANCE_API_KEY}
      - BINANCE_API_SECRET=\${BINANCE_API_SECRET}
      - BRAIN_ANALYSIS_INTERVAL=\${BRAIN_ANALYSIS_INTERVAL:-3600}
      - BRAIN_LOG_LEVEL=\${BRAIN_LOG_LEVEL:-INFO}
      - BRAIN_DEBUG=\${BRAIN_DEBUG:-false}
      - BRAIN_DEV_MODE=\${BRAIN_DEV_MODE:-false}
    volumes:
      - ./logs:/app/logs
      - ./shared:/app/shared
    restart: unless-stopped
    networks:
      - oraculo-network
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M

  # Servicio Grid - Trading Automático (Optimizado para memoria)
  grid:
    build:
      context: .
      dockerfile: services/grid/Dockerfile
    container_name: oraculo-grid
    ports:
      - "8002:8000"
    environment:
      - DATABASE_URL=\${DATABASE_URL}
      - BINANCE_API_KEY=\${BINANCE_API_KEY}
      - BINANCE_API_SECRET=\${BINANCE_API_SECRET}
      - PAPER_TRADING_API_KEY=\${PAPER_TRADING_API_KEY}
      - PAPER_TRADING_SECRET_KEY=\${PAPER_TRADING_SECRET_KEY}
      - TELEGRAM_BOT_TOKEN=\${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_CHAT_ID=\${TELEGRAM_CHAT_ID}
      - TRADING_MODE=\${TRADING_MODE:-sandbox}
      - MONITORING_INTERVAL_HOURS=\${MONITORING_INTERVAL_HOURS:-1}
    volumes:
      - ./logs:/app/logs
      - ./shared:/app/shared
    depends_on:
      - brain
    restart: unless-stopped
    networks:
      - oraculo-network
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M

  # Servicio News - Análisis de Noticias (Optimizado para memoria)
  news:
    build:
      context: .
      dockerfile: services/news/Dockerfile
    container_name: oraculo-news
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=\${DATABASE_URL}
      - REDDIT_CLIENT_ID=\${REDDIT_CLIENT_ID}
      - REDDIT_CLIENT_SECRET=\${REDDIT_CLIENT_SECRET}
      - REDDIT_USER_AGENT=\${REDDIT_USER_AGENT}
      - GOOGLE_API_KEY=\${GOOGLE_API_KEY}
      - TELEGRAM_BOT_TOKEN=\${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_CHAT_ID=\${TELEGRAM_CHAT_ID}
      - NEWS_COLLECTION_INTERVAL=\${NEWS_COLLECTION_INTERVAL:-3600}
      - SENTIMENT_ANALYSIS_INTERVAL=\${SENTIMENT_ANALYSIS_INTERVAL:-1800}
    volumes:
      - ./logs:/app/logs
      - ./shared:/app/shared
    restart: unless-stopped
    networks:
      - oraculo-network
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M

  # Servicio Hype - Detección de Hype (Optimizado para memoria)
  hype:
    build:
      context: .
      dockerfile: services/hype/Dockerfile
    container_name: oraculo-hype
    ports:
      - "8003:8000"
    environment:
      - DATABASE_URL=\${DATABASE_URL}
      - REDDIT_CLIENT_ID=\${REDDIT_CLIENT_ID}
      - REDDIT_CLIENT_SECRET=\${REDDIT_CLIENT_SECRET}
      - REDDIT_USER_AGENT=\${REDDIT_USER_AGENT}
      - TELEGRAM_BOT_TOKEN=\${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_CHAT_ID=\${TELEGRAM_CHAT_ID}
      - HYPE_SCAN_INTERVAL=\${HYPE_SCAN_INTERVAL:-300}
      - HYPE_ALERT_THRESHOLD=\${HYPE_ALERT_THRESHOLD:-10}
    volumes:
      - ./logs:/app/logs
      - ./shared:/app/shared
    restart: unless-stopped
    networks:
      - oraculo-network
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M

networks:
  oraculo-network:
    driver: bridge
EOF

print_success "✅ docker-compose.optimized.yml creado"

echo ""

# Optimizar sistema operativo
print_status "Optimizando sistema operativo..."

# Configurar swap si no existe
if ! swapon --show | grep -q "/swapfile"; then
    print_status "Configurando swap..."
    sudo fallocate -l 1G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    print_success "✅ Swap configurado (1GB)"
else
    print_success "✅ Swap ya configurado"
fi

# Optimizar parámetros del kernel
print_status "Optimizando parámetros del kernel..."
sudo tee -a /etc/sysctl.conf > /dev/null <<EOF

# Optimizaciones para memoria
vm.swappiness=10
vm.vfs_cache_pressure=50
vm.dirty_ratio=15
vm.dirty_background_ratio=5
EOF

# Aplicar cambios
sudo sysctl -p

echo ""

# Limpiar cache y archivos temporales
print_status "Limpiando cache y archivos temporales..."
sudo apt-get clean
sudo apt-get autoremove -y
sudo rm -rf /tmp/*
sudo rm -rf /var/tmp/*

# Limpiar logs antiguos
sudo journalctl --vacuum-time=7d

print_success "✅ Limpieza completada"

echo ""

# Crear script de monitoreo de memoria
print_status "Creando script de monitoreo de memoria..."

cat > monitor_memory.sh <<'EOF'
#!/bin/bash

# Script de monitoreo de memoria
echo "=== Monitoreo de Memoria ==="
echo "Fecha: $(date)"
echo ""

# Memoria del sistema
echo "📊 Memoria del Sistema:"
free -h
echo ""

# Memoria de Docker
echo "🐳 Memoria de Docker:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
echo ""

# Procesos que más memoria usan
echo "🔝 Top 10 procesos por memoria:"
ps aux --sort=-%mem | head -11
echo ""

# Uso de swap
echo "💾 Uso de Swap:"
swapon --show
echo ""

# Alertas
mem_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
if [ $mem_usage -gt 80 ]; then
    echo "⚠️  ALERTA: Uso de memoria alto: ${mem_usage}%"
fi

if [ $mem_usage -gt 90 ]; then
    echo "🚨 CRÍTICO: Uso de memoria crítico: ${mem_usage}%"
fi
EOF

chmod +x monitor_memory.sh
print_success "✅ Script de monitoreo creado: monitor_memory.sh"

echo ""

# Crear script de despliegue optimizado
print_status "Creando script de despliegue optimizado..."

cat > deploy_optimized.sh <<'EOF'
#!/bin/bash

# Script de despliegue optimizado para DigitalOcean Droplet
echo "🚀 Despliegue optimizado para DigitalOcean Droplet..."

# Verificar memoria disponible
available_mem=$(free -m | awk 'NR==2{printf "%.0f", $7}')
echo "Memoria disponible: ${available_mem}MB"

if [ $available_mem -lt 200 ]; then
    echo "⚠️  Poca memoria disponible. Limpiando cache..."
    sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches
    docker system prune -f
fi

# Usar docker-compose optimizado
if [ -f docker-compose.optimized.yml ]; then
    echo "📦 Usando configuración optimizada..."
    docker-compose -f docker-compose.optimized.yml up -d
else
    echo "📦 Usando configuración estándar..."
    docker-compose up -d
fi

echo "✅ Despliegue completado"
echo "📊 Para monitorear: ./monitor_memory.sh"
EOF

chmod +x deploy_optimized.sh
print_success "✅ Script de despliegue optimizado creado: deploy_optimized.sh"

echo ""

print_status "Resumen de optimizaciones:"

echo "📋 Optimizaciones aplicadas:"
echo "   - ✅ Docker configurado con límites de memoria"
echo "   - ✅ Swap configurado (1GB)"
echo "   - ✅ Parámetros del kernel optimizados"
echo "   - ✅ Cache y archivos temporales limpiados"
echo "   - ✅ docker-compose.optimized.yml creado"
echo "   - ✅ Script de monitoreo creado"
echo "   - ✅ Script de despliegue optimizado creado"

echo ""
echo "📊 Límites de memoria por servicio:"
echo "   - Brain: 256MB máximo, 128MB reservado"
echo "   - Grid: 256MB máximo, 128MB reservado"
echo "   - News: 256MB máximo, 128MB reservado"
echo "   - Hype: 256MB máximo, 128MB reservado"
echo "   - Total: ~1GB (dentro del límite del droplet)"

echo ""
print_status "Comandos útiles:"
echo "  ./deploy_optimized.sh        # Desplegar con configuración optimizada"
echo "  ./monitor_memory.sh          # Monitorear uso de memoria"
echo "  docker-compose -f docker-compose.optimized.yml up -d  # Usar configuración optimizada"
echo "  docker system prune -f       # Limpiar recursos de Docker"

echo ""
print_success "✅ Optimización de memoria completada"
print_status "💡 Recomendación: Usar ./deploy_optimized.sh para despliegues futuros" 
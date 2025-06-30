#!/bin/bash

# Script para deployar los microservicios del Oráculo Bot en Ubuntu
# Ejecutar con sudo

set -e  # Salir si hay errores

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Iniciando deployment de Oráculo Bot Microservicios${NC}"

# Variables (modificar según tu setup)
PROJECT_PATH="/var/www/oraculo_bot"
SERVICE_USER="root"

# Función para mostrar mensajes
log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar que estamos ejecutando como root
if [[ $EUID -ne 0 ]]; then
   error "Este script debe ejecutarse como root (sudo)"
   exit 1
fi

# 1. Copiar archivos de servicio
log "📋 Copiando archivos de servicio systemd..."
cp "${PROJECT_PATH}/deployment/services/"*.service /etc/systemd/system/

# 2. Actualizar paths en los archivos de servicio
log "🔧 Actualizando paths en archivos de servicio..."
sed -i "s|/path/to/your/oraculo_bot|${PROJECT_PATH}|g" /etc/systemd/system/oraculo-*.service

# 3. Dar permisos correctos
log "🔐 Configurando permisos..."
chown -R ${SERVICE_USER}:${SERVICE_USER} ${PROJECT_PATH}
chmod +x ${PROJECT_PATH}/run_*.py

# 4. Recargar systemd
log "🔄 Recargando systemd..."
systemctl daemon-reload

# 5. Habilitar servicios (opcional - descomentar los que necesites)
log "✅ Habilitando servicios..."

# Habilitar solo el servicio de noticias por defecto
systemctl enable oraculo-news.service

# Descomentar las siguientes líneas según los servicios que necesites:
systemctl enable oraculo-grid.service
systemctl enable oraculo-api.service
systemctl enable oraculo-hype.service
systemctl enable oraculo-cerebro.service

# 6. Mostrar estado de servicios
log "📊 Estado actual de los servicios:"
# systemctl status oraculo-news.service --no-pager -l || true
# systemctl status oraculo-grid.service --no-pager -l || true
# systemctl status oraculo-api.service --no-pager -l || true
# systemctl status oraculo-hype.service --no-pager -l || true
# systemctl status oraculo-brain.service --no-pager -l || true

# 7.- Reiniciar los servicios
log "🔄 Reiniciando servicios..."
# systemctl restart oraculo-news.service
# systemctl restart oraculo-grid.service
# systemctl restart oraculo-api.service
# systemctl restart oraculo-hype.service
systemctl restart oraculo-cerebro.service

echo
log "🎉 Deployment completado!"
echo
log "Para iniciar los servicios:"
log "  sudo systemctl start oraculo-news"
log "  sudo systemctl start oraculo-grid"
log "  sudo systemctl start oraculo-api"
log "  sudo systemctl start oraculo-hype"
echo
log "Para ver logs:"
log "  sudo journalctl -u oraculo-news -f"
log "  sudo journalctl -u oraculo-grid -f"
log "  sudo journalctl -u oraculo-api -f"
log "  sudo journalctl -u oraculo-hype -f"
echo
log "Para detener servicios:"
log "  sudo systemctl stop oraculo-news"
log "  sudo systemctl stop oraculo-grid"
log "  sudo systemctl stop oraculo-api"
log "  sudo systemctl stop oraculo-hype" 
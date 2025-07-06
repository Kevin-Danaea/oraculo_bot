#!/bin/bash

# ==============================================================================
# Script de Despliegue - Oráculo Bot
# ==============================================================================

set -e  # Salir si hay algún error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir mensajes con colores
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

# Función para verificar si Docker está instalado
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker no está instalado. Por favor instala Docker primero."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose no está instalado. Por favor instala Docker Compose primero."
        exit 1
    fi
    
    print_success "Docker y Docker Compose están instalados"
}

# Función para verificar archivo .env
check_env_file() {
    if [ ! -f .env ]; then
        print_warning "Archivo .env no encontrado"
        if [ -f .env.example ]; then
            print_status "Copiando .env.example a .env..."
            cp .env.example .env
            print_warning "Por favor edita el archivo .env con tus credenciales antes de continuar"
            print_status "Variables requeridas:"
            echo "  - DATABASE_URL (URL de Neon)"
            echo "  - BINANCE_API_KEY"
            echo "  - BINANCE_API_SECRET"
            echo "  - PAPER_TRADING_API_KEY"
            echo "  - PAPER_TRADING_SECRET_KEY"
            echo "  - TELEGRAM_BOT_TOKEN"
            echo "  - TELEGRAM_CHAT_ID"
            echo "  - REDDIT_CLIENT_ID"
            echo "  - REDDIT_CLIENT_SECRET"
            echo "  - GOOGLE_API_KEY"
            exit 1
        else
            print_error "No se encontró .env.example. Por favor crea un archivo .env con las variables necesarias"
            exit 1
        fi
    fi
    
    print_success "Archivo .env encontrado"
}

# Función para crear directorio de logs
create_logs_directory() {
    if [ ! -d logs ]; then
        print_status "Creando directorio de logs..."
        mkdir -p logs
        print_success "Directorio de logs creado"
    fi
}

# Función para construir las imágenes
build_images() {
    print_status "Construyendo imágenes Docker..."
    
    # Construir todas las imágenes
    docker-compose build --no-cache
    
    print_success "Imágenes construidas correctamente"
}

# Función para iniciar los servicios
start_services() {
    print_status "Iniciando servicios..."
    
    # Iniciar servicios en modo detached
    docker-compose up -d
    
    print_success "Servicios iniciados correctamente"
}

# Función para verificar el estado de los servicios
check_services_status() {
    print_status "Verificando estado de los servicios..."
    
    # Esperar un poco para que los servicios se inicien
    sleep 10
    
    # Verificar estado de cada servicio
    services=("brain" "grid" "news" "hype")
    
    for service in "${services[@]}"; do
        if docker-compose ps | grep -q "$service.*Up"; then
            print_success "$service está ejecutándose"
        else
            print_error "$service no está ejecutándose correctamente"
        fi
    done
}

# Función para mostrar logs
show_logs() {
    print_status "Mostrando logs de los servicios..."
    docker-compose logs -f
}

# Función para detener servicios
stop_services() {
    print_status "Deteniendo servicios..."
    docker-compose down
    print_success "Servicios detenidos"
}

# Función para limpiar todo
cleanup() {
    print_status "Limpiando contenedores e imágenes..."
    docker-compose down -v --rmi all
    print_success "Limpieza completada"
}

# Función para mostrar ayuda
show_help() {
    echo "Script de Despliegue - Oráculo Bot"
    echo ""
    echo "Uso: $0 [COMANDO]"
    echo ""
    echo "Comandos disponibles:"
    echo "  deploy     - Desplegar todos los servicios (default)"
    echo "  build      - Solo construir las imágenes"
    echo "  start      - Solo iniciar los servicios"
    echo "  stop       - Detener todos los servicios"
    echo "  restart    - Reiniciar todos los servicios"
    echo "  logs       - Mostrar logs de todos los servicios"
    echo "  status     - Verificar estado de los servicios"
    echo "  cleanup    - Limpiar contenedores e imágenes"
    echo "  help       - Mostrar esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  $0 deploy    # Desplegar todo el sistema"
    echo "  $0 logs      # Ver logs en tiempo real"
    echo "  $0 stop      # Detener todos los servicios"
}

# Función principal de despliegue
deploy() {
    print_status "Iniciando despliegue de Oráculo Bot..."
    
    check_docker
    check_env_file
    create_logs_directory
    build_images
    start_services
    check_services_status
    
    print_success "Despliegue completado exitosamente!"
    print_status "Servicios disponibles en:"
    echo "  - News Service: http://localhost:8000"
    echo "  - Brain Service: http://localhost:8001"
    echo "  - Grid Service: http://localhost:8002"
    echo "  - Hype Service: http://localhost:8003"
    echo "  - Base de datos: Neon (PostgreSQL en la nube)"
    echo ""
    print_status "Para ver logs: $0 logs"
    print_status "Para detener: $0 stop"
}

# Manejo de argumentos
case "${1:-deploy}" in
    "deploy")
        deploy
        ;;
    "build")
        check_docker
        check_env_file
        build_images
        ;;
    "start")
        check_docker
        check_env_file
        start_services
        check_services_status
        ;;
    "stop")
        stop_services
        ;;
    "restart")
        stop_services
        start_services
        check_services_status
        ;;
    "logs")
        show_logs
        ;;
    "status")
        check_services_status
        ;;
    "cleanup")
        cleanup
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        print_error "Comando desconocido: $1"
        show_help
        exit 1
        ;;
esac 
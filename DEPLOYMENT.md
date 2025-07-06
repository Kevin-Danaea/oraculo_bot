# 🚀 Guía de Despliegue - Oráculo Bot

## 📋 Descripción General

Oráculo Bot es un sistema de trading automatizado compuesto por 4 microservicios que funcionan de manera independiente pero coordinada:

- **🧠 Brain Service** (Puerto 8001): Motor de decisiones de trading
- **📊 Grid Service** (Puerto 8002): Bot de trading automático
- **📰 News Service** (Puerto 8000): Análisis de noticias y sentimiento
- **🔥 Hype Service** (Puerto 8003): Detección de hype en Reddit

## 🏗️ Arquitectura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Brain Service │    │   Grid Service  │    │   News Service  │    │   Hype Service  │
│   (Puerto 8001) │    │   (Puerto 8002) │    │   (Puerto 8000) │    │   (Puerto 8003) │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │                       │
         └───────────────────────┼───────────────────────┼───────────────────────┘
                                 │                       │
                    ┌─────────────────────────────────────────────────────────────┐
                    │                    Neon Database                            │
                    │              (PostgreSQL en la nube)                       │
                    └─────────────────────────────────────────────────────────────┘
```

## 📋 Prerrequisitos

### 1. Docker y Docker Compose
```bash
# Verificar instalación
docker --version
docker-compose --version
```

### 2. Credenciales de APIs
Necesitarás las siguientes credenciales:

- **Binance API**: Para trading automático
- **Paper Trading API**: Para modo sandbox del Grid bot
- **Telegram Bot**: Para notificaciones
- **Reddit API**: Para análisis de noticias y hype
- **Google Gemini API**: Para análisis de sentimiento
- **Neon Database**: URL de conexión a PostgreSQL

## 🚀 Despliegue Rápido

### 1. Clonar el repositorio
```bash
git clone <tu-repositorio>
cd oraculo_bot
```

### 2. Configurar variables de entorno
```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar con tus credenciales
nano .env
```

### 3. Ejecutar despliegue
```bash
# Hacer ejecutable el script
chmod +x deploy.sh

# Desplegar todo el sistema
./deploy.sh deploy
```

## ⚙️ Configuración Detallada

### Variables de Entorno Requeridas

```bash
# Base de datos Neon (PostgreSQL en la nube)
DATABASE_URL=postgresql://usuario:password@tu-instancia-neon.region.aws.neon.tech/tu-database?sslmode=require

# Binance API (Requerido para Brain y Grid)
BINANCE_API_KEY=tu_binance_api_key_aqui
BINANCE_API_SECRET=tu_binance_api_secret_aqui

# Paper Trading API (Requerido para Grid en modo sandbox)
PAPER_TRADING_API_KEY=tu_paper_trading_api_key_aqui
PAPER_TRADING_SECRET_KEY=tu_paper_trading_secret_key_aqui

# Telegram Bot (Requerido para notificaciones)
TELEGRAM_BOT_TOKEN=tu_telegram_bot_token_aqui
TELEGRAM_CHAT_ID=tu_telegram_chat_id_aqui

# Reddit API (Requerido para News y Hype)
REDDIT_CLIENT_ID=tu_reddit_client_id_aqui
REDDIT_CLIENT_SECRET=tu_reddit_client_secret_aqui
REDDIT_USER_AGENT=OraculoBot by Grand_Maintenance_13

# Google Gemini API (Requerido para News)
GOOGLE_API_KEY=tu_google_api_key_aqui
```

### Configuración de Servicios

```bash
# Brain Service
BRAIN_ANALYSIS_INTERVAL=3600        # Intervalo de análisis en segundos
BRAIN_LOG_LEVEL=INFO               # Nivel de logging
BRAIN_DEBUG=false                  # Modo debug
BRAIN_DEV_MODE=false               # Modo desarrollo

# Grid Service
TRADING_MODE=sandbox               # sandbox o production
MONITORING_INTERVAL_HOURS=1        # Intervalo de monitoreo

# News Service
NEWS_COLLECTION_INTERVAL=3600      # Intervalo de recolección de noticias
SENTIMENT_ANALYSIS_INTERVAL=1800   # Intervalo de análisis de sentimiento

# Hype Service
HYPE_SCAN_INTERVAL=300             # Intervalo de escaneo de hype
HYPE_ALERT_THRESHOLD=10            # Umbral de alertas de hype
```

## 🛠️ Comandos de Gestión

### Script de Despliegue
```bash
# Desplegar todo el sistema
./deploy.sh deploy

# Solo construir imágenes
./deploy.sh build

# Solo iniciar servicios
./deploy.sh start

# Detener servicios
./deploy.sh stop

# Reiniciar servicios
./deploy.sh restart

# Ver logs en tiempo real
./deploy.sh logs

# Verificar estado de servicios
./deploy.sh status

# Limpiar todo (contenedores e imágenes)
./deploy.sh cleanup

# Mostrar ayuda
./deploy.sh help
```

### Docker Compose Directo
```bash
# Construir imágenes
docker-compose build

# Iniciar servicios
docker-compose up -d

# Ver logs
docker-compose logs -f

# Ver estado
docker-compose ps

# Detener servicios
docker-compose down

# Reiniciar un servicio específico
docker-compose restart brain
```

## 🌐 Acceso a Servicios

Una vez desplegado, los servicios estarán disponibles en:

- **📰 News Service**: http://localhost:8000
  - Health check: http://localhost:8000/health
  - Documentación: http://localhost:8000/docs

- **🧠 Brain Service**: http://localhost:8001
  - Health check: http://localhost:8001/health
  - Documentación: http://localhost:8001/docs

- **📊 Grid Service**: http://localhost:8002
  - Health check: http://localhost:8002/health
  - Documentación: http://localhost:8002/docs

- **🔥 Hype Service**: http://localhost:8003
  - Health check: http://localhost:8003/health
  - Documentación: http://localhost:8003/docs

## 📊 Monitoreo y Logs

### Ver Logs de Todos los Servicios
```bash
./deploy.sh logs
```

### Ver Logs de un Servicio Específico
```bash
# Logs del Brain
docker-compose logs -f brain

# Logs del Grid
docker-compose logs -f grid

# Logs del News
docker-compose logs -f news

# Logs del Hype
docker-compose logs -f hype
```

### Logs Persistentes
Los logs se guardan en el directorio `./logs/` del host:
```bash
# Ver logs del Brain
tail -f logs/brain.log

# Ver logs del Grid
tail -f logs/grid.log

# Ver logs del News
tail -f logs/news.log

# Ver logs del Hype
tail -f logs/hype.log
```

## 🔧 Troubleshooting

### Problemas Comunes

#### 1. Error de Conexión a Base de Datos
```bash
# Verificar que DATABASE_URL esté correcta
echo $DATABASE_URL

# Verificar conectividad
docker-compose exec brain python -c "
from shared.database.session import SessionLocal
db = SessionLocal()
print('Conexión exitosa')
db.close()
"
```

#### 2. Error de Credenciales de Binance
```bash
# Verificar variables de entorno
docker-compose exec grid env | grep BINANCE

# Verificar en logs
docker-compose logs grid | grep -i "binance\|api"
```

#### 3. Error de Paper Trading (Sandbox)
```bash
# Verificar variables de entorno
docker-compose exec grid env | grep PAPER_TRADING

# Verificar en logs
docker-compose logs grid | grep -i "paper\|sandbox"
```

#### 4. Error de Telegram Bot
```bash
# Verificar token y chat ID
docker-compose exec grid env | grep TELEGRAM

# Verificar en logs
docker-compose logs grid | grep -i "telegram"
```

#### 5. Servicio No Inicia
```bash
# Verificar estado
./deploy.sh status

# Ver logs específicos
docker-compose logs <nombre-servicio>

# Reiniciar servicio
docker-compose restart <nombre-servicio>
```

### Comandos de Diagnóstico

```bash
# Ver uso de recursos
docker stats

# Ver redes Docker
docker network ls

# Ver volúmenes
docker volume ls

# Ver imágenes
docker images | grep oraculo
```

## 🔄 Actualización del Sistema

### Actualizar Código
```bash
# Obtener últimos cambios
git pull origin main

# Reconstruir y reiniciar
./deploy.sh restart
```

### Actualizar Configuración
```bash
# Editar variables de entorno
nano .env

# Reiniciar servicios
./deploy.sh restart
```

## 🧹 Limpieza y Mantenimiento

### Limpieza Completa
```bash
# Detener y eliminar contenedores
docker-compose down

# Eliminar imágenes
docker-compose down --rmi all

# Eliminar volúmenes (¡CUIDADO! Esto elimina datos)
docker-compose down -v

# Limpieza completa con script
./deploy.sh cleanup
```

### Limpieza de Logs
```bash
# Limpiar logs antiguos
find ./logs -name "*.log" -mtime +7 -delete

# Comprimir logs
gzip ./logs/*.log
```

## 📈 Escalabilidad

### Aumentar Recursos
```bash
# Editar docker-compose.yml para agregar límites de recursos
services:
  brain:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
```

### Monitoreo de Recursos
```bash
# Ver uso de recursos en tiempo real
docker stats

# Ver logs de rendimiento
docker-compose logs | grep -i "memory\|cpu\|performance"
```

## 🔒 Seguridad

### Variables de Entorno
- ✅ Nunca committear archivo `.env` al repositorio
- ✅ Usar `.env.example` como plantilla
- ✅ Rotar credenciales regularmente
- ✅ Usar variables de entorno en producción

### Redes Docker
- ✅ Usar red interna `oraculo-network`
- ✅ No exponer puertos innecesarios
- ✅ Usar HTTPS en producción

### Base de Datos
- ✅ Usar SSL para conexiones a Neon
- ✅ Limitar acceso por IP si es posible
- ✅ Hacer backups regulares

## 📞 Soporte

### Logs de Error
```bash
# Ver errores de todos los servicios
docker-compose logs | grep -i "error\|exception\|traceback"

# Ver errores de un servicio específico
docker-compose logs <servicio> | grep -i "error"
```

### Health Checks
```bash
# Verificar salud de todos los servicios
curl http://localhost:8000/health  # News
curl http://localhost:8001/health  # Brain
curl http://localhost:8002/health  # Grid
curl http://localhost:8003/health  # Hype
```

---

## ✅ Checklist de Despliegue

- [ ] Docker y Docker Compose instalados
- [ ] Archivo `.env` configurado con credenciales
- [ ] Variables de Paper Trading configuradas
- [ ] Directorio `logs/` creado
- [ ] Script `deploy.sh` ejecutable
- [ ] Todas las imágenes construidas correctamente
- [ ] Todos los servicios iniciados
- [ ] Health checks pasando
- [ ] Logs sin errores críticos
- [ ] Base de datos conectada
- [ ] APIs externas funcionando

¡Tu Oráculo Bot está listo para funcionar! 🎉 
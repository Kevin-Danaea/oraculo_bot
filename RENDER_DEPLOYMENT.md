# 🚀 Despliegue en Render - Oráculo Bot

Guía completa para desplegar el Oráculo Bot en Render con todos sus microservicios.

## 📋 Prerrequisitos

- Cuenta en [Render](https://render.com)
- Repositorio Git con el código
- Variables de entorno configuradas

## 🔧 Configuración

### 1. Variables de Entorno Requeridas

Cada servicio necesita estas variables configuradas en Render:

#### 🧠 Brain Service
```env
DATABASE_URL=postgresql://user:pass@host:port/db
BRAIN_ANALYSIS_INTERVAL=3600
BRAIN_ANALYSIS_TIMEFRAME=4h
BRAIN_ANALYSIS_DAYS=40
BRAIN_LOG_LEVEL=INFO
BRAIN_DEBUG=false
BRAIN_DEV_MODE=false
```

#### 📊 Grid Service
```env
DATABASE_URL=postgresql://user:pass@host:port/db
BINANCE_API_KEY=tu_api_key_paper
BINANCE_SECRET_KEY=tu_secret_key_paper
TELEGRAM_BOT_TOKEN=tu_bot_token
TELEGRAM_CHAT_ID=tu_chat_id
GRID_LOG_LEVEL=INFO
GRID_DEBUG=false
GRID_DEV_MODE=false
```

#### 📰 News Service
```env
DATABASE_URL=postgresql://user:pass@host:port/db
GOOGLE_API_KEY=tu_google_api_key
REDDIT_CLIENT_ID=tu_client_id
REDDIT_CLIENT_SECRET=tu_client_secret
NEWS_LOG_LEVEL=INFO
NEWS_DEBUG=false
NEWS_DEV_MODE=false
```

#### 🔥 Hype Service
```env
DATABASE_URL=postgresql://user:pass@host:port/db
TELEGRAM_BOT_TOKEN=tu_bot_token
TELEGRAM_CHAT_ID=tu_chat_id
HYPE_LOG_LEVEL=INFO
HYPE_DEBUG=false
HYPE_DEV_MODE=false
```

## 🚀 Pasos de Despliegue

### 1. Conectar Repositorio
1. Ve a [Render Dashboard](https://dashboard.render.com)
2. Haz clic en "New +" → "Blueprint"
3. Conecta tu repositorio Git
4. Render detectará automáticamente el `render.yaml`

### 2. Configurar Variables de Entorno
1. Para cada servicio, ve a "Environment"
2. Agrega todas las variables requeridas
3. Usa la misma `DATABASE_URL` para todos los servicios

### 3. Desplegar
1. Render construirá automáticamente todos los servicios
2. El Brain service instalará TA-Lib con conda
3. Todos los servicios se conectarán a la base de datos PostgreSQL

## 📊 Servicios Desplegados

| Servicio | URL | Puerto | Descripción |
|----------|-----|--------|-------------|
| Brain | `https://oraculo-brain.onrender.com` | 8001 | Análisis técnico |
| Grid | `https://oraculo-grid.onrender.com` | 8002 | Trading automatizado |
| News | `https://oraculo-news.onrender.com` | 8003 | Análisis de noticias |
| Hype | `https://oraculo-hype.onrender.com` | 8004 | Detección de tendencias |

## 🔍 Verificación

### 1. Verificar TA-Lib en Brain
```bash
# En los logs del servicio Brain deberías ver:
✅ TA-Lib version: 0.4.28
```

### 2. Verificar Conexión a Base de Datos
```bash
# En los logs de cada servicio deberías ver:
✅ Conectado a base de datos PostgreSQL
```

### 3. Verificar Servicios Activos
- Todos los servicios deben mostrar estado "Live"
- Los logs no deben mostrar errores de conexión
- Los puertos deben estar abiertos y accesibles

## 🛠️ Solución de Problemas

### Error de TA-Lib
Si el Brain service falla al instalar TA-Lib:
1. Revisa los logs de construcción
2. Verifica que conda se instaló correctamente
3. Asegúrate de que Python 3.10 esté configurado

### Error de Base de Datos
Si hay problemas de conexión:
1. Verifica que la `DATABASE_URL` sea correcta
2. Asegúrate de que la base de datos esté activa
3. Revisa que las credenciales sean válidas

### Error de Variables de Entorno
Si faltan variables:
1. Ve a cada servicio en Render
2. Configura todas las variables requeridas
3. Reinicia el servicio después de agregar variables

## 💰 Costos

- **Plan Starter**: $7/mes por servicio
- **Base de Datos**: $7/mes
- **Total estimado**: $35/mes para todos los servicios

## 🔄 Actualizaciones

Para actualizar el código:
1. Haz push a tu repositorio Git
2. Render detectará automáticamente los cambios
3. Reconstruirá y desplegará automáticamente

## 📞 Soporte

- [Render Documentation](https://render.com/docs)
- [Render Community](https://community.render.com)
- Logs disponibles en el dashboard de cada servicio 
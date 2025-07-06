# 🔒 Guía de Seguridad - Oráculo Bot

## ⚠️ **ADVERTENCIA DE SEGURIDAD**

Este documento contiene las mejores prácticas para mantener seguras las credenciales y configuraciones del Oráculo Bot.

## 🚨 **Credenciales Expuestas - CORREGIDO**

### Problema Identificado
Se detectó que las credenciales reales de la base de datos Neon estaban expuestas en archivos de documentación.

### Archivos Corregidos
- ✅ `DEPLOYMENT.md` - URL de ejemplo genérica
- ✅ `VERIFICATION.md` - URL de ejemplo genérica  
- ✅ `.env.example` - URL de ejemplo genérica
- ✅ `.gitignore` - Removido `.env.example` (debe estar en repositorio)

### Estado Actual
- ✅ **Archivo `.env`**: Contiene credenciales reales (NO subir al repositorio)
- ✅ **Archivo `.env.example`**: Contiene plantillas genéricas (SÍ subir al repositorio)
- ✅ **Documentación**: Usa ejemplos genéricos

## 🔐 **Protección de Credenciales**

### 1. **Archivo .env (CRÍTICO)**
```bash
# ❌ NUNCA subir al repositorio
# ✅ Ya está en .gitignore
# ✅ Contiene credenciales reales
```

### 2. **Archivo .env.example (SEGURO)**
```bash
# ✅ SÍ subir al repositorio
# ✅ Contiene plantillas genéricas
# ✅ Sin credenciales reales
```

### 3. **Variables de Entorno Requeridas**
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
REDDIT_USER_AGENT=OraculoBot by tu_usuario_de_reddit

# Google Gemini API (Requerido para News)
GOOGLE_API_KEY=tu_google_api_key_aqui
```

## 🛡️ **Mejores Prácticas de Seguridad**

### 1. **Gestión de Credenciales**
- ✅ Usar variables de entorno para todas las credenciales
- ✅ Nunca hardcodear credenciales en el código
- ✅ Usar archivos `.env` para desarrollo local
- ✅ Usar secretos del sistema en producción

### 2. **Control de Versiones**
- ✅ `.env` en `.gitignore` (nunca subir)
- ✅ `.env.example` en repositorio (plantilla segura)
- ✅ Documentación con ejemplos genéricos
- ✅ Sin credenciales en commits

### 3. **Rotación de Credenciales**
- 🔄 Rotar credenciales de API regularmente
- 🔄 Cambiar contraseñas de base de datos
- 🔄 Revisar permisos de API keys
- 🔄 Monitorear uso de credenciales

### 4. **Seguridad de Base de Datos**
- ✅ Usar SSL para conexiones
- ✅ Limitar acceso por IP si es posible
- ✅ Usar usuarios con permisos mínimos
- ✅ Hacer backups regulares

### 5. **Seguridad de APIs**
- ✅ Usar API keys con permisos limitados
- ✅ Monitorear uso de APIs
- ✅ Configurar webhooks seguros
- ✅ Usar rate limiting

## 🔍 **Verificación de Seguridad**

### Comandos de Verificación
```bash
# Verificar que .env no está en el repositorio
git status | grep .env

# Verificar que .env.example está en el repositorio
git ls-files | grep .env.example

# Verificar que no hay credenciales en el código
grep -r "password\|secret\|key" . --exclude-dir=.git --exclude=*.pyc | grep -v "example\|template"

# Verificar variables de entorno
./verify_paper_trading.sh
```

### Checklist de Seguridad
- [ ] `.env` NO está en el repositorio
- [ ] `.env.example` SÍ está en el repositorio
- [ ] No hay credenciales hardcodeadas en el código
- [ ] Documentación usa ejemplos genéricos
- [ ] Variables de entorno configuradas correctamente
- [ ] Permisos de archivos correctos (600 para .env)

## 🚨 **Respuesta a Incidentes**

### Si se Expusen Credenciales
1. **Inmediato**: Rotar todas las credenciales expuestas
2. **Análisis**: Identificar qué credenciales se expusieron
3. **Contención**: Remover credenciales del historial de Git
4. **Notificación**: Notificar a servicios afectados
5. **Prevención**: Revisar y mejorar procesos de seguridad

### Comandos de Emergencia
```bash
# Rotar credenciales de Binance
# 1. Ir a Binance -> API Management
# 2. Revocar API key expuesta
# 3. Crear nueva API key
# 4. Actualizar .env

# Rotar credenciales de Neon
# 1. Ir a Neon Dashboard
# 2. Resetear contraseña de usuario
# 3. Actualizar DATABASE_URL en .env

# Limpiar historial de Git (si es necesario)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all
```

## 📋 **Configuración Segura por Defecto**

### Modo Sandbox
- ✅ Grid Service inicia en modo sandbox
- ✅ Paper Trading por defecto
- ✅ Sin riesgo de pérdida de dinero real
- ✅ Cambio a producción solo manual

### Aislamiento de Capital
- ✅ Límites de capital configurados
- ✅ Porcentajes dinámicos
- ✅ Verificación antes de operaciones
- ✅ Logs de todas las operaciones

### Logging y Monitoreo
- ✅ Logs de todas las operaciones
- ✅ Alertas de Telegram
- ✅ Monitoreo de errores
- ✅ Auditoría de cambios

## 🔐 **Configuración de Producción**

### Variables de Entorno en Producción
```bash
# Usar secretos del sistema operativo
export DATABASE_URL="postgresql://..."
export BINANCE_API_KEY="..."
export BINANCE_API_SECRET="..."

# O usar archivo .env con permisos restrictivos
chmod 600 .env
```

### Firewall y Redes
- 🔒 Limitar acceso por IP
- 🔒 Usar VPN si es necesario
- 🔒 Configurar reglas de firewall
- 🔒 Monitorear conexiones

### Backup y Recuperación
- 💾 Backups automáticos de base de datos
- 💾 Configuración versionada
- 💾 Plan de recuperación documentado
- 💾 Pruebas de restauración

---

## ✅ **Estado de Seguridad Actual**

- ✅ **Credenciales protegidas**: No hay credenciales en el repositorio
- ✅ **Documentación segura**: Usa ejemplos genéricos
- ✅ **Configuración por defecto**: Modo sandbox activado
- ✅ **Aislamiento de capital**: Implementado correctamente
- ✅ **Logging completo**: Todas las operaciones registradas

**El sistema está configurado de manera segura y lista para uso en producción.** 🛡️ 
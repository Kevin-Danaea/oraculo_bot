# 🤖 Grid Trading Service

Servicio especializado en ejecutar estrategias de grid trading automatizadas consultando directamente la base de datos cada hora para monitorear órdenes.

## 🚀 Características Principales

- **Monitoreo Automático**: Verificación cada hora de transiciones de estado
- **Tiempo Real**: Detección inmediata de fills y creación de órdenes complementarias
- **Aislamiento de Capital**: Cada bot opera con su capital asignado específico
- **Comandos Telegram**: Control completo via Telegram con comandos interactivos
- **Notificaciones Detalladas**: Resúmenes con capital, órdenes y estado de bots
- **Gestión de Riesgos**: Stop loss y trailing up automáticos

## 📋 Comandos de Telegram

### 🚀 Comandos Básicos
- `/start` - Mensaje de bienvenida
- `/help` - Lista completa de comandos

### 📊 Información
- `/status` - Estado del sistema y scheduler
- `/balance` - Capital asignado y balances por bot

### 🎮 Control
- `/start_bot` - Iniciar Grid Trading
- `/stop_bot` - Detener Grid Trading
- `/monitor` - Ejecutar monitoreo manual

### ⚙️ Configuración
- `/sandbox` - Cambiar a modo pruebas
- `/production` - Cambiar a modo real (requiere confirmación)

**📖 Ver documentación completa en [TELEGRAM_COMMANDS.md](TELEGRAM_COMMANDS.md)**

## 🏗️ Arquitectura

```
services/grid/
├── app/
│   ├── application/          # Casos de uso
│   │   ├── manage_grid_transitions_use_case.py
│   │   ├── realtime_grid_monitor_use_case.py
│   │   ├── risk_management_use_case.py
│   │   ├── trading_stats_use_case.py
│   │   └── mode_switch_use_case.py
│   ├── domain/              # Entidades e interfaces
│   │   ├── entities.py
│   │   └── interfaces.py
│   ├── infrastructure/      # Implementaciones
│   │   ├── database_repository.py
│   │   ├── exchange_service.py
│   │   ├── notification_service.py
│   │   ├── grid_calculator.py
│   │   ├── scheduler.py
│   │   └── telegram_bot.py
│   ├── config.py
│   └── main.py
├── tests/
├── Dockerfile
├── requirements.txt
└── README.md
```

## 🔧 Configuración

### Variables de Entorno Requeridas

```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Binance (Sandbox)
PAPER_TRADING_API_KEY=your_sandbox_api_key
PAPER_TRADING_SECRET_KEY=your_sandbox_secret_key

# Binance (Producción)
BINANCE_API_KEY=your_production_api_key
BINANCE_API_SECRET=your_production_secret_key

# Base de Datos
DATABASE_URL=postgresql://user:password@host:port/database
```

### Configuración de Trading

```python
# services/grid/app/config.py
MIN_ORDER_VALUE_USDT = 10.0  # Mínimo 10 USDT por orden
GRID_LEVELS_DEFAULT = 30     # Niveles de grilla por defecto
PRICE_RANGE_PERCENT_DEFAULT = 10.0  # Rango de precios
STOP_LOSS_PERCENT_DEFAULT = 5.0     # Stop loss por defecto
```

## 🚀 Instalación y Ejecución

### 1. Instalación Local

```bash
cd services/grid
pip install -r requirements.txt
python -m app.main
```

### 2. Con Docker

```bash
# Construir imagen
docker build -t grid-trading-service .

# Ejecutar contenedor
docker run -p 8002:8002 --env-file .env grid-trading-service
```

### 3. Con Docker Compose

```bash
# Desde el directorio raíz del proyecto
sudo docker-compose up --build grid
```

## 📊 Monitoreo y Logs

### Endpoints de API

- `GET /` - Información del servicio
- `GET /health` - Health check detallado
- `POST /telegram/command` - Comandos de Telegram (testing)
- `POST /manual-monitor` - Monitoreo manual

### Logs Detallados

El servicio genera logs detallados para:

- **Activación de Bots**: Capital, órdenes creadas, precios
- **Creación de Grillas**: Niveles, cantidades, validaciones
- **Comandos Telegram**: Ejecución y respuestas
- **Monitoreo Tiempo Real**: Fills detectados, órdenes complementarias
- **Gestión de Riesgos**: Stop loss y trailing up

### Ejemplo de Logs

```
🚀 ========== DETECTANDO TRANSICIONES DE ESTADO ==========
📊 Evaluando transiciones para 2 configuraciones
🔍 Evaluando transición BTC/USDT: NO_DECISION → OPERAR_GRID
🚀 ACTIVANDO bot para BTC/USDT
🏗️ Creando grilla inicial para BTC/USDT a precio $43250.50
📊 Bot BTC/USDT: Creando 15 órdenes de venta con 0.000123 BTC cada una
✅ Bot BTC/USDT: Orden de compra creada exitosamente (ID: 12345)
✅ Bot BTC/USDT: Orden de venta creada exitosamente (ID: 12346)
🎉 Bot BTC/USDT: Grilla inicial completada - 15 órdenes de compra, 15 órdenes de venta
📱 Notificación detallada enviada para grilla inicial de BTC/USDT
```

## 🧪 Testing

### Script de Pruebas

```bash
# Ejecutar pruebas de comandos Telegram
python test_telegram_commands.py
```

### Pruebas Manuales

1. **Health Check**: `curl http://localhost:8002/health`
2. **Comando Status**: `curl -X POST http://localhost:8002/telegram/command -H "Content-Type: application/json" -d '"status"'`
3. **Monitoreo Manual**: `curl -X POST http://localhost:8002/manual-monitor`

## 🔄 Flujo de Trabajo

### 1. Activación de Bot
1. El Cerebro cambia decisión a "OPERAR_GRID"
2. El servicio detecta la transición
3. Compra 50% del capital asignado al mercado
4. Crea grilla de órdenes de compra y venta
5. Envía notificación detallada con resumen

### 2. Monitoreo Tiempo Real
1. Cada 10 segundos verifica órdenes activas
2. Detecta fills inmediatamente
3. Crea órdenes complementarias al instante
4. Mantiene la grilla dinámica

### 3. Gestión Horaria
1. Cada hora verifica transiciones de estado
2. Envía resúmenes periódicos cada 2 horas
3. Notifica cambios de decisión
4. Limpia cache del monitor tiempo real

## 🛡️ Gestión de Riesgos

### Stop Loss
- Se activa cuando el precio cae más del porcentaje configurado
- Cancela todas las órdenes activas
- Liquida posiciones al mercado
- Pausa el bot automáticamente

### Trailing Up
- Se activa cuando el precio sube más del 5% sobre el nivel más alto
- Cancela órdenes existentes
- Reinicializa grilla con nuevo precio base
- Optimiza ganancias en tendencias alcistas

## 📈 Métricas y Estadísticas

### Resúmenes Periódicos (cada 2 horas)
- Número de bots activos
- Trades ejecutados
- Ganancia total
- Detalles por par (P&L, órdenes activas)

### Notificaciones de Activación
- Capital asignado y utilizado
- Número de órdenes creadas (compras/ventas)
- Precio actual y niveles de grilla
- Timestamp de activación

## 🚨 Troubleshooting

### Problemas Comunes

1. **Comandos Telegram no funcionan**
   - Verificar que el bot esté activo en logs
   - Confirmar token y chat ID configurados
   - Revisar permisos del bot

2. **No se crean órdenes de venta**
   - Verificar balance de moneda base
   - Revisar logs de validación de capital
   - Confirmar que la compra inicial fue exitosa

3. **No se reciben notificaciones**
   - Verificar conexión a Telegram
   - Revisar logs de error
   - Confirmar permisos de envío

### Logs de Debug

```bash
# Ver logs en tiempo real
docker logs -f grid-trading-service

# Buscar errores específicos
grep "❌" logs/grid.log
grep "⚠️" logs/grid.log
```

## 📞 Soporte

Para problemas técnicos:

1. Revisar logs en `services/grid/logs/`
2. Verificar configuración de variables de entorno
3. Ejecutar script de pruebas: `python test_telegram_commands.py`
4. Consultar documentación de comandos: `TELEGRAM_COMMANDS.md`

## 🔄 Changelog

### v2.0.0 - Comandos Telegram Interactivos
- ✅ Bot de Telegram con polling automático
- ✅ Comandos interactivos completos
- ✅ Logging detallado de creación de órdenes
- ✅ Notificaciones detalladas de activación
- ✅ Script de pruebas automatizado
- ✅ Documentación completa de comandos

### v1.0.0 - Funcionalidad Básica
- ✅ Monitoreo horario de transiciones
- ✅ Creación de grillas iniciales
- ✅ Aislamiento de capital por bot
- ✅ Gestión de riesgos básica 
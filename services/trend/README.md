# Trend Following Bot

Bot de trading automático que sigue tendencias a largo plazo para un único par de criptomonedas.

## Descripción

El Trend Following Bot es un servicio autónomo y especializado cuya única misión es ejecutar una estrategia de seguimiento de tendencias a largo plazo. A diferencia del Grid Bot que se beneficia de la volatilidad en rangos, este bot está diseñado para capturar grandes movimientos direccionales del mercado, permaneciendo en una posición durante semanas o meses.

### Características Principales

- 🧠 **Sin lógica de decisión**: Actúa como "brazo ejecutor" táctico basado en directivas del cerebro
- 📊 **Seguimiento de tendencias**: Captura movimientos direccionales a largo plazo
- 🛑 **Trailing Stop**: Protección automática de ganancias
- 💰 **Una posición por símbolo**: Enfoque en una sola tendencia
- 🔄 **Ciclo de 1 hora**: Frecuencia apropiada para estrategia a largo plazo
- 📱 **Notificaciones Telegram**: Alertas en tiempo real de todas las operaciones

## Arquitectura

```
services/trend/
├── app/
│   ├── domain/          # Entidades y reglas de negocio
│   │   ├── entities.py  # TrendPosition, TrendBotStatus, etc.
│   │   └── interfaces.py # Contratos del dominio
│   ├── application/     # Casos de uso
│   │   ├── trend_bot_cycle_use_case.py
│   │   └── service_lifecycle_use_case.py
│   ├── infrastructure/  # Adaptadores externos
│   │   ├── brain_directive_repository.py  # Directivas del cerebro
│   │   ├── exchange_service.py           # CCXT para Binance
│   │   ├── notification_service.py       # Telegram
│   │   ├── trend_bot_repository.py       # Persistencia JSON
│   │   └── state_manager.py              # Gestión de estado
│   ├── config.py        # Configuración
│   └── main.py         # Punto de entrada
├── data/               # Archivos de persistencia
├── logs/              # Archivos de log
├── Dockerfile         # Contenedor Docker
├── requirements.txt   # Dependencias Python
└── README.md         # Esta documentación
```

## Estados del Bot

### FUERA_DEL_MERCADO
- Espera directiva `INICIAR_COMPRA_TENDENCIA` del cerebro
- No tiene posiciones abiertas
- Listo para entrar al mercado

### EN_POSICION_LARGA
- Tiene una posición abierta
- Monitorea precio para trailing stop
- Espera directiva `CERRAR_POSICION` del cerebro
- Actualiza `highest_price_since_entry`

## Lógica de Operación

### 1. Ciclo Principal (cada 1 hora)
1. **Consultar estado**: Obtener estado actual del bot
2. **Leer directiva**: Obtener última directiva del cerebro desde `estrategia_status`
3. **Obtener precio**: Consultar precio actual del símbolo
4. **Ejecutar lógica**: Según estado y directiva
5. **Actualizar estado**: Guardar estado actualizado

### 2. Lógica de Entrada
- **Estado**: FUERA_DEL_MERCADO
- **Directiva**: INICIAR_COMPRA_TENDENCIA
- **Acción**: Ejecutar orden de compra a mercado con 100% del capital
- **Resultado**: Cambiar a EN_POSICION_LARGA

### 3. Lógica de Mantenimiento
- **Estado**: EN_POSICION_LARGA
- **Directiva**: MANTENER_POSICION
- **Acción**: Solo actualizar `highest_price_since_entry`
- **Resultado**: Mantener posición

### 4. Lógica de Salida Táctica (Trailing Stop)
- **Estado**: EN_POSICION_LARGA
- **Condición**: Precio actual ≤ Trailing Stop
- **Acción**: Ejecutar orden de venta a mercado
- **Resultado**: Cambiar a FUERA_DEL_MERCADO

### 5. Lógica de Salida Estratégica
- **Estado**: EN_POSICION_LARGA
- **Directiva**: CERRAR_POSICION
- **Acción**: Ejecutar orden de venta a mercado
- **Resultado**: Cambiar a FUERA_DEL_MERCADO

## Configuración

### Variables de Entorno

```bash
# Configuración del bot
TREND_SYMBOL=BTCUSDT                    # Par a operar
TREND_CAPITAL_ALLOCATION=1000           # Capital en USDT
TREND_TRAILING_STOP_PERCENT=5.0         # % de trailing stop

# Intervalo de ciclo
TREND_CYCLE_INTERVAL_HOURS=1            # Horas entre ciclos

# Logging
TREND_LOG_LEVEL=INFO
TREND_LOG_FILE=logs/trend_bot.log

# Heredadas de settings.py
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
BINANCE_TESTNET=true
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
DATABASE_URL=your_database_url
```

### Ejemplo de Configuración

```python
bot_config = TrendBotConfig(
    symbol="BTCUSDT",
    capital_allocation=Decimal("1000"),  # $1000
    trailing_stop_percent=5.0,           # 5%
    sandbox_mode=True                    # Testnet
)
```

## Uso

### Desarrollo Local

```bash
# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
export TREND_SYMBOL=BTCUSDT
export TREND_CAPITAL_ALLOCATION=1000
export TREND_TRAILING_STOP_PERCENT=5.0

# Ejecutar el servicio
python -m services.trend.app.main
```

### Docker

```bash
# Construir imagen
docker build -t trend-bot services/trend/

# Ejecutar contenedor
docker run -d \
  --name trend-bot \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/data:/app/data \
  trend-bot
```

### Docker Compose

```bash
# Ejecutar todos los servicios
docker-compose up trend

# Ver logs
docker-compose logs -f trend
```

## Persistencia de Estado

El bot mantiene su estado en archivos JSON:

- `data/trend_bot_status.json`: Estado actual del bot
- `data/trend_positions.json`: Historial de posiciones
- `data/trend_metrics.json`: Métricas de rendimiento

### Ejemplo de Estado

```json
{
  "trend_bot_BTCUSDT_abc123": {
    "bot_id": "trend_bot_BTCUSDT_abc123",
    "symbol": "BTCUSDT",
    "state": "EN_POSICION_LARGA",
    "current_position": {
      "id": "pos_123",
      "entry_price": "45000.00",
      "entry_quantity": "0.02222222",
      "highest_price_since_entry": "47000.00"
    },
    "last_decision": "MANTENER_POSICION",
    "last_update": "2024-01-15T14:30:00"
  }
}
```

## Notificaciones

El bot envía notificaciones detalladas por Telegram:

### Posición Abierta
```
🚀 POSICIÓN ABIERTA - TREND BOT 🚀

🪙 Par: BTCUSDT
💰 Precio Entrada: $45,000.00
📦 Cantidad: 0.022222
💵 Valor: $1,000.00
🛑 Trailing Stop: 5.0%
💸 Comisiones: $1.00

⏰ Tiempo: 2024-01-15 14:30 UTC

📊 Configuración:
• Capital: $1,000.00
• Modo: Testnet
```

### Salida por Trailing Stop
```
🛑 SALIDA POR TRAILING STOP 🛑

🪙 Par: BTCUSDT
💰 Precio Entrada: $45,000.00
📈 Precio Máximo: $47,000.00
📉 Precio Actual: $44,650.00
🛑 Trailing Stop: $44,650.00
🏁 Precio Salida: $44,650.00
📦 Cantidad: 0.022222
✅ PnL: -$7.78 (-0.78%)
💸 Comisiones: $2.00

⏰ Tiempo: 2024-01-15 16:30 UTC
```

## Integración con el Cerebro

El bot lee las directivas del cerebro desde la tabla `estrategia_status`:

```sql
SELECT * FROM estrategia_status 
WHERE par = 'BTCUSDT' AND estrategia = 'TREND' 
ORDER BY timestamp DESC LIMIT 1;
```

### Decisiones Soportadas

- `INICIAR_COMPRA_TENDENCIA`: Abrir posición
- `MANTENER_POSICION`: Mantener posición actual
- `CERRAR_POSICION`: Cerrar posición por señal del cerebro

## Monitoreo

### Logs

Los logs se almacenan en:
- **Archivo**: `logs/trend_bot.log`
- **Consola**: Salida estándar
- **Niveles**: DEBUG, INFO, WARNING, ERROR

### Métricas

El bot calcula y almacena métricas de rendimiento:

- Total de trades
- Win rate
- PnL total
- Mejor/peor trade
- Tiempo promedio de retención
- Profit factor

### Health Check

El bot incluye verificaciones de salud:

- Conexión con Binance
- Acceso a base de datos
- Estado de archivos de persistencia
- Validación de configuración

## Troubleshooting

### Problemas Comunes

1. **No recibe directivas del cerebro**
   - Verificar tabla `estrategia_status`
   - Comprobar que `estrategia = 'TREND'`
   - Revisar logs del cerebro

2. **Errores de trading**
   - Verificar credenciales de Binance
   - Comprobar balance disponible
   - Revisar símbolo configurado

3. **Estado inconsistente**
   - Verificar archivos en `data/`
   - Revisar logs de persistencia
   - Reiniciar servicio si es necesario

### Logs Útiles

```bash
# Ver solo errores
grep "ERROR" logs/trend_bot.log

# Seguir logs en tiempo real
tail -f logs/trend_bot.log

# Filtrar por símbolo
grep "BTCUSDT" logs/trend_bot.log
```

## Desarrollo

### Estructura del Código

El proyecto sigue **Arquitectura Limpia**:

- **Domain**: Lógica de negocio pura
- **Application**: Casos de uso y orchestación
- **Infrastructure**: Adaptadores externos

### Principios SOLID

- **S**: Cada clase tiene una responsabilidad
- **O**: Extensible sin modificar código existente
- **L**: Interfaces intercambiables
- **I**: Interfaces específicas por funcionalidad
- **D**: Dependencias inyectadas via interfaces

### Testing

```bash
# Ejecutar tests
python -m pytest services/trend/tests/

# Con cobertura
python -m pytest --cov=services.trend services/trend/tests/
```

## Contribución

1. Fork el repositorio
2. Crea una rama para tu feature
3. Implementa siguiendo la arquitectura existente
4. Añade tests para tu código
5. Envía un Pull Request

## Licencia

MIT License - ver archivo LICENSE para detalles. 
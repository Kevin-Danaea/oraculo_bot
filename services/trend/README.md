# Trend Following Bot

Bot de trading automático que sigue tendencias alcistas en el mercado de criptomonedas.

## Descripción

El Trend Following Bot es un servicio autónomo que:

- 🔍 **Analiza tendencias** del mercado usando indicadores técnicos
- 📈 **Detecta señales alcistas** con alta probabilidad de éxito
- 💰 **Ejecuta trades automáticos** siguiendo la tendencia
- 🛡️ **Gestiona riesgo** con stop loss y take profit
- 📊 **Monitorea posiciones** en tiempo real
- 📱 **Notifica en Telegram** sobre todas las operaciones

## Diferencias con Grid Bot

A diferencia del Grid Bot que mantiene múltiples órdenes:

- **Una sola posición por símbolo**: Se enfoca en seguir una tendencia específica
- **Dirección alcista**: Solo opera en tendencias bullish
- **Hold hasta objetivo**: Mantiene la posición hasta alcanzar take profit o stop loss
- **Trailing stop**: Puede mover el stop loss para maximizar ganancias

## Características Principales

### 🎯 Estrategia de Trading
- **Trend Following**: Sigue tendencias alcistas confirmadas
- **Análisis técnico**: Usa EMA, RSI, volumen y otros indicadores
- **Gestión de riesgo**: Stop loss y take profit automáticos
- **Trailing stop**: Optimiza las ganancias siguiendo el precio

### 🔧 Configuración Flexible
- **Múltiples timeframes**: Análisis en 4h con confirmación en 1h
- **Filtros de calidad**: Solo señales con alta confianza
- **Tamaño de posición**: Calculado automáticamente según el capital
- **Personalizable**: Parámetros ajustables por símbolo

### 📊 Monitoreo y Métricas
- **Tiempo real**: Actualización constante de posiciones
- **Métricas completas**: Win rate, profit factor, drawdown
- **Notificaciones**: Alertas en Telegram para todos los eventos
- **Logging detallado**: Registro completo de operaciones

## Arquitectura

```
services/trend/
├── app/
│   ├── domain/          # Entidades y reglas de negocio
│   │   ├── entities.py  # TrendSignal, TrendPosition, etc.
│   │   └── interfaces.py # Contratos del dominio
│   ├── application/     # Casos de uso
│   │   ├── analyze_market_use_case.py
│   │   ├── execute_trades_use_case.py
│   │   ├── manage_positions_use_case.py
│   │   └── service_lifecycle_use_case.py
│   ├── infrastructure/  # Adaptadores externos
│   │   ├── exchange_service.py       # CCXT para Binance
│   │   ├── notification_service.py   # Telegram
│   │   ├── trend_analyzer.py         # Análisis técnico
│   │   ├── position_manager.py       # Gestión de posiciones
│   │   ├── risk_manager.py          # Gestión de riesgo
│   │   └── database_repository.py   # Persistencia
│   ├── config.py        # Configuración
│   └── main.py         # Punto de entrada
├── tests/              # Pruebas unitarias
├── logs/              # Archivos de log
├── Dockerfile         # Contenedor Docker
├── requirements.txt   # Dependencias Python
└── README.md         # Esta documentación
```

## Configuración

### Variables de Entorno

```bash
# Configuración del bot
TREND_ANALYSIS_TIMEFRAME=4h
TREND_CONFIRMATION_TIMEFRAME=1h
TREND_MIN_SIGNAL_CONFIDENCE=0.7
TREND_MAX_POSITIONS_PER_SYMBOL=1

# Gestión de riesgo
TREND_DEFAULT_STOP_LOSS_PERCENT=3.0
TREND_DEFAULT_TAKE_PROFIT_PERCENT=9.0
TREND_DEFAULT_TRAILING_STOP_PERCENT=2.0
TREND_MAX_POSITION_SIZE_PERCENT=10.0

# Intervalos de ejecución (minutos)
TREND_MARKET_ANALYSIS_INTERVAL=15
TREND_TRADE_EXECUTION_INTERVAL=5
TREND_POSITION_MANAGEMENT_INTERVAL=2

# Logging
TREND_LOG_LEVEL=INFO
TREND_LOG_FILE=logs/trend_bot.log
```

### Configuración de Estrategias

Las estrategias se configuran en la base de datos para cada símbolo:

```python
strategy = TrendStrategy(
    name="BTC-Trend",
    symbol="BTCUSDT", 
    enabled=True,
    capital_allocation=Decimal("1000"),  # $1000 por estrategia
    max_position_size=Decimal("500"),    # Máximo $500 por posición
    min_position_size=Decimal("50"),     # Mínimo $50
    stop_loss_percentage=3.0,            # 3% stop loss
    take_profit_percentage=9.0,          # 9% take profit
    trailing_stop_percentage=2.0,        # 2% trailing stop
    max_positions=1,                     # Una posición a la vez
    min_signal_strength=SignalStrength.MODERATE,
    min_confidence=0.7                   # 70% confianza mínima
)
```

## Uso

### Desarrollo Local

```bash
# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

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
  trend-bot
```

### Docker Compose

```bash
# Ejecutar todos los servicios
docker-compose up trend

# Ver logs
docker-compose logs -f trend
```

## Monitoreo

### Logs

Los logs se almacenan en:
- **Archivo**: `logs/trend_bot.log`
- **Consola**: Salida estándar
- **Niveles**: DEBUG, INFO, WARNING, ERROR

### Métricas en Telegram

El bot envía actualizaciones periódicas:

- 🔥 **Nuevas señales** detectadas
- 🚀 **Posiciones abiertas** con detalles
- ✅ **Posiciones cerradas** con PnL
- 📊 **Resumen diario** de rendimiento
- ⚠️ **Alertas de error** si hay problemas

### Ejemplo de Notificación

```
🔥 NUEVA SEÑAL TREND 🔥

🪙 Par: BTCUSDT
📈 Dirección: BULLISH
💪 Fuerza: STRONG
💰 Precio Entrada: $45,230.50
🛑 Stop Loss: $43,873.59
🎯 Take Profit: $49,301.25
🎲 Confianza: 85.2%
⚖️ R/R Ratio: 3.00

⏰ Tiempo: 2024-01-15 14:30 UTC
```

## Algoritmo de Trading

### 1. Análisis de Mercado (cada 15 min)
- Obtiene datos de precio históricos
- Calcula indicadores técnicos (EMA, RSI, volumen)
- Detecta patrones de tendencia alcista
- Genera señales con score de confianza

### 2. Validación de Señales (cada 5 min)
- Verifica calidad de la señal
- Comprueba gestión de riesgo
- Calcula tamaño óptimo de posición
- Ejecuta orden si pasa todos los filtros

### 3. Gestión de Posiciones (cada 2 min)
- Monitorea precio actual vs stop/take profit
- Actualiza trailing stop si está configurado
- Cierra posición si se alcanzan los objetivos
- Actualiza métricas de rendimiento

### 4. Indicadores Utilizados

- **EMA 20/50**: Tendencia principal
- **RSI**: Momentum y sobrecompra/sobreventa
- **Volumen**: Confirmación de movimientos
- **ATR**: Volatilidad para stop loss
- **Soportes/Resistencias**: Niveles clave

## Gestión de Riesgo

### Tamaño de Posición
```python
position_size = min(
    capital_allocation * position_percent / 100,
    max_position_size,
    available_balance * max_exposure / 100
)
```

### Stop Loss Dinámico
- **Fijo**: Porcentaje desde precio de entrada
- **ATR**: Basado en volatilidad reciente
- **Trailing**: Se mueve con el precio favorable

### Limits de Exposición
- **Por símbolo**: Una posición máxima
- **Total**: No más del 50% del capital
- **Por operación**: Máximo 10% del capital

## Troubleshooting

### Problemas Comunes

1. **No se generan señales**
   - Verificar configuración de timeframes
   - Revisar filtros de confianza
   - Comprobar datos de mercado

2. **Órdenes fallan**
   - Verificar credenciales de Binance
   - Comprobar balance disponible
   - Revisar símbolos configurados

3. **Notificaciones no llegan**
   - Verificar token de Telegram
   - Comprobar chat ID
   - Revisar logs de errores

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
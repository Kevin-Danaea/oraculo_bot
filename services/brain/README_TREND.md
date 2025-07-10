# Brain Service - Análisis de Tendencia (TREND)

## Descripción

El Brain Service ha sido expandido para soportar análisis y decisiones específicas para la estrategia **TREND**, de forma independiente a la estrategia **GRID**.

## Nuevas Funcionalidades

### 1. Indicadores Específicos para TREND

- **SMA30**: Media Móvil Simple de 30 periodos
- **SMA150**: Media Móvil Simple de 150 periodos  
- **ADX14**: Average Directional Index de 14 periodos
- **Sentiment 7d**: Media móvil de sentimiento de 7 días

### 2. Estados de Posición

- **FUERA_DEL_MERCADO**: El bot no tiene posiciones abiertas
- **EN_POSICION**: El bot tiene una posición activa

### 3. Decisiones de TREND

- **INICIAR_COMPRA_TENDENCIA**: Señal de entrada cuando se cumplen todas las condiciones
- **CERRAR_POSICION**: Señal de salida cuando se detecta cruce de la muerte
- **MANTENER_ESPERA**: Esperar mejores condiciones para entrada
- **MANTENER_POSICION**: Mantener posición actual

## Lógica de Decisión

### Señales de Entrada (FUERA_DEL_MERCADO)

Se requiere que se cumplan **TODAS** estas condiciones:

1. **Cruce Dorado**: SMA30 > SMA150
2. **Fuerza de Tendencia**: ADX > 25
3. **Sentimiento Favorable**: Sentiment 7d > -0.1

### Señales de Salida (EN_POSICION)

Se requiere que se cumpla **UNA** de estas condiciones:

1. **Cruce de la Muerte**: SMA30 < SMA150

## Configuración

### Recetas Maestras para TREND

```python
TREND_MASTER_RECIPES = {
    'ETH/USDT': {
        'name': 'Receta TREND Maestra ETH',
        'conditions': {
            'adx_threshold': 30,
            'bollinger_bandwidth_threshold': 0.025,
            'sentiment_threshold': -0.20,
            'adx_trend_threshold': 25.0,  # ADX mínimo para tendencia
            'sentiment_trend_threshold': -0.1,  # Sentimiento mínimo
        },
        'trend_config': {
            'sma_short_period': 30,
            'sma_long_period': 150,
            'adx_period': 14,
            'sentiment_avg_days': 7,
        }
    }
}
```

## Ejemplo de Uso

### Análisis Individual de TREND

```python
from application.analyze_trend_use_case import AnalyzeTrendUseCase

# Crear instancia
trend_analyzer = AnalyzeTrendUseCase(
    market_data_repo=market_data_repo,
    decision_repo=decision_repo,
    recipe_repo=recipe_repo,
    notification_service=notification_service
)

# Ejecutar análisis para ETH/USDT
decision = await trend_analyzer.execute('ETH/USDT')

if decision:
    print(f"Decisión: {decision.decision.value}")
    print(f"Estado: {decision.current_state.value}")
    print(f"Razón: {decision.reason}")
    print(f"SMA30: {decision.indicators.sma30}")
    print(f"SMA150: {decision.indicators.sma150}")
    print(f"ADX: {decision.indicators.adx}")
    print(f"Sentimiento 7d: {decision.indicators.sentiment_7d_avg}")
```

### Análisis Batch Completo

El análisis batch ahora incluye automáticamente tanto GRID como TREND:

```python
from application.batch_analysis_use_case import BatchAnalysisUseCase

# Ejecutar análisis batch
result = await batch_analysis_use_case.execute()

print(f"Decisiones tomadas: {result['decisions_made']}")
print(f"Pares exitosos: {result['successful_pairs']}")
print(f"Duración: {result['duration_seconds']}s")
```

## Base de Datos

Las decisiones de TREND se almacenan en la tabla `estrategia_status` con:

- `estrategia = 'TREND'`
- `decision` = Una de las decisiones de TREND
- Indicadores específicos de tendencia
- Umbrales utilizados

## Monitoreo

### Logs de Análisis TREND

```
📈 ========== ANÁLISIS TREND PARA ETH/USDT ==========
📊 SMA30: 2450.50, SMA150: 2400.25
📊 Cruce Dorado: True
📊 Cruce de la Muerte: False
📊 ADX: 28.50, Fuerza OK: True
📊 Sentimiento 7d: 0.15, OK: True
🎯 Decisión TREND para ETH/USDT: INICIAR_COMPRA_TENDENCIA
📝 Razón: Estado: FUERA_DEL_MERCADO. Cruce Dorado detectado; ADX fuerte (28.50 > 25); Sentimiento favorable (0.150 > -0.1)
✅ ETH/USDT TREND: INICIAR_COMPRA_TENDENCIA - Estado: FUERA_DEL_MERCADO. Cruce Dorado detectado; ADX fuerte (28.50 > 25); Sentimiento favorable (0.150 > -0.1)
```

## Integración con Trend Bot

El Trend Bot consulta las decisiones del Brain Service desde la base de datos:

```python
# En el Trend Bot
from shared.database.models import EstrategiaStatus

# Obtener última decisión para ETH/USDT
latest_decision = db.query(EstrategiaStatus).filter(
    EstrategiaStatus.par == 'ETH/USDT',
    EstrategiaStatus.estrategia == 'TREND'
).order_by(EstrategiaStatus.timestamp.desc()).first()

if latest_decision.decision == 'INICIAR_COMPRA_TENDENCIA':
    # Ejecutar compra
    execute_buy_order('ETH/USDT')
elif latest_decision.decision == 'CERRAR_POSICION':
    # Ejecutar venta
    execute_sell_order('ETH/USDT')
```

## Ventajas de la Arquitectura

1. **Separación de Responsabilidades**: Brain toma decisiones, Trend Bot ejecuta
2. **Escalabilidad**: Fácil agregar nuevas estrategias
3. **Mantenibilidad**: Lógica centralizada en el Brain
4. **Consistencia**: Mismo patrón para GRID y TREND
5. **Monitoreo**: Logs detallados para debugging

## Próximas Mejoras

1. **Detección de Cruces**: Implementar detección real de cruces (no solo condición actual)
2. **Backtesting**: Validar parámetros con datos históricos
3. **Optimización**: Ajustar umbrales basado en performance
4. **Alertas**: Notificaciones específicas para señales importantes
5. **Métricas**: Dashboard para monitorear performance de decisiones 
# Brain Service - Motor de Decisiones de Trading

## Descripción

El **Brain Service** es el motor central de decisiones del sistema de trading. Funciona de manera completamente independiente, analizando el mercado cada hora y publicando sus decisiones en la base de datos para que los bots las consulten.

## Arquitectura

### Clean Architecture
- **Dominio**: Entidades y reglas de negocio puras
- **Aplicación**: Casos de uso que orquestan la lógica
- **Infraestructura**: Implementaciones concretas de repositorios y servicios

### Independencia Total
- ✅ **Sin dependencias externas**: No requiere otros servicios para funcionar
- ✅ **Comunicación por BD**: Las decisiones se publican en `estrategia_status`
- ✅ **Sin APIs innecesarias**: Solo endpoints básicos de salud
- ✅ **Preparado para Redis**: Arquitectura lista para comunicación en tiempo real

## Funcionalidades

### Análisis Continuo
- **Frecuencia**: Cada 1 hora automáticamente
- **Modo**: Análisis batch de todos los pares simultáneamente
- **Persistencia**: Decisiones guardadas en base de datos
- **Independencia**: Los bots consultan la BD para obtener decisiones

### Pares Soportados
- **ETH/USDT**: ADX < 30, Bollinger > 0.025, Rango 10%
- **BTC/USDT**: ADX < 25, Bollinger > 0.035, Rango 7.5%
- **AVAX/USDT**: ADX < 35, Bollinger > 0.020, Rango 10%

### Indicadores Analizados
- **ADX**: Fuerza de la tendencia
- **Bandas de Bollinger**: Volatilidad del mercado
- **Sentimiento (7 días)**: Promedio de sentimiento de los últimos 7 días, validado contra el umbral de la receta
- **RSI**: Momentum del precio
- **MACD**: Señales de tendencia
- **EMA 21/50**: Medias móviles

## Comunicación

### Base de Datos
```sql
-- Tabla donde se publican las decisiones
estrategia_status:
- par: Par de trading (ej: 'ETH/USDT')
- estrategia: Tipo de bot ('GRID')
- decision: 'OPERAR_GRID' o 'PAUSAR_GRID'
- razon: Explicación de la decisión
- adx_actual, volatilidad_actual, sentiment_promedio: Indicadores
- umbral_adx, umbral_volatilidad, umbral_sentimiento: Umbrales
- timestamp: Fecha/hora de la decisión
```

### Flujo de Comunicación
1. **Brain analiza** → Calcula indicadores y toma decisiones
2. **Brain publica** → Guarda decisiones en `estrategia_status`
3. **Bots consultan** → Leen la BD para obtener decisiones
4. **Bots actúan** → Operan o pausan según la decisión

### Preparado para Redis
La arquitectura está preparada para migrar a Redis en el futuro:
- ✅ Interfaces definidas para notificaciones
- ✅ Servicio de notificaciones modular
- ✅ Comentarios TODO para implementación Redis

## Endpoints

### Básicos (Solo Salud)
- **GET /**: Información del servicio
- **GET /health/**: Health check (incluye estado del brain)

### Sin Endpoints de Análisis
- ❌ No hay endpoints para análisis individual
- ❌ No hay endpoints para análisis batch manual
- ❌ No hay endpoints para consultar decisiones
- ❌ No hay endpoints para recetas

**Razón**: El brain es independiente y no debe ser contactado externamente.

## Instalación y Uso

### Desarrollo Local
```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar servicio
python run_brain_service.py
```

### Docker
```bash
# Construir imagen
docker build -t brain-service .

# Ejecutar contenedor
docker run -p 8000:8000 brain-service
```

### Docker Compose
```bash
# Incluir en docker-compose.yml
services:
  brain:
    build: ./services/brain
    ports:
      - "8000:8000"
    environment:
      - BINANCE_API_KEY=${BINANCE_API_KEY}
      - BINANCE_API_SECRET=${BINANCE_API_SECRET}
    volumes:
      - ./logs:/app/logs
```

## Configuración

### Variables de Entorno
```bash
# Binance API
BINANCE_API_KEY=tu_api_key
BINANCE_API_SECRET=tu_api_secret

# Base de datos
DATABASE_URL=postgresql://user:pass@localhost:5432/oraculo_bot

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/brain.log
```

### Configuración de Análisis
```python
# services/brain/app/config.py
ANALYSIS_INTERVAL = 3600  # 1 hora en segundos
SUPPORTED_PAIRS = ['ETH/USDT', 'BTC/USDT', 'AVAX/USDT']
```

## Monitoreo

### Health Check
```bash
curl http://localhost:8000/health/
```

Respuesta:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00",
  "service": "brain",
  "is_running": true,
  "analysis_task_active": true,
  "cycle_count": 24,
  "last_analysis_time": "2024-01-01T11:00:00",
  "total_decisions_processed": 72,
  "successful_decisions": 70,
  "failed_decisions": 2
}
```

### Logs
```bash
# Ver logs en tiempo real
tail -f logs/brain.log

# Buscar errores
grep "ERROR" logs/brain.log

# Ver análisis batch
grep "ANÁLISIS BATCH" logs/brain.log
```

## Integración con Bots

### Consulta de Decisiones
Los bots deben consultar la base de datos cada hora:

```python
# Ejemplo de consulta para obtener última decisión
from shared.database.session import SessionLocal
from shared.database.models import EstrategiaStatus

def get_latest_decision(pair: str, bot_type: str = 'GRID'):
    db = SessionLocal()
    try:
        decision = db.query(EstrategiaStatus).filter(
            EstrategiaStatus.par == pair,
            EstrategiaStatus.estrategia == bot_type
        ).order_by(EstrategiaStatus.timestamp.desc()).first()
        
        return decision
    finally:
        db.close()
```

### Verificación de Cambios
```python
# Verificar si hay nueva decisión
last_decision = get_latest_decision('ETH/USDT')
if last_decision and last_decision.timestamp > last_check:
    if last_decision.decision == 'OPERAR_GRID':
        start_grid_bot()
    elif last_decision.decision == 'PAUSAR_GRID':
        stop_grid_bot()
```

## Ejemplos Prácticos y Casos de Uso

### 🎯 **Caso de Uso 1: Inicio del Sistema**

#### Escenario
El sistema se inicia por primera vez y el brain comienza a analizar el mercado.

#### Flujo Completo
```python
# 1. Brain inicia automáticamente
python run_brain_service.py

# 2. Logs de inicio
"""
🎯 ========== INICIANDO BRAIN SERVICE ==========
🧠 Brain Service - Motor de Decisiones de Trading (Clean Architecture)
📋 Configuración:
   📊 Pares soportados: 3
   🔢 Pares: ETH/USDT, BTC/USDT, AVAX/USDT
   ⏰ Intervalo de análisis: 3600s
   📁 Log level: INFO
🧠 Recetas maestras cargadas para cada par
🚀 Iniciando servicio brain...
✅ Brain service iniciado correctamente
"""

# 3. Primer análisis batch automático
"""
🚀 ========== INICIANDO ANÁLISIS BATCH ==========
📊 Analizando 3 pares: ETH/USDT, BTC/USDT, AVAX/USDT
📈 Analizando ETH/USDT...
📊 Obteniendo datos para ETH/USDT (4h, 40 días)...
✅ Obtenidos 240 registros para ETH/USDT
📰 Obteniendo datos de sentimiento de la base de datos...
✅ Datos de sentimiento agregados: 15 días
✅ Indicadores calculados para ETH/USDT
✅ ETH/USDT: OPERAR_GRID - Condiciones favorables: ADX=25.30<30, Vol=0.0280>0.0250
📈 Analizando BTC/USDT...
✅ BTC/USDT: PAUSAR_GRID - Condiciones desfavorables: ADX=32.15>=25
📈 Analizando AVAX/USDT...
✅ AVAX/USDT: OPERAR_GRID - Condiciones favorables: ADX=28.45<35, Vol=0.0225>0.0200
🎯 ========== ANÁLISIS BATCH COMPLETADO ==========
✅ Pares exitosos: 3/3
❌ Pares fallidos: 0/3
⏱️ Duración: 45.23s
🔄 Ciclo: 1
"""
```

#### Resultado en Base de Datos
```sql
-- Tabla estrategia_status después del primer análisis
SELECT par, decision, razon, adx_actual, volatilidad_actual, timestamp 
FROM estrategia_status 
ORDER BY timestamp DESC LIMIT 3;

-- Resultado:
-- ETH/USDT | OPERAR_GRID | Condiciones favorables: ADX=25.30<30, Vol=0.0280>0.0250 | 25.30 | 0.0280 | 2024-01-01 12:00:00
-- BTC/USDT | PAUSAR_GRID | Condiciones desfavorables: ADX=32.15>=25 | 32.15 | 0.0310 | 2024-01-01 12:00:00  
-- AVAX/USDT | OPERAR_GRID | Condiciones favorables: ADX=28.45<35, Vol=0.0225>0.0200 | 28.45 | 0.0225 | 2024-01-01 12:00:00
```

### 🎯 **Caso de Uso 2: Cambio de Condiciones de Mercado**

#### Escenario
El mercado cambia y ETH/USDT pasa de condiciones favorables a desfavorables.

#### Flujo Completo
```python
# 1. Análisis anterior (hora 12:00)
# ETH/USDT: OPERAR_GRID - ADX=25.30, Vol=0.0280

# 2. Mercado cambia (hora 13:00)
# ETH/USDT: ADX sube a 35.20, Vol baja a 0.0200

# 3. Brain detecta cambio automáticamente
"""
🚀 ========== INICIANDO ANÁLISIS BATCH ==========
📊 Analizando 3 pares: ETH/USDT, BTC/USDT, AVAX/USDT
📈 Analizando ETH/USDT...
✅ Indicadores calculados para ETH/USDT
✅ ETH/USDT: PAUSAR_GRID - Condiciones desfavorables: ADX=35.20>=30, Vol=0.0200<=0.0250
🔔 Notificación de cambio de decisión:
   📊 Par: ETH/USDT
   🤖 Bot: GRID
   📈 Decisión: PAUSAR_GRID
   📝 Razón: Condiciones desfavorables: ADX=35.20>=30, Vol=0.0200<=0.0250
   ⏰ Timestamp: 2024-01-01 13:00:00
"""
```

#### Resultado en Base de Datos
```sql
-- Nueva entrada en estrategia_status
INSERT INTO estrategia_status (
    par, estrategia, decision, razon, 
    adx_actual, volatilidad_actual, sentiment_promedio,
    umbral_adx, umbral_volatilidad, umbral_sentimiento,
    timestamp
) VALUES (
    'ETH/USDT', 'GRID', 'PAUSAR_GRID',
    'Condiciones desfavorables: ADX=35.20>=30, Vol=0.0200<=0.0250',
    35.20, 0.0200, 0.65,
    30.0, 0.025, 0.5,
    '2024-01-01 13:00:00'
);
```

### 🎯 **Caso de Uso 3: Integración con GRID Bot**

#### Escenario
El GRID bot consulta la base de datos para obtener la última decisión del brain.

#### Flujo Completo
```python
# 1. GRID bot consulta cada hora
from shared.database.session import SessionLocal
from shared.database.models import EstrategiaStatus
from datetime import datetime, timedelta

def check_brain_decision(pair: str = 'ETH/USDT'):
    db = SessionLocal()
    try:
        # Obtener última decisión
        latest_decision = db.query(EstrategiaStatus).filter(
            EstrategiaStatus.par == pair,
            EstrategiaStatus.estrategia == 'GRID'
        ).order_by(EstrategiaStatus.timestamp.desc()).first()
        
        if not latest_decision:
            print(f"❌ No hay decisión para {pair}")
            return None
        
        # Verificar si la decisión es reciente (última hora)
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        if latest_decision.timestamp < one_hour_ago:
            print(f"⚠️ Decisión antigua para {pair}: {latest_decision.timestamp}")
        
        print(f"📊 Última decisión para {pair}:")
        print(f"   🤖 Decisión: {latest_decision.decision}")
        print(f"   📝 Razón: {latest_decision.razon}")
        print(f"   📈 ADX: {latest_decision.adx_actual}")
        print(f"   📊 Volatilidad: {latest_decision.volatilidad_actual}")
        print(f"   ⏰ Timestamp: {latest_decision.timestamp}")
        
        return latest_decision
        
    finally:
        db.close()

# 2. Ejecutar consulta
decision = check_brain_decision('ETH/USDT')

# 3. Salida esperada
"""
📊 Última decisión para ETH/USDT:
   🤖 Decisión: PAUSAR_GRID
   📝 Razón: Condiciones desfavorables: ADX=35.20>=30, Vol=0.0200<=0.0250
   📈 ADX: 35.20
   📊 Volatilidad: 0.0200
   ⏰ Timestamp: 2024-01-01 13:00:00
"""

# 4. GRID bot toma acción
if decision.decision == 'OPERAR_GRID':
    print("🚀 Iniciando GRID bot para ETH/USDT")
    start_grid_trading('ETH/USDT')
elif decision.decision == 'PAUSAR_GRID':
    print("⏸️ Pausando GRID bot para ETH/USDT")
    stop_grid_trading('ETH/USDT')
```

### 🎯 **Caso de Uso 4: Manejo de Errores**

#### Escenario
El brain encuentra un error al obtener datos de mercado para un par.

#### Flujo Completo
```python
# 1. Error en obtención de datos
"""
📈 Analizando BTC/USDT...
📊 Obteniendo datos para BTC/USDT (4h, 40 días)...
❌ Error obteniendo datos para BTC/USDT: Connection timeout
❌ Error analizando BTC/USDT: Connection timeout
🔔 Notificación de error:
   ❌ Error: Error analizando BTC/USDT
   📋 Contexto: {'pair': 'BTC/USDT', 'error': 'Connection timeout'}
"""

# 2. Decisión de error guardada en BD
"""
INSERT INTO estrategia_status (
    par, estrategia, decision, razon, 
    adx_actual, volatilidad_actual, sentiment_promedio,
    umbral_adx, umbral_volatilidad, umbral_sentimiento,
    timestamp
) VALUES (
    'BTC/USDT', 'GRID', 'ERROR',
    'Error en análisis: Connection timeout',
    NULL, NULL, NULL,
    25.0, 0.035, 0.5,
    '2024-01-01 14:00:00'
);
"""

# 3. GRID bot maneja decisión de error
def handle_brain_decision(decision):
    if decision.decision == 'ERROR':
        print(f"⚠️ Error en brain para {decision.pair}: {decision.razon}")
        print("🔄 Manteniendo estado actual del bot")
        # No cambiar el estado del bot, mantener el último estado válido
        return 'MAINTAIN_CURRENT_STATE'
    elif decision.decision == 'OPERAR_GRID':
        return 'START_TRADING'
    elif decision.decision == 'PAUSAR_GRID':
        return 'STOP_TRADING'
```

### 🎯 **Caso de Uso 5: Monitoreo y Health Check**

#### Escenario
Administrador verifica el estado del brain y su rendimiento.

#### Flujo Completo
```bash
# 1. Health check del servicio
curl http://localhost:8000/health/

# 2. Respuesta esperada
{
  "status": "healthy",
  "timestamp": "2024-01-01T15:00:00",
  "service": "brain",
  "is_running": true,
  "analysis_task_active": true,
  "cycle_count": 3,
  "last_analysis_time": "2024-01-01T14:00:00",
  "total_decisions_processed": 9,
  "successful_decisions": 8,
  "failed_decisions": 1
}

# 3. Verificar logs
tail -f logs/brain.log

# 4. Salida esperada
"""
2024-01-01 15:00:00 - INFO - 🔄 ========== INICIANDO ANÁLISIS BATCH ==========
2024-01-01 15:00:00 - INFO - 📊 Analizando 3 pares: ETH/USDT, BTC/USDT, AVAX/USDT
2024-01-01 15:00:01 - INFO - ✅ ETH/USDT: OPERAR_GRID - Condiciones favorables
2024-01-01 15:00:02 - INFO - ✅ BTC/USDT: OPERAR_GRID - Condiciones favorables
2024-01-01 15:00:03 - INFO - ✅ AVAX/USDT: PAUSAR_GRID - Condiciones desfavorables
2024-01-01 15:00:03 - INFO - 🎯 ========== ANÁLISIS BATCH COMPLETADO ==========
2024-01-01 15:00:03 - INFO - ✅ Pares exitosos: 3/3
2024-01-01 15:00:03 - INFO - ⏱️ Duración: 3.45s
2024-01-01 15:00:03 - INFO - 🔄 Ciclo: 3
"""

# 5. Verificar estadísticas en BD
SELECT 
    decision,
    COUNT(*) as count,
    AVG(adx_actual) as avg_adx,
    AVG(volatilidad_actual) as avg_volatility
FROM estrategia_status 
WHERE timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY decision;

-- Resultado esperado:
-- OPERAR_GRID | 15 | 24.5 | 0.028
-- PAUSAR_GRID | 6  | 32.1 | 0.018
-- ERROR       | 1  | NULL | NULL
```

### 🎯 **Caso de Uso 6: Escalabilidad - Agregar Nuevo Par**

#### Escenario
Se quiere agregar un nuevo par de trading al sistema.

#### Flujo Completo
```python
# 1. Agregar nuevo par en config.py
SUPPORTED_PAIRS = ['ETH/USDT', 'BTC/USDT', 'AVAX/USDT', 'SOL/USDT']

# 2. Agregar receta en recipe_repository.py
SOL_USDT_RECIPE = TradingRecipe(
    pair='SOL/USDT',
    name='SOL Grid Strategy',
    conditions={
        'adx_threshold': 40,
        'bollinger_bandwidth_threshold': 0.030,
        'sentiment_threshold': 0.4
    },
    grid_config={
        'range_percentage': 12,
        'grid_levels': 10,
        'investment_per_level': 50
    },
    description='Estrategia GRID para SOL/USDT con alta volatilidad',
    bot_type=BotType.GRID
)

# 3. Reiniciar brain service
# El brain automáticamente comenzará a analizar SOL/USDT

# 4. Logs esperados
"""
🎯 ========== INICIANDO BRAIN SERVICE ==========
📋 Configuración:
   📊 Pares soportados: 4
   🔢 Pares: ETH/USDT, BTC/USDT, AVAX/USDT, SOL/USDT
   
🚀 ========== INICIANDO ANÁLISIS BATCH ==========
📊 Analizando 4 pares: ETH/USDT, BTC/USDT, AVAX/USDT, SOL/USDT
📈 Analizando SOL/USDT...
✅ SOL/USDT: OPERAR_GRID - Condiciones favorables: ADX=28.30<40, Vol=0.0350>0.0300
"""

# 5. Nueva entrada en BD
"""
INSERT INTO estrategia_status (
    par, estrategia, decision, razon, 
    adx_actual, volatilidad_actual, sentiment_promedio,
    umbral_adx, umbral_volatilidad, umbral_sentimiento,
    timestamp
) VALUES (
    'SOL/USDT', 'GRID', 'OPERAR_GRID',
    'Condiciones favorables: ADX=28.30<40, Vol=0.0350>0.0300',
    28.30, 0.0350, 0.72,
    40.0, 0.030, 0.4,
    '2024-01-01 16:00:00'
);
"""
```

### 🎯 **Caso de Uso 7: Preparación para Redis**

#### Escenario
Se quiere migrar de notificaciones por logs a Redis para comunicación en tiempo real.

#### Flujo Completo
```python
# 1. Implementar Redis en notification_service.py
import redis.asyncio as redis

class RedisNotificationService(NotificationService):
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.channels = {
            BotType.GRID: 'brain:grid:decisions',
            BotType.TREND_FOLLOWING: 'brain:trend:decisions',
            BotType.DCA_FUTURES: 'brain:dca:decisions'
        }
    
    async def notify_decision_change(self, decision: TradingDecision) -> bool:
        try:
            channel = self.channels.get(decision.bot_type, 'brain:general')
            message = {
                'pair': decision.pair,
                'decision': decision.decision.value,
                'reason': decision.reason,
                'indicators': {
                    'adx': decision.indicators.adx,
                    'volatility': decision.indicators.volatility,
                    'sentiment': decision.indicators.sentiment
                },
                'timestamp': decision.timestamp.isoformat()
            }
            
            await self.redis_client.publish(channel, json.dumps(message))
            return True
        except Exception as e:
            logger.error(f"Error enviando notificación Redis: {e}")
            return False

# 2. GRID bot escucha Redis
import redis.asyncio as redis
import json

async def listen_brain_decisions():
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe('brain:grid:decisions')
    
    async for message in pubsub.listen():
        if message['type'] == 'message':
            decision_data = json.loads(message['data'])
            print(f"🔔 Nueva decisión recibida: {decision_data}")
            
            if decision_data['decision'] == 'OPERAR_GRID':
                await start_grid_bot(decision_data['pair'])
            elif decision_data['decision'] == 'PAUSAR_GRID':
                await stop_grid_bot(decision_data['pair'])

# 3. Ejecutar listener
asyncio.run(listen_brain_decisions())

# 4. Salida esperada
"""
🔔 Nueva decisión recibida: {
  'pair': 'ETH/USDT',
  'decision': 'PAUSAR_GRID',
  'reason': 'Condiciones desfavorables: ADX=35.20>=30',
  'indicators': {
    'adx': 35.20,
    'volatility': 0.0200,
    'sentiment': 0.65
  },
  'timestamp': '2024-01-01T17:00:00'
}
⏸️ Pausando GRID bot para ETH/USDT
"""
```

## Próximos Pasos

### Redis Integration
1. **Implementar cliente Redis** en `notification_service.py`
2. **Configurar canales** para cada tipo de bot
3. **Migrar notificaciones** de logs a Redis
4. **Actualizar bots** para escuchar Redis

### LLM Integration
1. **Integrar modelo de lenguaje** para análisis avanzado
2. **Mejorar razones** de decisiones con IA
3. **Análisis de sentimiento** más sofisticado
4. **Predicciones** de mercado

### Monitoreo Avanzado
1. **Métricas Prometheus** para monitoreo
2. **Alertas automáticas** para errores
3. **Dashboard Grafana** para visualización
4. **Trazabilidad** completa de decisiones

## Estructura del Proyecto

```
services/brain/
├── app/
│   ├── domain/           # Entidades y reglas de negocio
│   │   ├── entities.py   # Entidades principales
│   │   └── interfaces.py # Contratos/Interfaces
│   ├── application/      # Casos de uso
│   │   ├── analyze_pair_use_case.py
│   │   ├── batch_analysis_use_case.py
│   │   └── service_lifecycle_use_case.py
│   ├── infrastructure/   # Implementaciones concretas
│   │   ├── market_data_repository.py
│   │   ├── recipe_repository.py
│   │   ├── decision_repository.py
│   │   ├── notification_service.py
│   │   └── brain_status_repository.py
│   ├── config.py         # Configuración centralizada
│   └── main.py           # Aplicación FastAPI
├── requirements.txt      # Dependencias
├── Dockerfile           # Imagen Docker
├── run_brain_service.py # Script de ejecución
└── README.md           # Documentación
```

## Contribución

1. **Seguir Clean Architecture** en todas las modificaciones
2. **Mantener independencia** del brain
3. **Documentar cambios** en el código
4. **Probar funcionalidad** antes de commit
5. **Actualizar README** si es necesario

## Licencia

Este proyecto es parte del sistema Oráculo Bot y está bajo licencia privada. 
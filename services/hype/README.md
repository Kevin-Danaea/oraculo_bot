# Servicio Hype - Detector de Tendencias en Reddit

## Descripción

El **Servicio Hype** es un microservicio especializado en detectar tendencias emergentes de criptomonedas mediante el análisis de menciones en subreddits específicos de Reddit. Utiliza análisis de volumen para identificar aumentos significativos en la actividad de discusión sobre tickers específicos y envía alertas en tiempo real a través de Telegram.

## Funcionalidades Principales

### 🔍 Detección de Tendencias
- **Monitoreo continuo** de subreddits de criptomonedas
- **Extracción inteligente** de tickers usando expresiones regulares
- **Análisis de volumen** para detectar aumentos significativos en menciones
- **Sistema de cooldown** para evitar spam de alertas

### 📊 Análisis de Datos
- **Conteo agregado** de menciones por ticker
- **Detección de patrones** anómalos en el volumen de menciones
- **Historial de eventos** para análisis retrospectivo
- **Métricas de tendencias** con umbrales configurables

### 🚨 Sistema de Alertas
- **Notificaciones instantáneas** vía Telegram
- **Alertas formateadas** con información detallada del evento
- **Notificaciones de ciclo de vida** del servicio
- **Gestión de errores** con alertas de estado

### 💾 Persistencia de Datos
- **Almacenamiento** de eventos de hype detectados
- **Historial completo** de escaneos realizados
- **Consultas optimizadas** para análisis temporal
- **Recuperación** de eventos recientes

## Arquitectura Limpia

El servicio sigue los principios de **Arquitectura Limpia** y **SOLID**, organizando el código en capas bien definidas:

```
services/hype/
├── Dockerfile
├── requirements.txt
├── README.md
└── app/
    ├── __init__.py
    ├── config.py
    ├── main.py
    ├── domain/           # Entidades y reglas de negocio
    │   ├── __init__.py
    │   ├── entities.py   # Modelos de dominio
    │   └── interfaces.py # Contratos/Interfaces
    ├── application/      # Casos de uso y lógica de aplicación
    │   ├── __init__.py
    │   ├── scan_and_detect_hype_use_case.py
    │   ├── get_recent_hype_events_use_case.py
    │   └── service_lifecycle_use_case.py
    └── infrastructure/   # Implementaciones técnicas
        ├── __init__.py
        ├── database_repository.py
        ├── reddit_adapter.py
        ├── notification_adapter.py
        ├── hype_analyzer_adapter.py
        └── scheduler.py
```

### 🏛️ Capa de Dominio

**Entidades principales:**

- **`Post`**: Representa un post individual de Reddit
  ```python
  @dataclass
  class Post:
      title: str
      content: str
      author: str
      created_utc: float
      subreddit: str
      url: str
  ```

- **`TickerMention`**: Menciones agregadas de tickers
  ```python
  @dataclass
  class TickerMention:
      ticker: str
      count: int
      posts: List[Post]
  ```

- **`HypeEvent`**: Eventos de alerta detectados
  ```python
  @dataclass
  class HypeEvent:
      ticker: str
      mention_count: int
      detection_time: datetime
      alert_message: str
      posts: List[Post]
  ```

**Interfaces (Contratos):**

- `HypeCollector`: Para recolección de datos de Reddit
- `HypeRepository`: Para persistencia en base de datos
- `NotificationService`: Para envío de alertas
- `HypeAnalyzer`: Para análisis de tendencias

### 🎯 Capa de Aplicación

**Casos de Uso:**

1. **`ScanAndDetectHypeUseCase`** - Caso de uso principal
   - Orquesta todo el proceso de detección
   - Recolecta posts de múltiples subreddits
   - Analiza menciones y detecta alertas
   - Envía notificaciones y guarda resultados

2. **`GetRecentHypeEventsUseCase`** - Consulta de eventos
   - Recupera eventos de hype recientes
   - Filtrado por período de tiempo
   - Útil para APIs y análisis

3. **`ServiceLifecycleUseCase`** - Gestión del ciclo de vida
   - Notificaciones de inicio/parada del servicio
   - Gestión de errores del sistema

4. **`SendDailySummaryUseCase`** - Resumen diario automático
   - Recopila eventos de hype de las últimas 24 horas
   - Genera estadísticas de tendencias del día
   - Envía resumen formateado por Telegram a las 11:00 AM

### 🔧 Capa de Infraestructura

**Adaptadores e Implementaciones:**

1. **`RedditAdapter`** - Integración con Reddit API
   - Conexión con PRAW (Python Reddit API Wrapper)
   - Extracción de tickers con regex avanzado
   - Monitoreo de subreddits configurables

2. **`DatabaseRepository`** - Persistencia con SQLAlchemy
   - Guardado de eventos y escaneos
   - Consultas optimizadas
   - Gestión de sesiones de base de datos

3. **`TelegramNotificationService`** - Alertas por Telegram
   - Mensajes formateados con markdown
   - Gestión de errores de envío
   - Múltiples tipos de notificaciones

4. **`HypeAnalyzerAdapter`** - Análisis de tendencias
   - `VolumeHypeAnalyzer`: Análisis por volumen
   - Sistema de cooldown configurable
   - Detección de patrones anómalos

5. **`HypeScheduler`** - Trabajos periódicos
   - **Trabajo de ALERTA** (cada 5 minutos): Solo análisis y alertas
   - **Trabajo de GUARDADO** (cada 24 horas): Incluye persistencia completa
   - **Trabajo de RESUMEN DIARIO** (11:00 AM): Envía resumen de tendencias del día

## Configuración

### Variables de Entorno Requeridas

```bash
# Reddit API
REDDIT_CLIENT_ID=tu_client_id
REDDIT_CLIENT_SECRET=tu_client_secret
REDDIT_USER_AGENT=tu_user_agent

# Telegram
TELEGRAM_HYPE_BOT_TOKEN=tu_bot_token
TELEGRAM_HYPE_CHAT_ID=tu_chat_id

# Base de Datos
DATABASE_URL=postgresql://user:pass@host:port/db
```

### Subreddits Monitoreados

El servicio monitorea los siguientes subreddits por defecto:

- `CryptoMoonShots`
- `SatoshiStreetBets` 
- `CryptoCurrency`
- `altcoin`
- `CryptoMarkets`

Configurables en `app/config.py`:

```python
HYPE_SUBREDDITS = [
    "CryptoMoonShots",
    "SatoshiStreetBets", 
    "CryptoCurrency",
    "altcoin",
    "CryptoMarkets"
]
```

### Tickers Objetivo

Lista de criptomonedas monitoreadas definida en `reddit_adapter.py`:

```python
TARGET_TICKERS = [
    'BTC', 'ETH', 'BNB', 'XRP', 'ADA', 'SOL', 'DOGE', 'DOT', 'AVAX', 'SHIB',
    'MATIC', 'LTC', 'UNI', 'LINK', 'ATOM', 'XLM', 'BCH', 'ALGO', 'VET', 'ICP',
    # ... más tickers
]
```

## Ejecución

### Con Docker (Recomendado)

```bash
# Construir imagen
docker build -t hype-service .

# Ejecutar contenedor
docker run -d \
  --name hype-service \
  --env-file .env \
  -p 8002:8000 \
  hype-service
```

### Desarrollo Local

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar servicio
python app/main.py
```

### Con Docker Compose

```bash
# Desde el directorio raíz del proyecto
docker-compose up hype
```

## API Endpoints

### `GET /`
Endpoint de salud básico
```json
{
  "service": "hype",
  "status": "running",
  "version": "1.0.0"
}
```

### `GET /health`
Verificación detallada de salud del servicio
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "uptime": "2h 15m"
}
```

### `GET /events`
Obtiene eventos de hype recientes
```json
{
  "events": [
    {
      "ticker": "DOGE",
      "mention_count": 25,
      "detection_time": "2024-01-15T10:25:00Z",
      "alert_message": "🚨 ALERTA HYPE: DOGE mencionado 25 veces..."
    }
  ]
}
```

### `POST /daily-summary`
Envía resumen diario manualmente (para pruebas)
```json
{
  "status": "success",
  "events_count": 15,
  "summary_stats": {
    "total_alerts_sent": 15,
    "unique_tickers_alerted": 8,
    "top_trending_tickers": {
      "DOGE": 5,
      "SHIB": 3,
      "PEPE": 2
    }
  }
}
```

## Funcionamiento del Sistema

### 🔄 Ciclo de Detección

1. **Recolección de Datos**
   - El scheduler ejecuta cada 5 minutos el trabajo de ALERTA
   - Se conecta a Reddit y extrae posts de subreddits configurados
   - Analiza títulos y contenido en busca de tickers

2. **Análisis de Menciones**
   - Cuenta menciones por ticker usando regex inteligente
   - Aplica filtros para evitar falsos positivos
   - Agrupa resultados por ticker

3. **Detección de Alertas**
   - El `VolumeHypeAnalyzer` evalúa si hay suficiente volumen
   - Verifica cooldowns para evitar spam
   - Determina si se debe generar una alerta

4. **Envío de Notificaciones**
   - Formatea mensaje con detalles del evento
   - Envía alerta a Telegram
   - Incluye información de posts relevantes

5. **Persistencia (cada 24 horas)**
   - Guarda eventos detectados en base de datos
   - Almacena historial completo de escaneos
   - Mantiene métricas para análisis histórico

6. **Resumen Diario (11:00 AM)**
   - Recopila eventos de las últimas 24 horas
   - Calcula estadísticas de tendencias
   - Envía resumen por Telegram con top tickers del día

### 📊 Sistema de Análisis

**VolumeHypeAnalyzer:**
- **Umbral mínimo**: 5 menciones para considerar alerta
- **Cooldown**: 1 hora entre alertas del mismo ticker
- **Análisis inteligente**: Considera contexto y frecuencia

**Detección de Patrones:**
- Aumentos súbitos en volumen de menciones
- Comparación con patrones históricos
- Filtrado de ruido y menciones irrelevantes

### 🔧 Gestión de Errores

- **Reconexión automática** a Reddit API
- **Reintentos** en caso de fallos de red
- **Notificaciones de error** vía Telegram
- **Logs detallados** para debugging

## Monitoreo y Logs

### Estructura de Logs

```python
# Configuración en shared/services/logging_config.py
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '[%(asctime)s] %(levelname)s in %(name)s: %(message)s'
        }
    }
}
```

### Eventos Loggeados

- ✅ Inicio/parada del servicio
- 🔍 Escaneos realizados y resultados
- 🚨 Alertas generadas y enviadas
- ❌ Errores de conexión o procesamiento
- 📊 Métricas de rendimiento

## Desarrollo y Extensibilidad

### Agregar Nuevos Analizadores

```python
# Implementar la interfaz HypeAnalyzer
class NewHypeAnalyzer:
    def should_alert(self, ticker: str, mention_count: int, posts: List[Post]) -> bool:
        # Tu lógica de análisis aquí
        pass
```

### Agregar Nuevas Fuentes de Datos

```python
# Implementar la interfaz HypeCollector
class NewDataCollector:
    def collect_posts(self, sources: List[str]) -> List[Post]:
        # Tu lógica de recolección aquí
        pass
```

### Personalizar Notificaciones

```python
# Extender NotificationService
class CustomNotificationService:
    def send_alert(self, event: HypeEvent) -> bool:
        # Tu lógica de notificación personalizada
        pass
```

## Dependencias Principales

- **FastAPI**: Framework web asíncrono
- **PRAW**: Reddit API wrapper
- **SQLAlchemy**: ORM para base de datos
- **APScheduler**: Scheduler para trabajos periódicos
- **Requests**: Cliente HTTP para Telegram
- **Pydantic**: Validación y serialización de datos

## Contribución

1. Fork del repositorio
2. Crear branch para feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit changes (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push al branch (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

## Licencia

Este proyecto está bajo la licencia MIT. Ver archivo `LICENSE` para más detalles.

---

**Servicio Hype** - Parte del ecosistema Oráculo Bot para trading de criptomonedas. 
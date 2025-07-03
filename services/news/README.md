# News Service - Clean Architecture

Servicio de recolección de noticias y análisis de sentimientos implementado con arquitectura limpia (hexagonal).

## 🏗️ Arquitectura

```
/services/news/
├── Dockerfile
├── requirements.txt
├── README.md
└── app/
    ├── domain/                           # Entidades de negocio e interfaces
    │   ├── entities.py                   # News, SentimentAnalysis
    │   └── interfaces.py                 # Puertos (contratos)
    ├── application/                      # Casos de uso (uno por archivo)
    │   ├── __init__.py                   # Exports all use cases
    │   ├── collect_news_use_case.py      # Recolección de noticias
    │   ├── analyze_sentiment_use_case.py # Análisis de sentimientos
    │   ├── news_pipeline_use_case.py     # Pipeline completo
    │   └── service_lifecycle_use_case.py # Ciclo de vida del servicio
    ├── infrastructure/                   # Implementaciones concretas
    │   ├── reddit_adapter.py             # Reddit API
    │   ├── gemini_adapter.py             # Google Gemini
    │   ├── database_repository.py        # SQLAlchemy
    │   ├── notification_adapter.py       # Telegram
    │   └── scheduler.py                  # APScheduler
    └── main.py                           # FastAPI app + DI
```

## 🚀 Funcionalidades

- **Recolección de Noticias**: Obtiene posts de múltiples subreddits crypto vía Reddit API
- **Análisis de Sentimiento**: Utiliza Google Gemini para análisis enriquecido
  - Score de sentimiento (-1.0 a 1.0)
  - Emoción primaria (Euforia, Optimismo, Neutral, Incertidumbre, Miedo)
  - Categoría (Regulación, Tecnología/Adopción, Mercado/Trading, Seguridad, Macroeconomía)
- **Pipeline Automatizado**: Ejecuta recolección + análisis cada hora
- **API REST**: Endpoints para health checks y ejecución manual

## 🐳 Docker

### Construcción

Desde la raíz del proyecto:

```bash
docker build -f services/news/Dockerfile -t oraculo-news .
```

### Ejecución con Docker Compose

```bash
# Desde la raíz del proyecto
docker-compose up news
```

### Ejecución directa con Docker

```bash
docker run -d \
  --name oraculo-news \
  -p 8000:8000 \
  --env-file .env \
  oraculo-news
```

## 🔧 Configuración

Variables de entorno requeridas:

```bash
# Base de datos
DATABASE_URL=postgresql://user:pass@host:port/dbname

# Reddit API
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=your_user_agent

# Google Gemini
GOOGLE_API_KEY=your_api_key

# Telegram (opcional, para notificaciones)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## 📡 Endpoints

- `GET /` - Status básico
- `GET /health` - Health check detallado
- `POST /pipeline/run` - Ejecuta el pipeline manualmente
- `GET /stats` - Estadísticas del servicio

## 🧪 Testing

```bash
# Health check
curl http://localhost:8000/health

# Ejecutar pipeline manualmente
curl -X POST http://localhost:8000/pipeline/run
```

## 📈 Monitoreo

Los logs se almacenan en `/app/logs` dentro del contenedor (mapeado a `./logs` en el host).

## 🔄 Desarrollo

Para desarrollo local sin Docker:

```bash
# Instalar dependencias
pip install -r services/news/requirements.txt

# Ejecutar servicio
python run_news_service.py
``` 
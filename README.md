# �� Oráculo Cripto Bot - Arquitectura de Microservicios

Un sistema inteligente de microservicios para trading automatizado y análisis de noticias de criptomonedas que funciona como un oráculo completo del mercado crypto.

## 📋 Descripción del Proyecto

El **Oráculo Cripto Bot** es un ecosistema de microservicios construido con FastAPI que combina **trading automatizado** y **análisis de sentimientos** de noticias cripto. El sistema está diseñado como una arquitectura moderna de microservicios que proporciona datos actualizados y ejecuta estrategias de trading de manera continua y automática.

### 🎯 Funcionalidades Principales

#### 📰 Servicio de Noticias
- **Recolección Automática**: Obtiene noticias de Reddit (r/CryptoCurrency) cada hora
- **Análisis de Sentimientos**: Procesa noticias con Google Gemini AI cada 4 horas
- **Filtrado Inteligente**: Solo recolecta de dominios confiables (CoinDesk, CoinTelegraph, etc.)
- **Prevención de Duplicados**: Evita almacenar noticias duplicadas usando URL como identificador único

#### 🤖 Servicio de Grid Trading
- **Grid Trading Bot**: Ejecuta estrategias de grid trading en Binance
- **Trading Automatizado**: Operaciones continuas 24/7 con parámetros configurables
- **Gestión de Riesgos**: Stop loss y take profit automáticos
- **Múltiples Estrategias**: Soporte para diferentes algoritmos de trading

#### 🌐 API Gateway
- **Endpoints Unificados**: Centraliza acceso a todos los microservicios
- **Load Balancing**: Distribución inteligente de requests
- **Monitoring**: Estado y salud de todos los servicios
- **Documentación Automática**: Swagger UI integrado

### 🏗️ Arquitectura de Microservicios

```
oraculo_bot/
├── services/                    # 🔥 MICROSERVICIOS INDEPENDIENTES
│   ├── api/                     # API Gateway (Puerto 8002)
│   │   ├── main.py              # Entry point del gateway
│   │   └── routers/             # Routers modulares por servicio
│   │       ├── news_router.py   # Endpoints de noticias
│   │       ├── grid_router.py   # Endpoints de trading
│   │       └── status_router.py # Endpoints de estado del sistema
│   ├── news/                    # Servicio de Noticias (Puerto 8000)
│   │   ├── main.py              # Entry point del servicio
│   │   ├── schedulers/          # Tareas programadas automáticas
│   │   │   └── news_scheduler.py # Reddit + Sentiment analysis jobs
│   │   ├── services/            # Lógica de negocio
│   │   │   ├── reddit_service.py    # Integración con Reddit API
│   │   │   └── sentiment_service.py # Análisis con Google Gemini
│   │   └── api/                 # Endpoints específicos del servicio
│   └── grid/                    # Servicio de Trading (Puerto 8001)
│       ├── main.py              # Entry point del servicio
│       ├── core/                # Motor de trading
│   │   └── trading_engine.py # Engine principal de trading
│   │   └── schedulers/          # Tareas de trading automáticas
│   │       └── grid_scheduler.py # Jobs de grid trading
│   │   └── strategies/          # Estrategias de trading modulares
│   ├── shared/                      # 🧩 CÓDIGO COMPARTIDO
│   │   ├── config/                  # Configuración centralizada
│   │   │   └── settings.py          # Settings unificados para todos los servicios
│   │   ├── database/                # Capa de datos compartida
│   │   │   ├── models.py            # Modelos SQLAlchemy (Noticia, Trading, etc.)
│   │   │   └── session.py           # Configuración de sesión de base de datos
│   │   └── services/                # Servicios compartidos
│   │       ├── logging_config.py    # Logging centralizado
│   │       └── telegram_service.py  # Notificaciones Telegram
│   ├── run_api_service.py           # 🚀 Entry point API Gateway
│   ├── run_news_service.py          # 🚀 Entry point News Service  
│   └── run_grid_service.py          # 🚀 Entry point Grid Trading Service
│   └── requirements.txt             # Dependencias unificadas
└── oraculo.db                   # Base de datos SQLite compartida
```

#### 🔧 Componentes Principales

1. **API Gateway** (`services/api/`): Centraliza todos los endpoints y maneja el routing
2. **News Service** (`services/news/`): Recolección de Reddit y análisis de sentimientos
3. **Grid Service** (`services/grid/`): Motor de trading automatizado y estrategias
4. **Shared Layer** (`shared/`): Código común, configuración y base de datos
5. **Entry Points**: Scripts independientes para cada microservicio

#### 📊 Modelo de Datos

**Tabla `noticias`**:
- `id`: Identificador único
- `source`: Fuente de la noticia
- `headline`: Título de la noticia
- `url`: URL única (previene duplicados)
- `published_at`: Fecha de publicación
- `sentiment_score`: Puntuación de sentimiento (-1.0 a 1.0)
- `entities`: Entidades extraídas (futuras funcionalidades)

## 🚀 Instalación y Configuración

### 📋 Prerrequisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)
- Cuenta de Reddit para API credentials
- Google API Key para análisis de sentimientos
- Cuenta de Binance para trading (opcional)
- Bot de Telegram para notificaciones (opcional)

### 🔧 Instalación Local

1. **Clonar el repositorio**:
   ```bash
   git clone <url-del-repositorio>
   cd oraculo_bot
   ```

2. **Crear y activar el entorno virtual**:
   ```bash
   # En Windows
   python -m venv venv
   venv\Scripts\activate

   # En macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Instalar las dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variables de entorno**:
   
   Crear un archivo `.env` en la raíz del proyecto:
   ```env
   # Configuración General
   PROJECT_NAME=Oráculo Cripto Bot
   DATABASE_URL=sqlite:///./oraculo.db
   
   # Reddit API (para noticias)
   REDDIT_CLIENT_ID=tu_client_id_aqui
   REDDIT_CLIENT_SECRET=tu_client_secret_aqui
   REDDIT_USER_AGENT=OraculoBot by tu_usuario_de_reddit
   
   # Google Gemini API (para análisis de sentimientos)
   GOOGLE_API_KEY=tu_google_api_key_aqui
   
   # Binance API (para trading)
   BINANCE_API_KEY=tu_binance_api_key_aqui
   BINANCE_SECRET_KEY=tu_binance_secret_key_aqui
   
   # Telegram Bot (para notificaciones)
   TELEGRAM_BOT_TOKEN=tu_telegram_bot_token
   TELEGRAM_CHAT_ID=tu_chat_id
   ```

## 🎮 Ejecución del Proyecto

### 🔥 Ejecutar Microservicios Individuales

```bash
# Servicio de Noticias (Puerto 8000)
python run_news_service.py

# Servicio de Grid Trading (Puerto 8001)  
python run_grid_service.py

# API Gateway (Puerto 8002)
python run_api_service.py
```

### 🌐 URLs de los Servicios

- **API Gateway**: http://localhost:8002
  - **Documentación**: http://localhost:8002/docs
  - **Base URL API**: http://localhost:8002/api/v1/
- **News Service**: http://localhost:8000
- **Grid Service**: http://localhost:8001

### 📡 Endpoints del API Gateway

#### 📰 Endpoints de Noticias (`/api/v1/news/`)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/news/` | Estado del servicio de noticias |
| POST | `/news/trigger-collection` | Disparar recolección manual desde Reddit |
| POST | `/news/trigger-sentiment` | Disparar análisis de sentimientos manual |
| GET | `/news/status` | Estado detallado con jobs activos |

#### 🤖 Endpoints de Trading (`/api/v1/grid/`)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/grid/` | Estado del servicio de grid trading |
| GET | `/grid/status` | Estado detallado del trading bot |
| POST | `/grid/start` | Iniciar estrategia de grid trading |
| POST | `/grid/stop` | Detener estrategia de grid trading |
| GET | `/grid/config` | Configuración actual del bot |

#### 🌐 Endpoints del Sistema (`/api/v1/`)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Estado general del sistema |
| GET | `/health` | Health check de todos los servicios |
| GET | `/scheduler` | Estado de todos los schedulers |

### 🔍 Ejemplos de Uso

1. **Verificar estado del sistema**:
   ```bash
   curl http://localhost:8002/api/v1/
   ```

2. **Disparar recolección de noticias**:
   ```bash
   curl -X POST http://localhost:8002/api/v1/news/trigger-collection
   ```

3. **Verificar estado del trading bot**:
   ```bash
   curl http://localhost:8002/api/v1/grid/status
   ```

4. **Health check completo**:
   ```bash
   curl http://localhost:8002/api/v1/health
   ```

## 🐳 Deployment en VPS

### 🛠️ Configuración con Systemd

El proyecto incluye archivos de servicio para systemd en `deployment/services/`:

```bash
# Copiar archivos de servicio
sudo cp deployment/services/*.service /etc/systemd/system/

# Habilitar servicios
sudo systemctl enable oraculo-news oraculo-grid oraculo-api

# Iniciar servicios
sudo systemctl start oraculo-news
sudo systemctl start oraculo-grid  
sudo systemctl start oraculo-api

# Verificar estado
sudo systemctl status oraculo-*
```

### 📊 Monitoreo

- **Logs**: `journalctl -u oraculo-news -f`
- **Estado**: `systemctl status oraculo-*`
- **API Health**: `curl http://tu-vps:8002/api/v1/health`

## 🛠️ Tecnologías Utilizadas

### 🚀 Framework y APIs
- **[FastAPI](https://fastapi.tiangolo.com/)**: Framework web moderno para microservicios
- **[SQLAlchemy](https://www.sqlalchemy.org/)**: ORM para Python
- **[SQLite](https://www.sqlite.org/)**: Base de datos compartida
- **[APScheduler](https://apscheduler.readthedocs.io/)**: Scheduler de tareas automáticas

### 🤖 Integrations
- **[PRAW](https://praw.readthedocs.io/)**: Reddit API integration
- **[Google Gemini](https://ai.google.dev/)**: Análisis de sentimientos con IA
- **[Binance API](https://github.com/sammchardy/python-binance)**: Trading automatizado
- **[python-telegram-bot](https://python-telegram-bot.org/)**: Notificaciones

### 🔧 Infraestructura
- **[Uvicorn](https://www.uvicorn.org/)**: Servidor ASGI de alto rendimiento
- **[Pydantic](https://pydantic-docs.helpmanual.io/)**: Validación de datos
- **Systemd**: Gestión de servicios en producción

## 🔮 Características Avanzadas

### 🤖 Trading Automatizado
- **Grid Strategy**: Compra y venta automática en rangos de precio
- **Risk Management**: Stop loss y take profit configurables
- **Portfolio Balancing**: Gestión automática del balance
- **24/7 Operations**: Trading continuo sin intervención manual

### 🧠 Análisis de Sentimientos IA
- **Google Gemini Integration**: Análisis avanzado con IA de última generación
- **Context-Aware**: Entiende el contexto específico del mercado crypto
- **Batch Processing**: Procesa múltiples noticias eficientemente
- **Sentiment Scoring**: Puntuación de -1.0 (negativo) a 1.0 (positivo)

### 📊 Monitoreo y Alertas
- **Health Checks**: Verificación automática de estado de servicios
- **Telegram Notifications**: Alertas en tiempo real
- **Comprehensive Logging**: Logs detallados para debugging
- **Performance Metrics**: Métricas de rendimiento de trading

### 🔒 Seguridad y Robustez
- **Error Handling**: Manejo robusto de errores en todos los servicios
- **Rate Limiting**: Respeto a límites de APIs externas
- **Graceful Degradation**: Funcionamiento parcial si algún servicio falla
- **Configuration Management**: Variables de entorno centralizadas

## 🔮 Roadmap y Funcionalidades Futuras

### 🚀 Próximas Versiones
- **Multiple Exchange Support**: Soporte para más exchanges (Coinbase, Kraken, etc.)
- **Advanced Strategies**: Más algoritmos de trading (DCA, Scalping, etc.)
- **Machine Learning**: Predicciones basadas en sentimientos históricos
- **Web Dashboard**: Interfaz gráfica para monitoreo y control
- **Mobile App**: Aplicación móvil para monitoreo en tiempo real

### 🧠 IA y Analytics
- **Predictive Analytics**: Predicciones de precio basadas en noticias
- **Pattern Recognition**: Identificación de patrones en el mercado
- **Multi-source Sentiment**: Análisis de Twitter, Discord, otras fuentes
- **Entity Extraction**: Identificación automática de coins y proyectos

### 🔗 Integraciones
- **DEX Integration**: Trading en exchanges descentralizados
- **DeFi Protocols**: Integración con protocolos DeFi
- **Cross-chain**: Soporte para múltiples blockchains
- **API Marketplace**: APIs públicas para desarrolladores

## 🤝 Contribuciones

Las contribuciones son bienvenidas. El proyecto sigue la arquitectura de microservicios:

1. Haz fork del proyecto
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Desarrolla en el microservicio correspondiente (`services/news/`, `services/grid/`, etc.)
4. Asegúrate de mantener la compatibilidad con `shared/`
5. Commit tus cambios (`git commit -am 'Agregar nueva funcionalidad'`)
6. Push a la rama (`git push origin feature/nueva-funcionalidad`)
7. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

---

## 🏆 Arquitectura de Microservicios Moderna

**El Oráculo Cripto Bot** representa una implementación completa de arquitectura de microservicios para trading automatizado y análisis de noticias crypto, combinando las mejores prácticas de desarrollo moderno con tecnologías de punta en IA y trading algorítmico.

**Desarrollado con ❤️ para la comunidad crypto y trading automatizado** 
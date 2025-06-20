# 🔮 Oráculo Cripto Bot

Un bot inteligente para la recolección y análisis de noticias de criptomonedas que funciona como un oráculo de información del mercado crypto.

## 📋 Descripción del Proyecto

El **Oráculo Cripto Bot** es una aplicación web construida con FastAPI que automatiza la recolección de noticias relacionadas con criptomonedas desde la API de CryptoPanic. El sistema está diseñado para funcionar como un oráculo de información, proporcionando datos actualizados sobre el ecosistema cripto de manera continua y automática.

### 🎯 Funcionalidades Actuales

- **Recolección Automática de Noticias**: Obtiene noticias de CryptoPanic cada hora de forma automática
- **Prevención de Duplicados**: Evita almacenar noticias duplicadas usando la URL como identificador único
- **API REST**: Expone endpoints para consultar el estado del sistema y disparar recolecciones manuales
- **Base de Datos SQLite**: Almacena las noticias de forma persistente
- **Scheduler en Background**: Ejecuta tareas programadas sin interrumpir el servicio web

### 🏗️ Arquitectura del Sistema

El proyecto sigue una arquitectura modular y escalable organizada de la siguiente manera:

```
oraculo_bot/
├── app/
│   ├── api/              # Endpoints adicionales de la API (futura expansión)
│   ├── core/             # Configuración central del sistema
│   │   └── config.py     # Settings y variables de entorno
│   ├── db/               # Capa de datos
│   │   ├── models.py     # Modelos SQLAlchemy (tabla Noticia)
│   │   └── session.py    # Configuración de la sesión de base de datos
│   ├── services/         # Lógica de negocio
│   │   └── cryptopanic_service.py  # Servicio para interactuar con CryptoPanic API
│   ├── tasks/            # Tareas programadas
│   │   └── news_collector.py       # Scheduler para recolección automática
│   └── main.py           # Punto de entrada de la aplicación FastAPI
├── requirements.txt      # Dependencias del proyecto
└── venv/                # Entorno virtual de Python
```

#### 🔧 Componentes Principales

1. **FastAPI Application** (`main.py`): Servidor web que expone la API REST
2. **CryptoPanic Service**: Maneja la comunicación con la API externa de CryptoPanic
3. **Database Layer**: Gestiona el almacenamiento persistente usando SQLAlchemy + SQLite
4. **Background Scheduler**: Ejecuta la recolección de noticias cada hora usando APScheduler
5. **Configuration Management**: Centraliza la configuración usando Pydantic Settings

#### 📊 Modelo de Datos

La tabla `noticias` almacena:
- `id`: Identificador único
- `source`: Fuente de la noticia (actualmente "CryptoPanic")
- `headline`: Título de la noticia
- `url`: URL única de la noticia (evita duplicados)
- `published_at`: Fecha de publicación
- `sentiment_score`: Puntuación de sentimiento (para futuras funcionalidades)
- `entities`: Entidades extraídas (para futuras funcionalidades)

## 🚀 Instalación y Configuración

### 📋 Prerrequisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)
- Cuenta en [CryptoPanic](https://cryptopanic.com/) para obtener API Key

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
   PROJECT_NAME=Oráculo Cripto Bot
   DATABASE_URL=sqlite:///./oraculo.db
   CRYPTOPANIC_API_KEY=tu_api_key_aqui
   ```

   > **Nota**: Obtén tu API Key gratuita registrándote en [CryptoPanic](https://cryptopanic.com/developers/api/)

## 🎮 Ejecución del Proyecto

### 🔥 Ejecutar el Servidor

```bash
# Asegúrate de estar en el entorno virtual activado
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

La aplicación estará disponible en:
- **API**: http://localhost:8000
- **Documentación interactiva**: http://localhost:8000/docs
- **Documentación alternativa**: http://localhost:8000/redoc

### 📡 Endpoints Disponibles

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Verificar estado del sistema |
| POST | `/tasks/trigger-collection` | Disparar recolección manual de noticias |

### 🔍 Ejemplo de Uso

1. **Verificar que el sistema está funcionando**:
   ```bash
   curl http://localhost:8000/
   ```

2. **Disparar recolección manual de noticias**:
   ```bash
   curl -X POST http://localhost:8000/tasks/trigger-collection
   ```

## 🛠️ Tecnologías Utilizadas

- **[FastAPI](https://fastapi.tiangolo.com/)**: Framework web moderno y rápido para Python
- **[SQLAlchemy](https://www.sqlalchemy.org/)**: ORM para Python
- **[SQLite](https://www.sqlite.org/)**: Base de datos ligera y embedida
- **[APScheduler](https://apscheduler.readthedocs.io/)**: Scheduler de tareas en background
- **[Pydantic](https://pydantic-docs.helpmanual.io/)**: Validación de datos y settings
- **[Requests](https://requests.readthedocs.io/)**: Cliente HTTP para Python
- **[Uvicorn](https://www.uvicorn.org/)**: Servidor ASGI de alto rendimiento

## 🔮 Roadmap y Funcionalidades Futuras

- **Análisis de Sentimientos**: Implementar análisis automático del sentimiento de las noticias
- **Extracción de Entidades**: Identificar criptomonedas, exchanges y personas mencionadas
- **Webhooks**: Notificaciones en tiempo real cuando se detecten noticias importantes
- **Dashboard Web**: Interfaz gráfica para visualizar las noticias y análisis
- **Múltiples Fuentes**: Integración con más APIs de noticias crypto
- **Filtros Avanzados**: Filtrado por criptomonedas específicas, tipos de noticias, etc.
- **API de Predicciones**: Endpoints para obtener insights y predicciones basadas en las noticias

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Haz fork del proyecto
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

---

**Desarrollado con ❤️ para la comunidad crypto** 
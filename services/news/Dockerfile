# ==============================================================================
# Dockerfile para el servicio de Noticias (News Worker)
# ==============================================================================

# --- Etapa 1: Imagen Base ---
# Usamos una imagen oficial y ligera de Python.
# 'slim' significa que no viene con un montón de herramientas innecesarias.
FROM python:3.11-slim

# --- Configuración del Entorno ---
# Establecemos el directorio de trabajo DENTRO del contenedor.
# Todo lo que hagamos a partir de ahora será relativo a /app.
WORKDIR /app

# Le decimos a Python que no guarde archivos .pyc en caché, es una buena práctica.
ENV PYTHONDONTWRITEBYTECODE 1
# Le decimos a Python que corra en modo "sin buffer" para que los logs (prints)
# aparezcan instantáneamente y no se queden atascados. CRUCIAL para el debugging.
ENV PYTHONUNBUFFERED 1

# Configuramos el PYTHONPATH para que Python encuentre nuestros módulos.
# Esto es necesario para que las importaciones desde 'shared' y 'app' funcionen correctamente.
ENV PYTHONPATH=/app


# --- Etapa 2: Instalación de Dependencias del Sistema ---
# Instalamos herramientas del sistema que necesitamos para compilar algunas librerías de Python.
# gcc y g++ son necesarios para compilar extensiones nativas (como psycopg2).
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*


# --- Etapa 3: Instalación de Dependencias de Python ---
# Primero, copiamos SOLO el archivo de requerimientos.
# La razón de hacerlo por separado es aprovechar el caché de Docker.
# Si no cambiamos las dependencias, Docker reutilizará esta capa y la construcción será mucho más rápida.
COPY ./services/news/requirements.txt .

# Ejecutamos pip install para instalar las dependencias de este servicio.
# --no-cache-dir evita que pip guarde caché, manteniendo la imagen más pequeña.
RUN pip install --no-cache-dir -r requirements.txt


# --- Etapa 4: Copiar el Código ---
# Aquí está la magia. Copiamos tanto el código compartido como el código específico del servicio.

# Copiamos nuestra librería compartida a una carpeta 'shared' DENTRO del contenedor.
# Esta librería contiene modelos de BD, configuraciones, logging, etc.
COPY ./shared/ /app/shared/

# Copiamos el código específico de este servicio (News) con arquitectura limpia.
# La estructura será: /app/app/ que contiene domain/, application/, infrastructure/, main.py
COPY ./services/news/app/ /app/app/


# --- Etapa 5: Configuración del Puerto ---
# Exponemos el puerto 8000 donde correrá nuestro FastAPI server.
# Esto es solo documentativo, el puerto real se mapea en docker-compose o docker run.
EXPOSE 8000


# --- Etapa 6: Comando de Ejecución ---
# Este es el comando que se ejecutará cuando el contenedor se inicie.
# Ejecuta uvicorn (servidor ASGI) con nuestra aplicación FastAPI.
# - app.main:app = módulo app.main, variable app
# - --host 0.0.0.0 = escucha en todas las interfaces (necesario para Docker)
# - --port 8000 = puerto donde correr el servidor
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 
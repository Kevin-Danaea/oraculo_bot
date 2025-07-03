# Etapa 1: Builder - Instalar dependencias
FROM python:3.11-slim as builder

WORKDIR /app

# Instalar dependencias del sistema operativo
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar solo el archivo de requerimientos para optimizar el caché de Docker
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt


# Etapa 2: Runner - Entorno de ejecución final
FROM python:3.11-slim

WORKDIR /app

# Copiar dependencias instaladas desde la etapa de builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copiar el directorio de la aplicación y el directorio compartido
COPY ./app ./app
COPY ../../shared ./shared

# Variables de entorno (se pueden sobreescribir en docker-compose)
ENV PYTHONPATH=/app
ENV LOG_LEVEL="INFO"

# Exponer el puerto
EXPOSE 8000

# Comando para iniciar la aplicación
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 
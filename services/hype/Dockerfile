# ==============================================================================
# Dockerfile Estandarizado - Oráculo Bot Hype Service
# ==============================================================================

FROM python:3.10-slim

# Configuración del entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependencias Python
COPY services/hype/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY services/hype/app/ ./app/
COPY shared/ ./shared/

# Crear directorio para logs
RUN mkdir -p logs

# Exponer puerto
EXPOSE 8004

# Comando para ejecutar el servicio
CMD ["python", "-m", "app.main"] 
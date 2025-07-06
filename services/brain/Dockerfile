# Brain Service Dockerfile
# ========================

FROM python:3.11-slim

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependencias Python
COPY services/brain/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY services/brain/app/ ./app/
COPY shared/ ./shared/

# Crear directorio para logs
RUN mkdir -p logs

# Exponer puerto
EXPOSE 8000

# Variables de entorno por defecto
ENV BRAIN_ANALYSIS_INTERVAL=3600
ENV BRAIN_ANALYSIS_TIMEFRAME=4h
ENV BRAIN_ANALYSIS_DAYS=40
ENV BRAIN_LOG_LEVEL=INFO
ENV BRAIN_DEBUG=false
ENV BRAIN_DEV_MODE=false
ENV PYTHONPATH=/app

# Comando para ejecutar la aplicación
CMD ["python", "-m", "app.main"] 
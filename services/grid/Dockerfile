FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY services/grid/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY services/grid/app/ ./app/
COPY shared/ ./shared/

# Crear directorio para logs
RUN mkdir -p logs

# Exponer puerto
EXPOSE 8000

# Variables de entorno por defecto
ENV PYTHONPATH=/app
ENV TRADING_MODE=sandbox
ENV MONITORING_INTERVAL_HOURS=1

# Comando por defecto
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 
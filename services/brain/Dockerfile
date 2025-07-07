# ==============================================================================
# Dockerfile Estandarizado - Oráculo Bot Brain Service
# ==============================================================================

FROM python:3.10-slim

# Configuración del entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# Instalar dependencias del sistema necesarias para TA-Lib
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    wget \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Descargar e instalar TA-Lib desde el código fuente
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# Copiar requirements e instalar dependencias Python
COPY services/brain/requirements.txt .
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY services/brain/app/ ./app/
COPY shared/ ./shared/

# Crear directorio para logs
RUN mkdir -p logs

# Exponer puerto
EXPOSE 8001

# Comando para ejecutar el servicio
CMD ["python", "app/main.py"] 
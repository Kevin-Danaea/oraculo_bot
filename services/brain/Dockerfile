# ==============================================================================
# Dockerfile Definitivo - Oráculo Bot Brain Service
# ==============================================================================

FROM python:3.10-slim

# --- Configuración del Entorno ---
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# --- Instalación de dependencias del sistema ---
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    wget \
    build-essential \
    pkg-config \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# --- Instalación de TA-Lib desde fuente ---
RUN cd /tmp && \
    wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr/local && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# --- Configurar variables de entorno para TA-Lib ---
ENV TA_INCLUDE_PATH=/usr/local/include
ENV TA_LIBRARY_PATH=/usr/local/lib
ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH
ENV PKG_CONFIG_PATH=/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH

# --- Actualizar ldconfig ---
RUN ldconfig

# --- Instalación de dependencias de Python ---
COPY services/brain/requirements.txt .

# --- Instalar TA-Lib primero ---
RUN pip install --no-cache-dir TA-Lib==0.4.28

# --- Instalar el resto de dependencias ---
RUN pip install --no-cache-dir -r requirements.txt

# --- Copiar el Código de la Aplicación ---
COPY shared/ ./shared/
COPY services/brain/app/ ./app/

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

# --- Verificar que TA-Lib funciona ---
RUN python -c "import talib; print('✅ TA-Lib version:', talib.__version__)"

# --- Comando de Ejecución ---
CMD ["python", "-m", "app.main"] 
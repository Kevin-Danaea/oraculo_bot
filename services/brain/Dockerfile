# ==============================================================================
# Dockerfile Definitivo para servicios con TA-Lib
# ==============================================================================

# --- Etapa 1: Imagen Base ---
FROM python:3.10-slim

# --- Configuración del Entorno ---
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# --- Etapa 2: Instalación de Dependencias del Sistema para TA-Lib (EL PASO CLAVE) ---
# Actualizamos la lista de paquetes e instalamos las herramientas necesarias
RUN apt-get update && apt-get install -y \
    wget \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Descargamos el código fuente de la librería TA-Lib en C
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
# Descomprimimos el archivo
RUN tar -xvzf ta-lib-0.4.0-src.tar.gz
# Navegamos a la carpeta descomprimida y compilamos
WORKDIR /ta-lib
RUN ./configure --prefix=/usr && make && make install
# Configurar las variables de entorno para que Python encuentre la librería
RUN echo "/usr/lib" > /etc/ld.so.conf.d/talib.conf && ldconfig
# Limpiamos los archivos de instalación que ya no necesitamos
WORKDIR /app
RUN rm -rf /ta-lib ta-lib-0.4.0-src.tar.gz

# --- Etapa 3: Instalación de Dependencias de Python ---
# Ahora que la base de C está instalada, podemos instalar el wrapper de Python.
COPY services/brain/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Etapa 4: Copiar el Código de la Aplicación ---
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

# --- Etapa 5: Comando de Ejecución ---
CMD ["python", "-m", "app.main"] 
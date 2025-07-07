# ==============================================================================
# Dockerfile Estandarizado - Oráculo Bot Brain Service
# ==============================================================================

FROM continuumio/miniconda3:latest

# Configuración del entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# Actualizar conda e instalar TA-Lib
RUN conda update -n base -c defaults conda -y && \
    conda install -c conda-forge ta-lib python=3.10 -y

# Copiar requirements e instalar dependencias Python
COPY services/brain/requirements.txt .
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
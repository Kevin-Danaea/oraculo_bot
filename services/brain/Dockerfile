# ==============================================================================
# Dockerfile Definitivo - Oráculo Bot Brain Service
# ==============================================================================

FROM continuumio/miniconda3:latest

# Establecer variables de entorno
ENV PYTHONUNBUFFERED=1

# Actualizar conda
RUN conda update -n base -c defaults conda -y

# Instalar TA-Lib globalmente (más simple)
RUN conda install -c conda-forge ta-lib python=3.10 -y

# Copiar requirements
COPY requirements.txt /tmp/requirements.txt

# Instalar dependencias Python
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copiar código de la aplicación
COPY app/ /app/
COPY shared/ /shared/

# Establecer directorio de trabajo
WORKDIR /app

# Exponer puerto
EXPOSE 8001

# Comando para ejecutar el servicio
CMD ["python", "main.py"] 
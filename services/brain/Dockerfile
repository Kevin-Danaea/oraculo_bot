# ==============================================================================
# Dockerfile Definitivo - Oráculo Bot Brain Service
# ==============================================================================

FROM continuumio/miniconda3:latest

# Establecer variables de entorno
ENV PYTHONUNBUFFERED=1
ENV CONDA_ENV=brain_env

# Crear y activar entorno conda
RUN conda create -n $CONDA_ENV python=3.10 -y
SHELL ["conda", "run", "-n", "brain_env", "/bin/bash", "-c"]

# Instalar TA-Lib desde conda-forge (más estable)
RUN conda install -c conda-forge ta-lib -y

# Copiar requirements y instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY app/ /app/
COPY shared/ /shared/

# Establecer directorio de trabajo
WORKDIR /app

# Exponer puerto
EXPOSE 8001

# Comando para ejecutar el servicio
CMD ["conda", "run", "-n", "brain_env", "python", "main.py"] 
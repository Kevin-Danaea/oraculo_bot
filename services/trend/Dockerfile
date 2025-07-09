FROM python:3.11-slim

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar y instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY . .

# Copiar archivos compartidos
COPY ../../shared ./shared/

# Crear directorio para logs
RUN mkdir -p logs

# Variable de entorno para Python
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Puerto (aunque este servicio no expone HTTP)
EXPOSE 8000

# Comando por defecto
CMD ["python", "-m", "services.trend.app.main"] 
#!/bin/bash

echo "🧪 Probando servicio Brain..."

# Construir solo el servicio Brain
echo "🔨 Construyendo Brain..."
docker-compose build brain

# Verificar TA-Lib
echo "🔍 Verificando TA-Lib..."
docker-compose run --rm brain /bin/bash -c "source activate brain_env && python -c \"import talib; print('✅ TA-Lib version:', talib.__version__)\""

if [ $? -eq 0 ]; then
    echo "✅ TA-Lib funciona correctamente"
else
    echo "❌ Error con TA-Lib"
    echo "📋 Logs de construcción:"
    docker-compose logs brain
    exit 1
fi

# Probar que el servicio puede iniciar
echo "🚀 Probando inicio del servicio..."
docker-compose up brain -d
sleep 10

# Verificar estado
echo "📊 Estado del servicio:"
docker-compose ps brain

# Verificar logs
echo "📋 Logs del servicio:"
docker-compose logs brain --tail=10

# Limpiar
echo "🧹 Limpiando..."
docker-compose down

echo "✅ Prueba completada!" 
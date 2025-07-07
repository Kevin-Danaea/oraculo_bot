#!/bin/bash

echo "🧪 Probando TA-Lib en Brain..."

# Construir Brain
echo "🔨 Construyendo Brain..."
docker-compose build brain

# Probar TA-Lib
echo "🔍 Verificando TA-Lib..."
docker-compose run --rm brain python -c "import talib; print('✅ TA-Lib version:', talib.__version__)"

if [ $? -eq 0 ]; then
    echo "✅ TA-Lib funciona correctamente"
else
    echo "❌ Error con TA-Lib"
    echo "📋 Logs:"
    docker-compose logs brain
fi

echo "✅ Prueba completada!" 
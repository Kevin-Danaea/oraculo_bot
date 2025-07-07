# 🚀 Oráculo Bot - Despliegue Simplificado

## 📋 Instrucciones Rápidas

### 1. Configurar Variables de Entorno
```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar con tus credenciales
nano .env
```

### 2. Desplegar Todo el Sistema
```bash
# Opción 1: Script automático
./deploy.sh

# Opción 2: Comando directo
docker-compose up --build -d
```

### 3. Verificar que Funciona
```bash
# Ver estado de servicios
docker-compose ps

# Ver logs
docker-compose logs -f

# Verificar TA-Lib
docker-compose exec brain python -c "import talib; print(talib.__version__)"
```

## 🌐 Servicios Disponibles

- **📰 News Service**: http://localhost:8000
- **🧠 Brain Service**: http://localhost:8001  
- **📊 Grid Service**: http://localhost:8002
- **🔥 Hype Service**: http://localhost:8003

## 🔧 Comandos Útiles

```bash
# Ver logs en tiempo real
docker-compose logs -f

# Ver logs de un servicio específico
docker-compose logs -f brain
docker-compose logs -f grid
docker-compose logs -f news
docker-compose logs -f hype

# Detener todos los servicios
docker-compose down

# Reiniciar un servicio
docker-compose restart brain

# Ver estado de servicios
docker-compose ps
```

## 📊 Monitoreo

```bash
# Verificar memoria
./monitor_memory.sh

# Verificar TA-Lib
./verify_talib.sh
```

## 🚨 Si Hay Problemas

### Error de TA-Lib
```bash
# Reconstruir solo el brain
docker-compose build --no-cache brain
docker-compose up -d brain
```

### Error de Memoria (DigitalOcean 1GB)
```bash
# Optimizar memoria
./optimize_memory.sh

# Usar configuración optimizada
docker-compose -f docker-compose.optimized.yml up --build -d
```

### Limpiar Todo y Empezar de Nuevo
```bash
# Detener y eliminar todo
docker-compose down --rmi all

# Limpiar cache
docker system prune -f

# Reconstruir
docker-compose up --build -d
```

## ✅ Verificación Final

```bash
# Health checks
curl http://localhost:8000/health  # News
curl http://localhost:8001/health  # Brain
curl http://localhost:8002/health  # Grid
curl http://localhost:8003/health  # Hype

# Verificar TA-Lib
docker-compose exec brain python -c "import talib; print('✅ TA-Lib funciona')"
```

---

## 🎉 ¡Listo!

Tu Oráculo Bot está funcionando con:
- ✅ TA-Lib instalado correctamente
- ✅ Todos los servicios ejecutándose
- ✅ Base de datos Neon configurada
- ✅ Variables de entorno seguras
- ✅ Modo sandbox por defecto

**¡Disfruta de tu bot de trading!** 🚀 
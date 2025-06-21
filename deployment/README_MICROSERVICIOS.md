# 🚀 Guía de Deployment - Microservicios Oráculo Bot

Esta guía explica cómo deployar y gestionar los microservicios del Oráculo Bot en Ubuntu.

## 📋 Arquitectura de Microservicios

El sistema ahora se compone de 3 microservicios independientes:

| Servicio | Puerto | Descripción | Archivo de entrada |
|----------|--------|-------------|-------------------|
| **News Service** | 8000 | Servicio de recolección de noticias y análisis de sentimiento | `run_news_service.py` |
| **Grid Trading** | 8001 | Bot de trading con estrategia Grid | `run_grid_service.py` |
| **API Service** | 8002 | Solo API REST (sin schedulers) | `run_api_service.py` |

## 🔧 Configuración

### Variables de Entorno

Agrega las siguientes variables a tu archivo `.env`:

```bash
# Configuración de Microservicios
SERVICE_MODE=all  # "all", "news", "grid", "api"

# Configuración para Grid Bot
BINANCE_API_KEY=tu_api_key_aqui
BINANCE_API_SECRET=tu_api_secret_aqui
```

### Modos de Servicio

- `all`: Ejecuta todos los servicios (noticias + grid trading + API)
- `news`: Solo servicio de noticias
- `grid`: Solo grid trading bot
- `api`: Solo API REST

## 🏗️ Deployment en Ubuntu

### 1. Preparación

```bash
# Clonar/actualizar el repositorio
cd /home/tu_usuario/
git pull origin main

# Instalar dependencias
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configurar Services

```bash
# Editar el path en el script de deployment
nano deployment/deploy_services.sh

# Cambiar esta línea con tu path real:
PROJECT_PATH="/home/tu_usuario/oraculo_bot"
```

### 3. Ejecutar Deployment

```bash
# Dar permisos al script
chmod +x deployment/deploy_services.sh

# Ejecutar deployment
sudo ./deployment/deploy_services.sh
```

## 🎯 Gestión de Servicios

### Iniciar servicios

```bash
# Iniciar servicio de noticias
sudo systemctl start oraculo-news

# Iniciar grid trading bot
sudo systemctl start oraculo-grid

# Iniciar solo API
sudo systemctl start oraculo-api
```

### Ver estado

```bash
# Estado de servicios
sudo systemctl status oraculo-news
sudo systemctl status oraculo-grid
sudo systemctl status oraculo-api
```

### Ver logs en tiempo real

```bash
# Logs del servicio de noticias
sudo journalctl -u oraculo-news -f

# Logs del grid trading
sudo journalctl -u oraculo-grid -f

# Logs de la API
sudo journalctl -u oraculo-api -f
```

### Detener servicios

```bash
sudo systemctl stop oraculo-news
sudo systemctl stop oraculo-grid
sudo systemctl stop oraculo-api
```

### Reiniciar servicios

```bash
sudo systemctl restart oraculo-news
sudo systemctl restart oraculo-grid
sudo systemctl restart oraculo-api
```

## 🔍 Monitoreo

### Verificar que los servicios están corriendo

```bash
# Ver todos los servicios del oráculo
sudo systemctl list-units --type=service | grep oraculo

# Ver puertos en uso
netstat -tlnp | grep -E '8000|8001|8002'
```

### Logs detallados

```bash
# Ver últimas 100 líneas de logs
sudo journalctl -u oraculo-news -n 100

# Ver logs de las últimas 24 horas
sudo journalctl -u oraculo-grid --since "24 hours ago"
```

## 🚨 Troubleshooting

### Problemas comunes

1. **Servicio no inicia:**
   ```bash
   # Verificar logs de error
   sudo journalctl -u oraculo-news -n 50
   
   # Verificar permisos
   ls -la /home/tu_usuario/oraculo_bot/
   ```

2. **Puerto ya en uso:**
   ```bash
   # Ver qué proceso usa el puerto
   sudo lsof -i :8000
   
   # Matar proceso si es necesario
   sudo kill -9 <PID>
   ```

3. **Variables de entorno no cargan:**
   ```bash
   # Verificar archivo .env
   cat /home/tu_usuario/oraculo_bot/.env
   
   # Verificar path en archivo de servicio
   cat /etc/systemd/system/oraculo-news.service
   ```

## 🔄 Actualización de Código

```bash
# 1. Detener servicios
sudo systemctl stop oraculo-news oraculo-grid oraculo-api

# 2. Actualizar código
cd /home/tu_usuario/oraculo_bot
git pull origin main

# 3. Actualizar dependencias si es necesario
source venv/bin/activate
pip install -r requirements.txt

# 4. Reiniciar servicios
sudo systemctl start oraculo-news oraculo-grid oraculo-api
```

## 📊 Monitoreo de Recursos

```bash
# Ver uso de CPU y memoria por servicio
ps aux | grep python | grep oraculo

# Ver logs de sistema relacionados
dmesg | grep -i python
```

## 🌐 Proxy Reverso (Opcional)

Si quieres usar Nginx como proxy reverso:

```nginx
# /etc/nginx/sites-available/oraculo-bot
server {
    listen 80;
    server_name tu-dominio.com;

    location /api/ {
        proxy_pass http://127.0.0.1:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /news/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /grid/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🔐 Seguridad

- Los servicios corren bajo el usuario `www-data` por seguridad
- Los logs se almacenan en el journal de systemd
- Las claves API se cargan desde variables de entorno

---

¿Necesitas ayuda? Revisa los logs o contacta al administrador del sistema. 
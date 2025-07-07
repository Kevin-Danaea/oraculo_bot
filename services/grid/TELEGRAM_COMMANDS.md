# 🤖 Comandos de Telegram - Grid Trading Bot

## 📋 Comandos Disponibles

### 🚀 Comandos Básicos
- `/start` - Mensaje de bienvenida y comandos principales
- `/help` - Lista completa de comandos disponibles

### 📊 Información del Sistema
- `/status` - Estado del scheduler y modo de trading
- `/balance` - Capital asignado y balances por bot

### 🎮 Control del Sistema
- `/start_bot` - Iniciar Grid Trading
- `/stop_bot` - Detener Grid Trading
- `/monitor` - Ejecutar monitoreo manual

### ⚙️ Configuración
- `/sandbox` - Cambiar a modo pruebas (sandbox)
- `/production` - Cambiar a modo real (requiere confirmación)

## 📱 Cómo Usar los Comandos

### 1. Comandos Interactivos
Los comandos funcionan directamente en Telegram:
```
/status
/balance
/start_bot
```

### 2. Comandos sin Barra
También puedes usar los comandos sin la barra `/`:
```
status
balance
start_bot
```

### 3. Comandos por API (Testing)
Para testing, puedes usar el endpoint:
```
POST /telegram/command
Body: "status"
```

## 🔧 Detalles de Cada Comando

### `/start`
Muestra el mensaje de bienvenida con los comandos principales.

### `/help`
Muestra la lista completa de comandos organizados por categorías.

### `/status`
Muestra:
- Estado del scheduler (running/stopped)
- Intervalo de monitoreo
- Modo de trading (SANDBOX/PRODUCCIÓN)

### `/balance`
Muestra para cada bot activo:
- Capital asignado
- Capital disponible en cuenta
- Capital utilizable por bot
- Balance de monedas base y USDT
- Estado del aislamiento de capital

### `/start_bot`
Inicia el Grid Trading si no está ejecutándose.

### `/stop_bot`
Detiene el Grid Trading si está ejecutándose.

### `/monitor`
Ejecuta manualmente el monitoreo horario (gestión de transiciones).

### `/sandbox`
Cambia el sistema a modo sandbox:
- Cancela todas las órdenes activas
- Liquida posiciones
- Cambia credenciales a modo pruebas

### `/production`
Cambia el sistema a modo producción:
- Requiere confirmación: `production confirm`
- Cancela todas las órdenes activas
- Liquida posiciones
- Cambia credenciales a modo real

## 🚨 Notificaciones Automáticas

El bot también envía notificaciones automáticas:

### 🚀 Activación de Bot
Cuando un bot se activa, recibirás:
- Notificación de cambio de estado
- Resumen detallado con:
  - Capital asignado y utilizado
  - Número de órdenes creadas (compras y ventas)
  - Precio actual
  - Niveles de grilla

### 📊 Resúmenes Periódicos
Cada 2 horas recibirás:
- Número de bots activos
- Trades ejecutados
- Ganancia total
- Detalles por par

### 🔄 Cambios de Decisión
Cuando el Cerebro cambia decisiones:
- Estado anterior vs actual
- Acción tomada (activar/pausar)
- Capital asignado

## ⚠️ Notas Importantes

1. **Modo Producción**: El comando `/production` requiere confirmación para evitar activaciones accidentales.

2. **Aislamiento de Capital**: Cada bot opera con su capital asignado específico.

3. **Logs Detallados**: Todos los comandos generan logs detallados para debugging.

4. **Polling**: El bot está en modo polling, por lo que responde inmediatamente a los comandos.

## 🛠️ Troubleshooting

### Si los comandos no funcionan:
1. Verifica que el bot esté activo en los logs
2. Asegúrate de que el token de Telegram esté configurado
3. Verifica que el chat ID esté configurado correctamente

### Si no recibes notificaciones:
1. Verifica la conexión a Telegram
2. Revisa los logs de error
3. Asegúrate de que el bot tenga permisos para enviar mensajes

## 📞 Soporte

Para problemas técnicos, revisa los logs del servicio Grid Trading en:
```
services/grid/logs/
``` 
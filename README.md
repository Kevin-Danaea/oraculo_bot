# 🤖 Oráculo Bot - Sistema de Trading Automatizado

Sistema de microservicios para análisis y trading automatizado de criptomonedas con **TA-Lib estable** usando conda.

## 🎯 Características Principales

### 🧠 **Brain - Análisis Técnico**
- **TA-Lib Estable**: Instalado via conda para evitar problemas de compilación
- **Análisis Avanzado**: Indicadores técnicos y toma de decisiones
- **Python 3.10**: Compatibilidad garantizada

### 📊 **Grid - Trading Automatizado**
- **Estrategias Grid**: Trading automatizado con gestión de riesgo
- **Modo Sandbox**: Activado por defecto para seguridad
- **Control Telegram**: Interfaz completa via bot

### 📰 **News - Análisis de Sentimiento**
- **Análisis IA**: Procesamiento de noticias con Google Gemini
- **Monitoreo 24/7**: Recolección automática de fuentes confiables
- **Alertas Inteligentes**: Notificaciones basadas en sentimiento

### 🔥 **Hype - Detección de Tendencias**
- **Radar Social**: Monitoreo de redes sociales
- **Detección Temprana**: Identificación de tendencias emergentes
- **Alertas Automáticas**: Notificaciones en tiempo real

### 🏗️ **Arquitectura Modular Refactorizada**
- **Microservicios**: Servicios independientes y escalables
- **Telegram Interface**: Completamente refactorizada en handlers modulares
- **Código Limpio**: 70% reducción de líneas por archivo
- **Zero Breaking Changes**: Compatibilidad total mantenida

## 🏗️ Arquitectura del Sistema

```
🤖 Oráculo Bot
├── 🧠 Brain (Puerto 8001)           # Análisis técnico con TA-Lib
├── 📊 Grid (Puerto 8002)            # Trading automatizado
├── 📰 News (Puerto 8003)            # Análisis de noticias
└── 🔥 Hype (Puerto 8004)            # Detección de tendencias
```

### 📁 Estructura del Proyecto

```
oraculo_bot/
├── services/                    # 🔥 MICROSERVICIOS
│   ├── brain/                   # 🧠 Análisis técnico con TA-Lib
│   │   ├── app/
│   │   │   ├── application/     # Casos de uso
│   │   │   ├── domain/          # Entidades y interfaces
│   │   │   └── infrastructure/  # Implementaciones
│   │   └── Dockerfile           # Con conda para TA-Lib
│   ├── grid/                    # 📊 Grid trading
│   │   ├── app/
│   │   └── Dockerfile
│   ├── news/                    # 📰 Análisis de noticias
│   │   ├── app/
│   │   └── Dockerfile
│   └── hype/                    # 🔥 Detección de tendencias
│       ├── app/
│       └── Dockerfile
├── shared/                      # 🧩 CÓDIGO COMPARTIDO
│   ├── config/                  # ⚙️ Configuración
│   ├── database/                # 💾 Base de datos
│   └── services/                # 🔧 Servicios comunes
├── deployment/                  # 🚀 Scripts de despliegue
├── docker-compose.yml           # 🐳 Orquestación
└── deploy.sh                    # 🚀 Despliegue simplificado
```

## 🤖 Grid Bot V2.5 - Funcionalidades

### 🛡️ **Estrategias Defensivas**

#### 🚨 Stop-Loss Inteligente
```
Trigger: Precio < (orden_más_baja × (1 - stop_loss%))
Acción:  Cancelar TODO → Vender TODO → Detener bot → Modo standby
Control: Configurable desde Telegram (0.1% - 20%)
```

#### 🧹 Limpieza Automática de Órdenes Huérfanas
```
Al Reiniciar: Detecta órdenes en Binance del bot anterior
Identifica:   Por clientOrderId (GRID_BUY_, GRID_SELL_)
Cancela:      Automáticamente todas las órdenes huérfanas
Notifica:     Resultado detallado vía Telegram
```

### 📈 **Estrategias Ofensivas**

#### 🎯 Trailing Up Dinámico
```
Trigger: Precio > límite_superior_del_grid
Acción:  Recalcular grid → Nuevas órdenes en niveles altos
Objetivo: Seguir tendencias alcistas automáticamente
```

### ⏸️ **Modo Standby Inteligente**
```
Al Reiniciar: NO inicia trading automáticamente
Limpia:       Órdenes huérfanas de sesiones anteriores  
Notifica:     Estado y acciones tomadas
Activación:   Solo manual con /start_bot
```

## 📰 News Service V2.5 - Funcionalidades

### 🔍 **Recolección Inteligente de Contenido**

#### 📱 Subreddits Monitoreados (25 total)
```
Principales: CryptoCurrency, Bitcoin, ethereum, ethtrader, defi
Trading:     CryptoMarkets, CryptoCurrencyTrading, altcoin, btc  
Comunidad:   dogecoin, litecoin, ripple, cardano, CryptoNews
Exchanges:   binance, Coinbase, Crypto_com
Trending:    CryptoMoonShots, cryptomoonshots, SatoshiStreetBets
Variantes:   bitcoin, Ethereum, DeFi (case-sensitive coverage)
```

#### 🌐 Dominios de Noticias Confiables (25 total)
```
Crypto Tier 1: coindesk.com, cointelegraph.com, decrypt.co
Finance Tier 1: bloomberg.com, reuters.com, wsj.com, ft.com
Tech & News:    forbes.com, cnbc.com, techcrunch.com
Exchanges:      coinbase.com, kraken.com, crypto.com, binance.com
Specialized:    theblockcrypto.com, cryptoslate.com, beincrypto.com
```

### 🧠 **Filtros de Calidad Aplicados**

#### 🚫 Pipeline de Filtros
```
1. Calidad Básica    → Elimina [deleted], [removed], stickied posts
2. Engagement Mínimo → Score ≥ 6 (retención de audiencia)
3. Contenido Válido  → Noticias: dominios confiables | Posts: >150 chars
4. Anti-Duplicados   → Previene reprocesamiento de URLs
```

#### 📊 Tipos de Contenido Procesado
```
📰 Noticias Externas:
   - Enlaces de dominios verificados
   - Solo títulos (headlines)
   - Fuente: "Reddit r/Bitcoin (coindesk.com)"

💬 Posts de Comunidad:
   - Self-posts con contenido sustancial (>150 chars)
   - Título + contenido combinado para análisis
   - Engagement mínimo validado
   - Fuente: "Reddit r/CryptoCurrency (Community Post)"
```

### 🤖 **Análisis IA con Google Gemini**

#### 📈 Capacidad de Procesamiento
```
Límite por Ciclo: 500 noticias (8x incremento vs V2.0)
Frecuencia:       Cada 4 horas
Rate Limiting:    2 segundos entre análisis
Throughput:       ~2,000 noticias procesadas por día
```

#### 🧠 Análisis Multidimensional
```
Sentiment Score:   -1.0 a +1.0 (cuantitativo)
Primary Emotion:   Euforia, Optimismo, Neutral, Incertidumbre, Miedo
News Category:     Regulación, Tecnología/Adopción, Mercado/Trading, 
                   Seguridad, Macroeconomía
```

## 🎮 Comandos de Telegram

### 📋 **Comandos Básicos**
```
/start          - Bienvenida e información general
/config         - Configuración paso a paso inteligente
/start_bot      - Iniciar trading manual
/stop_bot       - Detener trading (modo standby)
/restart_bot    - Reiniciar con nueva configuración
/status         - Estado detallado con protecciones
/delete_config  - Eliminar configuración guardada
```

### 🛡️ **Comandos de Protecciones**
```
/protections         - Ver estado completo de protecciones
/enable_stop_loss    - Activar stop-loss
/disable_stop_loss   - Desactivar stop-loss  
/enable_trailing     - Activar trailing up
/disable_trailing    - Desactivar trailing up
/set_stop_loss X     - Configurar % stop-loss (0.1-20%)
```

## 🚀 Instalación y Configuración

### 📋 Prerrequisitos
- Python 3.8+
- Cuenta Binance con API keys
- Bot de Telegram  
- Google API Key (Gemini)
- Reddit API credentials

### 🔧 Instalación Rápida

1. **Clonar y configurar**:
   ```bash
   git clone <repo>
   cd oraculo_bot
   pip install -r requirements.txt
   ```

2. **Configurar variables (.env)**:
   ```env
   # Binance API
   BINANCE_API_KEY=tu_api_key
   BINANCE_SECRET_KEY=tu_secret_key
   
   # Telegram Bot
   TELEGRAM_BOT_TOKEN=tu_bot_token
   TELEGRAM_CHAT_ID=tu_chat_id
   
   # Google Gemini API
   GOOGLE_API_KEY=tu_google_api_key
   
   # Reddit API  
   REDDIT_CLIENT_ID=tu_client_id
   REDDIT_CLIENT_SECRET=tu_client_secret
   ```

3. **Ejecutar servicios**:
   ```bash
   # Grid Trading (Principal)
   python run_grid_service.py
   
   # News Analysis  
   python run_news_service.py
   
   # Hype Radar
   python run_hype_service.py
   
   # API Gateway
   python run_api_service.py
   ```

## 🏭 Despliegue en Producción (VPS)

```bash
# Clonar y configurar
git clone <repo> && cd oraculo_bot

# Configurar environment
cp .env.example .env
# Editar .env con tus credenciales

# Desplegar servicios systemd
chmod +x deployment/deploy_services.sh
sudo ./deployment/deploy_services.sh

# Verificar servicios
sudo systemctl status oraculo-grid.service
sudo systemctl status oraculo-news.service
sudo systemctl status oraculo-hype.service  
sudo systemctl status oraculo-api.service
```

## 💾 Base de Datos

### 📊 **GridBotConfig V2.5**
```sql
- pair: ETH/USDT, BTC/USDT, etc.
- total_capital: Capital en USDT
- grid_levels: Número de niveles del grid
- price_range_percent: % rango del precio
- stop_loss_percent: % stop-loss (1-20%)
- enable_stop_loss: Activar/desactivar stop-loss
- enable_trailing_up: Activar/desactivar trailing up
```

## 📈 Monitoreo

### 🔍 **Health Checks**
- **API Gateway**: `http://localhost:8002/api/v1/health`
- **Grid Worker**: `http://localhost:8001/health`  
- **News Worker**: `http://localhost:8000/health`

### 📂 **Logs**
```bash
# Ver logs del Grid Bot
tail -f logs/oraculo_grid.log

# Ver activación de protecciones
grep -E "(stop-loss|trailing)" logs/oraculo_grid.log

# Ver modo standby
grep "standby" logs/oraculo_grid.log
```

## 🎯 Flujo de Operación

### 🆕 **Primer Uso**
```
1. /config → Configuración automática inteligente
2. /start_bot → Inicio manual del trading  
3. 🤖 Bot opera con estrategias activadas
4. 📊 /status → Monitoreo en tiempo real
```

### 🔄 **Reinicio de Servidor**
```
1. 🧹 Limpieza automática de órdenes huérfanas
2. ⏸️ Modo standby (NO inicia automáticamente)
3. 📢 Notificación automática a Telegram  
4. 🎮 /start_bot → Reactivación manual
```

## 🛡️ Características de Seguridad

✅ **Control Manual**: No trading automático tras reinicio  
✅ **Limpieza Inteligente**: Detecta y cancela órdenes huérfanas  
✅ **Stop-Loss**: Protección automática contra pérdidas  
✅ **Identificación Única**: Todas las órdenes marcadas como del bot  
✅ **Notificaciones**: Información completa vía Telegram  
✅ **Logs Detallados**: Monitoreo completo de operaciones  

---

## 🎯 Hype Radar - Detector de Tendencias

### 🔍 **¿Qué Detecta?**
El Hype Radar monitorea **incrementos súbitos** en menciones de criptomonedas en subreddits de alto riesgo para identificar posibles "pumps" antes de que ocurran.

### 📡 **Subreddits Monitoreados**
```
• SatoshiStreetBets        • CryptoMoonShots
• CryptoCurrencyTrading    • altcoin
• CryptoHorde             • CryptoBets  
• CryptoPumping           • SmallCryptos
• shitcoinstreetbets
```

### 🎯 **Detección Inteligente**
- **Lista Principal**: 45+ tickers conocidos (DOGE, SHIB, PEPE, etc.)
- **Detección Automática**: Cualquier ticker que supere el umbral
- **Patrones**: $TICKER, TICKER/USD, "TICKER is pumping", etc.

### 📊 **Algoritmo de Análisis**
```
1. 🕐 Escaneo cada 5 minutos
2. 📈 Cuenta menciones por ticker
3. 🔍 Compara vs promedio de 24h
4. 🚨 Alerta si incremento > 500%
5. 💾 Guarda evento en base de datos
6. 📱 Envía notificación por Telegram
```

### 🚨 **Tipos de Alertas**
```
🔥 ALERTA DE HYPE (500%+)     - Incremento significativo
🔥🔥 ALERTA ALTA (1000%+)     - Incremento muy alto  
🔥🔥🔥 ALERTA EXTREMA (1500%+) - Posible pump viral
```

### 📱 **Ejemplo de Alerta**
```
🚨 ALERTA DE HYPE

🔥 TICKER: $DOGE
📈 Menciones última hora: 15
📊 Promedio 24h: 2.5  
🚀 Incremento: 500.0%
⚡ Umbral configurado: 500%

📡 HYPE SIGNIFICATIVO DETECTADO
💡 Monitorear de cerca

⏰ 2025-06-23 15:30:00
🤖 Hype Radar Alert System
```

### 🌙 **Resumen Diario (23:00 México Centro)**
```
📊 RESUMEN DIARIO - HYPE RADAR
📅 Fecha: 2025-06-23

🚨 Alertas enviadas: 5

🔥 TOP TRENDING DEL DÍA:
1. $DOGE: 47 menciones
2. $SHIB: 23 menciones  
3. $PEPE: 18 menciones
4. $SOL: 12 menciones
5. $ADA: 8 menciones
```

### 🔧 **Configuración**
- **Puerto**: 8003
- **Umbral por defecto**: 500% de incremento
- **Cooldown**: 1 hora por ticker (evita spam)
- **Base de datos**: Tabla `hype_events` con todos los eventos

### 🌐 **Endpoints API**
```
GET  /health          - Estado del servicio
GET  /trends?hours=24  - Resumen de tendencias
GET  /events?hours=24  - Eventos desde BD
POST /configure?threshold=500.0  - Configurar umbral
GET  /alerts/test      - Probar sistema de alertas
```

## 📚 Documentación Adicional

- **[CHANGELOG.md](CHANGELOG.md)** - Historial completo de cambios
- **[deployment/](deployment/)** - Guías de despliegue
- **[logs/](logs/)** - Archivos de log del sistema

---

**🔮 Oráculo Cripto Bot V2.5** - Trading Inteligente + Análisis de Noticias + Detección de Tendencias  
*Desarrollado con 💚 para traders crypto* 

## Servicio Grid Trading (Arquitectura 2025)

### Flujo Híbrido Tiempo-Real + Gestión Horaria

| Frecuencia | Caso de uso | Responsabilidad |
|------------|-------------|-----------------|
| **Cada `REALTIME_MONITOR_INTERVAL_SECONDS` segundos** | `RealTimeGridMonitorUseCase` | • Detecta fills inmediatamente<br>• Crea órdenes complementarias al instante<br>• Envía notificaciones de trades |
| **Cada `MONITORING_INTERVAL_HOURS` horas** | `ManageGridTransitionsUseCase` | • Pausar/activar bots según decisiones del Cerebro<br>• Limpia la caché del monitor RT<br>• Envía resúmenes de actividad |

### Scheduler Híbrido
El archivo `services/grid/app/infrastructure/scheduler.py` coordina ambos casos de uso mediante `apscheduler`.

```python
# Intervalos configurables en services/grid/app/config.py
REALTIME_MONITOR_INTERVAL_SECONDS = 10   # ⚡ Monitor RT
MONITORING_INTERVAL_HOURS = 1            # ⏰ Gestión horaria
```

### Estructura de Carpetas (Clean Architecture)
```
services/grid/
└── app/
    ├── domain/
    ├── application/
    │   ├── realtime_grid_monitor_use_case.py
    │   ├── manage_grid_transitions_use_case.py
    │   └── service_lifecycle_use_case.py
    ├── infrastructure/
    │   ├── scheduler.py  ← Scheduler híbrido
    │   └── ...
    └── config.py
```

### Cambios Importantes
1. **Eliminados módulos legacy** (`MonitorGridOrdersUseCase`, `GetSystemStatusUseCase`).
2. **Nuevo caso de uso** `RealTimeGridMonitorUseCase` para tiempo real.
3. **Constantes de configuración** añadidas: `REALTIME_MONITOR_INTERVAL_SECONDS`, `REALTIME_CACHE_EXPIRY_MINUTES`.
4. **Scheduler** ahora crea dos jobs: tiempo real y gestión horaria.

> Para iniciar el servicio Grid:
>
> ```bash
> python services/grid/app/main.py  # arranca GridScheduler.start()
> ```

--- 
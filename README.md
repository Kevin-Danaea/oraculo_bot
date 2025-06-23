# 🔮 Oráculo Cripto Bot V2.5 - Grid Trading Inteligente + News Analysis + Arquitectura Modular

Un sistema avanzado de **microservicios** para **trading automatizado inteligente** y **análisis de noticias crypto** con **estrategias defensivas/ofensivas** y **control total desde Telegram**.

## 📋 Descripción del Proyecto

El **Oráculo Cripto Bot V2.0** es un ecosistema moderno que combina **Grid Trading inteligente con IA** y **análisis de sentimientos** de noticias crypto. La arquitectura está diseñada con **microservicios independientes** y **control avanzado desde Telegram**.

### 🎯 Arquitectura V2: Pure Workers + Gateway + Telegram Control

#### 📰 News Worker (Puerto 8000)
- **Recolección Automática**: Reddit (r/CryptoCurrency) cada hora
- **Análisis de Sentimientos**: Google Gemini AI cada 4 horas  
- **Background Jobs**: Schedulers independientes
- **Health Check**: `/health` para monitoreo

#### 🤖 Grid Worker V2.0 (Puerto 8001) ⭐ **NUEVO**
- **🛡️ Grid Trading Inteligente**: Stop-Loss + Trailing Up automático
- **⏸️ Modo Standby**: NO inicia automáticamente tras reinicio
- **🧹 Limpieza Automática**: Cancela órdenes huérfanas al startup
- **🎮 Control Total**: Comandos manuales desde Telegram
- **🚨 Estrategias Defensivas**: Protección automática contra pérdidas
- **📈 Estrategias Ofensivas**: Seguimiento de tendencias alcistas
- **Background Jobs**: Trading 24/7 con IA integrada

#### 🌐 API Gateway (Puerto 8002)
- **Único Punto HTTP**: Entrada pública centralizada
- **Health Checks Agregados**: Estado de todos los workers
- **Monitoreo Centralizado**: Estado completo del sistema

### 🏗️ Arquitectura V2.0 Mejorada

```
oraculo_bot/
├── services/                    # 🔥 MICROSERVICIOS
│   ├── api/                     # 🌐 API Gateway (Puerto 8002)
│   │   ├── main.py              # Entry point HTTP
│   │   └── routers/
│   │       └── status_router.py # Health checks agregados
│   ├── news/                    # 📰 News Worker (Puerto 8000)
│   │   ├── main.py              # News + Sentiment analysis
│   │   ├── schedulers/          # Reddit + Gemini AI jobs
│   │   └── services/            # Reddit API + Google Gemini
│   └── grid/                    # 🤖 Grid Worker V2.0 (Puerto 8001) ⭐
│       ├── main.py              # Grid trading service
│       ├── core/                # 🧠 Trading engine V2
│   │   ├── startup_manager.py     # ⭐ Limpieza + Standby
│   │   ├── monitor_v2.py          # ⭐ Monitor inteligente
│   │   ├── trading_engine.py      # Motor principal
│   │   ├── config_manager.py      # Gestión configuración
│   │   ├── order_manager.py       # Gestión órdenes
│   │   └── state_manager.py       # Persistencia estado
│   │   └── interfaces/          # 🎮 Control V2 Refactorizado ⭐
│   │       ├── telegram_interface.py    # ⭐ Orquestador principal (12KB)
│   │       └── handlers/                # ⭐ Handlers modulares
│   │           ├── base_handler.py      # Métodos comunes + DB ops
│   │           ├── basic_commands.py    # Comandos básicos (/start, /status)
│   │           ├── config_flow.py       # Flujo configuración (/config)
│   │           └── advanced_strategies.py # Estrategias V2 (/protections)
│   └── schedulers/          # 📅 Jobs V2
│       └── grid_scheduler.py      # ⭐ Modo standby
├── shared/                      # 🧩 CÓDIGO COMPARTIDO
│   ├── config/                  # Configuración centralizada
│   ├── database/                # 💾 SQLite + Modelos V2
│   │   ├── models.py            # ⭐ Modelos actualizados V2
│   │   └── session.py           # Gestión DB
│   └── services/                # 🔧 Servicios compartidos
│       ├── logging_config.py    # Logging centralizado
│       ├── telegram_service.py  # Mensajería Telegram
│       └── telegram_bot_service.py # Bot service
├── deployment/                  # 🚀 DESPLIEGUE
│   ├── deploy_services.sh       # Script automático
│   └── services/                # Servicios systemd
│       ├── oraculo-api.service
│       ├── oraculo-news.service
│       └── oraculo-grid.service
├── run_api_service.py           # 🚀 Entry point API
├── run_news_service.py          # 🚀 Entry point News
├── run_grid_service.py          # 🚀 Entry point Grid V2
└── requirements.txt             # Dependencias
```

## 🧩 Arquitectura Modular V2.5 - Refactorización Completa ⭐

### 🎯 Telegram Interface Refactorizada

El **control de Telegram** ha sido completamente **refactorizado** con **arquitectura modular** para mejorar mantenibilidad, escalabilidad y colaboración:

#### 📊 **Comparativa Before/After**
- **❌ Antes**: `telegram_interface.py` → **858 líneas** (41KB) - Monolítico
- **✅ Después**: **Arquitectura modular** → **~200 líneas por módulo** (12KB principal)
- **🎯 Reducción**: **70% menos código** por archivo

#### 🏗️ **Nueva Estructura Modular**
```
services/grid/interfaces/
├── telegram_interface.py           # 🎮 Orquestador principal (12KB)
│   ├── Inicialización handlers
│   ├── Registro de comandos
│   ├── Métodos de compatibilidad
│   └── Delegación a handlers especializados
└── handlers/                       # 🧩 Handlers especializados
    ├── base_handler.py             # 🏗️ Base común (6.3KB)
    │   ├── Métodos DB compartidos
    │   ├── Validaciones comunes
    │   ├── Configuración óptima
    │   └── Gestión usuarios
    ├── basic_commands.py           # 📋 Comandos básicos (13.6KB)
    │   ├── /start, /status
    │   ├── /start_bot, /stop_bot
    │   ├── /restart_bot
    │   └── /delete_config
    ├── config_flow.py              # ⚙️ Configuración (9.5KB)
    │   ├── /config (flujo completo)
    │   ├── Selección de pares
    │   ├── Input de capital
    │   └── Confirmación final
    └── advanced_strategies.py      # 🛡️ Estrategias V2 (9.2KB)
        ├── /protections
        ├── /enable_stop_loss, /disable_stop_loss
        ├── /enable_trailing, /disable_trailing
        └── /set_stop_loss X
```

#### ✅ **Beneficios de la Refactorización**

🔧 **Mantenibilidad**
- **Separación clara** de responsabilidades
- **Código específico** por funcionalidad  
- **Fácil localización** de bugs
- **Testing granular** por módulo

📈 **Escalabilidad**
- **Nuevos comandos** → Agregar al handler correspondiente
- **Nuevas funcionalidades** → Crear nuevo handler
- **Zero impact** en otros módulos
- **Crecimiento sostenible**

👥 **Colaboración**
- **Equipos paralelos** pueden trabajar en diferentes handlers
- **Merge conflicts** minimizados
- **Code reviews** más enfocados
- **Onboarding** más rápido

🛡️ **Robustez**
- **Manejo de errores** estandarizado
- **Logging consistente** por módulo
- **Configuración centralizada**
- **Compatibilidad total** mantenida

#### 🔄 **Zero Breaking Changes Garantizado**

✅ **API Externa Idéntica**: Todos los métodos públicos funcionan igual  
✅ **Imports Compatibles**: `from telegram_interface import GridTelegramInterface`  
✅ **Comportamiento Igual**: Misma experiencia de usuario en Telegram  
✅ **Configuración Igual**: Mismos comandos y flujos  

#### 🎮 **Comandos por Handler**

**📋 BasicCommandsHandler**
```
/start          - Bienvenida + estado del sistema
/status         - Estado detallado con protecciones V2
/start_bot      - Iniciar trading manual
/stop_bot       - Detener trading (modo standby)  
/restart_bot    - Reiniciar con nueva configuración
/delete_config  - Eliminar configuración guardada
```

**⚙️ ConfigFlowHandler**  
```
/config                - Iniciar configuración paso a paso
config_pair_selection  - Manejo selección de pares
config_capital_input   - Manejo input de capital
config_confirmation    - Confirmación final
```

**🛡️ AdvancedStrategiesHandler**
```
/protections         - Estado completo de protecciones
/enable_stop_loss    - Activar stop-loss
/disable_stop_loss   - Desactivar stop-loss  
/enable_trailing     - Activar trailing up
/disable_trailing    - Desactivar trailing up
/set_stop_loss X     - Configurar % stop-loss (0.1-20%)
```

## 🚀 Grid Bot V2.0 - Funcionalidades Avanzadas

### 🛡️ Estrategias Defensivas

#### 🚨 Stop-Loss Inteligente
- **Trigger**: Precio < (orden_más_baja × (1 - stop_loss%))
- **Acción**: Cancelar TODO → Vender TODO → Detener bot → Modo standby
- **Objetivo**: Protección automática contra pérdidas > X%
- **Control**: Configurable desde Telegram (0.1% - 20%)

#### ⏸️ Modo Standby Automático
- **Al reiniciar servidor**: Bot NO inicia automáticamente
- **Limpieza automática**: Cancela órdenes huérfanas de sesiones anteriores
- **Notificación**: Informa limpieza y estado standby
- **Activación**: Solo manual con `/start_bot` desde Telegram

### 📈 Estrategias Ofensivas

#### 🎯 Trailing Up Dinámico
- **Trigger**: Precio > límite_superior_del_grid
- **Acción**: Cancelar órdenes → Recalcular grid → Nuevas órdenes en niveles altos
- **Objetivo**: Seguir tendencias alcistas automáticamente
- **Optimización**: Reutiliza balances para minimizar comisiones

### 🎮 Control Total desde Telegram

#### 📋 Comandos Básicos V2
```
/start          - Bienvenida e información general
/config         - Configuración paso a paso inteligente
/start_bot      - ⭐ Iniciar trading manual
/stop_bot       - ⭐ Detener trading (modo standby)
/restart_bot    - ⭐ Reiniciar con nueva configuración
/status         - ⭐ Estado detallado V2 con protecciones
/delete_config  - Eliminar configuración guardada
```

#### 🛡️ Comandos V2 - Estrategias Avanzadas
```
/protections         - Ver estado completo de protecciones
/enable_stop_loss    - Activar stop-loss
/disable_stop_loss   - Desactivar stop-loss  
/enable_trailing     - Activar trailing up
/disable_trailing    - Desactivar trailing up
/set_stop_loss X     - Configurar % stop-loss (0.1-20%)
```

#### 🧠 Configuración Automática Inteligente V2
- **Capital < $50**: 2 niveles, 5% rango, **3% stop-loss**
- **Capital $50-100**: 4 niveles, 8% rango, **4% stop-loss**
- **Capital $100-500**: 6 niveles, 10% rango, **5% stop-loss**
- **Capital > $500**: 6 niveles, 12% rango, **6% stop-loss**

### 🔄 Flujo de Operación V2

#### 🆕 Primer Uso
```
1. /config → Configuración automática inteligente
2. /start_bot → Inicio manual del trading
3. 🤖 Bot opera con estrategias V2 activadas
4. 📊 /status → Monitoreo en tiempo real
```

#### 🔄 Reinicio de Servidor
```
1. 🧹 Limpieza automática de órdenes huérfanas
2. ⏸️ Modo standby (NO inicia automáticamente)
3. 📢 Notificación automática a Telegram
4. 🎮 /start_bot → Reactivación manual
```

#### 🚨 Activación de Stop-Loss
```
1. 📉 Precio baja > X% del grid
2. 🚫 Cancelación automática de órdenes
3. 💸 Venta automática de crypto
4. 🛑 Detención automática del bot
5. ⏸️ Modo standby hasta reactivación manual
6. 📨 Notificación detallada de pérdidas
```

#### 📈 Activación de Trailing Up
```
1. 🚀 Precio sube > límite superior del grid
2. 🚫 Cancelación automática de órdenes antiguas
3. 🎯 Recálculo de grid en niveles superiores
4. 📈 Nuevas órdenes en zona alta
5. 🤖 Continúa trading automáticamente
6. 📨 Notificación de reposicionamiento
```

## 🚀 Instalación y Configuración

### 📋 Prerrequisitos

- Python 3.8 o superior
- **Cuenta de Reddit** para API credentials (noticias)
- **Google API Key** para análisis de sentimientos con Gemini
- **Cuenta de Binance** para trading
- **Bot de Telegram** para control y notificaciones

### 🔧 Instalación Local

1. **Clonar el repositorio**:
   ```bash
   git clone <url-del-repositorio>
   cd oraculo_bot
   ```

2. **Crear y activar el entorno virtual**:
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Instalar las dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variables de entorno** (`.env`):
   ```env
   # Configuración General
   PROJECT_NAME=Oráculo Cripto Bot V2
   DATABASE_URL=sqlite:///./oraculo.db
   
   # Reddit API (noticias)
   REDDIT_CLIENT_ID=tu_client_id_aqui
   REDDIT_CLIENT_SECRET=tu_client_secret_aqui
   REDDIT_USER_AGENT=OraculoBot by tu_usuario_de_reddit
   
   # Google Gemini API (análisis sentimientos)
   GOOGLE_API_KEY=tu_google_api_key_aqui
   
   # Binance API (trading)
   BINANCE_API_KEY=tu_binance_api_key_aqui
   BINANCE_SECRET_KEY=tu_binance_secret_key_aqui
   
   # Telegram Bot (control + notificaciones)
   TELEGRAM_BOT_TOKEN=tu_telegram_bot_token
   TELEGRAM_CHAT_ID=tu_chat_id
   ```

## 🎮 Ejecución del Proyecto

### 🔥 Ejecutar Microservicios V2

```bash
# 📰 News Worker (Puerto 8000)
python run_news_service.py

# 🤖 Grid Trading Worker V2 (Puerto 8001) ⭐
python run_grid_service.py

# 🌐 API Gateway (Puerto 8002)
python run_api_service.py
```

### 🌐 URLs del Sistema

- **🌐 API Gateway**: http://localhost:8002
  - **Documentación**: http://localhost:8002/docs
  - **Health Check**: http://localhost:8002/api/v1/health
- **📰 News Worker**: http://localhost:8000/health (interno)
- **🤖 Grid Worker V2**: http://localhost:8001/health (interno)

## 🏭 Despliegue en Producción

### 🐧 VPS Ubuntu (Recomendado)

1. **Clonar y configurar**:
   ```bash
   git clone <repo>
   cd oraculo_bot
   cp .env.example .env
   # Editar .env con tus credenciales
   ```

2. **Desplegar servicios systemd**:
   ```bash
   chmod +x deployment/deploy_services.sh
   sudo ./deployment/deploy_services.sh
   ```

3. **Verificar servicios**:
   ```bash
   sudo systemctl status oraculo-grid.service
   sudo systemctl status oraculo-news.service
   sudo systemctl status oraculo-api.service
   ```

### 🎯 Beneficios del Modo Standby V2

✅ **Seguridad**: No trading automático tras reinicio  
✅ **Limpieza**: Cancela órdenes huérfanas automáticamente  
✅ **Control**: Inicio manual desde Telegram  
✅ **Notificaciones**: Informa estado tras reinicio  
✅ **Profesional**: Comportamiento predecible en producción  

## 🧠 Base de Datos V2

### 📊 Modelos Actualizados

#### GridBotConfig V2
```sql
CREATE TABLE gridbot_configs (
    id INTEGER PRIMARY KEY,
    pair VARCHAR(20) NOT NULL,           -- ETH/USDT, BTC/USDT
    total_capital FLOAT NOT NULL,        -- Capital en USDT
    grid_levels INTEGER NOT NULL,        -- Número de niveles
    price_range_percent FLOAT NOT NULL,  -- % rango del grid
    stop_loss_percent FLOAT DEFAULT 5.0, -- ⭐ % stop-loss
    enable_stop_loss BOOLEAN DEFAULT 1,  -- ⭐ Activar stop-loss
    enable_trailing_up BOOLEAN DEFAULT 1, -- ⭐ Activar trailing
    telegram_chat_id VARCHAR(50),        -- Chat ID Telegram
    is_active BOOLEAN DEFAULT 1,         -- Configuración activa
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### GridBotState V2
```sql
CREATE TABLE gridbot_states (
    id INTEGER PRIMARY KEY,
    config_id INTEGER,                   -- FK a config
    lowest_buy_price FLOAT,              -- ⭐ Precio compra más bajo
    highest_sell_price FLOAT,            -- ⭐ Precio venta más alto
    stop_loss_triggered_count INTEGER DEFAULT 0, -- ⭐ Veces activado SL
    trailing_up_triggered_count INTEGER DEFAULT 0, -- ⭐ Veces activado TU
    last_grid_adjustment TIMESTAMP,      -- ⭐ Último ajuste
    active_orders_json TEXT,             -- Órdenes activas JSON
    last_updated TIMESTAMP DEFAULT NOW()
);
```

## 📈 Monitoreo y Logs

### 📂 Estructura de Logs
```
logs/
├── oraculo_grid.log     # Grid Bot V2 principal
├── oraculo_news.log     # News worker
├── oraculo_api.log      # API Gateway
└── system.log           # Logs generales
```

### 🔍 Comandos de Monitoreo
```bash
# Ver logs del Grid Bot V2
tail -f logs/oraculo_grid.log

# Ver solo stop-loss y trailing up
grep -E "(stop-loss|trailing)" logs/oraculo_grid.log

# Ver modo standby
grep "standby" logs/oraculo_grid.log

# Estado de servicios
curl http://localhost:8002/api/v1/health
```

## 🛡️ Seguridad y Mejores Prácticas

### 🔐 API Keys
- Mantén las credenciales en `.env` (nunca en código)
- Usa permisos mínimos en Binance (solo trading spot)
- Revisa logs regularmente para detectar anomalías

### 💰 Trading Seguro
- Empieza con capital pequeño ($50-100)
- Usa stop-loss conservadores (3-5%)
- Monitorea desde Telegram diariamente
- Revisa configuración antes de reiniciar

### 🎮 Control desde Telegram
- Solo tú debes tener acceso al bot
- Usa `/status` frecuentemente
- Activa notificaciones importantes
- Mantén backup de configuraciones

## 🔮 Roadmap & Logros

### ✅ **V2.5 Completado - Refactorización Modular**
- [x] **Arquitectura Modular**: Telegram interface refactorizada (70% reducción código)
- [x] **Handlers Especializados**: 4 módulos independientes por funcionalidad
- [x] **Zero Breaking Changes**: Compatibilidad 100% mantenida
- [x] **Escalabilidad**: Base sólida para crecimiento futuro
- [x] **Mantenibilidad**: Código organizado y testeable

### 🚀 **V3.0 Próximas Funcionalidades**
- [ ] **Multi-pair trading**: Varios pares simultáneos
- [ ] **DCA inteligente**: Dollar Cost Averaging con IA
- [ ] **Backtesting**: Pruebas históricas de estrategias
- [ ] **Web Dashboard**: Panel web para monitoreo
- [ ] **Stop-loss dinámico**: Ajuste automático según volatilidad
- [ ] **Integración CEX**: Soporte para más exchanges
- [ ] **Handler Testing**: Tests unitarios para cada módulo

---

## 🎯 Grid Bot V2.5 - Resumen Ejecutivo

**🛡️ Defensivo**: Stop-loss configurable, modo standby automático, limpieza de órdenes  
**📈 Ofensivo**: Trailing up dinámico, seguimiento de tendencias  
**🎮 Control**: Comandos avanzados desde Telegram con arquitectura modular  
**🏭 Producción**: Despliegue seguro, monitoreo completo  
**💡 Inteligente**: Configuración automática, estrategias adaptativas  
**🧩 Modular**: Refactorización completa, 70% menos código por archivo
**🚀 Escalable**: Base sólida para crecimiento futuro sin breaking changes

¡Grid Bot V2.5 está listo para trading profesional con código enterprise-grade! 🚀 
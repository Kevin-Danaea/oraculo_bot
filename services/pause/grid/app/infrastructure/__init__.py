"""
Capa de infraestructura para el servicio Grid Trading.

Esta capa contiene las implementaciones concretas de las interfaces del dominio:
- DatabaseGridRepository: Repositorio de datos usando SQLAlchemy
- BinanceExchangeService: Servicio de exchange usando Binance
- TelegramGridNotificationService: Servicio de notificaciones por Telegram
- GridTradingCalculator: Calculador de grillas y órdenes
- GridScheduler: Scheduler para monitoreo automático
- GridTelegramBot: Bot de Telegram para comandos básicos
""" 
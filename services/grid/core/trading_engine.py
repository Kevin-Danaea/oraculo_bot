"""
Grid Trading Engine - Orquestador Principal
Motor principal del Grid Trading Bot que coordina todos los módulos especializados.
"""

from typing import Dict, Any
from shared.services.logging_config import get_logger
from shared.services.telegram_service import send_telegram_message

# Importar módulos especializados
from .config_manager import (
    validate_config, 
    get_exchange_connection, 
    config_has_significant_changes
)
from .state_manager import (
    load_bot_state, 
    reset_bot_for_new_config, 
    force_reset_bot
)
from .grid_calculator import calculate_grid_prices
from .order_manager import create_initial_buy_orders
from .monitor import monitor_grid_orders

logger = get_logger(__name__)


def run_grid_trading_bot(config: Dict[str, Any]) -> None:
    """
    Función principal que orquesta todo el proceso del Grid Trading Bot
    
    Args:
        config: Configuración del bot desde el scheduler
    """
    try:
        logger.info("🤖 ========== INICIANDO GRID TRADING BOT ==========")
        
        # Validar configuración
        validated_config = validate_config(config)
        
        # Intentar cargar estado previo
        saved_orders, saved_config = load_bot_state()
        
        # Conectar con exchange (necesario para cancelar órdenes si es requerido)
        exchange = get_exchange_connection()
        
        # Verificar si hay cambios significativos en la configuración
        if saved_orders and saved_config:
            if config_has_significant_changes(saved_config, validated_config):
                logger.info("🔄 Detectados cambios significativos - Reiniciando bot...")
                reset_bot_for_new_config(exchange, saved_orders)
                # Después del reset, inicializar desde cero
                saved_orders, saved_config = [], None
        
        # Si hay estado previo válido y sin cambios significativos, continuar
        if saved_orders and saved_config:
            logger.info(f"📂 Continuando con {len(saved_orders)} órdenes previas")
            active_orders = saved_orders
        else:
            # Inicializar desde cero
            logger.info("🆕 Iniciando configuración nueva")
            
            # Obtener precio actual
            current_price = exchange.fetch_ticker(validated_config['pair'])['last']
            logger.info(f"💹 Precio actual de {validated_config['pair']}: ${current_price}")
            
            # Calcular precios de grilla
            grid_prices = calculate_grid_prices(current_price, validated_config)
            
            # Crear órdenes iniciales
            active_orders = create_initial_buy_orders(exchange, validated_config, grid_prices)
            
            if not active_orders:
                raise Exception("No se pudieron crear órdenes iniciales")
            
            # Enviar notificación de inicio
            startup_message = f"🚀 <b>GRID BOT INICIADO</b>\n\n"
            startup_message += f"📊 <b>Par:</b> {validated_config['pair']}\n"
            startup_message += f"💰 <b>Capital:</b> ${validated_config['total_capital']}\n"
            startup_message += f"🎯 <b>Niveles:</b> {validated_config['grid_levels']}\n"
            startup_message += f"📈 <b>Rango:</b> {validated_config['price_range_percent']}%\n"
            startup_message += f"💹 <b>Precio actual:</b> ${current_price:.2f}\n"
            startup_message += f"🟢 <b>Órdenes creadas:</b> {len(active_orders)}\n"
            startup_message += f"💵 <b>Ganancia objetivo:</b> {validated_config['profit_percentage']}%"
            
            send_telegram_message(startup_message)
        
        # Iniciar monitoreo continuo
        monitor_grid_orders(exchange, active_orders, validated_config)
        
    except Exception as e:
        error_msg = f"❌ Error fatal en Grid Trading Bot: {e}"
        logger.error(error_msg)
        send_telegram_message(f"🚨 <b>ERROR CRÍTICO EN GRID BOT</b>\n\n{str(e)}")
        raise
    finally:
        logger.info("🛑 ========== GRID TRADING BOT DETENIDO ==========")


# Re-exportar funciones para compatibilidad (zero breaking changes)
__all__ = ['run_grid_trading_bot', 'force_reset_bot']
"""
Trend Trading Engine - Ejecutor de Órdenes
Motor simplificado que solo ejecuta las órdenes del cerebro.
"""

from typing import Dict, Any
from datetime import datetime
from shared.services.logging_config import get_logger
from shared.services.telegram_service import send_telegram_message

# Importar módulos especializados
from .config_manager import validate_config, get_exchange_connection
from .state_manager import load_bot_state, save_bot_state, clear_bot_state
from .position_manager import (
    execute_market_buy,
    execute_market_sell,
    update_position_tracking
)

logger = get_logger(__name__)


def run_trend_trading_bot(config: Dict[str, Any]) -> None:
    """
    Función principal que ejecuta las órdenes del cerebro.
    NO toma decisiones propias, solo ejecuta lo que el cerebro ordena.
    
    Args:
        config: Configuración del bot con decisión del cerebro
    """
    try:
        logger.info("📈 ========== TREND BOT - EJECUTANDO ORDEN DEL CEREBRO ==========")
        
        # Validar configuración
        validated_config = validate_config(config)
        pair = validated_config['pair']
        
        # Obtener decisión del cerebro
        cerebro_decision = config.get('cerebro_decision', 'MANTENER_ESPERA')
        logger.info(f"🧠 Orden del cerebro: {cerebro_decision}")
        
        # Cargar estado previo
        saved_state = load_bot_state(pair)
        
        # Conectar con exchange
        exchange = get_exchange_connection()
        
        # Obtener precio actual
        ticker = exchange.fetch_ticker(pair)
        current_price = ticker['last']
        logger.info(f"💹 Precio actual de {pair}: ${current_price:.2f}")
        
        # Ejecutar la orden del cerebro
        if cerebro_decision == 'INICIAR_COMPRA_TENDENCIA':
            _execute_buy_order(exchange, validated_config, current_price, saved_state)
            
        elif cerebro_decision == 'CERRAR_POSICION':
            _execute_sell_order(exchange, validated_config, current_price, saved_state)
            
        elif cerebro_decision == 'MANTENER_POSICION':
            _update_position(exchange, validated_config, current_price, saved_state)
            
        else:  # MANTENER_ESPERA o cualquier otra
            logger.info(f"⏳ Manteniendo espera según orden del cerebro")
            
    except Exception as e:
        error_msg = f"❌ Error en Trend Bot: {e}"
        logger.error(error_msg)
        send_telegram_message(f"🚨 <b>ERROR EN TREND BOT</b>\n\n{str(e)}")
        raise
    finally:
        logger.info("✅ ========== TREND BOT - ORDEN EJECUTADA ==========")


def _execute_buy_order(exchange, config: Dict[str, Any], current_price: float, saved_state: Dict[str, Any]):
    """
    Ejecuta orden de compra del cerebro.
    """
    try:
        pair = config['pair']
        
        # Verificar que no hay posición abierta
        if saved_state and saved_state.get('position_open', False):
            logger.warning("⚠️ Ya hay una posición abierta, ignorando orden de compra")
            return
        
        logger.info("🛒 Ejecutando ORDEN DE COMPRA del cerebro...")
        
        # Ejecutar compra
        order_result = execute_market_buy(
            exchange=exchange,
            pair=pair,
            capital=config['total_capital'],
            current_price=current_price
        )
        
        if order_result['success']:
            # Guardar estado de posición
            position_state = {
                'position_open': True,
                'entry_price': order_result['price'],
                'entry_date': datetime.now().isoformat(),
                'position_size': order_result['amount'],
                'highest_price': order_result['price'],
                'stop_price': order_result['price'] * 0.8,  # Stop loss inicial 20%
                'pair': pair,
                'strategy': 'TREND',
                'capital_invested': config['total_capital'],
                'cerebro_reason': config.get('indicadores', {}).get('razon', 'Orden del cerebro')
            }
            
            # Guardar estado
            save_bot_state(pair, position_state)
            
            # Notificar
            _send_entry_notification(position_state)
            
            logger.info("✅ Compra ejecutada exitosamente")
        else:
            logger.error(f"❌ Error ejecutando compra: {order_result.get('error')}")
            
    except Exception as e:
        logger.error(f"❌ Error en ejecución de compra: {e}")
        raise


def _execute_sell_order(exchange, config: Dict[str, Any], current_price: float, saved_state: Dict[str, Any]):
    """
    Ejecuta orden de venta del cerebro.
    """
    try:
        pair = config['pair']
        
        # Verificar que hay posición abierta
        if not saved_state or not saved_state.get('position_open', False):
            logger.warning("⚠️ No hay posición abierta, ignorando orden de venta")
            return
        
        logger.info("💸 Ejecutando ORDEN DE VENTA del cerebro...")
        
        position_size = saved_state['position_size']
        
        # Ejecutar venta
        order_result = execute_market_sell(
            exchange=exchange,
            pair=pair,
            amount=position_size,
            current_price=current_price
        )
        
        if order_result['success']:
            # Calcular métricas
            entry_price = saved_state['entry_price']
            exit_price = order_result['price']
            pnl = (exit_price - entry_price) * position_size
            pnl_percentage = ((exit_price - entry_price) / entry_price) * 100
            
            # Preparar resumen
            trade_summary = {
                'entry_date': saved_state['entry_date'],
                'exit_date': datetime.now().isoformat(),
                'entry_price': entry_price,
                'exit_price': exit_price,
                'position_size': position_size,
                'pnl': pnl,
                'pnl_percentage': pnl_percentage,
                'highest_price': saved_state.get('highest_price', current_price),
                'exit_reason': config.get('indicadores', {}).get('razon', 'Orden del cerebro')
            }
            
            # Limpiar estado
            clear_bot_state(pair)
            
            # Notificar
            _send_exit_notification(trade_summary)
            
            logger.info(f"✅ Venta ejecutada - P&L: ${pnl:.2f} ({pnl_percentage:+.2f}%)")
        else:
            logger.error(f"❌ Error ejecutando venta: {order_result.get('error')}")
            
    except Exception as e:
        logger.error(f"❌ Error en ejecución de venta: {e}")
        raise


def _update_position(exchange, config: Dict[str, Any], current_price: float, saved_state: Dict[str, Any]):
    """
    Actualiza el tracking de una posición abierta.
    """
    try:
        if not saved_state or not saved_state.get('position_open', False):
            logger.info("ℹ️ No hay posición abierta para actualizar")
            return
        
        pair = config['pair']
        
        # Actualizar tracking
        updated_state = update_position_tracking(saved_state, current_price, config)
        
        # Guardar estado actualizado
        save_bot_state(pair, updated_state)
        
        # Log de estado
        entry_price = updated_state['entry_price']
        unrealized_pnl = updated_state.get('unrealized_pnl_pct', 0)
        
        logger.info(f"📊 Posición actualizada - Precio: ${current_price:.2f} | "
                   f"P&L: {unrealized_pnl:+.2f}% | "
                   f"Stop: ${updated_state.get('stop_price', 0):.2f}")
                   
    except Exception as e:
        logger.error(f"❌ Error actualizando posición: {e}")


def _send_entry_notification(position: Dict[str, Any]):
    """Envía notificación de entrada en posición."""
    try:
        message = f"📈 <b>TREND BOT - ENTRADA EN POSICIÓN</b>\n\n"
        message += f"🧠 <b>Orden del Cerebro ejecutada</b>\n\n"
        message += f"📊 <b>Par:</b> {position['pair']}\n"
        message += f"💰 <b>Capital:</b> ${position['capital_invested']:.2f}\n"
        message += f"💹 <b>Precio:</b> ${position['entry_price']:.2f}\n"
        message += f"🪙 <b>Cantidad:</b> {position['position_size']:.6f}\n"
        message += f"🛡️ <b>Stop Loss:</b> ${position['stop_price']:.2f}\n"
        message += f"📍 <b>Razón:</b> {position.get('cerebro_reason', 'N/A')}\n\n"
        message += f"🕐 <i>{datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
        
        send_telegram_message(message)
        
    except Exception as e:
        logger.error(f"❌ Error enviando notificación: {e}")


def _send_exit_notification(trade: Dict[str, Any]):
    """Envía notificación de salida de posición."""
    try:
        pnl_icon = "💹" if trade['pnl'] >= 0 else "📉"
        
        message = f"📊 <b>TREND BOT - CIERRE DE POSICIÓN</b>\n\n"
        message += f"🧠 <b>Orden del Cerebro ejecutada</b>\n\n"
        message += f"💰 <b>Entrada:</b> ${trade['entry_price']:.2f}\n"
        message += f"💸 <b>Salida:</b> ${trade['exit_price']:.2f}\n"
        message += f"{pnl_icon} <b>P&L:</b> ${trade['pnl']:.2f} ({trade['pnl_percentage']:+.2f}%)\n"
        message += f"📍 <b>Razón:</b> {trade['exit_reason']}\n\n"
        message += f"🕐 <i>{datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
        
        send_telegram_message(message)
        
    except Exception as e:
        logger.error(f"❌ Error enviando notificación: {e}")


__all__ = ['run_trend_trading_bot'] 
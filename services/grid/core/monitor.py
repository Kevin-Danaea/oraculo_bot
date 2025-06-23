"""
Módulo de monitoreo del Grid Trading Bot.
Maneja el monitoreo continuo de órdenes y procesamiento de trades ejecutados.
"""

import ccxt
import time
from typing import Dict, List, Any, Tuple
from shared.services.logging_config import get_logger
from shared.services.telegram_service import send_telegram_message, send_grid_trade_notification, send_grid_hourly_summary
from .config_manager import reconnect_exchange
from .state_manager import save_bot_state
from .order_manager import create_sell_order_after_buy, create_replacement_buy_order

logger = get_logger(__name__)

# ============================================================================
# CONSTANTES DE MONITOREO
# ============================================================================

MONITORING_INTERVAL = 30  # segundos entre chequeos
STATUS_REPORT_CYCLES = 120  # enviar resumen cada 120 ciclos (1 hora)


def check_and_process_filled_orders(exchange: ccxt.Exchange, active_orders: List[Dict[str, Any]], 
                                   config: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], int]:
    """
    Verifica órdenes ejecutadas y procesa las acciones correspondientes
    
    Args:
        exchange: Instancia del exchange
        active_orders: Lista de órdenes activas
        config: Configuración del bot
        
    Returns:
        Tuple de (órdenes_activas_actualizadas, trades_ejecutados)
    """
    updated_orders = []
    trades_executed = 0
    
    for order_info in active_orders:
        try:
            # Verificar estado de la orden
            order_status = exchange.fetch_order(order_info['id'], order_info['pair'])
            
            if order_status['status'] == 'closed':
                trades_executed += 1
                logger.info(f"✅ Trade ejecutado: {order_info['type']} {order_info['quantity']:.6f} a ${order_info['price']}")
                
                # Enviar notificación
                send_grid_trade_notification(order_info, config)
                
                if order_info['type'] == 'buy':
                    # Crear orden de venta correspondiente
                    sell_order = create_sell_order_after_buy(exchange, order_info)
                    if sell_order:
                        updated_orders.append(sell_order)
                        
                elif order_info['type'] == 'sell':
                    # Crear nueva orden de compra
                    new_buy_order = create_replacement_buy_order(exchange, order_info)
                    if new_buy_order:
                        updated_orders.append(new_buy_order)
            else:
                # Orden sigue activa
                updated_orders.append(order_info)
                
        except Exception as e:
            logger.error(f"❌ Error verificando orden {order_info['id']}: {e}")
            # Mantener la orden en la lista para reintentarlo después
            updated_orders.append(order_info)
    
    return updated_orders, trades_executed


def monitor_grid_orders(exchange: ccxt.Exchange, active_orders: List[Dict[str, Any]], 
                      config: Dict[str, Any]) -> None:
    """
    Bucle principal de monitoreo de órdenes
    
    Args:
        exchange: Instancia del exchange
        active_orders: Lista inicial de órdenes activas
        config: Configuración del bot
    """
    logger.info("🔄 Iniciando monitoreo continuo de órdenes...")
    
    cycle_count = 0
    trades_in_period = 0
    last_state_save = time.time()
    
    try:
        while True:
            cycle_count += 1
            
            try:
                # Verificar y procesar órdenes
                active_orders, new_trades = check_and_process_filled_orders(
                    exchange, active_orders, config
                )
                trades_in_period += new_trades
                
                # Guardar estado cada 10 minutos
                if time.time() - last_state_save > 600:  # 10 minutos
                    save_bot_state(active_orders, config)
                    last_state_save = time.time()
                
                # Enviar resumen periódico
                if cycle_count >= STATUS_REPORT_CYCLES:
                    if trades_in_period > 0:
                        send_grid_hourly_summary(active_orders, config, trades_in_period)
                        logger.info(f"📊 Resumen enviado - Trades: {trades_in_period}, Órdenes activas: {len(active_orders)}")
                    
                    cycle_count = 0
                    trades_in_period = 0
                
                logger.debug(f"👀 Monitoreo ciclo {cycle_count} - Órdenes activas: {len(active_orders)}")
                
            except ccxt.NetworkError as e:
                logger.error(f"🌐 Error de red: {e}")
                reconnected_exchange = reconnect_exchange()
                if not reconnected_exchange:
                    logger.error("❌ No se pudo reconectar, deteniendo bot")
                    break
                exchange = reconnected_exchange
                    
            except Exception as e:
                logger.error(f"❌ Error en ciclo de monitoreo: {e}")
                time.sleep(MONITORING_INTERVAL * 2)  # Esperar más tiempo en caso de error
                continue
            
            # Esperar antes del siguiente ciclo
            time.sleep(MONITORING_INTERVAL)
            
    except KeyboardInterrupt:
        logger.info("⏹️ Monitoreo detenido por usuario")
    except Exception as e:
        logger.error(f"❌ Error crítico en monitoreo: {e}")
        send_telegram_message(f"🚨 <b>ERROR CRÍTICO EN GRID BOT</b>\n\n{str(e)}")
    finally:
        # Guardar estado final
        save_bot_state(active_orders, config)
        logger.info("💾 Estado final guardado")


__all__ = [
    'MONITORING_INTERVAL',
    'STATUS_REPORT_CYCLES',
    'check_and_process_filled_orders',
    'monitor_grid_orders'
] 
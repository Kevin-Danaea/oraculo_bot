"""
Monitor V2 del Grid Trading Bot con estrategias avanzadas integradas.
Incluye stop-loss automático, trailing up y monitoreo de órdenes mejorado.
"""

import time
import ccxt
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

from shared.services.logging_config import get_logger
from shared.services.telegram_service import send_telegram_message, send_grid_trade_notification, send_grid_hourly_summary
from .config_manager import reconnect_exchange
from .state_manager import save_bot_state, cancel_all_active_orders
from ..strategies.advanced_strategies import (
    should_trigger_stop_loss,
    should_trigger_trailing_up, 
    execute_stop_loss_strategy,
    execute_trailing_up_strategy
)
from .order_manager import create_sell_order_after_buy, create_replacement_buy_order

logger = get_logger(__name__)

# ============================================================================
# CONSTANTES DE CONFIGURACIÓN
# ============================================================================

MONITORING_INTERVAL = 30  # segundos entre verificaciones
STATUS_REPORT_CYCLES = 120  # Cada X ciclos enviar resumen (60 minutos)  
ADVANCED_STRATEGIES_CHECK_INTERVAL = 10  # Cada X ciclos verificar estrategias avanzadas

# ============================================================================
# FUNCIONES DE UTILIDAD
# ============================================================================

def get_grid_boundaries(active_orders: List[Dict[str, Any]]) -> Tuple[Optional[float], Optional[float]]:
    """
    Obtiene los límites del grid (precio más bajo de compra y más alto de venta).
    
    Args:
        active_orders: Lista de órdenes activas
        
    Returns:
        Tuple de (precio_compra_más_bajo, precio_venta_más_alto)
    """
    buy_prices = [order['price'] for order in active_orders if order['type'] == 'buy']
    sell_prices = [order['price'] for order in active_orders if order['type'] == 'sell']
    
    lowest_buy = min(buy_prices) if buy_prices else None
    highest_sell = max(sell_prices) if sell_prices else None
    
    return lowest_buy, highest_sell


def check_manual_stop_requested() -> bool:
    """
    Verifica si se ha solicitado una parada manual del bot.
    Importa y verifica la variable global grid_bot_running.
    
    Returns:
        True si se debe detener el bot, False si debe continuar
    """
    try:
        # Importar variable global del scheduler
        from ..schedulers.grid_scheduler import grid_bot_running
        return not grid_bot_running
    except ImportError:
        logger.warning("⚠️ No se pudo importar grid_bot_running del scheduler")
        return False


def handle_manual_stop_cleanup(exchange: ccxt.Exchange, active_orders: List[Dict[str, Any]], 
                              config: Dict[str, Any]) -> None:
    """
    Maneja la limpieza al detectar una parada manual del bot.
    Cancela todas las órdenes activas y envía notificación.
    
    Args:
        exchange: Instancia del exchange
        active_orders: Lista de órdenes activas para cancelar
        config: Configuración del bot
    """
    try:
        logger.info("🛑 ========== PARADA MANUAL DETECTADA - INICIANDO LIMPIEZA ==========")
        
        if not active_orders:
            logger.info("ℹ️ No hay órdenes activas para cancelar")
            return
        
        # Cancelar todas las órdenes activas
        cancelled_count = cancel_all_active_orders(exchange, active_orders)
        
        # Limpiar estado guardado
        from .state_manager import clear_bot_state
        clear_bot_state()
        
        # Enviar notificación de parada limpia
        pair = config.get('pair', 'N/A')
        message = f"🛑 <b>GRID BOT DETENIDO MANUALMENTE</b>\n\n"
        message += f"📊 <b>Par:</b> {pair}\n"
        message += f"🚫 <b>Órdenes canceladas:</b> {cancelled_count}/{len(active_orders)}\n"
        message += f"🧹 <b>Estado limpiado:</b> ✅\n"
        message += f"⏸️ <b>Bot en modo standby</b>\n\n"
        message += f"▶️ Usa /start_bot para reanudar trading\n"
        message += f"🕐 <i>{datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
        
        send_telegram_message(message)
        
        logger.info(f"✅ Limpieza completada - {cancelled_count} órdenes canceladas")
        
    except Exception as e:
        logger.error(f"❌ Error durante limpieza de parada manual: {e}")
        # Enviar notificación de error
        send_telegram_message(f"🚨 <b>ERROR EN LIMPIEZA</b>\n\n❌ {str(e)}")


def check_advanced_strategies(exchange: ccxt.Exchange, active_orders: List[Dict[str, Any]], 
                            config: Dict[str, Any]) -> Tuple[str, Any]:
    """
    Verifica si se deben activar las estrategias avanzadas.
    
    Args:
        exchange: Instancia del exchange
        active_orders: Lista de órdenes activas
        config: Configuración del bot
        
    Returns:
        Tuple de (acción, resultado) donde acción puede ser: 'none', 'stop_loss', 'trailing_up'
    """
    try:
        # Obtener precio actual
        pair = config['pair']
        current_price = exchange.fetch_ticker(pair)['last']
        
        # Calcular límites del grid
        lowest_buy_price, highest_sell_price = get_grid_boundaries(active_orders)
        
        # Verificar stop-loss
        if should_trigger_stop_loss(
            current_price=current_price,
            lowest_buy_price=lowest_buy_price,
            stop_loss_percent=config.get('stop_loss_percent', 5.0),
            enable_stop_loss=config.get('enable_stop_loss', True)
        ):
            logger.warning("🚨 Activando estrategia STOP-LOSS")
            result = execute_stop_loss_strategy(exchange, active_orders, config)
            return 'stop_loss', result
        
        # Verificar trailing up
        if should_trigger_trailing_up(
            current_price=current_price,
            highest_sell_price=highest_sell_price,
            enable_trailing_up=config.get('enable_trailing_up', True)
        ):
            logger.info("📈 Activando estrategia TRAILING UP")
            new_orders, success = execute_trailing_up_strategy(exchange, active_orders, config)
            return 'trailing_up', {'new_orders': new_orders, 'success': success}
        
        return 'none', None
        
    except Exception as e:
        logger.error(f"❌ Error verificando estrategias avanzadas: {e}")
        return 'error', str(e)


def check_and_process_filled_orders_v2(exchange: ccxt.Exchange, active_orders: List[Dict[str, Any]], 
                                       config: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], int]:
    """
    Versión V2 de verificación de órdenes ejecutadas con logging mejorado.
    
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
                    sell_order = create_sell_order_after_buy(exchange, order_info, config)
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


def monitor_grid_orders_v2(exchange: ccxt.Exchange, active_orders: List[Dict[str, Any]], 
                          config: Dict[str, Any]) -> None:
    """
    Bucle principal de monitoreo V2 con estrategias avanzadas integradas.
    FIXED: Ahora verifica parada manual y cancela órdenes correctamente.
    
    Args:
        exchange: Instancia del exchange
        active_orders: Lista inicial de órdenes activas
        config: Configuración del bot
    """
    logger.info("🚀 Iniciando monitoreo V2 con estrategias avanzadas...")
    logger.info(f"🛡️ Stop-Loss: {'✅ Activo' if config.get('enable_stop_loss', True) else '❌ Inactivo'} ({config.get('stop_loss_percent', 5.0)}%)")
    logger.info(f"📈 Trailing Up: {'✅ Activo' if config.get('enable_trailing_up', True) else '❌ Inactivo'}")
    
    cycle_count = 0
    trades_in_period = 0
    last_state_save = time.time()
    bot_should_stop = False
    
    try:
        while not bot_should_stop:
            cycle_count += 1
            
            try:
                # 0. VERIFICAR PARADA MANUAL (NUEVO FIX) ⭐
                if check_manual_stop_requested():
                    logger.info("🛑 Parada manual detectada - Iniciando limpieza...")
                    handle_manual_stop_cleanup(exchange, active_orders, config)
                    bot_should_stop = True
                    break
                
                # 1. Verificar estrategias avanzadas cada N ciclos
                if cycle_count % ADVANCED_STRATEGIES_CHECK_INTERVAL == 0:
                    strategy_action, strategy_result = check_advanced_strategies(exchange, active_orders, config)
                    
                    if strategy_action == 'stop_loss':
                        logger.warning("🛑 Stop-Loss ejecutado - Deteniendo bot")
                        bot_should_stop = True
                        break
                    elif strategy_action == 'trailing_up' and strategy_result['success']:
                        logger.info("📈 Trailing Up ejecutado - Actualizando órdenes")
                        active_orders = strategy_result['new_orders']
                        # Guardar estado después de trailing up
                        save_bot_state(active_orders, config)
                
                # 2. Verificar y procesar órdenes ejecutadas
                active_orders, new_trades = check_and_process_filled_orders_v2(
                    exchange, active_orders, config
                )
                trades_in_period += new_trades
                
                # 3. Guardar estado cada 10 minutos
                if time.time() - last_state_save > 600:  # 10 minutos
                    save_bot_state(active_orders, config)
                    last_state_save = time.time()
                
                # 4. Enviar resumen periódico
                if cycle_count >= STATUS_REPORT_CYCLES:
                    if trades_in_period > 0:
                        send_grid_hourly_summary(active_orders, config, trades_in_period)
                        logger.info(f"📊 Resumen enviado - Trades: {trades_in_period}, Órdenes activas: {len(active_orders)}")
                    
                    cycle_count = 0
                    trades_in_period = 0
                
                # 5. Log de estado cada ciclo
                if cycle_count % 10 == 0:  # Cada 10 ciclos (5 minutos)
                    pair = config['pair']
                    current_price = exchange.fetch_ticker(pair)['last']
                    lowest_buy, highest_sell = get_grid_boundaries(active_orders)
                    
                    logger.info(f"📊 Estado V2 - Precio: ${current_price:.2f}, Órdenes: {len(active_orders)}, "
                              f"Límites: ${lowest_buy:.2f if lowest_buy else 0} - ${highest_sell:.2f if highest_sell else 0}")
                
                logger.debug(f"👀 Monitoreo V2 ciclo {cycle_count} - Órdenes activas: {len(active_orders)}")
                
            except ccxt.NetworkError as e:
                logger.error(f"🌐 Error de red: {e}")
                reconnected_exchange = reconnect_exchange()
                if not reconnected_exchange:
                    logger.error("❌ No se pudo reconectar, deteniendo bot")
                    break
                exchange = reconnected_exchange
                    
            except Exception as e:
                logger.error(f"❌ Error en ciclo de monitoreo V2: {e}")
                time.sleep(MONITORING_INTERVAL * 2)  # Esperar más tiempo en caso de error
                continue
            
            # Esperar antes del siguiente ciclo
            time.sleep(MONITORING_INTERVAL)
            
    except KeyboardInterrupt:
        logger.info("⏹️ Monitoreo V2 detenido por usuario")
    except Exception as e:
        logger.error(f"❌ Error crítico en monitoreo V2: {e}")
        send_telegram_message(f"🚨 <b>ERROR CRÍTICO EN GRID BOT V2</b>\n\n{str(e)}")
    finally:
        # Guardar estado final
        save_bot_state(active_orders, config)
        logger.info("💾 Estado final V2 guardado - Monitor detenido")


# Función de compatibilidad para usar monitor V2 como predeterminado
def monitor_grid_orders(exchange: ccxt.Exchange, active_orders: List[Dict[str, Any]], 
                      config: Dict[str, Any]) -> None:
    """
    Función wrapper para mantener compatibilidad.
    Redirige automáticamente al monitor V2.
    """
    logger.info("🔄 Redirigiendo a Monitor V2 con estrategias avanzadas")
    monitor_grid_orders_v2(exchange, active_orders, config)


__all__ = [
    'MONITORING_INTERVAL',
    'STATUS_REPORT_CYCLES', 
    'ADVANCED_STRATEGIES_CHECK_INTERVAL',
    'get_grid_boundaries',
    'check_manual_stop_requested',
    'handle_manual_stop_cleanup',
    'check_advanced_strategies',
    'check_and_process_filled_orders_v2',
    'monitor_grid_orders_v2',
    'monitor_grid_orders'  # Compatibilidad
] 
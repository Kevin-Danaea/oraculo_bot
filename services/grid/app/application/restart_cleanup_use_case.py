"""
Caso de uso para limpieza completa al reiniciar el servicio Grid Trading.
Cancela todas las órdenes, vende todos los activos y resetea a estado limpio.
"""
import logging
from typing import Dict, Any, List
from decimal import Decimal
from datetime import datetime

from app.domain.interfaces import GridRepository, ExchangeService, NotificationService
from app.domain.entities import GridConfig

logger = logging.getLogger(__name__)


class RestartCleanupUseCase:
    """
    Caso de uso para limpieza completa al reiniciar el servicio.
    
    Realiza las siguientes acciones:
    1. Cancela todas las órdenes activas en el exchange
    2. Vende todos los activos (excepto USDT) a mercado
    3. Limpia la base de datos de órdenes
    4. Resetea el estado de los bots a pausado
    5. Notifica el proceso de limpieza
    """
    
    def __init__(
        self,
        grid_repository: GridRepository,
        exchange_service: ExchangeService,
        notification_service: NotificationService
    ):
        self.grid_repository = grid_repository
        self.exchange_service = exchange_service
        self.notification_service = notification_service
    
    def execute(self) -> Dict[str, Any]:
        """
        Ejecuta la limpieza completa del sistema.
        
        Returns:
            Dict con el resultado de la limpieza
        """
        logger.info("🧹 ========== INICIANDO LIMPIEZA COMPLETA DE REINICIO ==========")
        
        try:
            cleanup_results = {
                'success': True,
                'orders_cancelled': 0,
                'assets_sold': {},
                'total_usdt_recovered': Decimal('0'),
                'bots_reset': 0,
                'errors': []
            }
            
            # PASO 1: Cancelar todas las órdenes activas
            logger.info("📋 PASO 1: Cancelando todas las órdenes activas...")
            cancelled_orders = self._cancel_all_active_orders()
            cleanup_results['orders_cancelled'] = cancelled_orders
            logger.info(f"✅ Canceladas {cancelled_orders} órdenes activas")
            
            # PASO 2: Vender todos los activos a mercado
            logger.info("💰 PASO 2: Vendiendo todos los activos a mercado...")
            sold_assets = self._sell_all_assets()
            cleanup_results['assets_sold'] = sold_assets
            
            total_recovered = sum(sold_assets.values())
            cleanup_results['total_usdt_recovered'] = total_recovered
            logger.info(f"✅ Vendidos activos por ${total_recovered:.2f} USDT")
            
            # PASO 3: Limpiar base de datos de órdenes
            logger.info("🗄️ PASO 3: Limpiando base de datos de órdenes...")
            cleaned_orders = self._clean_database_orders()
            logger.info(f"✅ Limpiadas {cleaned_orders} órdenes de la base de datos")
            
            # PASO 4: Resetear estado de bots a pausado
            logger.info("🔄 PASO 4: Reseteando estado de bots...")
            reset_bots = self._reset_bot_states()
            cleanup_results['bots_reset'] = reset_bots
            logger.info(f"✅ Reseteados {reset_bots} bots a estado pausado")
            
            # PASO 5: Verificar balance final
            logger.info("💰 PASO 5: Verificando balance final...")
            final_balance = self._verify_final_balance()
            cleanup_results['final_balance'] = final_balance
            
            # PASO 6: Enviar notificación de limpieza
            logger.info("📱 PASO 6: Enviando notificación de limpieza...")
            self._send_cleanup_notification(cleanup_results)
            
            logger.info("✅ ========== LIMPIEZA COMPLETA FINALIZADA ==========")
            
            return cleanup_results
            
        except Exception as e:
            error_msg = f"❌ Error en limpieza completa: {e}"
            logger.error(error_msg)
            cleanup_results['success'] = False
            cleanup_results['errors'].append(error_msg)
            
            # Enviar notificación de error
            self.notification_service.send_error_notification(
                "Restart Cleanup", 
                f"Error en limpieza: {e}"
            )
            
            return cleanup_results
    
    def _cancel_all_active_orders(self) -> int:
        """
        Cancela todas las órdenes activas en el exchange.
        
        Returns:
            Número de órdenes canceladas
        """
        try:
            # Cancelar todas las órdenes en el exchange de una vez
            logger.info("📋 Cancelando todas las órdenes activas...")
            total_cancelled = self.exchange_service.cancel_all_orders()
            logger.info(f"✅ Canceladas {total_cancelled} órdenes en total")
            
            return total_cancelled
            
        except Exception as e:
            logger.error(f"❌ Error cancelando órdenes: {e}")
            return 0
    
    def _sell_all_assets(self) -> Dict[str, Decimal]:
        """
        Vende todos los activos (excepto USDT) a mercado.
        
        Returns:
            Dict con activos vendidos y sus valores en USDT
        """
        try:
            logger.info("💰 Vendiendo todos los activos...")
            
            # Usar el método sell_all_positions que maneja todos los activos
            sold_positions = self.exchange_service.sell_all_positions()
            
            # Calcular valores en USDT de los activos vendidos
            sold_assets = {}
            for currency, amount in sold_positions.items():
                try:
                    pair = f"{currency}/USDT"
                    current_price = self.exchange_service.get_current_price(pair)
                    expected_value = amount * current_price
                    sold_assets[currency] = expected_value
                    logger.info(f"✅ Vendido {amount} {currency} por ~${expected_value:.2f} USDT")
                except Exception as e:
                    logger.warning(f"⚠️ No se pudo calcular valor de {currency}: {e}")
                    sold_assets[currency] = Decimal('0')
            
            logger.info(f"💰 Total de activos vendidos: {len(sold_positions)} monedas")
            return sold_assets
            
        except Exception as e:
            logger.error(f"❌ Error vendiendo activos: {e}")
            return {}
    
    def _clean_database_orders(self) -> int:
        """
        Limpia todas las órdenes de la base de datos.
        
        Returns:
            Número de órdenes limpiadas
        """
        try:
            # Obtener configuraciones activas
            active_configs = self.grid_repository.get_active_configs()
            total_cleaned = 0
            
            for config in active_configs:
                pair = config.pair
                # Cancelar órdenes en BD
                cancelled = self.grid_repository.cancel_all_orders_for_pair(pair)
                total_cleaned += cancelled
                logger.info(f"🗄️ Limpiadas {cancelled} órdenes de BD para {pair}")
            
            return total_cleaned
            
        except Exception as e:
            logger.error(f"❌ Error limpiando BD: {e}")
            return 0
    
    def _reset_bot_states(self) -> int:
        """
        Resetea el estado de todos los bots a pausado.
        
        Returns:
            Número de bots reseteados
        """
        try:
            active_configs = self.grid_repository.get_active_configs()
            reset_count = 0
            
            for config in active_configs:
                if config.id is not None:
                    # Actualizar estado a pausado
                    self.grid_repository.update_config_status(
                        config.id,
                        is_running=False,
                        last_decision='PAUSAR_GRID'
                    )
                    reset_count += 1
                    logger.info(f"🔄 Bot {config.pair} reseteado a pausado")
            
            return reset_count
            
        except Exception as e:
            logger.error(f"❌ Error reseteando bots: {e}")
            return 0
    
    def _verify_final_balance(self) -> Dict[str, Any]:
        """
        Verifica el balance final después de la limpieza.
        
        Returns:
            Dict con información del balance final
        """
        try:
            # Obtener balance final
            usdt_balance = self.exchange_service.get_balance('USDT')
            
            # Verificar que no hay órdenes activas
            active_configs = self.grid_repository.get_active_configs()
            total_orders = 0
            
            for config in active_configs:
                orders = self.grid_repository.get_active_orders(config.pair)
                total_orders += len(orders)
            
            return {
                'usdt_balance': float(usdt_balance),
                'active_orders': total_orders,
                'cleanup_successful': total_orders == 0
            }
            
        except Exception as e:
            logger.error(f"❌ Error verificando balance final: {e}")
            return {
                'usdt_balance': 0.0,
                'active_orders': -1,
                'cleanup_successful': False
            }
    
    def _send_cleanup_notification(self, results: Dict[str, Any]) -> None:
        """
        Envía notificación con el resultado de la limpieza.
        
        Args:
            results: Resultados de la limpieza
        """
        try:
            if not results['success']:
                return
            
            # Crear mensaje de notificación
            message = (
                "🧹 <b>LIMPIEZA COMPLETA DE REINICIO</b>\n\n"
                f"📋 <b>Órdenes canceladas:</b> {results['orders_cancelled']}\n"
                f"💰 <b>Activos vendidos:</b> {len(results['assets_sold'])} monedas\n"
                f"💵 <b>USDT recuperado:</b> ${results['total_usdt_recovered']:.2f}\n"
                f"🔄 <b>Bots reseteados:</b> {results['bots_reset']}\n"
                f"💎 <b>Balance final USDT:</b> ${results['final_balance']['usdt_balance']:.2f}\n"
                f"📊 <b>Órdenes activas:</b> {results['final_balance']['active_orders']}\n\n"
                f"✅ <b>Estado:</b> {'Limpio' if results['final_balance']['cleanup_successful'] else 'Con problemas'}\n"
                f"🕐 <b>Completado:</b> {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}"
            )
            
            # Enviar notificación usando método correcto
            self.notification_service.send_bot_status_notification("SYSTEM", "CLEANUP_COMPLETE", message)
            logger.info("📱 Notificación de limpieza enviada")
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación: {e}") 
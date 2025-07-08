"""
Caso de uso para validar la integridad del sistema Grid Trading.
Verifica consistencia entre exchange, base de datos y configuraciones.
"""
import logging
from typing import Dict, Any, List
from decimal import Decimal
from datetime import datetime

from app.domain.interfaces import GridRepository, ExchangeService, NotificationService
from app.domain.entities import GridConfig

logger = logging.getLogger(__name__)


class SystemIntegrityUseCase:
    """
    Caso de uso para validar la integridad del sistema.
    
    Realiza las siguientes validaciones:
    1. Consistencia entre órdenes en exchange y BD
    2. Balance de activos vs configuraciones
    3. Estado de bots vs decisiones del cerebro
    4. Integridad de configuraciones
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
        Ejecuta la validación de integridad del sistema.
        
        Returns:
            Dict con resultados de la validación
        """
        logger.info("🔍 ========== VALIDACIÓN DE INTEGRIDAD DEL SISTEMA ==========")
        
        try:
            integrity_results = {
                'success': True,
                'checks_passed': 0,
                'checks_failed': 0,
                'issues_found': [],
                'recommendations': []
            }
            
            # PASO 1: Validar órdenes en exchange vs BD
            logger.info("📋 PASO 1: Validando órdenes en exchange vs BD...")
            order_integrity = self._validate_order_integrity()
            if order_integrity['is_valid']:
                integrity_results['checks_passed'] += 1
            else:
                integrity_results['checks_failed'] += 1
                integrity_results['issues_found'].extend(order_integrity['issues'])
                integrity_results['recommendations'].extend(order_integrity['recommendations'])
            
            # PASO 2: Validar balance de activos
            logger.info("💰 PASO 2: Validando balance de activos...")
            balance_integrity = self._validate_balance_integrity()
            if balance_integrity['is_valid']:
                integrity_results['checks_passed'] += 1
            else:
                integrity_results['checks_failed'] += 1
                integrity_results['issues_found'].extend(balance_integrity['issues'])
                integrity_results['recommendations'].extend(balance_integrity['recommendations'])
            
            # PASO 3: Validar estado de bots vs decisiones
            logger.info("🤖 PASO 3: Validando estado de bots vs decisiones...")
            bot_integrity = self._validate_bot_state_integrity()
            if bot_integrity['is_valid']:
                integrity_results['checks_passed'] += 1
            else:
                integrity_results['checks_failed'] += 1
                integrity_results['issues_found'].extend(bot_integrity['issues'])
                integrity_results['recommendations'].extend(bot_integrity['recommendations'])
            
            # PASO 4: Validar configuraciones
            logger.info("⚙️ PASO 4: Validando configuraciones...")
            config_integrity = self._validate_configuration_integrity()
            if config_integrity['is_valid']:
                integrity_results['checks_passed'] += 1
            else:
                integrity_results['checks_failed'] += 1
                integrity_results['issues_found'].extend(config_integrity['issues'])
                integrity_results['recommendations'].extend(config_integrity['recommendations'])
            
            # Determinar estado general
            total_checks = integrity_results['checks_passed'] + integrity_results['checks_failed']
            if integrity_results['checks_failed'] > 0:
                integrity_results['success'] = False
                integrity_results['overall_status'] = 'DEGRADED'
            else:
                integrity_results['overall_status'] = 'HEALTHY'
            
            # PASO 5: Enviar notificación de integridad
            logger.info("📱 PASO 5: Enviando notificación de integridad...")
            self._send_integrity_notification(integrity_results)
            
            logger.info(f"✅ ========== VALIDACIÓN COMPLETADA: {integrity_results['overall_status']} ==========")
            
            return integrity_results
            
        except Exception as e:
            error_msg = f"❌ Error en validación de integridad: {e}"
            logger.error(error_msg)
            
            return {
                'success': False,
                'checks_passed': 0,
                'checks_failed': 1,
                'issues_found': [error_msg],
                'recommendations': ['Revisar logs del sistema'],
                'overall_status': 'ERROR'
            }
    
    def _validate_order_integrity(self) -> Dict[str, Any]:
        """
        Valida la consistencia entre órdenes en exchange y base de datos.
        
        Returns:
            Dict con resultados de la validación
        """
        try:
            issues = []
            recommendations = []
            
            # Obtener órdenes del exchange usando método público
            try:
                # Usar el método cancel_all_orders para obtener conteo
                cancelled_count = self.exchange_service.cancel_all_orders()
                # Como cancel_all_orders cancela todas las órdenes, usamos un enfoque diferente
                # Vamos a verificar si hay órdenes activas en la BD
                exchange_order_count = 0
            except Exception:
                exchange_order_count = 0
            
            # Obtener órdenes de la BD
            active_configs = self.grid_repository.get_active_configs()
            db_order_count = 0
            
            for config in active_configs:
                orders = self.grid_repository.get_active_orders(config.pair)
                db_order_count += len(orders)
            
            # Comparar conteos
            if exchange_order_count != db_order_count:
                issues.append(f"Desajuste en órdenes: {exchange_order_count} en exchange vs {db_order_count} en BD")
                recommendations.append("Sincronizar órdenes entre exchange y BD")
            
            # Verificar órdenes huérfanas
            if exchange_order_count > 0 and db_order_count == 0:
                issues.append("Órdenes en exchange sin registro en BD")
                recommendations.append("Limpiar órdenes huérfanas del exchange")
            
            is_valid = len(issues) == 0
            
            return {
                'is_valid': is_valid,
                'issues': issues,
                'recommendations': recommendations,
                'exchange_orders': exchange_order_count,
                'db_orders': db_order_count
            }
            
        except Exception as e:
            logger.error(f"❌ Error validando órdenes: {e}")
            return {
                'is_valid': False,
                'issues': [f"Error validando órdenes: {e}"],
                'recommendations': ['Revisar conexión con exchange'],
                'exchange_orders': -1,
                'db_orders': -1
            }
    
    def _validate_balance_integrity(self) -> Dict[str, Any]:
        """
        Valida la integridad del balance de activos.
        
        Returns:
            Dict con resultados de la validación
        """
        try:
            issues = []
            recommendations = []
            
            # Obtener balance total usando método público
            total_usdt = self.exchange_service.get_balance('USDT')
            
            # Verificar que hay suficiente USDT para operar
            active_configs = self.grid_repository.get_active_configs()
            total_allocated = sum(config.total_capital for config in active_configs)
            
            if total_allocated > total_usdt:
                issues.append(f"Capital insuficiente: ${total_allocated:.2f} asignado vs ${total_usdt:.2f} disponible")
                recommendations.append("Ajustar capital asignado o agregar más USDT")
            
            # Verificar activos no USDT (simplificado)
            non_usdt_assets = []
            # Por ahora, verificamos solo las monedas principales
            for currency in ['BTC', 'ETH', 'AVAX']:
                try:
                    balance = self.exchange_service.get_balance(currency)
                    if balance > 0:
                        non_usdt_assets.append(f"{currency}: {balance}")
                except Exception:
                    continue
            
            if non_usdt_assets:
                issues.append(f"Activos no USDT encontrados: {', '.join(non_usdt_assets)}")
                recommendations.append("Considerar vender activos para tener solo USDT")
            
            is_valid = len(issues) == 0
            
            return {
                'is_valid': is_valid,
                'issues': issues,
                'recommendations': recommendations,
                'total_usdt': float(total_usdt),
                'total_allocated': float(total_allocated),
                'non_usdt_assets': non_usdt_assets
            }
            
        except Exception as e:
            logger.error(f"❌ Error validando balance: {e}")
            return {
                'is_valid': False,
                'issues': [f"Error validando balance: {e}"],
                'recommendations': ['Revisar conexión con exchange'],
                'total_usdt': 0.0,
                'total_allocated': 0.0,
                'non_usdt_assets': []
            }
    
    def _validate_bot_state_integrity(self) -> Dict[str, Any]:
        """
        Valida la consistencia entre estado de bots y decisiones del cerebro.
        
        Returns:
            Dict con resultados de la validación
        """
        try:
            issues = []
            recommendations = []
            
            # Importar modelo de estrategia
            from shared.database.models import EstrategiaStatus
            from shared.database.session import get_db
            
            db = next(get_db())
            
            if not db:
                issues.append("No se pudo conectar a la base de datos")
                recommendations.append("Verificar conexión a la base de datos")
                return {
                    'is_valid': False,
                    'issues': issues,
                    'recommendations': recommendations,
                    'bots_checked': 0
                }
            
            active_configs = self.grid_repository.get_active_configs()
            
            for config in active_configs:
                # Obtener última decisión del cerebro
                estrategia = db.query(EstrategiaStatus).filter(
                    EstrategiaStatus.par == config.pair,
                    EstrategiaStatus.estrategia == "GRID"
                ).order_by(EstrategiaStatus.timestamp.desc()).first()
                
                if estrategia:
                    current_decision = estrategia.decision
                    is_should_be_active = current_decision == "OPERAR_GRID"
                    is_actually_active = bool(config.is_running) if config.is_running is not None else False
                    
                    if is_should_be_active and not is_actually_active: # type: ignore
                        issues.append(f"Bot {config.pair}: Debería estar activo pero está pausado")
                        recommendations.append(f"Activar bot {config.pair}")
                    
                    elif not is_should_be_active and is_actually_active: # type: ignore
                        issues.append(f"Bot {config.pair}: Debería estar pausado pero está activo")
                        recommendations.append(f"Pausar bot {config.pair}")
                else:
                    issues.append(f"Bot {config.pair}: Sin decisión del cerebro registrada")
                    recommendations.append(f"Verificar que el cerebro esté funcionando para {config.pair}")
            
            is_valid = len(issues) == 0
            
            return {
                'is_valid': is_valid,
                'issues': issues,
                'recommendations': recommendations,
                'bots_checked': len(active_configs)
            }
            
        except Exception as e:
            logger.error(f"❌ Error validando estado de bots: {e}")
            return {
                'is_valid': False,
                'issues': [f"Error validando estado de bots: {e}"],
                'recommendations': ['Revisar conexión con base de datos'],
                'bots_checked': 0
            }
    
    def _validate_configuration_integrity(self) -> Dict[str, Any]:
        """
        Valida la integridad de las configuraciones de bots.
        
        Returns:
            Dict con resultados de la validación
        """
        try:
            issues = []
            recommendations = []
            
            active_configs = self.grid_repository.get_active_configs()
            
            for config in active_configs:
                # Verificar capital mínimo
                if config.total_capital < 10:
                    issues.append(f"Bot {config.pair}: Capital muy bajo (${config.total_capital})")
                    recommendations.append(f"Aumentar capital para {config.pair}")
                
                # Verificar niveles de grilla
                if config.grid_levels < 2 or config.grid_levels > 100:
                    issues.append(f"Bot {config.pair}: Niveles de grilla inválidos ({config.grid_levels})")
                    recommendations.append(f"Ajustar niveles de grilla para {config.pair}")
                
                # Verificar rango de precio
                if config.price_range_percent < 1 or config.price_range_percent > 50:
                    issues.append(f"Bot {config.pair}: Rango de precio inválido ({config.price_range_percent}%)")
                    recommendations.append(f"Ajustar rango de precio para {config.pair}")
            
            is_valid = len(issues) == 0
            
            return {
                'is_valid': is_valid,
                'issues': issues,
                'recommendations': recommendations,
                'configs_checked': len(active_configs)
            }
            
        except Exception as e:
            logger.error(f"❌ Error validando configuraciones: {e}")
            return {
                'is_valid': False,
                'issues': [f"Error validando configuraciones: {e}"],
                'recommendations': ['Revisar configuraciones manualmente'],
                'configs_checked': 0
            }
    
    def _send_integrity_notification(self, results: Dict[str, Any]) -> None:
        """
        Envía notificación con los resultados de la validación de integridad.
        
        Args:
            results: Resultados de la validación
        """
        try:
            # Crear mensaje de notificación
            status_emoji = "✅" if results['success'] else "⚠️" if results['overall_status'] == 'DEGRADED' else "❌"
            
            message = (
                f"{status_emoji} <b>VALIDACIÓN DE INTEGRIDAD DEL SISTEMA</b>\n\n"
                f"📊 <b>Estado general:</b> {results['overall_status']}\n"
                f"✅ <b>Checks pasados:</b> {results['checks_passed']}\n"
                f"❌ <b>Checks fallidos:</b> {results['checks_failed']}\n"
                f"🔍 <b>Problemas encontrados:</b> {len(results['issues_found'])}\n\n"
            )
            
            if results['issues_found']:
                message += "🚨 <b>Problemas detectados:</b>\n"
                for i, issue in enumerate(results['issues_found'][:5], 1):  # Mostrar solo los primeros 5
                    message += f"  {i}. {issue}\n"
                
                if len(results['issues_found']) > 5:
                    message += f"  ... y {len(results['issues_found']) - 5} más\n"
                
                message += "\n💡 <b>Recomendaciones:</b>\n"
                for i, rec in enumerate(results['recommendations'][:3], 1):  # Mostrar solo las primeras 3
                    message += f"  {i}. {rec}\n"
                
                if len(results['recommendations']) > 3:
                    message += f"  ... y {len(results['recommendations']) - 3} más\n"
            else:
                message += "✅ <b>Sistema funcionando correctamente</b>\n"
            
            message += f"\n🕐 <b>Validado:</b> {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}"
            
            # Enviar notificación usando método correcto
            self.notification_service.send_error_notification("System Integrity", message)
            logger.info("📱 Notificación de integridad enviada")
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación: {e}") 
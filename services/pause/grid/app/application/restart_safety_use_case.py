"""
Caso de uso para manejar la seguridad al reiniciar el bot.
Cancela órdenes existentes y verifica capital antes de crear nuevas órdenes.
"""
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from app.domain.interfaces import GridRepository, ExchangeService, NotificationService
from app.domain.entities import GridConfig, GridOrder
from shared.services.logging_config import get_logger

logger = get_logger(__name__)

@dataclass
class CapitalVerification:
    """Resultado de la verificación de capital."""
    pair: str
    allocated_capital: float
    actual_balance_usdt: float
    actual_balance_crypto: float
    crypto_value_usdt: float
    total_value: float
    is_safe: bool
    missing_capital: float
    excess_capital: float

@dataclass
class RestartSafetyReport:
    """Reporte de seguridad al reiniciar."""
    total_orders_cancelled: int
    capital_verifications: List[CapitalVerification]
    total_missing_capital: float
    total_excess_capital: float
    is_safe_to_continue: bool
    recommendations: List[str]

class RestartSafetyUseCase:
    """
    Maneja la seguridad al reiniciar el bot, evitando sobrecompra.
    """
    
    def __init__(
        self, 
        repository: GridRepository, 
        exchange_service: ExchangeService,
        notification_service: NotificationService
    ):
        self.repository = repository
        self.exchange_service = exchange_service
        self.notification_service = notification_service
        logger.info("✅ RestartSafetyUseCase inicializado.")

    def perform_restart_safety_check(self) -> RestartSafetyReport:
        """
        Realiza verificación de seguridad al reiniciar.
        
        Returns:
            RestartSafetyReport: Reporte de seguridad
        """
        try:
            logger.info("🔒 Iniciando verificación de seguridad al reiniciar...")
            
            # Paso 1: Cancelar todas las órdenes existentes
            cancelled_orders = self._cancel_all_existing_orders()
            
            # Paso 2: Verificar capital para cada bot activo
            capital_verifications = self._verify_capital_for_all_bots()
            
            # Paso 3: Analizar resultados
            total_missing = sum(v.missing_capital for v in capital_verifications)
            total_excess = sum(v.excess_capital for v in capital_verifications)
            is_safe = all(v.is_safe for v in capital_verifications)
            
            # Paso 4: Generar recomendaciones
            recommendations = self._generate_recommendations(capital_verifications)
            
            report = RestartSafetyReport(
                total_orders_cancelled=cancelled_orders,
                capital_verifications=capital_verifications,
                total_missing_capital=total_missing,
                total_excess_capital=total_excess,
                is_safe_to_continue=is_safe,
                recommendations=recommendations
            )
            
            logger.info(f"✅ Verificación completada: {cancelled_orders} órdenes canceladas")
            logger.info(f"   Capital faltante: ${total_missing:,.2f} | Exceso: ${total_excess:,.2f}")
            logger.info(f"   Seguro para continuar: {is_safe}")
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Error en verificación de seguridad: {e}")
            raise

    def _cancel_all_existing_orders(self) -> int:
        """
        Cancela todas las órdenes existentes en todos los pares.
        
        Returns:
            int: Número de órdenes canceladas
        """
        try:
            logger.info("🚫 Cancelando todas las órdenes existentes...")
            
            # Obtener configuraciones activas
            active_configs = self.repository.get_active_configs()
            
            total_cancelled = 0
            for config in active_configs:
                try:
                    # Cancelar órdenes en el exchange (sin parámetros)
                    cancelled = self.exchange_service.cancel_all_orders()
                    
                    # Marcar como canceladas en la base de datos
                    db_cancelled = self.repository.cancel_all_orders_for_pair(config.pair)
                    
                    logger.info(f"   {config.pair}: {cancelled} órdenes canceladas en exchange, {db_cancelled} en BD")
                    total_cancelled += cancelled
                    
                except Exception as e:
                    logger.error(f"❌ Error cancelando órdenes de {config.pair}: {e}")
            
            logger.info(f"✅ Total de órdenes canceladas: {total_cancelled}")
            return total_cancelled
            
        except Exception as e:
            logger.error(f"❌ Error cancelando órdenes: {e}")
            return 0

    def _verify_capital_for_all_bots(self) -> List[CapitalVerification]:
        """
        Verifica el capital para todos los bots activos.
        
        Returns:
            List[CapitalVerification]: Lista de verificaciones de capital
        """
        try:
            logger.info("💰 Verificando capital para todos los bots...")
            
            active_configs = self.repository.get_active_configs()
            # Obtener solo USDT por ahora (implementación simplificada)
            usdt_balance = self.exchange_service.get_balance('USDT')
            exchange_balance = {'USDT': float(usdt_balance)}
            
            verifications = []
            for config in active_configs:
                verification = self._verify_capital_for_bot(config, exchange_balance)
                verifications.append(verification)
            
            return verifications
            
        except Exception as e:
            logger.error(f"❌ Error verificando capital: {e}")
            return []

    def _verify_capital_for_bot(
        self, 
        config: GridConfig, 
        exchange_balance: Dict[str, float]
    ) -> CapitalVerification:
        """
        Verifica el capital para un bot específico.
        
        Args:
            config: Configuración del bot
            exchange_balance: Balance del exchange
            
        Returns:
            CapitalVerification: Verificación de capital
        """
        try:
            # Extraer símbolo de la moneda (ej: BTC/USDT -> BTC)
            base_currency = config.pair.split('/')[0]
            
            # Capital asignado según configuración
            allocated_capital = config.total_capital
            
            # Balance actual en USDT
            actual_balance_usdt = exchange_balance.get('USDT', 0.0)
            
            # Balance actual en la moneda base
            actual_balance_crypto = exchange_balance.get(base_currency, 0.0)
            
            # Valor en USDT de la moneda base
            crypto_value_usdt = 0.0
            if actual_balance_crypto > 0:
                try:
                    current_price = self._get_current_price(config.pair)
                    crypto_value_usdt = actual_balance_crypto * current_price
                except Exception as e:
                    logger.warning(f"⚠️ No se pudo obtener precio de {config.pair}: {e}")
            
            # Valor total actual
            total_value = actual_balance_usdt + crypto_value_usdt
            
            # Calcular diferencias
            missing_capital = max(0, allocated_capital - total_value)
            excess_capital = max(0, total_value - allocated_capital)
            
            # Determinar si es seguro continuar
            # Permitimos un margen de error del 5%
            margin = allocated_capital * 0.05
            is_safe = missing_capital <= margin
            
            verification = CapitalVerification(
                pair=config.pair,
                allocated_capital=allocated_capital,
                actual_balance_usdt=actual_balance_usdt,
                actual_balance_crypto=actual_balance_crypto,
                crypto_value_usdt=crypto_value_usdt,
                total_value=total_value,
                is_safe=is_safe,
                missing_capital=missing_capital,
                excess_capital=excess_capital
            )
            
            logger.info(f"   {config.pair}: Asignado ${allocated_capital:,.2f}, Actual ${total_value:,.2f}")
            if missing_capital > 0:
                logger.warning(f"   ⚠️ Capital faltante: ${missing_capital:,.2f}")
            if excess_capital > 0:
                logger.info(f"   💰 Capital excedente: ${excess_capital:,.2f}")
            
            return verification
            
        except Exception as e:
            logger.error(f"❌ Error verificando capital de {config.pair}: {e}")
            # Retornar verificación de error
            return CapitalVerification(
                pair=config.pair,
                allocated_capital=config.total_capital,
                actual_balance_usdt=0.0,
                actual_balance_crypto=0.0,
                crypto_value_usdt=0.0,
                total_value=0.0,
                is_safe=False,
                missing_capital=config.total_capital,
                excess_capital=0.0
            )

    def _get_current_price(self, pair: str) -> float:
        """
        Obtiene el precio actual de un par.
        
        Args:
            pair: Par de trading
            
        Returns:
            float: Precio actual
        """
        try:
            # Usar el método get_current_price que ya existe
            price = self.exchange_service.get_current_price(pair)
            return float(price)
        except Exception as e:
            logger.error(f"❌ Error obteniendo precio de {pair}: {e}")
            return 0.0

    def _generate_recommendations(self, verifications: List[CapitalVerification]) -> List[str]:
        """
        Genera recomendaciones basadas en las verificaciones de capital.
        
        Args:
            verifications: Lista de verificaciones de capital
            
        Returns:
            List[str]: Lista de recomendaciones
        """
        recommendations = []
        
        # Analizar capital faltante
        missing_pairs = [v for v in verifications if v.missing_capital > 0]
        if missing_pairs:
            recommendations.append("⚠️ Capital faltante detectado. Considera:")
            for v in missing_pairs:
                recommendations.append(f"   • {v.pair}: Faltan ${v.missing_capital:,.2f} USDT")
            recommendations.append("   • Deposita capital adicional antes de continuar")
            recommendations.append("   • O reduce el capital asignado en la configuración")
        
        # Analizar capital excedente
        excess_pairs = [v for v in verifications if v.excess_capital > 0]
        if excess_pairs:
            recommendations.append("💰 Capital excedente detectado:")
            for v in excess_pairs:
                recommendations.append(f"   • {v.pair}: Exceso de ${v.excess_capital:,.2f} USDT")
            recommendations.append("   • Considera retirar el exceso o aumentar niveles de grid")
        
        # Verificar si es seguro continuar
        unsafe_pairs = [v for v in verifications if not v.is_safe]
        if unsafe_pairs:
            recommendations.append("🚨 ADVERTENCIA: No es seguro continuar con:")
            for v in unsafe_pairs:
                recommendations.append(f"   • {v.pair}: Capital insuficiente")
            recommendations.append("   • Resuelve los problemas de capital antes de activar los bots")
        else:
            recommendations.append("✅ Capital verificado correctamente")
            recommendations.append("   • Es seguro continuar con la creación de órdenes")
        
        return recommendations

    def send_safety_report_notification(self, report: RestartSafetyReport) -> None:
        """
        Envía notificación con el reporte de seguridad.
        
        Args:
            report: Reporte de seguridad
        """
        try:
            # Usar type casting para acceder al método específico
            from app.infrastructure.notification_service import TelegramGridNotificationService
            if isinstance(self.notification_service, TelegramGridNotificationService):
                self.notification_service.send_restart_safety_notification(report)
            else:
                # Fallback: usar método genérico si está disponible
                logger.warning("⚠️ Servicio de notificación no soporta reporte de seguridad")
            logger.info("✅ Notificación de reporte de seguridad enviada")
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de seguridad: {e}")

    def format_safety_report_message(self, report: RestartSafetyReport) -> str:
        """
        Formatea el reporte de seguridad como mensaje legible.
        
        Args:
            report: Reporte de seguridad
            
        Returns:
            str: Mensaje formateado
        """
        try:
            message = f"🔒 **REPORTE DE SEGURIDAD AL REINICIAR**\n\n"
            
            # Resumen general
            message += f"**📊 RESUMEN GENERAL**\n"
            message += f"• Órdenes canceladas: {report.total_orders_cancelled}\n"
            message += f"• Capital faltante total: ${report.total_missing_capital:,.2f} USDT\n"
            message += f"• Capital excedente total: ${report.total_excess_capital:,.2f} USDT\n"
            message += f"• Seguro para continuar: {'✅ SÍ' if report.is_safe_to_continue else '❌ NO'}\n\n"
            
            # Verificaciones por par
            message += f"**💰 VERIFICACIÓN POR PAR**\n"
            for verification in report.capital_verifications:
                message += f"\n**{verification.pair}**\n"
                message += f"• Capital asignado: ${verification.allocated_capital:,.2f} USDT\n"
                message += f"• Balance USDT: ${verification.actual_balance_usdt:,.2f}\n"
                message += f"• Balance {verification.pair.split('/')[0]}: {verification.actual_balance_crypto:,.8f}\n"
                message += f"• Valor total: ${verification.total_value:,.2f} USDT\n"
                
                if verification.missing_capital > 0:
                    message += f"• ⚠️ Capital faltante: ${verification.missing_capital:,.2f}\n"
                if verification.excess_capital > 0:
                    message += f"• 💰 Capital excedente: ${verification.excess_capital:,.2f}\n"
                
                message += f"• Estado: {'✅ SEGURO' if verification.is_safe else '❌ INSEGURO'}\n"
            
            # Recomendaciones
            if report.recommendations:
                message += f"\n**💡 RECOMENDACIONES**\n"
                for rec in report.recommendations:
                    message += f"• {rec}\n"
            
            return message
            
        except Exception as e:
            logger.error(f"❌ Error formateando reporte de seguridad: {e}")
            return f"❌ Error generando reporte de seguridad: {e}" 
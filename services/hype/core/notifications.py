"""
Notifications Module - Sistema de Alertas del Hype Radar
========================================================

Módulo especializado en generar y enviar alertas de tendencias de memecoins
utilizando el servicio de Telegram compartido.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from shared.services.telegram_service import send_telegram_message
from shared.services.logging_config import get_logger
from shared.database.session import SessionLocal
from shared.database.models import HypeEvent

logger = get_logger(__name__)

def send_telegram_alert(message: str) -> bool:
    """
    Envía una alerta por Telegram reutilizando el servicio compartido.
    
    Args:
        message: Mensaje de alerta a enviar
        
    Returns:
        bool: True si se envió correctamente, False si hubo error
    """
    try:
        logger.info(f"📢 Enviando alerta de hype por Telegram...")
        return send_telegram_message(message)
    except Exception as e:
        logger.error(f"❌ Error enviando alerta de hype: {e}")
        return False

def format_hype_alert(ticker: str, current_mentions: int, avg_mentions: float, velocity_percent: float, threshold: float) -> str:
    """
    Formatea una alerta de hype con información detallada.
    
    Args:
        ticker: Símbolo de la criptomoneda
        current_mentions: Menciones en la última hora
        avg_mentions: Promedio de menciones en 24h
        velocity_percent: Porcentaje de incremento
        threshold: Umbral de alerta configurado
        
    Returns:
        str: Mensaje formateado para Telegram con HTML
    """
    try:
        # Determinar nivel de alerta basado en el porcentaje
        if velocity_percent >= threshold * 3:  # 1500% o más
            alert_level = "🚨 ALERTA EXTREMA"
            emoji = "🔥🔥🔥"
        elif velocity_percent >= threshold * 2:  # 1000% o más
            alert_level = "🚨 ALERTA ALTA"
            emoji = "🔥🔥"
        else:  # Por encima del threshold normal
            alert_level = "⚠️ ALERTA DE HYPE"
            emoji = "🔥"
        
        # Timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Construir mensaje con formato HTML
        message = f"<b>{alert_level}</b>\n\n"
        message += f"{emoji} <b>TICKER:</b> ${ticker}\n"
        message += f"📈 <b>Menciones última hora:</b> {current_mentions}\n"
        message += f"📊 <b>Promedio 24h:</b> {avg_mentions:.1f}\n"
        message += f"🚀 <b>Incremento:</b> {velocity_percent:.1f}%\n"
        message += f"⚡ <b>Umbral configurado:</b> {threshold:.0f}%\n\n"
        
        # Añadir contexto basado en la magnitud
        if velocity_percent >= 1000:
            message += "🎯 <b>TENDENCIA VIRAL DETECTADA</b>\n"
            message += "💡 Posible pump en progreso\n\n"
        elif velocity_percent >= 500:
            message += "📡 <b>HYPE SIGNIFICATIVO DETECTADO</b>\n"
            message += "💡 Monitorear de cerca\n\n"
        
        message += f"⏰ <i>{timestamp}</i>\n"
        message += f"🤖 <i>Hype Radar Alert System</i>"
        
        return message
        
    except Exception as e:
        logger.error(f"❌ Error formateando alerta de hype: {e}")
        return f"🚨 ALERTA DE HYPE: ${ticker} (+{velocity_percent:.1f}%)"

def send_hype_alert(
    ticker: str, 
    current_mentions: int, 
    avg_mentions: float, 
    velocity_percent: float, 
    threshold: float,
    triggering_post_title: Optional[str] = None,
    source_subreddit: Optional[str] = None
) -> bool:
    """
    Genera y envía una alerta de hype completa, guardándola también en la base de datos.
    
    Args:
        ticker: Símbolo de la criptomoneda
        current_mentions: Menciones en la última hora
        avg_mentions: Promedio de menciones en 24h
        velocity_percent: Porcentaje de incremento
        threshold: Umbral de alerta configurado
        triggering_post_title: Título del post que disparó la alerta
        source_subreddit: Subreddit donde se detectó
        
    Returns:
        bool: True si se envió correctamente
    """
    try:
        # Formatear el mensaje
        formatted_message = format_hype_alert(ticker, current_mentions, avg_mentions, velocity_percent, threshold)
        
        # Enviar alerta por Telegram
        telegram_success = send_telegram_alert(formatted_message)
        
        # Guardar evento en base de datos
        db_success = save_hype_event_to_db(
            ticker=ticker,
            current_mentions=current_mentions,
            avg_mentions=avg_mentions,
            velocity_percent=velocity_percent,
            threshold=threshold,
            triggering_post_title=triggering_post_title,
            source_subreddit=source_subreddit,
            alert_sent=telegram_success
        )
        
        if telegram_success:
            logger.info(f"✅ Alerta de hype enviada para ${ticker}: +{velocity_percent:.1f}%")
        else:
            logger.error(f"❌ Error enviando alerta de hype para ${ticker}")
        
        if not db_success:
            logger.warning(f"⚠️ Error guardando evento de hype en BD para ${ticker}")
            
        return telegram_success  # Retornamos el éxito del envío de Telegram
        
    except Exception as e:
        logger.error(f"❌ Error en send_hype_alert para ${ticker}: {e}")
        return False

def send_daily_hype_summary(top_trending: Dict[str, int], total_alerts: int) -> bool:
    """
    Envía un resumen diario de las tendencias detectadas.
    
    Args:
        top_trending: Diccionario con los tickers más mencionados del día
        total_alerts: Número total de alertas enviadas
        
    Returns:
        bool: True si se envió correctamente
    """
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d")
        
        message = f"<b>📊 RESUMEN DIARIO - HYPE RADAR</b>\n"
        message += f"📅 <b>Fecha:</b> {timestamp}\n\n"
        
        message += f"🚨 <b>Alertas enviadas:</b> {total_alerts}\n\n"
        
        if top_trending:
            message += f"🔥 <b>TOP TRENDING DEL DÍA:</b>\n"
            for i, (ticker, mentions) in enumerate(list(top_trending.items())[:5], 1):
                message += f"{i}. ${ticker}: {mentions} menciones\n"
        else:
            message += f"😴 <b>Día tranquilo - Sin tendencias significativas</b>\n"
        
        message += f"\n🤖 <i>Hype Radar Daily Report</i>"
        
        return send_telegram_alert(message)
        
    except Exception as e:
        logger.error(f"❌ Error enviando resumen diario: {e}")
        return False

def save_hype_event_to_db(
    ticker: str, 
    current_mentions: int, 
    avg_mentions: float, 
    velocity_percent: float, 
    threshold: float,
    triggering_post_title: Optional[str] = None,
    source_subreddit: Optional[str] = None,
    alert_sent: bool = False
) -> bool:
    """
    Guarda un evento de hype en la base de datos.
    
    Args:
        ticker: Símbolo de la criptomoneda
        current_mentions: Menciones en la última hora
        avg_mentions: Promedio histórico de 24h
        velocity_percent: Porcentaje de incremento
        threshold: Umbral utilizado para la alerta
        triggering_post_title: Título del post que disparó la alerta
        source_subreddit: Subreddit donde se detectó
        alert_sent: Si se envió alerta por Telegram
        
    Returns:
        bool: True si se guardó correctamente
    """
    db = SessionLocal()
    try:
        # Determinar nivel de alerta
        if velocity_percent >= threshold * 3:
            alert_level = "EXTREME"
        elif velocity_percent >= threshold * 2:
            alert_level = "HIGH"
        else:
            alert_level = "NORMAL"
        
        # Crear el evento
        hype_event = HypeEvent(
            ticker=ticker,
            mention_increase_percent=velocity_percent,
            triggering_post_title=triggering_post_title,
            current_mentions=current_mentions,
            avg_mentions=avg_mentions,
            threshold_used=threshold,
            source_subreddit=source_subreddit,
            alert_sent=alert_sent,
            alert_level=alert_level
        )
        
        db.add(hype_event)
        db.commit()
        db.refresh(hype_event)
        
        logger.info(f"💾 Evento de hype guardado en BD: ${ticker} (ID: {hype_event.id})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error guardando evento de hype en BD: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def get_recent_hype_events(hours: int = 24, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Obtiene eventos de hype recientes de la base de datos.
    
    Args:
        hours: Horas hacia atrás a buscar
        limit: Máximo número de eventos a retornar
        
    Returns:
        List[Dict]: Lista de eventos de hype
    """
    db = SessionLocal()
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        events = db.query(HypeEvent)\
                  .filter(HypeEvent.timestamp >= cutoff_time)\
                  .order_by(HypeEvent.timestamp.desc())\
                  .limit(limit)\
                  .all()
        
        return [event.to_dict() for event in events]
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo eventos de hype de BD: {e}")
        return []
    finally:
        db.close()

def send_system_alert(message: str, alert_type: str = "INFO") -> bool:
    """
    Envía alertas del sistema (errores, estado, etc.).
    
    Args:
        message: Mensaje de la alerta
        alert_type: Tipo de alerta (INFO, WARNING, ERROR)
        
    Returns:
        bool: True si se envió correctamente
    """
    try:
        # Seleccionar emoji basado en el tipo
        emoji_map = {
            "INFO": "ℹ️",
            "WARNING": "⚠️", 
            "ERROR": "❌",
            "SUCCESS": "✅"
        }
        
        emoji = emoji_map.get(alert_type.upper(), "🤖")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        formatted_message = f"<b>{emoji} HYPE RADAR SYSTEM</b>\n\n"
        formatted_message += f"{message}\n\n"
        formatted_message += f"⏰ <i>{timestamp}</i>"
        
        return send_telegram_alert(formatted_message)
        
    except Exception as e:
        logger.error(f"❌ Error enviando alerta del sistema: {e}")
        return False 
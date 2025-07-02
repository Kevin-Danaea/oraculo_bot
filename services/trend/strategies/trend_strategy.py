"""
Estrategia de Trend Following - Implementación de la receta ganadora
SMA 30/150, ADX 25, Sentimiento -0.1, Trailing Stop 20%
"""

from typing import Dict, Any, Tuple, Optional
from datetime import datetime
import pandas as pd
import numpy as np
from shared.services.logging_config import get_logger

logger = get_logger(__name__)

# ============================================================================
# PARÁMETROS DE LA ESTRATEGIA (RECETA GANADORA)
# ============================================================================

TREND_PARAMS = {
    'ETH/USDT': {
        'sma_fast': 30,           # SMA rápida
        'sma_slow': 150,          # SMA lenta
        'adx_threshold': 25,      # Umbral ADX para tendencia fuerte
        'sentiment_threshold': -0.1,  # Umbral de sentimiento
        'trailing_stop_percent': 20,  # Trailing stop 20%
        'adx_period': 14          # Período para cálculo ADX
    }
    # En el futuro, agregar más pares aquí
}


def get_trend_parameters(pair: str) -> Dict[str, Any]:
    """
    Obtiene los parámetros optimizados para un par específico.
    
    Args:
        pair: Par de trading (ej: 'ETH/USDT')
        
    Returns:
        Diccionario con parámetros de la estrategia
    """
    return TREND_PARAMS.get(pair, TREND_PARAMS['ETH/USDT'])


def check_golden_cross(sma_fast_current: float, sma_slow_current: float,
                      sma_fast_previous: float, sma_slow_previous: float) -> bool:
    """
    Verifica si ha ocurrido un Golden Cross (cruce dorado).
    
    Args:
        sma_fast_current: SMA rápida actual
        sma_slow_current: SMA lenta actual
        sma_fast_previous: SMA rápida anterior
        sma_slow_previous: SMA lenta anterior
        
    Returns:
        True si hay Golden Cross
    """
    # Golden Cross: SMA rápida cruza por encima de la lenta
    cross_occurred = (sma_fast_current > sma_slow_current) and (sma_fast_previous <= sma_slow_previous)
    
    if cross_occurred:
        logger.info(f"🌟 Golden Cross detectado: SMA{sma_fast_current:.2f} > SMA{sma_slow_current:.2f}")
        
    return cross_occurred


def check_death_cross(sma_fast_current: float, sma_slow_current: float,
                     sma_fast_previous: float, sma_slow_previous: float) -> bool:
    """
    Verifica si ha ocurrido un Death Cross (cruce de la muerte).
    
    Args:
        sma_fast_current: SMA rápida actual
        sma_slow_current: SMA lenta actual
        sma_fast_previous: SMA rápida anterior
        sma_slow_previous: SMA lenta anterior
        
    Returns:
        True si hay Death Cross
    """
    # Death Cross: SMA rápida cruza por debajo de la lenta
    cross_occurred = (sma_fast_current < sma_slow_current) and (sma_fast_previous >= sma_slow_previous)
    
    if cross_occurred:
        logger.warning(f"💀 Death Cross detectado: SMA{sma_fast_current:.2f} < SMA{sma_slow_current:.2f}")
        
    return cross_occurred


def check_trend_strength(adx_value: float, adx_threshold: float) -> bool:
    """
    Verifica si la tendencia tiene fuerza suficiente usando ADX.
    
    Args:
        adx_value: Valor actual del ADX
        adx_threshold: Umbral mínimo de ADX
        
    Returns:
        True si la tendencia es fuerte
    """
    is_strong = adx_value > adx_threshold
    
    if is_strong:
        logger.info(f"💪 Tendencia fuerte: ADX {adx_value:.2f} > {adx_threshold}")
    else:
        logger.info(f"📉 Tendencia débil: ADX {adx_value:.2f} <= {adx_threshold}")
        
    return is_strong


def check_sentiment_support(sentiment_value: float, sentiment_threshold: float) -> bool:
    """
    Verifica si el sentimiento apoya la tendencia.
    
    Args:
        sentiment_value: Valor promedio de sentimiento
        sentiment_threshold: Umbral de sentimiento
        
    Returns:
        True si el sentimiento es favorable
    """
    is_favorable = sentiment_value > sentiment_threshold
    
    if is_favorable:
        logger.info(f"😊 Sentimiento favorable: {sentiment_value:.3f} > {sentiment_threshold}")
    else:
        logger.info(f"😰 Sentimiento desfavorable: {sentiment_value:.3f} <= {sentiment_threshold}")
        
    return is_favorable


def check_panic_sentiment(primary_emotion: str, news_intensity: float, 
                         intensity_threshold: float = 0.8) -> bool:
    """
    Verifica si hay señal de pánico por sentimiento extremo.
    
    Args:
        primary_emotion: Emoción dominante
        news_intensity: Intensidad de noticias (0-1)
        intensity_threshold: Umbral de intensidad anormal
        
    Returns:
        True si hay señal de pánico
    """
    is_panic = (primary_emotion.lower() == 'fear') and (news_intensity > intensity_threshold)
    
    if is_panic:
        logger.warning(f"🚨 Señal de pánico detectada: {primary_emotion} con intensidad {news_intensity:.2f}")
        
    return is_panic


def analyze_entry_signal(indicators: Dict[str, Any], params: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Analiza si hay señal de entrada basado en los indicadores.
    
    Args:
        indicators: Diccionario con todos los indicadores calculados
        params: Parámetros de la estrategia
        
    Returns:
        Tupla (hay_señal, razón)
    """
    try:
        # Verificar Golden Cross
        golden_cross = check_golden_cross(
            indicators['sma_fast_current'],
            indicators['sma_slow_current'],
            indicators['sma_fast_previous'],
            indicators['sma_slow_previous']
        )
        
        if not golden_cross:
            return False, "Sin Golden Cross"
        
        # Verificar fuerza de tendencia
        trend_strength = check_trend_strength(
            indicators['adx_current'],
            params['adx_threshold']
        )
        
        if not trend_strength:
            return False, "Tendencia débil (ADX bajo)"
        
        # Verificar sentimiento
        sentiment_support = check_sentiment_support(
            indicators['sentiment_average'],
            params['sentiment_threshold']
        )
        
        if not sentiment_support:
            return False, "Sentimiento desfavorable"
        
        # Todas las condiciones se cumplen
        return True, "Golden Cross + ADX fuerte + Sentimiento favorable"
        
    except Exception as e:
        logger.error(f"❌ Error analizando señal de entrada: {e}")
        return False, f"Error: {str(e)}"


def analyze_exit_signal(indicators: Dict[str, Any], params: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Analiza si hay señal de salida basado en los indicadores.
    
    Args:
        indicators: Diccionario con todos los indicadores calculados
        params: Parámetros de la estrategia
        
    Returns:
        Tupla (hay_señal, razón)
    """
    try:
        # Verificar Death Cross
        death_cross = check_death_cross(
            indicators['sma_fast_current'],
            indicators['sma_slow_current'],
            indicators['sma_fast_previous'],
            indicators['sma_slow_previous']
        )
        
        if death_cross:
            return True, "Death Cross detectado"
        
        # Verificar pánico por sentimiento
        if 'primary_emotion' in indicators and 'news_intensity' in indicators:
            panic_signal = check_panic_sentiment(
                indicators['primary_emotion'],
                indicators['news_intensity']
            )
            
            if panic_signal:
                return True, "Señal de pánico por sentimiento"
        
        # No hay señal de salida
        return False, "Mantener posición"
        
    except Exception as e:
        logger.error(f"❌ Error analizando señal de salida: {e}")
        return False, f"Error: {str(e)}"


def calculate_trailing_stop_price(highest_price: float, trailing_percent: float) -> float:
    """
    Calcula el precio del trailing stop.
    
    Args:
        highest_price: Precio más alto desde la entrada
        trailing_percent: Porcentaje de trailing stop
        
    Returns:
        Precio del trailing stop
    """
    stop_price = highest_price * (1 - trailing_percent / 100)
    return round(stop_price, 2)


def should_update_trailing_stop(current_price: float, highest_price: float, 
                               current_stop: float, trailing_percent: float) -> Tuple[bool, float]:
    """
    Determina si se debe actualizar el trailing stop.
    
    Args:
        current_price: Precio actual
        highest_price: Precio más alto registrado
        current_stop: Stop loss actual
        trailing_percent: Porcentaje de trailing
        
    Returns:
        Tupla (debe_actualizar, nuevo_stop_price)
    """
    if current_price > highest_price:
        new_stop = calculate_trailing_stop_price(current_price, trailing_percent)
        if new_stop > current_stop:
            return True, new_stop
    
    return False, current_stop


def check_stop_loss_hit(current_price: float, stop_price: float) -> bool:
    """
    Verifica si el precio actual ha tocado el stop loss.
    
    Args:
        current_price: Precio actual
        stop_price: Precio de stop loss
        
    Returns:
        True si se activó el stop loss
    """
    if current_price <= stop_price:
        logger.warning(f"🛑 Stop Loss activado: ${current_price:.2f} <= ${stop_price:.2f}")
        return True
    return False


def calculate_position_size(capital: float, price: float, max_position_pct: float = 0.95) -> float:
    """
    Calcula el tamaño de la posición basado en el capital disponible.
    
    Args:
        capital: Capital disponible en USDT
        price: Precio actual del activo
        max_position_pct: Porcentaje máximo del capital a usar
        
    Returns:
        Cantidad de crypto a comprar
    """
    # Usar máximo 95% del capital para dejar margen para comisiones
    available_capital = capital * max_position_pct
    position_size = available_capital / price
    
    # Redondear a 6 decimales
    return round(position_size, 6)


__all__ = [
    'TREND_PARAMS',
    'get_trend_parameters',
    'check_golden_cross',
    'check_death_cross',
    'check_trend_strength',
    'check_sentiment_support',
    'check_panic_sentiment',
    'analyze_entry_signal',
    'analyze_exit_signal',
    'calculate_trailing_stop_price',
    'should_update_trailing_stop',
    'check_stop_loss_hit',
    'calculate_position_size'
] 
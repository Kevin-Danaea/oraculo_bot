"""
Trade Aggregator - Agregador de Trades para Resúmenes Periódicos
==================================================================

Módulo que actúa como un singleton para agregar todos los trades
ejecutados en un período, para luego ser enviados en un resumen.
"""

import threading
from collections import defaultdict
from typing import Dict, List, Any

class TradeAggregator:
    """
    Singleton para agregar trades ejecutados. Es thread-safe.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TradeAggregator, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Inicializa el agregador de trades."""
        if hasattr(self, '_initialized') and self._initialized:
            return
        with self._lock:
            self._trades: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: {'buys': [], 'sells': []})
            self._initialized = True

    def add_trade(self, pair: str, trade_data: Dict[str, Any]):
        """
        Agrega un trade ejecutado al agregador.
        
        Args:
            pair: Par del trade (ej. 'ETH/USDT')
            trade_data: Diccionario con la información de la orden ejecutada
        """
        with self._lock:
            trade_type = trade_data.get('type')
            if trade_type == 'buy':
                self._trades[pair]['buys'].append(trade_data)
            elif trade_type == 'sell':
                self._trades[pair]['sells'].append(trade_data)

    def get_and_clear_summary(self) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """
        Obtiene todos los trades agregados y limpia el estado para el próximo período.
        
        Returns:
            Un diccionario con todos los trades del período.
        """
        with self._lock:
            summary = self._trades.copy()
            self._trades = defaultdict(lambda: {'buys': [], 'sells': []})
            return summary

# Instancia singleton del agregador
trade_aggregator = TradeAggregator()

__all__ = ['trade_aggregator'] 
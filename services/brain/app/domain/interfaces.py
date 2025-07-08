"""
Interfaces del Dominio Brain
============================

Define las interfaces (contratos) que deben implementar las capas externas.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime

from .entities import (
    TradingDecision, 
    MarketIndicators, 
    TradingRecipe, 
    BotType
)


class MarketDataRepository(ABC):
    """Interfaz para el repositorio de datos de mercado."""
    
    @abstractmethod
    async def fetch_market_data(
        self, 
        pair: str, 
        timeframe: str = '4h', 
        days: int = 40
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene datos históricos de mercado para un par específico.
        
        Args:
            pair: Par de trading (ej: 'ETH/USDT')
            timeframe: Marco temporal ('4h', '1h', '1d')
            days: Número de días de historial
            
        Returns:
            Datos de mercado o None si hay error
        """
        pass
    
    @abstractmethod
    async def calculate_indicators(self, market_data: Dict[str, Any]) -> Optional[MarketIndicators]:
        """
        Calcula indicadores técnicos a partir de datos de mercado.
        
        Args:
            market_data: Datos de mercado
            
        Returns:
            Indicadores calculados o None si hay error
        """
        pass


class DecisionRepository(ABC):
    """Interfaz para el repositorio de decisiones."""
    
    @abstractmethod
    async def save_decision(self, decision: TradingDecision) -> bool:
        """
        Guarda una decisión de trading en la base de datos.
        
        Args:
            decision: Decisión a guardar
            
        Returns:
            True si se guardó correctamente
        """
        pass
    
    @abstractmethod
    async def get_latest_decision(self, pair: str, bot_type: BotType) -> Optional[TradingDecision]:
        """
        Obtiene la última decisión para un par y tipo de bot.
        
        Args:
            pair: Par de trading
            bot_type: Tipo de bot
            
        Returns:
            Última decisión o None si no existe
        """
        pass
    
    @abstractmethod
    async def get_decisions_history(
        self, 
        pair: str, 
        bot_type: BotType, 
        limit: int = 10
    ) -> List[TradingDecision]:
        """
        Obtiene el historial de decisiones para un par y tipo de bot.
        
        Args:
            pair: Par de trading
            bot_type: Tipo de bot
            limit: Número máximo de decisiones a obtener
            
        Returns:
            Lista de decisiones ordenadas por timestamp descendente
        """
        pass


class RecipeRepository(ABC):
    """Interfaz para el repositorio de recetas."""
    
    @abstractmethod
    async def get_recipe(self, pair: str, bot_type: BotType = BotType.GRID) -> Optional[TradingRecipe]:
        """
        Obtiene la receta para un par específico.
        
        Args:
            pair: Par de trading
            bot_type: Tipo de bot
            
        Returns:
            Receta de trading o None si no existe
        """
        pass
    
    @abstractmethod
    async def get_all_recipes(self) -> List[TradingRecipe]:
        """
        Obtiene todas las recetas disponibles.
        
        Returns:
            Lista de recetas
        """
        pass
    
    @abstractmethod
    async def get_supported_pairs(self) -> List[str]:
        """
        Obtiene todos los pares soportados.
        
        Returns:
            Lista de pares soportados
        """
        pass


class NotificationService(ABC):
    """Interfaz para el servicio de notificaciones."""
    
    @abstractmethod
    async def notify_decision_change(self, decision: TradingDecision) -> bool:
        """
        Notifica un cambio de decisión.
        
        Args:
            decision: Decisión de trading
            
        Returns:
            True si se notificó correctamente
        """
        pass
    
    @abstractmethod
    async def notify_service_status(self, status: Dict[str, Any]) -> bool:
        """
        Notifica el estado del servicio.
        
        Args:
            status: Estado del servicio
            
        Returns:
            True si se notificó correctamente
        """
        pass
    
    @abstractmethod
    async def notify_error(self, error: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Notifica un error.
        
        Args:
            error: Mensaje de error
            context: Contexto adicional del error
            
        Returns:
            True si se notificó correctamente
        """
        pass
    
    @abstractmethod
    async def close(self):
        """Cierra el servicio de notificaciones."""
        pass





class LLMService(ABC):
    """Interfaz para el servicio de LLM (futuro)."""
    
    @abstractmethod
    async def analyze_market_context(
        self, 
        pair: str, 
        indicators: MarketIndicators, 
        historical_decisions: List[TradingDecision]
    ) -> Dict[str, Any]:
        """
        Analiza el contexto de mercado usando LLM.
        
        Args:
            pair: Par de trading
            indicators: Indicadores actuales
            historical_decisions: Decisiones históricas
            
        Returns:
            Análisis del LLM
        """
        pass
    
    @abstractmethod
    async def generate_decision_reason(
        self, 
        decision: TradingDecision, 
        market_context: Dict[str, Any]
    ) -> str:
        """
        Genera una razón detallada para la decisión usando LLM.
        
        Args:
            decision: Decisión tomada
            market_context: Contexto de mercado
            
        Returns:
            Razón generada por el LLM
        """
        pass 
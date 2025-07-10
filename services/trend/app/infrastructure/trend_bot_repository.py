"""Repository for trend bot using JSON file persistence."""

import json
import logging
import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

from ..domain.entities import TrendBotStatus, TrendPosition, TrendBotMetrics
from ..domain.interfaces import ITrendBotRepository

logger = logging.getLogger(__name__)


class JsonTrendBotRepository(ITrendBotRepository):
    """Implementación del repositorio usando archivos JSON para persistencia."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Archivos de datos
        self.status_file = self.data_dir / "trend_bot_status.json"
        self.positions_file = self.data_dir / "trend_positions.json"
        self.metrics_file = self.data_dir / "trend_metrics.json"
        
        logger.info(f"✅ JsonTrendBotRepository inicializado en {self.data_dir}")
    
    async def save_bot_status(self, status: TrendBotStatus) -> None:
        """Guarda el estado del bot."""
        try:
            # Cargar estados existentes
            statuses = self._load_json_file(self.status_file, {})
            
            # Actualizar estado
            statuses[status.bot_id] = self._status_to_dict(status)
            
            # Guardar archivo
            self._save_json_file(self.status_file, statuses)
            
            logger.debug(f"Estado del bot {status.bot_id} guardado")
            
        except Exception as e:
            logger.error(f"Error guardando estado del bot: {str(e)}")
            raise
    
    async def get_bot_status(self, bot_id: str) -> Optional[TrendBotStatus]:
        """Obtiene el estado del bot."""
        try:
            # Cargar estados
            statuses = self._load_json_file(self.status_file, {})
            
            if bot_id not in statuses:
                return None
            
            # Convertir de dict a entidad
            status_dict = statuses[bot_id]
            return self._dict_to_status(status_dict)
            
        except Exception as e:
            logger.error(f"Error obteniendo estado del bot: {str(e)}")
            return None
    
    async def save_position(self, position: TrendPosition) -> None:
        """Guarda una posición."""
        try:
            # Cargar posiciones existentes
            positions = self._load_json_file(self.positions_file, {})
            
            # Actualizar posición
            positions[position.id] = self._position_to_dict(position)
            
            # Guardar archivo
            self._save_json_file(self.positions_file, positions)
            
            logger.debug(f"Posición {position.id} guardada")
            
        except Exception as e:
            logger.error(f"Error guardando posición: {str(e)}")
            raise
    
    async def get_current_position(self, bot_id: str) -> Optional[TrendPosition]:
        """Obtiene la posición actual del bot."""
        try:
            # Obtener estado del bot
            bot_status = await self.get_bot_status(bot_id)
            if not bot_status or not bot_status.current_position:
                return None
            
            return bot_status.current_position
            
        except Exception as e:
            logger.error(f"Error obteniendo posición actual: {str(e)}")
            return None
    
    async def save_metrics(self, bot_id: str, metrics: TrendBotMetrics) -> None:
        """Guarda las métricas del bot."""
        try:
            # Cargar métricas existentes
            all_metrics = self._load_json_file(self.metrics_file, {})
            
            # Actualizar métricas
            all_metrics[bot_id] = self._metrics_to_dict(metrics)
            
            # Guardar archivo
            self._save_json_file(self.metrics_file, all_metrics)
            
            logger.debug(f"Métricas del bot {bot_id} guardadas")
            
        except Exception as e:
            logger.error(f"Error guardando métricas: {str(e)}")
            raise
    
    async def get_metrics(self, bot_id: str) -> Optional[TrendBotMetrics]:
        """Obtiene las métricas del bot."""
        try:
            # Cargar métricas
            all_metrics = self._load_json_file(self.metrics_file, {})
            
            if bot_id not in all_metrics:
                return None
            
            # Convertir de dict a entidad
            metrics_dict = all_metrics[bot_id]
            return self._dict_to_metrics(metrics_dict)
            
        except Exception as e:
            logger.error(f"Error obteniendo métricas: {str(e)}")
            return None
    
    def _load_json_file(self, file_path: Path, default_value):
        """Carga un archivo JSON."""
        if not file_path.exists():
            return default_value
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error cargando {file_path}: {str(e)}")
            return default_value
    
    def _save_json_file(self, file_path: Path, data):
        """Guarda datos en un archivo JSON."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error guardando {file_path}: {str(e)}")
            raise
    
    def _status_to_dict(self, status: TrendBotStatus) -> dict:
        """Convierte TrendBotStatus a diccionario."""
        return {
            'bot_id': status.bot_id,
            'symbol': status.symbol,
            'state': status.state.value,
            'current_position': self._position_to_dict(status.current_position) if status.current_position else None,
            'last_decision': status.last_decision.value if status.last_decision else None,
            'last_update': status.last_update.isoformat() if status.last_update else None
        }
    
    def _dict_to_status(self, status_dict: dict) -> TrendBotStatus:
        """Convierte diccionario a TrendBotStatus."""
        from ..domain.entities import TrendBotState, BrainDecision
        
        # Convertir estado
        state = TrendBotState(status_dict.get('state', 'FUERA_DEL_MERCADO'))
        
        # Convertir posición actual
        current_position = None
        if status_dict.get('current_position'):
            current_position = self._dict_to_position(status_dict['current_position'])
        
        # Convertir última decisión
        last_decision = None
        if status_dict.get('last_decision'):
            last_decision = BrainDecision(status_dict['last_decision'])
        
        # Convertir timestamp
        last_update = None
        if status_dict.get('last_update'):
            last_update = datetime.fromisoformat(status_dict['last_update'])
        
        return TrendBotStatus(
            bot_id=status_dict['bot_id'],
            symbol=status_dict['symbol'],
            state=state,
            current_position=current_position,
            last_decision=last_decision,
            last_update=last_update
        )
    
    def _position_to_dict(self, position: TrendPosition) -> dict:
        """Convierte TrendPosition a diccionario."""
        return {
            'id': position.id,
            'symbol': position.symbol,
            'entry_price': str(position.entry_price),
            'entry_quantity': str(position.entry_quantity),
            'entry_time': position.entry_time.isoformat(),
            'highest_price_since_entry': str(position.highest_price_since_entry),
            'current_price': str(position.current_price) if position.current_price else None,
            'exit_price': str(position.exit_price) if position.exit_price else None,
            'exit_quantity': str(position.exit_quantity) if position.exit_quantity else None,
            'exit_time': position.exit_time.isoformat() if position.exit_time else None,
            'exit_reason': position.exit_reason.value if position.exit_reason else None,
            'fees_paid': str(position.fees_paid)
        }
    
    def _dict_to_position(self, position_dict: dict) -> TrendPosition:
        """Convierte diccionario a TrendPosition."""
        from ..domain.entities import ExitReason
        
        # Convertir exit_reason
        exit_reason = None
        if position_dict.get('exit_reason'):
            exit_reason = ExitReason(position_dict['exit_reason'])
        
        # Convertir timestamps
        entry_time = datetime.fromisoformat(position_dict['entry_time'])
        exit_time = None
        if position_dict.get('exit_time'):
            exit_time = datetime.fromisoformat(position_dict['exit_time'])
        
        return TrendPosition(
            id=position_dict['id'],
            symbol=position_dict['symbol'],
            entry_price=Decimal(position_dict['entry_price']),
            entry_quantity=Decimal(position_dict['entry_quantity']),
            entry_time=entry_time,
            highest_price_since_entry=Decimal(position_dict['highest_price_since_entry']),
            current_price=Decimal(position_dict['current_price']) if position_dict.get('current_price') else None,
            exit_price=Decimal(position_dict['exit_price']) if position_dict.get('exit_price') else None,
            exit_quantity=Decimal(position_dict['exit_quantity']) if position_dict.get('exit_quantity') else None,
            exit_time=exit_time,
            exit_reason=exit_reason,
            fees_paid=Decimal(position_dict['fees_paid'])
        )
    
    def _metrics_to_dict(self, metrics: TrendBotMetrics) -> dict:
        """Convierte TrendBotMetrics a diccionario."""
        return {
            'total_trades': metrics.total_trades,
            'winning_trades': metrics.winning_trades,
            'losing_trades': metrics.losing_trades,
            'total_pnl': str(metrics.total_pnl),
            'total_fees': str(metrics.total_fees),
            'best_trade': str(metrics.best_trade),
            'worst_trade': str(metrics.worst_trade),
            'average_holding_time_hours': metrics.average_holding_time_hours,
            'win_rate': metrics.win_rate
        }
    
    def _dict_to_metrics(self, metrics_dict: dict) -> TrendBotMetrics:
        """Convierte diccionario a TrendBotMetrics."""
        return TrendBotMetrics(
            total_trades=metrics_dict.get('total_trades', 0),
            winning_trades=metrics_dict.get('winning_trades', 0),
            losing_trades=metrics_dict.get('losing_trades', 0),
            total_pnl=Decimal(metrics_dict.get('total_pnl', '0')),
            total_fees=Decimal(metrics_dict.get('total_fees', '0')),
            best_trade=Decimal(metrics_dict.get('best_trade', '0')),
            worst_trade=Decimal(metrics_dict.get('worst_trade', '0')),
            average_holding_time_hours=metrics_dict.get('average_holding_time_hours', 0.0),
            win_rate=metrics_dict.get('win_rate', 0.0)
        ) 
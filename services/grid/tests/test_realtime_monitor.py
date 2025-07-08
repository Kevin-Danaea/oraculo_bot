"""
Pruebas para el sistema de monitoreo en tiempo real con detección de fills.
"""
import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, MagicMock

from app.application.realtime_grid_monitor_use_case import RealTimeGridMonitorUseCase
from app.domain.entities import GridConfig
from app.domain.interfaces import GridRepository, ExchangeService, NotificationService, GridCalculator

class TestRealTimeGridMonitor:
    """Pruebas para el monitor en tiempo real."""
    
    def setup_method(self):
        """Configuración inicial para cada prueba."""
        self.mock_repository = Mock(spec=GridRepository)
        self.mock_exchange = Mock(spec=ExchangeService)
        self.mock_notification = Mock(spec=NotificationService)
        self.mock_calculator = Mock(spec=GridCalculator)
        
        self.monitor = RealTimeGridMonitorUseCase(
            grid_repository=self.mock_repository,
            exchange_service=self.mock_exchange,
            notification_service=self.mock_notification,
            grid_calculator=self.mock_calculator
        )
        
        # Configuración de prueba
        self.test_config = GridConfig(
            id=1,
            telegram_chat_id="123456",
            config_type="BTC",
            pair="BTC/USDT",
            total_capital=1000.0,
            grid_levels=5,
            price_range_percent=10.0,
            stop_loss_percent=5.0,
            enable_stop_loss=True,
            enable_trailing_up=True,
            is_active=True,
            is_configured=True,
            is_running=True,
            last_decision="running",
            last_decision_timestamp=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    def test_detect_fills_method_1_comparison(self):
        """Prueba detección de fills por comparación de órdenes."""
        # Simular órdenes anteriores
        previous_orders = [
            {'exchange_order_id': 'order1', 'side': 'buy', 'amount': Decimal('0.001')},
            {'exchange_order_id': 'order2', 'side': 'sell', 'amount': Decimal('0.001')},
            {'exchange_order_id': 'order3', 'side': 'buy', 'amount': Decimal('0.001')}
        ]
        
        # Simular órdenes actuales (order2 desapareció)
        current_orders = [
            {'exchange_order_id': 'order1', 'side': 'buy', 'amount': Decimal('0.001')},
            {'exchange_order_id': 'order3', 'side': 'buy', 'amount': Decimal('0.001')}
        ]
        
        # Simular respuesta del exchange para order2
        filled_order = {
            'exchange_order_id': 'order2',
            'side': 'sell',
            'amount': Decimal('0.001'),
            'price': Decimal('50000'),
            'status': 'closed',
            'filled': Decimal('0.001'),
            'remaining': Decimal('0'),
            'timestamp': int(datetime.now().timestamp() * 1000),
            'type': 'limit'
        }
        
        self.mock_exchange.get_active_orders_from_exchange.return_value = current_orders
        self.mock_exchange.detect_fills_by_comparison.return_value = [filled_order]
        
        # Configurar el monitor con órdenes anteriores
        self.monitor._previous_active_orders['BTC/USDT'] = previous_orders
        
        # Ejecutar monitoreo
        result = self.monitor._monitor_bot_realtime(self.test_config)
        
        # Verificar resultados
        assert result['fills_detected'] == 1
        assert result['new_orders_created'] == 1
        self.mock_exchange.detect_fills_by_comparison.assert_called_once()

    def test_detect_fills_method_2_closed_orders(self):
        """Prueba detección de fills usando fetch_closed_orders."""
        # Simular órdenes cerradas recientemente
        closed_orders = [
            {
                'exchange_order_id': 'order4',
                'side': 'buy',
                'amount': Decimal('0.001'),
                'price': Decimal('49000'),
                'status': 'closed',
                'filled': Decimal('0.001'),
                'remaining': Decimal('0'),
                'timestamp': int(datetime.now().timestamp() * 1000),
                'type': 'limit'
            }
        ]
        
        self.mock_exchange.get_active_orders_from_exchange.return_value = []
        self.mock_exchange.get_filled_orders_from_exchange.return_value = closed_orders
        self.mock_exchange.create_order.return_value = Mock()  # Simular orden creada
        
        # Ejecutar monitoreo
        result = self.monitor._monitor_bot_realtime(self.test_config)
        
        # Verificar resultados
        assert result['fills_detected'] == 1
        assert result['new_orders_created'] == 1
        self.mock_exchange.get_filled_orders_from_exchange.assert_called_once()

    def test_detect_fills_method_3_my_trades(self):
        """Prueba detección de fills usando fetch_my_trades."""
        # Simular trades recientes
        trades = [
            {
                'trade_id': 'trade1',
                'order_id': 'order5',
                'pair': 'BTC/USDT',
                'side': 'sell',
                'amount': Decimal('0.001'),
                'price': Decimal('51000'),
                'cost': Decimal('51.00'),
                'timestamp': int(datetime.now().timestamp() * 1000)
            }
        ]
        
        # Simular estado de orden completada
        order_status = {
            'exchange_order_id': 'order5',
            'side': 'sell',
            'amount': Decimal('0.001'),
            'price': Decimal('51000'),
            'status': 'closed',
            'filled': Decimal('0.001'),
            'remaining': Decimal('0'),
            'timestamp': int(datetime.now().timestamp() * 1000),
            'type': 'limit'
        }
        
        self.mock_exchange.get_active_orders_from_exchange.return_value = []
        self.mock_exchange.get_recent_trades_from_exchange.return_value = trades
        self.mock_exchange.get_order_status_from_exchange.return_value = order_status
        self.mock_exchange.create_order.return_value = Mock()
        
        # Ejecutar monitoreo
        result = self.monitor._monitor_bot_realtime(self.test_config)
        
        # Verificar resultados
        assert result['fills_detected'] == 1
        assert result['new_orders_created'] == 1
        self.mock_exchange.get_recent_trades_from_exchange.assert_called_once()

    def test_multiple_fills_detection(self):
        """Prueba detección de múltiples fills usando todos los métodos."""
        # Simular fills de diferentes métodos
        fills_method_1 = [
            {
                'exchange_order_id': 'order1',
                'side': 'buy',
                'amount': Decimal('0.001'),
                'price': Decimal('50000'),
                'status': 'closed',
                'filled': Decimal('0.001'),
                'remaining': Decimal('0'),
                'timestamp': int(datetime.now().timestamp() * 1000),
                'type': 'limit'
            }
        ]
        
        fills_method_2 = [
            {
                'exchange_order_id': 'order2',
                'side': 'sell',
                'amount': Decimal('0.001'),
                'price': Decimal('51000'),
                'status': 'closed',
                'filled': Decimal('0.001'),
                'remaining': Decimal('0'),
                'timestamp': int(datetime.now().timestamp() * 1000),
                'type': 'limit'
            }
        ]
        
        self.mock_exchange.get_active_orders_from_exchange.return_value = []
        self.mock_exchange.detect_fills_by_comparison.return_value = fills_method_1
        self.mock_exchange.get_filled_orders_from_exchange.return_value = fills_method_2
        self.mock_exchange.get_recent_trades_from_exchange.return_value = []
        self.mock_exchange.create_order.return_value = Mock()
        
        # Ejecutar monitoreo
        result = self.monitor._monitor_bot_realtime(self.test_config)
        
        # Verificar resultados (debería detectar 2 fills únicos)
        assert result['fills_detected'] == 2
        assert result['new_orders_created'] == 2

    def test_duplicate_fills_removal(self):
        """Prueba eliminación de fills duplicados."""
        # Simular el mismo fill detectado por múltiples métodos
        same_fill = {
            'exchange_order_id': 'order1',
            'side': 'buy',
            'amount': Decimal('0.001'),
            'price': Decimal('50000'),
            'status': 'closed',
            'filled': Decimal('0.001'),
            'remaining': Decimal('0'),
            'timestamp': int(datetime.now().timestamp() * 1000),
            'type': 'limit'
        }
        
        self.mock_exchange.get_active_orders_from_exchange.return_value = []
        self.mock_exchange.detect_fills_by_comparison.return_value = [same_fill]
        self.mock_exchange.get_filled_orders_from_exchange.return_value = [same_fill]
        self.mock_exchange.get_recent_trades_from_exchange.return_value = []
        self.mock_exchange.create_order.return_value = Mock()
        
        # Ejecutar monitoreo
        result = self.monitor._monitor_bot_realtime(self.test_config)
        
        # Verificar que solo se procesa una vez
        assert result['fills_detected'] == 1
        assert result['new_orders_created'] == 1

    def test_complementary_order_creation(self):
        """Prueba creación de órdenes complementarias."""
        filled_order = {
            'exchange_order_id': 'order1',
            'side': 'buy',
            'amount': Decimal('0.001'),
            'price': Decimal('50000'),
            'status': 'closed',
            'filled': Decimal('0.001'),
            'remaining': Decimal('0'),
            'timestamp': int(datetime.now().timestamp() * 1000),
            'type': 'limit'
        }
        
        # Simular validación de capital exitosa
        capital_check = {
            'can_use': True,
            'available_balance': Decimal('100'),
            'required_amount': Decimal('0.001')
        }
        
        # Simular orden complementaria creada
        mock_complementary_order = Mock()
        
        self.mock_exchange.can_bot_use_capital.return_value = capital_check
        self.mock_exchange.create_order.return_value = mock_complementary_order
        self.mock_calculator.calculate_complementary_price.return_value = Decimal('51000')
        
        # Crear orden complementaria
        result = self.monitor._create_complementary_order_from_dict(filled_order, self.test_config)
        
        # Verificar resultados
        assert result is not None
        self.mock_exchange.create_order.assert_called_once()
        self.mock_notification.send_notification.assert_called_once()

    def test_insufficient_capital_for_complementary_order(self):
        """Prueba manejo de capital insuficiente para orden complementaria."""
        filled_order = {
            'exchange_order_id': 'order1',
            'side': 'buy',
            'amount': Decimal('0.001'),
            'price': Decimal('50000'),
            'status': 'closed',
            'filled': Decimal('0.001'),
            'remaining': Decimal('0'),
            'timestamp': int(datetime.now().timestamp() * 1000),
            'type': 'limit'
        }
        
        # Simular validación de capital fallida
        capital_check = {
            'can_use': False,
            'available_balance': Decimal('0'),
            'required_amount': Decimal('0.001')
        }
        
        self.mock_exchange.can_bot_use_capital.return_value = capital_check
        
        # Intentar crear orden complementaria
        result = self.monitor._create_complementary_order_from_dict(filled_order, self.test_config)
        
        # Verificar que no se crea la orden
        assert result is None
        self.mock_exchange.create_order.assert_not_called()

if __name__ == "__main__":
    # Ejecutar pruebas
    pytest.main([__file__, "-v"]) 
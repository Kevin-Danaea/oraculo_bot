"""
Tests para el sistema de gestión de riesgos (Stop Loss y Trailing Up).
"""
import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, MagicMock

from app.domain.entities import GridConfig, GridOrder
from app.application.risk_management_use_case import RiskManagementUseCase
from app.infrastructure.grid_calculator import GridTradingCalculator


class TestRiskManagement:
    """Tests para el sistema de gestión de riesgos."""
    
    @pytest.fixture
    def mock_repository(self):
        """Mock del repositorio."""
        repo = Mock()
        repo.get_active_orders.return_value = []
        repo.update_config_status.return_value = None
        repo.save_order.return_value = None
        return repo
    
    @pytest.fixture
    def mock_exchange(self):
        """Mock del servicio de exchange."""
        exchange = Mock()
        exchange.get_current_price.return_value = Decimal('2000.00')
        exchange.get_bot_allocated_balance.return_value = {
            'allocated_capital': Decimal('1000.00'),
            'total_available_in_account': Decimal('5000.00'),
            'total_value_usdt': Decimal('1000.00'),
            'base_balance': Decimal('0.5'),
            'quote_balance': Decimal('500.00')
        }
        exchange.get_balance.return_value = Decimal('0.25')
        exchange.cancel_order.return_value = True
        exchange.create_order.return_value = Mock(exchange_order_id='test_order_123')
        exchange.get_order_status.return_value = {'filled': '0.25'}
        exchange.calculate_net_amount_after_fees.return_value = Decimal('0.24')
        return exchange
    
    @pytest.fixture
    def mock_notification(self):
        """Mock del servicio de notificaciones."""
        notification = Mock()
        notification.send_bot_status_notification.return_value = None
        return notification
    
    @pytest.fixture
    def grid_calculator(self):
        """Instancia del calculador de grid."""
        return GridTradingCalculator()
    
    @pytest.fixture
    def risk_management(self, mock_repository, mock_exchange, mock_notification, grid_calculator):
        """Instancia del caso de uso de gestión de riesgos."""
        return RiskManagementUseCase(
            grid_repository=mock_repository,
            exchange_service=mock_exchange,
            notification_service=mock_notification,
            grid_calculator=grid_calculator
        )
    
    @pytest.fixture
    def sample_config(self):
        """Configuración de ejemplo para testing."""
        return GridConfig(
            id=1,
            telegram_chat_id="123456789",
            config_type="ETH",
            pair="ETH/USDT",
            total_capital=1000.0,
            grid_levels=30,
            price_range_percent=10.0,
            stop_loss_percent=4.0,
            enable_stop_loss=True,
            enable_trailing_up=True,
            is_active=True,
            is_configured=True,
            is_running=True,
            last_decision="RUNNING",
            last_decision_timestamp=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    def test_stop_loss_triggered(self, risk_management, sample_config, mock_repository, mock_exchange):
        """Test: Stop loss se activa cuando el precio cae más del porcentaje configurado."""
        # Configurar mocks
        mock_exchange.get_current_price.return_value = Decimal('1900.00')  # 5% de caída
        
        # Crear orden de compra previa
        buy_order = GridOrder(
            id="buy_123",
            exchange_order_id="ex_buy_123",
            pair="ETH/USDT",
            side="buy",
            amount=Decimal('0.25'),
            price=Decimal('2000.00'),
            status="filled",
            order_type="grid_buy",
            grid_level=15,
            created_at=datetime.now(),
            filled_at=datetime.now()
        )
        mock_repository.get_active_orders.return_value = [buy_order]
        
        # Ejecutar verificación de riesgo
        result = risk_management.check_and_handle_risk_events(sample_config)
        
        # Verificar que se activó stop loss
        assert result['success'] is True
        assert len(result['events_handled']) == 1
        assert result['events_handled'][0]['type'] == 'stop_loss'
        assert result['events_handled'][0]['triggered'] is True
        assert result['events_handled'][0]['drop_percent'] == 5.0

    def test_stop_loss_not_triggered(self, risk_management, sample_config, mock_repository, mock_exchange):
        """Test: Stop loss NO se activa cuando la caída es menor al porcentaje configurado."""
        # Configurar mocks
        mock_exchange.get_current_price.return_value = Decimal('1950.00')  # 2.5% de caída
        
        # Crear orden de compra previa
        buy_order = GridOrder(
            id="buy_123",
            exchange_order_id="ex_buy_123",
            pair="ETH/USDT",
            side="buy",
            amount=Decimal('0.25'),
            price=Decimal('2000.00'),
            status="filled",
            order_type="grid_buy",
            grid_level=15,
            created_at=datetime.now(),
            filled_at=datetime.now()
        )
        mock_repository.get_active_orders.return_value = [buy_order]
        
        # Ejecutar verificación de riesgo
        result = risk_management.check_and_handle_risk_events(sample_config)
        
        # Verificar que NO se activó stop loss
        assert result['success'] is True
        assert len(result['events_handled']) == 0

    def test_trailing_up_triggered(self, risk_management, sample_config, mock_repository, mock_exchange):
        """Test: Trailing up se activa cuando el precio sube más del 5%."""
        # Configurar mocks
        mock_exchange.get_current_price.return_value = Decimal('2200.00')  # 5% de subida
        
        # Crear órdenes de venta activas
        sell_order = GridOrder(
            id="sell_123",
            exchange_order_id="ex_sell_123",
            pair="ETH/USDT",
            side="sell",
            amount=Decimal('0.25'),
            price=Decimal('2100.00'),  # Nivel más alto de venta
            status="open",
            order_type="grid_sell",
            grid_level=15,
            created_at=datetime.now(),
            filled_at=None
        )
        mock_repository.get_active_orders.return_value = [sell_order]
        
        # Ejecutar verificación de riesgo
        result = risk_management.check_and_handle_risk_events(sample_config)
        
        # Verificar que se activó trailing up
        assert result['success'] is True
        assert len(result['events_handled']) == 1
        assert result['events_handled'][0]['type'] == 'trailing_up'
        assert result['events_handled'][0]['triggered'] is True
        assert result['events_handled'][0]['rise_percent'] == 4.76  # (2200-2100)/2100 * 100

    def test_trailing_up_not_triggered(self, risk_management, sample_config, mock_repository, mock_exchange):
        """Test: Trailing up NO se activa cuando la subida es menor al 5%."""
        # Configurar mocks
        mock_exchange.get_current_price.return_value = Decimal('2150.00')  # 2.38% de subida
        
        # Crear órdenes de venta activas
        sell_order = GridOrder(
            id="sell_123",
            exchange_order_id="ex_sell_123",
            pair="ETH/USDT",
            side="sell",
            amount=Decimal('0.25'),
            price=Decimal('2100.00'),  # Nivel más alto de venta
            status="open",
            order_type="grid_sell",
            grid_level=15,
            created_at=datetime.now(),
            filled_at=None
        )
        mock_repository.get_active_orders.return_value = [sell_order]
        
        # Ejecutar verificación de riesgo
        result = risk_management.check_and_handle_risk_events(sample_config)
        
        # Verificar que NO se activó trailing up
        assert result['success'] is True
        assert len(result['events_handled']) == 0

    def test_stop_loss_disabled(self, risk_management, sample_config, mock_repository, mock_exchange):
        """Test: Stop loss no se activa cuando está deshabilitado."""
        # Deshabilitar stop loss
        sample_config.enable_stop_loss = False
        mock_exchange.get_current_price.return_value = Decimal('1900.00')  # 5% de caída
        
        # Crear orden de compra previa
        buy_order = GridOrder(
            id="buy_123",
            exchange_order_id="ex_buy_123",
            pair="ETH/USDT",
            side="buy",
            amount=Decimal('0.25'),
            price=Decimal('2000.00'),
            status="filled",
            order_type="grid_buy",
            grid_level=15,
            created_at=datetime.now(),
            filled_at=datetime.now()
        )
        mock_repository.get_active_orders.return_value = [buy_order]
        
        # Ejecutar verificación de riesgo
        result = risk_management.check_and_handle_risk_events(sample_config)
        
        # Verificar que NO se activó stop loss
        assert result['success'] is True
        assert len(result['events_handled']) == 0

    def test_trailing_up_disabled(self, risk_management, sample_config, mock_repository, mock_exchange):
        """Test: Trailing up no se activa cuando está deshabilitado."""
        # Deshabilitar trailing up
        sample_config.enable_trailing_up = False
        mock_exchange.get_current_price.return_value = Decimal('2200.00')  # 5% de subida
        
        # Crear órdenes de venta activas
        sell_order = GridOrder(
            id="sell_123",
            exchange_order_id="ex_sell_123",
            pair="ETH/USDT",
            side="sell",
            amount=Decimal('0.25'),
            price=Decimal('2100.00'),
            status="open",
            order_type="grid_sell",
            grid_level=15,
            created_at=datetime.now(),
            filled_at=None
        )
        mock_repository.get_active_orders.return_value = [sell_order]
        
        # Ejecutar verificación de riesgo
        result = risk_management.check_and_handle_risk_events(sample_config)
        
        # Verificar que NO se activó trailing up
        assert result['success'] is True
        assert len(result['events_handled']) == 0

    def test_no_orders_no_risk_events(self, risk_management, sample_config, mock_repository, mock_exchange):
        """Test: No hay eventos de riesgo cuando no hay órdenes."""
        # Configurar sin órdenes
        mock_repository.get_active_orders.return_value = []
        
        # Ejecutar verificación de riesgo
        result = risk_management.check_and_handle_risk_events(sample_config)
        
        # Verificar que no hay eventos
        assert result['success'] is True
        assert len(result['events_handled']) == 0

    def test_grid_calculator_methods(self, grid_calculator):
        """Test: Métodos del calculador de grid para gestión de riesgos."""
        # Crear órdenes de ejemplo
        orders = [
            GridOrder(
                id="buy_1",
                exchange_order_id="ex_buy_1",
                pair="ETH/USDT",
                side="buy",
                amount=Decimal('0.25'),
                price=Decimal('2000.00'),
                status="filled",
                order_type="grid_buy",
                grid_level=15,
                created_at=datetime.now(),
                filled_at=datetime.now()
            ),
            GridOrder(
                id="sell_1",
                exchange_order_id="ex_sell_1",
                pair="ETH/USDT",
                side="sell",
                amount=Decimal('0.25'),
                price=Decimal('2100.00'),
                status="open",
                order_type="grid_sell",
                grid_level=15,
                created_at=datetime.now(),
                filled_at=None
            )
        ]
        
        # Test get_last_buy_price
        last_buy_price = grid_calculator.get_last_buy_price(orders)
        assert last_buy_price == Decimal('2000.00')
        
        # Test get_highest_sell_price
        highest_sell_price = grid_calculator.get_highest_sell_price(orders)
        assert highest_sell_price == Decimal('2100.00')
        
        # Test check_stop_loss_triggered
        config = GridConfig(
            id=1,
            telegram_chat_id="123456789",
            config_type="ETH",
            pair="ETH/USDT",
            total_capital=1000.0,
            grid_levels=30,
            price_range_percent=10.0,
            stop_loss_percent=4.0,
            enable_stop_loss=True,
            enable_trailing_up=True,
            is_active=True,
            is_configured=True,
            is_running=True,
            last_decision="RUNNING",
            last_decision_timestamp=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Precio actual por debajo del stop loss
        triggered = grid_calculator.check_stop_loss_triggered(
            current_price=Decimal('1900.00'),
            last_buy_price=Decimal('2000.00'),
            config=config
        )
        assert triggered is True
        
        # Precio actual por encima del stop loss
        not_triggered = grid_calculator.check_stop_loss_triggered(
            current_price=Decimal('1950.00'),
            last_buy_price=Decimal('2000.00'),
            config=config
        )
        assert not_triggered is False
        
        # Test check_trailing_up_triggered
        triggered = grid_calculator.check_trailing_up_triggered(
            current_price=Decimal('2200.00'),
            highest_sell_price=Decimal('2100.00'),
            config=config
        )
        assert triggered is True
        
        not_triggered = grid_calculator.check_trailing_up_triggered(
            current_price=Decimal('2150.00'),
            highest_sell_price=Decimal('2100.00'),
            config=config
        )
        assert not_triggered is False

    def test_stop_loss_uses_config_percentage(self, grid_calculator):
        """Test: Stop loss usa el porcentaje específico configurado por par."""
        # Configuración con stop loss personalizado
        config_high_risk = GridConfig(
            id=1,
            telegram_chat_id="123456789",
            config_type="ETH",
            pair="ETH/USDT",
            total_capital=1000.0,
            grid_levels=30,
            price_range_percent=10.0,
            stop_loss_percent=2.0,  # Stop loss más agresivo
            enable_stop_loss=True,
            enable_trailing_up=True,
            is_active=True,
            is_configured=True,
            is_running=True,
            last_decision="RUNNING",
            last_decision_timestamp=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        config_low_risk = GridConfig(
            id=2,
            telegram_chat_id="123456789",
            config_type="BTC",
            pair="BTC/USDT",
            total_capital=1000.0,
            grid_levels=30,
            price_range_percent=7.5,
            stop_loss_percent=6.0,  # Stop loss más conservador
            enable_stop_loss=True,
            enable_trailing_up=True,
            is_active=True,
            is_configured=True,
            is_running=True,
            last_decision="RUNNING",
            last_decision_timestamp=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Test con ETH (2% stop loss)
        # Caída de 2.5% debería activar stop loss en ETH
        triggered_eth = grid_calculator.check_stop_loss_triggered(
            current_price=Decimal('1950.00'),  # 2.5% de caída
            last_buy_price=Decimal('2000.00'),
            config=config_high_risk
        )
        assert triggered_eth is True
        
        # Test con BTC (6% stop loss)
        # Caída de 2.5% NO debería activar stop loss en BTC
        not_triggered_btc = grid_calculator.check_stop_loss_triggered(
            current_price=Decimal('1950.00'),  # 2.5% de caída
            last_buy_price=Decimal('2000.00'),
            config=config_low_risk
        )
        assert not_triggered_btc is False
        
        # Caída de 7% debería activar stop loss en BTC
        triggered_btc = grid_calculator.check_stop_loss_triggered(
            current_price=Decimal('1860.00'),  # 7% de caída
            last_buy_price=Decimal('2000.00'),
            config=config_low_risk
        )
        assert triggered_btc is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 
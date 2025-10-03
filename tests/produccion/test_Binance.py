"""Tests comprehensivos para la clase BinanceConnector que maneja la conexión con Binance Futures"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any
import logging

from binance.client import Client
from binance.exceptions import BinanceAPIException

from src.produccion.binance import BinanceConnector
from src.produccion.config.config import ProductionConfig, ObsNorm, MarketStats, PortfolioStats


class TestBinanceConnector:
    """Suite de tests para la clase BinanceConnector siguiendo principios SOLID"""
    
    def setup_method(self):
        """Configuración inicial para cada test (SRP: responsabilidad única de configuración)"""
        # Mock del cliente de Binance
        self.mock_client = Mock(spec=Client)
        
        # Mock de la configuración de producción
        self.mock_config = Mock(spec=ProductionConfig)
        self.mock_config.simbolo = "BTCUSDT"
        self.mock_config.apalancamiento = 10.0
        
        # Configurar el mock del cliente para que no falle en la inicialización
        self.mock_client.futures_change_leverage.return_value = {"leverage": 10}
    
    def test_init_successful_initialization(self):
        """Test: Inicialización exitosa del conector con configuración de apalancamiento"""
        # Arrange & Act
        connector = BinanceConnector(self.mock_client, self.mock_config)
        
        # Assert
        assert connector._client == self.mock_client
        assert connector._config == self.mock_config
        assert connector._balance == 0.0
        assert connector._equity == 0.0
        assert connector._pnl_total == 0.0
        assert connector._posicion_abierta is False
        
        # Verificar que se configuró el apalancamiento
        self.mock_client.futures_change_leverage.assert_called_once_with(
            symbol="BTCUSDT",
            leverage=10
        )
    
    def test_init_leverage_setup_failure(self):
        """Test: Fallo al configurar el apalancamiento durante la inicialización"""
        # Arrange
        mock_response = Mock()
        mock_response.text = '{"code": -4003, "msg": "Invalid leverage"}'
        
        self.mock_client.futures_change_leverage.side_effect = BinanceAPIException(
            response=mock_response, status_code=400, text='{"code": -4003, "msg": "Invalid leverage"}'
        )
        
        # Act & Assert
        with pytest.raises(BinanceAPIException):
            BinanceConnector(self.mock_client, self.mock_config)
    
    def test_create_order_market_buy_success(self):
        """Test: Creación exitosa de orden de compra a mercado"""
        # Arrange
        connector = BinanceConnector(self.mock_client, self.mock_config)
        expected_order = {
            "orderId": 12345,
            "symbol": "BTCUSDT",
            "side": "BUY",
            "type": "MARKET",
            "quantity": "0.1"
        }
        
        self.mock_client.futures_create_order.return_value = expected_order
        self.mock_client.futures_account.return_value = {
            "totalWalletBalance": "1000.0",
            "totalMarginBalance": "1050.0",
            "totalUnrealizedProfit": "50.0"
        }
        self.mock_client.futures_position_information.return_value = [
            {"positionAmt": "0.0"}
        ]
        
        # Act
        result = connector.create_order(
            symbol="BTCUSDT",
            side="BUY", 
            quantity=0.1,
            order_type="MARKET"
        )
        
        # Assert
        assert result == expected_order
        self.mock_client.futures_create_order.assert_called_once_with(
            symbol="BTCUSDT",
            side="BUY",
            type="MARKET",
            quantity=0.1,
            reduceOnly=False
        )
        # Verificar que se actualizó la información de cuenta
        self.mock_client.futures_account.assert_called_once()
    
    def test_create_order_limit_sell_with_time_in_force(self):
        """Test: Creación de orden límite con timeInForce especificado"""
        # Arrange
        connector = BinanceConnector(self.mock_client, self.mock_config)
        expected_order = {"orderId": 67890}
        
        self.mock_client.futures_create_order.return_value = expected_order
        self._setup_account_info_mocks()
        
        # Act
        result = connector.create_order(
            symbol="ETHUSDT",
            side="SELL",
            quantity=1.0,
            order_type="LIMIT",
            time_in_force="IOC"
        )
        
        # Assert
        self.mock_client.futures_create_order.assert_called_once_with(
            symbol="ETHUSDT",
            side="SELL",
            type="LIMIT",
            quantity=1.0,
            reduceOnly=False,
            timeInForce="IOC"
        )
    
    def test_create_order_reduce_only(self):
        """Test: Creación de orden con reduce_only=True"""
        # Arrange
        connector = BinanceConnector(self.mock_client, self.mock_config)
        expected_order = {"orderId": 11111}
        
        self.mock_client.futures_create_order.return_value = expected_order
        self._setup_account_info_mocks()
        
        # Act
        result = connector.create_order(
            symbol="BTCUSDT",
            side="SELL",
            quantity=0.05,
            reduce_only=True
        )
        
        # Assert
        self.mock_client.futures_create_order.assert_called_once_with(
            symbol="BTCUSDT",
            side="SELL",
            type="MARKET",
            quantity=0.05,
            reduceOnly=True
        )
    
    def test_create_order_api_exception(self):
        """Test: Manejo de excepción de API al crear orden"""
        # Arrange
        connector = BinanceConnector(self.mock_client, self.mock_config)
        
        mock_response = Mock()
        mock_response.text = '{"code": -1001, "msg": "Insufficient balance"}'
        
        self.mock_client.futures_create_order.side_effect = BinanceAPIException(
            response=mock_response, status_code=400, text='{"code": -1001, "msg": "Insufficient balance"}'
        )
        
        # Act & Assert
        with pytest.raises(BinanceAPIException):
            connector.create_order(
                symbol="BTCUSDT",
                side="BUY",
                quantity=10.0
            )
    
    def test_get_account_info_success(self):
        """Test: Obtención exitosa de información de cuenta"""
        # Arrange
        connector = BinanceConnector(self.mock_client, self.mock_config)
        
        account_data = {
            "totalWalletBalance": "5000.50",
            "totalMarginBalance": "5250.75",
            "totalUnrealizedProfit": "250.25"
        }
        
        position_data = [
            {"positionAmt": "0.1"},  # Posición abierta
            {"positionAmt": "0.0"}   # Sin posición
        ]
        
        self.mock_client.futures_account.return_value = account_data
        self.mock_client.futures_position_information.return_value = position_data
        
        # Act
        result = connector.get_account_info()
        
        # Assert
        assert result is True
        assert connector.balance == 5000.50
        assert connector.equity == 5250.75
        assert connector.pnl_total == 250.25
        assert connector.posicion_abierta is True
        
        self.mock_client.futures_account.assert_called_once()
        self.mock_client.futures_position_information.assert_called_once_with(
            symbol="BTCUSDT"
        )
    
    def test_get_account_info_no_open_positions(self):
        """Test: Información de cuenta sin posiciones abiertas"""
        # Arrange
        connector = BinanceConnector(self.mock_client, self.mock_config)
        
        account_data = {
            "totalWalletBalance": "1000.0",
            "totalMarginBalance": "1000.0", 
            "totalUnrealizedProfit": "0.0"
        }
        
        position_data = [
            {"positionAmt": "0.0"},
            {"positionAmt": "0.0"}
        ]
        
        self.mock_client.futures_account.return_value = account_data
        self.mock_client.futures_position_information.return_value = position_data
        
        # Act
        result = connector.get_account_info()
        
        # Assert
        assert result is True
        assert connector.posicion_abierta is False
    
    def test_get_account_info_api_exception(self):
        """Test: Manejo de excepción al obtener información de cuenta"""
        # Arrange
        connector = BinanceConnector(self.mock_client, self.mock_config)
        
        mock_response = Mock()
        mock_response.text = '{"code": -1001, "msg": "API temporarily unavailable"}'
        
        self.mock_client.futures_account.side_effect = BinanceAPIException(
            response=mock_response, status_code=503, text='{"code": -1001, "msg": "API temporarily unavailable"}'
        )
        
        # Act
        result = connector.get_account_info()
        
        # Assert
        assert result is False
        # Los valores deben permanecer en sus valores por defecto
        assert connector.balance == 0.0
        assert connector.equity == 0.0
    
    def test_properties_access(self):
        """Test: Acceso a propiedades de solo lectura (Principio de Encapsulación)"""
        # Arrange
        connector = BinanceConnector(self.mock_client, self.mock_config)
        
        # Actualizar valores internos
        connector._balance = 1500.0
        connector._equity = 1600.0
        connector._pnl_total = 100.0
        connector._posicion_abierta = True
        
        # Act & Assert
        assert connector.balance == 1500.0
        assert connector.equity == 1600.0
        assert connector.pnl_total == 100.0
        assert connector.posicion_abierta is True
        assert connector.simbolo == "BTCUSDT"
        assert connector.apalancamiento == 10.0
    
    def test_properties_are_read_only(self):
        """Test: Las propiedades son de solo lectura"""
        # Arrange
        connector = BinanceConnector(self.mock_client, self.mock_config)
        
        # Act & Assert - Verificar que no se pueden modificar las propiedades
        with pytest.raises(AttributeError):
            connector.balance = 2000.0
        
        with pytest.raises(AttributeError):
            connector.equity = 2100.0
            
        with pytest.raises(AttributeError):
            connector.posicion_abierta = False
    
    def test_logging_configuration(self):
        """Test: Configuración correcta del sistema de logging"""
        # Act
        # Reimportar el módulo para verificar la configuración del logger
        import importlib
        import src.produccion.binance
        importlib.reload(src.produccion.binance)
        
        # Assert - Verificar que el logger está configurado correctamente
        assert src.produccion.binance.log.name == "AFML.Binance"
    
    def _setup_account_info_mocks(self):
        """Método auxiliar para configurar mocks de información de cuenta (DRY)"""
        self.mock_client.futures_account.return_value = {
            "totalWalletBalance": "1000.0",
            "totalMarginBalance": "1000.0",
            "totalUnrealizedProfit": "0.0"
        }
        self.mock_client.futures_position_information.return_value = [
            {"positionAmt": "0.0"}
        ]


class TestBinanceConnectorIntegration:
    """Tests de integración para validar el comportamiento completo del sistema"""
    
    def test_full_trading_workflow(self):
        """Test: Flujo completo de trading - inicialización, orden, actualización de cuenta"""
        # Arrange
        mock_client = Mock(spec=Client)
        mock_config = Mock(spec=ProductionConfig)
        mock_config.simbolo = "ETHUSDT"
        mock_config.apalancamiento = 5.0
        
        # Configurar respuestas del cliente
        mock_client.futures_change_leverage.return_value = {"leverage": 5}
        mock_client.futures_create_order.return_value = {"orderId": 999}
        mock_client.futures_account.return_value = {
            "totalWalletBalance": "2000.0",
            "totalMarginBalance": "2100.0", 
            "totalUnrealizedProfit": "100.0"
        }
        mock_client.futures_position_information.return_value = [
            {"positionAmt": "0.5"}
        ]
        
        # Act
        connector = BinanceConnector(mock_client, mock_config)
        order_result = connector.create_order(
            symbol="ETHUSDT",
            side="BUY",
            quantity=0.5
        )
        
        # Assert
        assert order_result["orderId"] == 999
        assert connector.balance == 2000.0
        assert connector.equity == 2100.0
        assert connector.pnl_total == 100.0
        assert connector.posicion_abierta is True
        
        # Verificar secuencia de llamadas
        assert mock_client.futures_change_leverage.call_count == 1
        assert mock_client.futures_create_order.call_count == 1
        assert mock_client.futures_account.call_count == 1
        assert mock_client.futures_position_information.call_count == 1


# Fixtures para reutilización en otros tests (DRY)
@pytest.fixture
def mock_binance_client():
    """Fixture que proporciona un cliente mock de Binance configurado"""
    client = Mock(spec=Client)
    client.futures_change_leverage.return_value = {"leverage": 10}
    client.futures_account.return_value = {
        "totalWalletBalance": "1000.0",
        "totalMarginBalance": "1000.0",
        "totalUnrealizedProfit": "0.0"
    }
    client.futures_position_information.return_value = [{"positionAmt": "0.0"}]
    return client


@pytest.fixture
def mock_production_config():
    """Fixture que proporciona una configuración mock de producción"""
    config = Mock(spec=ProductionConfig)
    config.simbolo = "BTCUSDT"
    config.apalancamiento = 10.0
    return config


@pytest.fixture
def binance_connector(mock_binance_client, mock_production_config):
    """Fixture que proporciona una instancia configurada de BinanceConnector"""
    return BinanceConnector(mock_binance_client, mock_production_config)

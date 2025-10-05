"""Tests para verificar el manejo correcto de operaciones fallidas."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from binance.exceptions import BinanceAPIException

from src.produccion.binance import BinanceConnector
from src.produccion.config.config import ProductionConfig


class TestOperacionesFallidas:
    """Tests para verificar el manejo de operaciones que fallan."""
    
    @pytest.fixture
    def production_config(self, config_metadata_dict):
        """Fixture de configuración de producción."""
        config = ProductionConfig(
            **config_metadata_dict,
            train_id="test_train",
            model_path="/path/to/model",
            scaler_path="/path/to/scaler",
            is_live=False
        )
        return config
    
    def test_margen_insuficiente_no_reintenta(self, mock_binance_client, production_config):
        """Test que error -2019 (margen insuficiente) NO se reintenta."""
        connector = BinanceConnector(mock_binance_client, production_config)
        
        # Simular error -2019
        mock_binance_client.futures_create_order.side_effect = BinanceAPIException(
            Mock(), -2019, "Margin is insufficient."
        )
        
        result = connector.create_order(
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.001
        )
        
        # Debe retornar None inmediatamente (sin reintentos)
        assert result is None
        # Verificar que solo se llamó UNA vez (no 3 reintentos)
        assert mock_binance_client.futures_create_order.call_count == 1
    
    def test_error_recuperable_si_reintenta(self, mock_binance_client, production_config):
        """Test que errores recuperables SÍ se reintentan."""
        connector = BinanceConnector(mock_binance_client, production_config)
        
        # Simular error recuperable (código que NO está en lista de no-recuperables)
        mock_binance_client.futures_create_order.side_effect = BinanceAPIException(
            Mock(), -1001, "Server error"  # Error genérico
        )
        
        result = connector.create_order(
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.001
        )
        
        # Debe retornar None tras reintentar
        assert result is None
        # Verificar que se reintentó 3 veces
        assert mock_binance_client.futures_create_order.call_count == 3
    
    def test_parametros_invalidos_no_reintenta(self, mock_binance_client, production_config):
        """Test que error -1100 (parámetros inválidos) NO se reintenta."""
        connector = BinanceConnector(mock_binance_client, production_config)
        
        mock_binance_client.futures_create_order.side_effect = BinanceAPIException(
            Mock(), -1100, "Invalid parameters"
        )
        
        result = connector.create_order(
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.001
        )
        
        assert result is None
        assert mock_binance_client.futures_create_order.call_count == 1
    
    def test_permisos_insuficientes_no_reintenta(self, mock_binance_client, production_config):
        """Test que error -2015 (permisos insuficientes) NO se reintenta."""
        connector = BinanceConnector(mock_binance_client, production_config)
        
        mock_binance_client.futures_create_order.side_effect = BinanceAPIException(
            Mock(), -2015, "Invalid API-key, IP, or permissions for action"
        )
        
        result = connector.create_order(
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.001
        )
        
        assert result is None
        assert mock_binance_client.futures_create_order.call_count == 1
    
    def test_timeout_si_reintenta(self, mock_binance_client, production_config):
        """Test que timeouts de red SÍ se reintentan."""
        from requests.exceptions import ReadTimeout
        
        connector = BinanceConnector(mock_binance_client, production_config)
        
        # Simular timeout
        mock_binance_client.futures_create_order.side_effect = ReadTimeout("Connection timeout")
        
        result = connector.create_order(
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.001
        )
        
        # Debe retornar None tras 3 reintentos
        assert result is None
        # Verificar que se reintentó 3 veces
        assert mock_binance_client.futures_create_order.call_count == 3
    
    def test_orden_exitosa_tras_reintentos(self, mock_binance_client, production_config):
        """Test que orden exitosa tras reintentos retorna correctamente."""
        connector = BinanceConnector(mock_binance_client, production_config)
        
        # Primera vez falla, segunda exitosa
        mock_binance_client.futures_create_order.side_effect = [
            BinanceAPIException(Mock(), -1001, "Server error"),
            {
                'orderId': 12345,
                'symbol': 'BTCUSDT',
                'status': 'FILLED'
            }
        ]
        
        result = connector.create_order(
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.001
        )
        
        # Debe retornar la orden exitosa
        assert result is not None
        assert result['orderId'] == 12345
        # Se llamó 2 veces (1 fallo + 1 éxito)
        assert mock_binance_client.futures_create_order.call_count == 2

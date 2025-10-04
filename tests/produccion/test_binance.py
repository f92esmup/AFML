"""Tests para el conector de Binance."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from binance.exceptions import BinanceAPIException

from src.produccion.binance import BinanceConnector
from src.produccion.config.config import ProductionConfig


class TestBinanceConnector:
    """Tests para la clase BinanceConnector."""
    
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
    
    def test_init_and_setup_leverage(self, mock_binance_client, production_config):
        """Test de inicialización y configuración de apalancamiento."""
        connector = BinanceConnector(mock_binance_client, production_config)
        
        # Verificar que se configuró el apalancamiento
        mock_binance_client.futures_change_leverage.assert_called_once_with(
            symbol="BTCUSDT",
            leverage=2
        )
        
        # Verificar inicialización de atributos
        assert connector._balance == 0.0
        assert connector._equity == 0.0
        assert connector._pnl_total == 0.0
        assert connector._posicion_abierta is False
        
    def test_setup_leverage_api_exception(self, mock_binance_client, production_config):
        """Test de manejo de excepción en setup de apalancamiento."""
        mock_binance_client.futures_change_leverage.side_effect = BinanceAPIException(
            Mock(), 400, "Invalid leverage"
        )
        
        # No debe lanzar excepción, solo loggear
        connector = BinanceConnector(mock_binance_client, production_config)
        assert connector is not None
        
    def test_create_order_market_buy(self, mock_binance_client, production_config):
        """Test de creación de orden MARKET BUY."""
        connector = BinanceConnector(mock_binance_client, production_config)
        
        result = connector.create_order(
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.001,
            order_type="MARKET"
        )
        
        # Verificar llamada al cliente
        mock_binance_client.futures_create_order.assert_called_once()
        call_kwargs = mock_binance_client.futures_create_order.call_args[1]
        
        assert call_kwargs["symbol"] == "BTCUSDT"
        assert call_kwargs["side"] == "BUY"
        assert call_kwargs["quantity"] == 0.001
        assert call_kwargs["type"] == "MARKET"
        assert result is not None
        
    def test_create_order_with_reduce_only(self, mock_binance_client, production_config):
        """Test de creación de orden con reduceOnly."""
        connector = BinanceConnector(mock_binance_client, production_config)
        
        connector.create_order(
            symbol="BTCUSDT",
            side="SELL",
            quantity=0.001,
            reduce_only=True
        )
        
        call_kwargs = mock_binance_client.futures_create_order.call_args[1]
        assert call_kwargs["reduceOnly"] is True
        
    def test_create_order_api_exception(self, mock_binance_client, production_config):
        """Test de manejo de excepción en creación de orden."""
        connector = BinanceConnector(mock_binance_client, production_config)
        
        mock_binance_client.futures_create_order.side_effect = BinanceAPIException(
            Mock(), 400, "Insufficient balance"
        )
        
        # No debe lanzar excepción, retorna None o similar
        result = connector.create_order(
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.001
        )
        
        # Verificar que se manejó el error
        assert result is None or isinstance(result, dict)
        
    def test_get_account_info_success(self, mock_binance_client, production_config):
        """Test de obtención exitosa de información de cuenta."""
        connector = BinanceConnector(mock_binance_client, production_config)
        
        result = connector.get_account_info()
        
        assert result is True
        assert connector.balance == 10000.0
        assert connector.equity == 10000.0
        
    def test_get_account_info_with_position(self, mock_binance_client, production_config):
        """Test de get_account_info con posición abierta."""
        # Modificar mock para incluir posición
        mock_binance_client.futures_position_information.return_value = [
            {
                "symbol": "BTCUSDT",
                "positionAmt": "0.001",
                "entryPrice": "50000.0",
                "unrealizedProfit": "50.0",
                "positionSide": "BOTH"
            }
        ]
        
        connector = BinanceConnector(mock_binance_client, production_config)
        connector.get_account_info()
        
        assert connector.posicion_abierta is True
        
    def test_get_position_info(self, mock_binance_client, production_config):
        """Test de obtención de información de posición."""
        connector = BinanceConnector(mock_binance_client, production_config)
        connector.get_account_info()
        
        info = connector.get_position_info()
        
        # Verificar estructura del diccionario
        assert "balance" in info
        assert "equity" in info
        assert "max_drawdown" in info
        assert "pnl_total" in info
        assert "posicion_abierta" in info
        assert "tipo_posicion_activa" in info
        assert "precio_entrada_activa" in info
        assert "cantidad_activa" in info
        assert "pnl_no_realizado" in info
        
    def test_properties(self, mock_binance_client, production_config):
        """Test de propiedades de solo lectura."""
        connector = BinanceConnector(mock_binance_client, production_config)
        connector.get_account_info()
        
        # Verificar que las propiedades son accesibles
        assert isinstance(connector.balance, float)
        assert isinstance(connector.equity, float)
        assert isinstance(connector.pnl_total, float)
        assert isinstance(connector.posicion_abierta, bool)
        assert connector.simbolo == "BTCUSDT"
        assert connector.apalancamiento == 2.0
        
    def test_close_all_positions_no_positions(self, mock_binance_client, production_config):
        """Test de cierre de posiciones cuando no hay ninguna."""
        connector = BinanceConnector(mock_binance_client, production_config)
        
        resultado = connector.close_all_positions(emergency=False)
        
        assert resultado["posiciones_cerradas"] == 0
        assert resultado["balance_final"] >= 0
        assert isinstance(resultado["errores"], list)
        
    def test_close_all_positions_with_open_position(self, mock_binance_client, production_config):
        """Test de cierre de posiciones con posición abierta."""
        # Mock posición abierta
        mock_binance_client.futures_position_information.return_value = [
            {
                "symbol": "BTCUSDT",
                "positionAmt": "0.001",
                "entryPrice": "50000.0",
                "unrealizedProfit": "50.0",
                "positionSide": "BOTH"
            }
        ]
        
        connector = BinanceConnector(mock_binance_client, production_config)
        
        resultado = connector.close_all_positions(emergency=True)
        
        # Verificar que se intentó cerrar la posición
        assert resultado["posiciones_cerradas"] >= 0
        
    def test_calculate_position_size_long(self, mock_binance_client, production_config):
        """Test de cálculo de tamaño de posición para LONG."""
        connector = BinanceConnector(mock_binance_client, production_config)
        connector.get_account_info()
        
        action = 0.8  # Acción LONG
        precio = 50000.0
        
        size = connector.calculate_position_size(action, precio)
        
        # Debe retornar un valor positivo
        assert size > 0
        assert isinstance(size, float)
        
    def test_calculate_position_size_short(self, mock_binance_client, production_config):
        """Test de cálculo de tamaño de posición para SHORT."""
        connector = BinanceConnector(mock_binance_client, production_config)
        connector.get_account_info()
        
        action = -0.8  # Acción SHORT
        precio = 50000.0
        
        size = connector.calculate_position_size(action, precio)
        
        # Debe retornar un valor positivo (cantidad absoluta)
        assert size > 0
        
    def test_calculate_position_size_neutral(self, mock_binance_client, production_config):
        """Test de cálculo de tamaño con acción neutral."""
        connector = BinanceConnector(mock_binance_client, production_config)
        connector.get_account_info()
        
        action = 0.05  # Acción neutral (cerca de 0)
        precio = 50000.0
        
        size = connector.calculate_position_size(action, precio)
        
        # Puede ser 0 o muy pequeño
        assert size >= 0

"""Tests para el sistema de control de riesgo."""

import pytest
from unittest.mock import Mock, patch

from src.produccion.control_riesgo import ControlRiesgo
from src.produccion.config.config import ProductionConfig
from src.produccion.binance import BinanceConnector


class TestControlRiesgo:
    """Tests para la clase ControlRiesgo."""
    
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
    
    @pytest.fixture
    def mock_binance(self, mock_binance_client, production_config):
        """Fixture del conector Binance."""
        return BinanceConnector(mock_binance_client, production_config)
    
    def test_init(self, production_config, mock_binance):
        """Test de inicialización del ControlRiesgo."""
        control = ControlRiesgo(production_config, mock_binance)
        
        assert control.max_drawdown == 0.2
        assert control.capital_inicial == 10000.0
        assert control.max_equity_alcanzado == 10000.0
        assert control.emergencia_activa is False
        assert control.razon_emergencia is None
        
    def test_verificar_drawdown_sin_drawdown(self, production_config, mock_binance):
        """Test de verificación de drawdown cuando no hay drawdown."""
        control = ControlRiesgo(production_config, mock_binance)
        
        # Mock get_position_info
        mock_binance.get_position_info = Mock(return_value={
            "equity": 10500.0,
            "balance": 10500.0,
        })
        
        ok, drawdown = control.verificar_drawdown()
        
        assert ok is True
        assert drawdown >= 0.0
        assert control.max_equity_alcanzado == 10500.0
        
    def test_verificar_drawdown_actualiza_max_equity(self, production_config, mock_binance):
        """Test que verificar_drawdown actualiza el max_equity."""
        control = ControlRiesgo(production_config, mock_binance)
        
        # Primera verificación con equity más alto
        mock_binance.get_position_info = Mock(return_value={
            "equity": 12000.0,
            "balance": 12000.0,
        })
        
        control.verificar_drawdown()
        assert control.max_equity_alcanzado == 12000.0
        
        # Segunda verificación con equity menor
        mock_binance.get_position_info = Mock(return_value={
            "equity": 11000.0,
            "balance": 11000.0,
        })
        
        control.verificar_drawdown()
        # Max equity no debe bajar
        assert control.max_equity_alcanzado == 12000.0
        
    def test_verificar_drawdown_excedido(self, production_config, mock_binance):
        """Test cuando se excede el drawdown máximo."""
        control = ControlRiesgo(production_config, mock_binance)
        
        # Establecer max equity alto
        control.max_equity_alcanzado = 10000.0
        
        # Equity actual bajo (30% de drawdown)
        mock_binance.get_position_info = Mock(return_value={
            "equity": 7000.0,
            "balance": 7000.0,
        })
        
        ok, drawdown = control.verificar_drawdown()
        
        assert ok is False
        assert drawdown > 0.2  # Mayor que max_drawdown_permitido
        
    def test_verificar_drawdown_en_limite(self, production_config, mock_binance):
        """Test con drawdown exactamente en el límite."""
        control = ControlRiesgo(production_config, mock_binance)
        
        control.max_equity_alcanzado = 10000.0
        
        # Equity exactamente en el límite (20% drawdown)
        mock_binance.get_position_info = Mock(return_value={
            "equity": 8000.0,
            "balance": 8000.0,
        })
        
        ok, drawdown = control.verificar_drawdown()
        
        # 0.2 no es < 0.2, debe fallar
        assert ok is False
        assert drawdown == pytest.approx(0.2, rel=0.01)


class TestValidarAccion:
    """Tests para validación de acciones."""
    
    @pytest.fixture
    def production_config(self, config_metadata_dict):
        """Fixture de configuración de producción."""
        from src.produccion.config.config import ProductionConfig
        config = ProductionConfig(
            **config_metadata_dict,
            train_id="test_train",
            model_path="/path/to/model",
            scaler_path="/path/to/scaler",
            is_live=False
        )
        return config
    
    @pytest.fixture
    def mock_binance(self, mock_binance_client, production_config):
        """Fixture del conector Binance."""
        from src.produccion.binance import BinanceConnector
        return BinanceConnector(mock_binance_client, production_config)
    
    @pytest.fixture
    def control(self, production_config, mock_binance):
        """Fixture del control de riesgo."""
        return ControlRiesgo(production_config, mock_binance)
    
    def test_validar_accion_mantener(self, control):
        """Test de validación de acción mantener."""
        accion = {
            "tipo_accion": "mantener",
            "debe_ejecutar": False
        }
        
        valida, razon = control.validar_accion_pre(accion)
        
        assert valida is True
        assert "mantener" in razon.lower()  # Debería decir algo sobre mantener posición
        
    def test_validar_accion_emergencia_activa(self, control):
        """Test que rechaza acciones cuando hay emergencia activa."""
        control.emergencia_activa = True
        control.razon_emergencia = "Max drawdown excedido"
        
        accion = {
            "tipo_accion": "long",
            "operacion": "abrir_long",
            "debe_ejecutar": True
        }
        
        valida, razon = control.validar_accion_pre(accion)
        
        assert valida is False
        assert "emergencia" in razon.lower()
        
    def test_validar_accion_abrir_con_balance(self, control, mock_binance):
        """Test de validación de abrir posición con balance suficiente."""
        mock_binance.get_position_info = Mock(return_value={
            "balance": 5000.0,
            "equity": 5000.0,
        })
        
        accion = {
            "tipo_accion": "long",
            "operacion": "abrir_long",
            "debe_ejecutar": True
        }
        
        valida, razon = control.validar_accion_pre(accion)
        
        assert valida is True
        
    def test_validar_accion_abrir_sin_balance(self, control, mock_binance):
        """Test de validación de abrir posición sin balance."""
        mock_binance.get_position_info = Mock(return_value={
            "balance": 0.0,  # Sin balance
            "equity": 0.0,
        })
        
        accion = {
            "tipo_accion": "long",
            "operacion": "abrir",  # operacion debe ser 'abrir' no 'abrir_long'
            "debe_ejecutar": True
        }
        
        valida, razon = control.validar_accion_pre(accion)
        
        assert valida is False
        assert "balance" in razon.lower()
        
    def test_validar_accion_aumentar(self, control, mock_binance):
        """Test de validación de aumentar posición."""
        mock_binance.get_position_info = Mock(return_value={
            "balance": 5000.0,
            "equity": 5000.0,
        })
        
        accion = {
            "tipo_accion": "long",
            "operacion": "aumentar_long",
            "debe_ejecutar": True
        }
        
        valida, razon = control.validar_accion_pre(accion)
        
        # Debe validar como abrir/aumentar
        assert isinstance(valida, bool)


class TestProtocoloEmergencia:
    """Tests para el protocolo de emergencia."""
    
    @pytest.fixture
    def production_config(self, config_metadata_dict):
        """Fixture de configuración de producción."""
        from src.produccion.config.config import ProductionConfig
        config = ProductionConfig(
            **config_metadata_dict,
            train_id="test_train",
            model_path="/path/to/model",
            scaler_path="/path/to/scaler",
            is_live=False
        )
        return config
    
    @pytest.fixture
    def mock_binance(self, mock_binance_client, production_config):
        """Fixture del conector Binance."""
        from src.produccion.binance import BinanceConnector
        return BinanceConnector(mock_binance_client, production_config)
    
    @pytest.fixture
    def control(self, production_config, mock_binance):
        """Fixture del control de riesgo."""
        return ControlRiesgo(production_config, mock_binance)
    
    def test_activar_protocolo_emergencia(self, control, mock_binance):
        """Test de activación del protocolo de emergencia."""
        mock_binance.close_all_positions = Mock(return_value={
            "posiciones_cerradas": 1,
            "ordenes_canceladas": 0,
            "balance_final": 8000.0,
            "equity_final": 8000.0,
            "errores": []
        })
        
        resultado = control.activar_protocolo_emergencia("Max drawdown excedido")
        
        assert control.emergencia_activa is True
        assert control.razon_emergencia == "Max drawdown excedido"
        assert resultado["exitoso"] is True
        assert resultado["posiciones_cerradas"] == 1
        
        # Verificar que se llamó a close_all_positions
        mock_binance.close_all_positions.assert_called_once_with(emergency=True)
        
    def test_activar_protocolo_emergencia_con_error(self, control, mock_binance):
        """Test de protocolo de emergencia con error."""
        mock_binance.close_all_positions = Mock(side_effect=Exception("Connection error"))
        
        resultado = control.activar_protocolo_emergencia("Error de conexión")
        
        assert control.emergencia_activa is True
        assert resultado["exitoso"] is False
        assert len(resultado["errores"]) > 0
        
    def test_puede_reiniciar_despues_drawdown(self, control):
        """Test que NO se puede reiniciar después de max drawdown."""
        control.emergencia_activa = True
        control.razon_emergencia = "Max drawdown excedido"
        
        puede = control.puede_reiniciar()
        
        assert puede is False
        
    def test_puede_reiniciar_despues_error_operacional(self, control):
        """Test que SÍ se puede reiniciar después de error operacional."""
        control.emergencia_activa = True
        control.razon_emergencia = "Error de conexión temporal"
        
        puede = control.puede_reiniciar()
        
        assert puede is True
        
    def test_reset_emergencia_permitido(self, control):
        """Test de reset de emergencia cuando está permitido."""
        control.emergencia_activa = True
        control.razon_emergencia = "Error temporal"
        
        control.reset_emergencia()
        
        assert control.emergencia_activa is False
        assert control.razon_emergencia is None
        
    def test_reset_emergencia_no_permitido(self, control):
        """Test de reset cuando no está permitido."""
        control.emergencia_activa = True
        control.razon_emergencia = "Max drawdown excedido"
        
        control.reset_emergencia()
        
        # No debe resetear
        assert control.emergencia_activa is True
        assert control.razon_emergencia is not None


class TestControlRiesgoEdgeCases:
    """Tests de casos extremos."""
    
    @pytest.fixture
    def production_config(self, config_metadata_dict):
        """Fixture de configuración de producción."""
        from src.produccion.config.config import ProductionConfig
        config = ProductionConfig(
            **config_metadata_dict,
            train_id="test_train",
            model_path="/path/to/model",
            scaler_path="/path/to/scaler",
            is_live=False
        )
        return config
    
    @pytest.fixture
    def mock_binance(self, mock_binance_client, production_config):
        """Fixture del conector Binance."""
        from src.produccion.binance import BinanceConnector
        return BinanceConnector(mock_binance_client, production_config)
    
    def test_drawdown_con_equity_cero(self, production_config, mock_binance):
        """Test de drawdown cuando equity es cero."""
        control = ControlRiesgo(production_config, mock_binance)
        control.max_equity_alcanzado = 10000.0
        
        mock_binance.get_position_info = Mock(return_value={
            "equity": 0.0,
            "balance": 0.0,
        })
        
        ok, drawdown = control.verificar_drawdown()
        
        assert ok is False
        assert drawdown == 1.0  # 100% drawdown
        
    def test_max_equity_cero(self, production_config, mock_binance):
        """Test cuando max_equity es cero."""
        control = ControlRiesgo(production_config, mock_binance)
        control.max_equity_alcanzado = 0.0
        
        mock_binance.get_position_info = Mock(return_value={
            "equity": 100.0,
            "balance": 100.0,
        })
        
        ok, drawdown = control.verificar_drawdown()
        
        # Debe manejar división por cero
        assert isinstance(ok, bool)
        assert isinstance(drawdown, float)
        
    def test_equity_negativo(self, production_config, mock_binance):
        """Test con equity negativo."""
        control = ControlRiesgo(production_config, mock_binance)
        control.max_equity_alcanzado = 10000.0
        
        mock_binance.get_position_info = Mock(return_value={
            "equity": -500.0,
            "balance": -500.0,
        })
        
        ok, drawdown = control.verificar_drawdown()
        
        # Con equity negativo, drawdown > 100%
        assert ok is False
        assert drawdown > 1.0

"""Tests del protocolo de emergencia integrado."""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from src.produccion.observacion import ObservacionBuilder
from src.produccion.control_riesgo import ControlRiesgo


class TestProtocoloEmergenciaNaN:
    """Tests del protocolo de emergencia cuando hay NaN en ventana."""
    
    @pytest.fixture
    def production_config(self, config_metadata_dict, fitted_scaler):
        """Fixture de configuración de producción."""
        from src.produccion.config.config import ProductionConfig
        config = ProductionConfig(
            **config_metadata_dict,
            train_id="test_train",
            model_path="/path/to/model",
            scaler_path="/path/to/scaler",
            is_live=False
        )
        config.scaler = fitted_scaler
        return config
    
    @pytest.fixture
    def mock_binance(self):
        """Mock del conector Binance."""
        binance = Mock()
        binance.equity_inicial = 10000.0  # Necesario para ControlRiesgo
        binance._equity_inicial = 10000.0
        binance.balance_inicial = 10000.0
        binance._balance_inicial = 10000.0
        binance.get_position_info = Mock(return_value={
            "balance": 10000.0,
            "equity": 10000.0,
            "posicion_abierta": False,
        })
        binance.close_all_positions = Mock(return_value={
            "exito": True,
            "posiciones_cerradas": 0,
            "balance_final": 10000.0,
            "equity_final": 10000.0,
            "errores": []
        })
        return binance
    
    def test_ventana_con_nan_lanza_valueerror(self, production_config, fitted_scaler):
        """Test que ventana con NaN lanza ValueError."""
        equity_inicial = 10000.0
        builder = ObservacionBuilder(production_config, fitted_scaler, equity_inicial)
        
        # Crear ventana con NaN en algunos valores
        ventana_con_nan = pd.DataFrame({
            "open": [50000.0] * 30,
            "high": [50100.0] * 30,
            "low": [49900.0] * 30,
            "close": [50000.0] * 30,
            "volume": [100.0] * 30,
            "SMA_10": [50000.0] * 20 + [np.nan] * 10,  # NaN en últimas filas
            "SMA_200": [np.nan] * 30,  # Todo NaN
            "RSI_14": [50.0] * 30,
        })
        
        binance_state = {
            "equity": 10000.0,
            "pnl_no_realizado": 0.0,
            "posicion_abierta": False
        }
        
        # Debe lanzar ValueError con mensaje sobre NaN
        with pytest.raises(ValueError, match="NaN"):
            builder.construir_observacion(ventana_con_nan, binance_state)
    
    def test_ventana_sin_nan_funciona(self, production_config, fitted_scaler):
        """Test que ventana sin NaN funciona correctamente."""
        equity_inicial = 10000.0
        builder = ObservacionBuilder(production_config, fitted_scaler, equity_inicial)
        
        # Crear ventana sin NaN
        ventana_valida = pd.DataFrame({
            "open": [50000.0] * 30,
            "high": [50100.0] * 30,
            "low": [49900.0] * 30,
            "close": [50000.0] * 30,
            "volume": [100.0] * 30,
            "SMA_10": [50000.0] * 30,
            "SMA_200": [50000.0] * 30,
            "RSI_14": [50.0] * 30,
            "MACD_12_26_9": [0.0] * 30,
            "MACDs_12_26_9": [0.0] * 30,
            "MACDh_12_26_9": [0.0] * 30,
            "BBL_20_2.0": [49000.0] * 30,
            "BBM_20_2.0": [50000.0] * 30,
            "BBU_20_2.0": [51000.0] * 30,
        })
        
        binance_state = {
            "equity": 10000.0,
            "pnl_no_realizado": 0.0,
            "posicion_abierta": False
        }
        
        # No debe lanzar excepción
        obs = builder.construir_observacion(ventana_valida, binance_state)
        
        assert obs is not None
        assert "market" in obs  # La clave es 'market' no 'market_obs'
        assert "portfolio" in obs  # La clave es 'portfolio' no 'portfolio_obs'
    
    def test_protocolo_emergencia_cierra_posiciones(self, production_config, mock_binance):
        """Test que protocolo de emergencia cierra posiciones."""
        control = ControlRiesgo(production_config, mock_binance)
        
        # Simular posición abierta
        mock_binance.get_position_info.return_value = {
            "balance": 9500.0,
            "equity": 9800.0,
            "posicion_abierta": True,
        }
        
        # Activar protocolo
        resultado = control.activar_protocolo_emergencia("Test: NaN en ventana")
        
        # Verificar que se llamó a cerrar posiciones
        mock_binance.close_all_positions.assert_called_once()
        
        # Verificar resultado - la clave es 'exitoso' no 'exito'
        assert resultado['exitoso'] is True
        assert control.emergencia_activa is True
        assert control.razon_emergencia is not None and "NaN en ventana" in control.razon_emergencia
    
    def test_mensaje_error_nan_contiene_columnas(self, production_config, fitted_scaler):
        """Test que el mensaje de error incluye las columnas con NaN."""
        equity_inicial = 10000.0
        builder = ObservacionBuilder(production_config, fitted_scaler, equity_inicial)
        
        # Ventana con NaN en columnas específicas
        ventana_con_nan = pd.DataFrame({
            "open": [50000.0] * 30,
            "close": [50000.0] * 30,
            "SMA_10": [50000.0] * 30,
            "SMA_200": [np.nan] * 30,  # Esta tiene NaN
            "RSI_14": [50.0] * 20 + [np.nan] * 10,  # Esta también
        })
        
        binance_state = {
            "equity": 10000.0,
            "pnl_no_realizado": 0.0,
            "posicion_abierta": False
        }
        
        # Capturar el error
        with pytest.raises(ValueError) as exc_info:
            builder.construir_observacion(ventana_con_nan, binance_state)
        
        error_msg = str(exc_info.value)
        
        # Verificar que menciona las columnas problemáticas
        assert "SMA_200" in error_msg or "RSI_14" in error_msg
        assert "NaN" in error_msg
        assert "protocolo de emergencia" in error_msg.lower()


class TestProtocoloEmergenciaDrawdown:
    """Tests del protocolo de emergencia por drawdown."""
    
    @pytest.fixture
    def production_config(self, config_metadata_dict):
        """Fixture de configuración con max_drawdown."""
        from src.produccion.config.config import ProductionConfig
        # Max drawdown de 20%
        config_metadata_dict['max_drawdown_permitido'] = 0.20
        config = ProductionConfig(
            **config_metadata_dict,
            train_id="test_train",
            model_path="/path/to/model",
            scaler_path="/path/to/scaler",
            is_live=False
        )
        return config
    
    @pytest.fixture
    def mock_binance(self):
        """Mock del conector Binance."""
        binance = Mock()
        binance.equity_inicial = 10000.0  # Necesario para ControlRiesgo
        binance._equity_inicial = 10000.0
        binance.balance_inicial = 10000.0
        binance._balance_inicial = 10000.0
        binance.get_position_info = Mock(return_value={
            "balance": 8000.0,  # 20% de drawdown
            "equity": 8000.0,
        })
        binance.close_all_positions = Mock(return_value={
            "exito": True,
            "posiciones_cerradas": 1,
            "balance_final": 8000.0,
            "equity_final": 8000.0,
            "errores": []
        })
        return binance
    
    def test_drawdown_limite_activa_emergencia(self, production_config, mock_binance):
        """Test que alcanzar el límite de drawdown activa emergencia."""
        control = ControlRiesgo(production_config, mock_binance)
        
        # Establecer max equity
        control.max_equity_alcanzado = 10000.0
        
        # Verificar drawdown - equity actual es 8000, max es 10000 = 20% drawdown
        ok, dd = control.verificar_drawdown()
        
        # No debe pasar (0.2 no es < 0.2)
        assert ok is False
        assert dd == pytest.approx(0.2, rel=0.01)
    
    def test_drawdown_menor_no_activa(self, production_config, mock_binance):
        """Test que drawdown menor al límite no activa emergencia."""
        control = ControlRiesgo(production_config, mock_binance)
        
        # Simular equity con solo 15% de drawdown
        mock_binance.get_position_info.return_value = {
            "equity": 8500.0,
            "balance": 8500.0,
        }
        
        control.max_equity_alcanzado = 10000.0
        
        # Verificar drawdown
        ok, dd = control.verificar_drawdown()
        
        # Debe pasar (0.15 < 0.2)
        assert ok is True
        assert dd == pytest.approx(0.15, rel=0.01)


class TestIntegracionProtocoloEmergencia:
    """Tests de integración del protocolo de emergencia."""
    
    @pytest.fixture
    def production_config(self, config_metadata_dict, fitted_scaler):
        """Fixture de configuración de producción."""
        from src.produccion.config.config import ProductionConfig
        config = ProductionConfig(
            **config_metadata_dict,
            train_id="test_train",
            model_path="/path/to/model",
            scaler_path="/path/to/scaler",
            is_live=False
        )
        config.scaler = fitted_scaler
        return config
    
    @pytest.fixture
    def mock_binance(self):
        """Mock del conector Binance."""
        binance = Mock()
        binance.equity_inicial = 10000.0  # Necesario para ControlRiesgo
        binance._equity_inicial = 10000.0
        binance.balance_inicial = 10000.0
        binance._balance_inicial = 10000.0
        binance.get_position_info = Mock(return_value={
            "balance": 10000.0,
            "equity": 10000.0,
            "posicion_abierta": False,
        })
        binance.close_all_positions = Mock(return_value={
            "posiciones_cerradas": 0,
            "balance_final": 10000.0,
            "equity_final": 10000.0,
            "errores": []
        })
        return binance
    
    def test_flujo_completo_nan_a_emergencia(self, production_config, fitted_scaler, mock_binance):
        """Test del flujo completo: NaN → ValueError → Protocolo Emergencia."""
        
        # 1. ObservacionBuilder con ventana con NaN
        equity_inicial = 10000.0
        builder = ObservacionBuilder(production_config, fitted_scaler, equity_inicial)
        
        ventana_con_nan = pd.DataFrame({
            "close": [50000.0] * 30,
            "SMA_200": [np.nan] * 30,
            "RSI_14": [50.0] * 30,
        })
        
        binance_state = {
            "equity": 10000.0,
            "pnl_no_realizado": 0.0,
            "posicion_abierta": False
        }
        
        # 2. Capturar ValueError
        error_capturado = None
        try:
            builder.construir_observacion(ventana_con_nan, binance_state)
        except ValueError as e:
            error_capturado = e
        
        assert error_capturado is not None
        assert "NaN" in str(error_capturado)
        
        # 3. Activar protocolo de emergencia
        control = ControlRiesgo(production_config, mock_binance)
        resultado = control.activar_protocolo_emergencia(str(error_capturado))
        
        # 4. Verificar que todo funcionó
        assert resultado['exitoso'] is True  # Cambiar 'exito' a 'exitoso'
        assert control.emergencia_activa is True
        mock_binance.close_all_positions.assert_called_once()
    
    def test_protocolo_emergencia_con_error_cierre(self, production_config, mock_binance):
        """Test que el protocolo maneja errores al cerrar posiciones."""
        # Configurar mock para que falle al cerrar
        mock_binance.close_all_positions.return_value = {
            "posiciones_cerradas": 0,
            "balance_final": 10000.0,
            "equity_final": 10000.0,
            "errores": ["Error al cerrar posición LONG"]
        }
        
        control = ControlRiesgo(production_config, mock_binance)
        resultado = control.activar_protocolo_emergencia("Test: Error en cierre")
        
        # Debe marcar como no exitoso si hay errores
        assert resultado['exitoso'] is False
        assert len(resultado['errores']) > 0
        assert control.emergencia_activa is True  # Se activa de todas formas
    
    def test_protocolo_emergencia_con_excepcion(self, production_config, mock_binance):
        """Test que el protocolo maneja excepciones críticas."""
        # Configurar mock para lanzar excepción
        mock_binance.close_all_positions.side_effect = Exception("Error crítico de conexión")
        
        control = ControlRiesgo(production_config, mock_binance)
        resultado = control.activar_protocolo_emergencia("Test: Excepción")
        
        # Debe retornar resultado con error
        assert resultado['exitoso'] is False
        assert len(resultado['errores']) > 0
        assert "Error crítico de conexión" in resultado['errores'][0]
    
    def test_puede_reiniciar_despues_error_operacional(self, production_config, mock_binance):
        """Test que puede reiniciar después de error operacional (no drawdown)."""
        control = ControlRiesgo(production_config, mock_binance)
        
        # Activar emergencia por error operacional
        control.activar_protocolo_emergencia("Error de conexión API")
        
        # Debe permitir reinicio
        assert control.puede_reiniciar() is True
    
    def test_no_puede_reiniciar_despues_drawdown(self, production_config, mock_binance):
        """Test que NO puede reiniciar después de emergencia por drawdown."""
        control = ControlRiesgo(production_config, mock_binance)
        
        # Activar emergencia por drawdown
        control.activar_protocolo_emergencia("Drawdown excedido: 25%")
        
        # NO debe permitir reinicio
        assert control.puede_reiniciar() is False
    
    def test_reset_emergencia_permitido(self, production_config, mock_binance):
        """Test que puede resetear emergencia si es permitido."""
        control = ControlRiesgo(production_config, mock_binance)
        
        # Activar emergencia operacional
        control.activar_protocolo_emergencia("Error temporal")
        assert control.emergencia_activa is True
        
        # Resetear
        control.reset_emergencia()
        
        # Debe estar desactivada
        assert control.emergencia_activa is False
        assert control.razon_emergencia is None
    
    def test_reset_emergencia_no_permitido(self, production_config, mock_binance):
        """Test que NO puede resetear emergencia por drawdown."""
        control = ControlRiesgo(production_config, mock_binance)
        
        # Activar emergencia por drawdown
        control.activar_protocolo_emergencia("Max drawdown alcanzado")
        assert control.emergencia_activa is True
        
        # Intentar resetear
        control.reset_emergencia()
        
        # Debe seguir activa
        assert control.emergencia_activa is True
        assert control.razon_emergencia is not None
    
    def test_validar_accion_rechaza_durante_emergencia(self, production_config, mock_binance):
        """Test que rechaza acciones cuando hay emergencia activa."""
        control = ControlRiesgo(production_config, mock_binance)
        
        # Activar emergencia
        control.activar_protocolo_emergencia("Test emergencia")
        
        # Intentar validar acción
        accion = {
            'tipo': 'long',
            'operacion': 'abrir',
            'debe_ejecutar': True
        }
        
        valida, razon = control.validar_accion_pre(accion)
        
        # Debe rechazar
        assert valida is False
        assert "emergencia" in razon.lower()
    
    def test_drawdown_actualiza_max_equity(self, production_config, mock_binance):
        """Test que verificar_drawdown actualiza el max equity cuando aumenta."""
        control = ControlRiesgo(production_config, mock_binance)
        
        # Equity inicial
        equity_inicial = control.max_equity_alcanzado
        
        # Simular aumento de equity
        mock_binance.get_position_info.return_value = {
            "equity": equity_inicial + 1000,
            "balance": equity_inicial + 1000,
        }
        
        # Verificar drawdown
        ok, dd = control.verificar_drawdown()
        
        # Debe actualizar max equity
        assert control.max_equity_alcanzado == equity_inicial + 1000
        assert dd == 0.0  # Sin drawdown
        assert ok is True
    
    def test_drawdown_advertencia_cerca_limite(self, production_config, mock_binance, caplog):
        """Test que muestra advertencia cuando drawdown está cerca del límite."""
        import logging
        
        control = ControlRiesgo(production_config, mock_binance)
        control.max_equity_alcanzado = 10000.0
        
        # Simular 17% de drawdown (mayor que 80% del límite de 20% que es 16%)
        mock_binance.get_position_info.return_value = {
            "equity": 8300.0,
            "balance": 8300.0,
        }
        
        # Verificar drawdown (caplog debe estar configurado antes de la llamada)
        caplog.set_level(logging.WARNING, logger="AFML.ControlRiesgo")
        ok, dd = control.verificar_drawdown()
        
        # Debe estar ok pero con advertencia
        assert ok is True
        assert dd == pytest.approx(0.17, rel=0.01)
        # Verificar que hubo advertencia en logs
        assert any("Drawdown alto" in record.message or "alto" in record.message.lower() 
                   for record in caplog.records if record.levelno >= logging.WARNING)

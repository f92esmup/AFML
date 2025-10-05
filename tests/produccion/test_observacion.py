"""Tests para el constructor de observaciones."""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock

from src.produccion.observacion import ObservacionBuilder
from src.produccion.config.config import ProductionConfig


class TestObservacionBuilder:
    """Tests para la clase ObservacionBuilder."""
    
    @pytest.fixture
    def production_config(self, config_metadata_dict, fitted_scaler):
        """Fixture de configuración de producción."""
        config = ProductionConfig(
            **config_metadata_dict,
            train_id="test_train",
            model_path="/path/to/model",
            scaler_path="/path/to/scaler",
            is_live=False
        )
        config.scaler = fitted_scaler
        return config
    
    def test_init(self, production_config, fitted_scaler):
        """Test de inicialización del ObservacionBuilder."""
        equity_inicial = 10000.0
        builder = ObservacionBuilder(production_config, fitted_scaler, equity_inicial)
        
        assert builder.window_size == 30
        assert builder.normalizar_portfolio is True
        assert builder.scaler is not None
        # Escalas dinámicas basadas en equity_inicial REAL
        assert builder.equity_scale == 10000.0
        assert builder.pnl_scale == 1000.0  # 10% del equity
    
    def test_init_equity_inicial_invalido(self, production_config, fitted_scaler):
        """Test que rechaza equity_inicial inválido."""
        with pytest.raises(ValueError, match="equity_inicial inválido"):
            ObservacionBuilder(production_config, fitted_scaler, equity_inicial=0.0)
        
        with pytest.raises(ValueError, match="equity_inicial inválido"):
            ObservacionBuilder(production_config, fitted_scaler, equity_inicial=-100.0)
        
    def test_construir_observacion_success(self, production_config, fitted_scaler, sample_market_data, binance_state_dict):
        """Test de construcción exitosa de observación."""
        equity_inicial = 10000.0
        builder = ObservacionBuilder(production_config, fitted_scaler, equity_inicial)
        
        observacion = builder.construir_observacion(sample_market_data, binance_state_dict)
        
        # Verificar estructura
        assert "market" in observacion
        assert "portfolio" in observacion
        
        # Verificar tipos
        assert isinstance(observacion["market"], np.ndarray)
        assert isinstance(observacion["portfolio"], np.ndarray)
        
        # Verificar shapes
        assert observacion["market"].shape == (30, 14)  # window_size x num_features
        assert observacion["portfolio"].shape == (3,)  # equity, pnl, posicion
        
        # Verificar dtype
        assert observacion["market"].dtype == np.float32
        assert observacion["portfolio"].dtype == np.float32
        
    def test_construir_observacion_ventana_insuficiente(self, production_config, fitted_scaler, binance_state_dict):
        """Test de error con ventana insuficiente."""
        equity_inicial = 10000.0
        builder = ObservacionBuilder(production_config, fitted_scaler, equity_inicial)
        
        # DataFrame con menos filas que window_size
        df_corto = pd.DataFrame({
            "close": [100] * 10,
        })
        
        with pytest.raises(ValueError, match="Ventana insuficiente"):
            builder.construir_observacion(df_corto, binance_state_dict)
            
    def test_construir_observacion_normaliza_market(self, production_config, fitted_scaler, sample_market_data, binance_state_dict):
        """Test que los datos de mercado se normalizan con el scaler."""
        equity_inicial = 10000.0
        builder = ObservacionBuilder(production_config, fitted_scaler, equity_inicial)
        
        observacion = builder.construir_observacion(sample_market_data, binance_state_dict)
        
        # Los valores normalizados deben ser diferentes de los originales
        ventana_reciente = sample_market_data.tail(30).values
        assert not np.array_equal(observacion["market"], ventana_reciente)
        
        # Los valores normalizados deben tener media ~0 y std ~1
        # (puede no ser exacto debido al tamaño de la muestra)
        market_mean = observacion["market"].mean()
        market_std = observacion["market"].std()
        assert -2 < market_mean < 2  # Aproximadamente centrado
        assert 0.5 < market_std < 2.0  # Aproximadamente escala estándar
        
    def test_construir_observacion_normaliza_portfolio(self, production_config, fitted_scaler, sample_market_data, binance_state_dict):
        """Test que el portfolio se normaliza cuando está configurado."""
        equity_inicial = 10000.0
        builder = ObservacionBuilder(production_config, fitted_scaler, equity_inicial)
        
        observacion = builder.construir_observacion(sample_market_data, binance_state_dict)
        
        # Verificar normalización de equity
        equity_norm = observacion["portfolio"][0]
        expected_equity_norm = binance_state_dict["equity"] / equity_inicial
        assert equity_norm == pytest.approx(expected_equity_norm, rel=0.01)
        
        # Verificar normalización de PnL (10% del equity_inicial)
        pnl_norm = observacion["portfolio"][1]
        expected_pnl_norm = binance_state_dict["pnl_no_realizado"] / (equity_inicial * 0.1)
        assert pnl_norm == pytest.approx(expected_pnl_norm, rel=0.01)
        
        # Verificar posición abierta (0 o 1, no normalizada)
        posicion = observacion["portfolio"][2]
        assert posicion in [0.0, 1.0]
        
    def test_construir_observacion_sin_normalizar_portfolio(self, config_metadata_dict, fitted_scaler, sample_market_data, binance_state_dict):
        """Test de construcción sin normalizar portfolio."""
        # Crear config con normalizar_portfolio=False
        config = ProductionConfig(
            **{**config_metadata_dict, "normalizar_portfolio": False},
            train_id="test_train",
            model_path="/path/to/model",
            scaler_path="/path/to/scaler",
            is_live=False
        )
        config.scaler = fitted_scaler
        
        equity_inicial = 10000.0
        builder = ObservacionBuilder(config, fitted_scaler, equity_inicial)
        
        observacion = builder.construir_observacion(sample_market_data, binance_state_dict)
        
        # Los valores deben ser los originales
        assert observacion["portfolio"][0] == binance_state_dict["equity"]
        assert observacion["portfolio"][1] == binance_state_dict["pnl_no_realizado"]
        
    def test_construir_observacion_posicion_abierta_true(self, production_config, fitted_scaler, sample_market_data):
        """Test con posición abierta."""
        equity_inicial = 10000.0
        builder = ObservacionBuilder(production_config, fitted_scaler, equity_inicial)
        
        binance_state = {
            "equity": 10500.0,
            "pnl_no_realizado": 100.0,
            "posicion_abierta": True,
        }
        
        observacion = builder.construir_observacion(sample_market_data, binance_state)
        
        # Posición debe ser 1.0
        assert observacion["portfolio"][2] == 1.0
        
    def test_construir_observacion_posicion_abierta_false(self, production_config, fitted_scaler, sample_market_data):
        """Test con posición cerrada."""
        equity_inicial = 10000.0
        builder = ObservacionBuilder(production_config, fitted_scaler, equity_inicial)
        
        binance_state = {
            "equity": 10500.0,
            "pnl_no_realizado": 0.0,
            "posicion_abierta": False,
        }
        
        observacion = builder.construir_observacion(sample_market_data, binance_state)
        
        # Posición debe ser 0.0
        assert observacion["portfolio"][2] == 0.0
        
    def test_construir_observacion_elimina_timestamp(self, production_config, fitted_scaler, sample_market_data, binance_state_dict):
        """Test que se elimina la columna timestamp si existe."""
        equity_inicial = 10000.0
        builder = ObservacionBuilder(production_config, fitted_scaler, equity_inicial)
        
        # Agregar columna timestamp
        df_with_timestamp = sample_market_data.reset_index()
        df_with_timestamp.rename(columns={"index": "timestamp"}, inplace=True)
        
        observacion = builder.construir_observacion(df_with_timestamp, binance_state_dict)
        
        # La observación debe crearse correctamente sin incluir timestamp
        assert observacion["market"].shape == (30, 14)
        
    def test_construir_observacion_valores_por_defecto(self, production_config, fitted_scaler, sample_market_data):
        """Test con valores por defecto en binance_state."""
        equity_inicial = 10000.0
        builder = ObservacionBuilder(production_config, fitted_scaler, equity_inicial)
        
        # Estado incompleto
        binance_state = {}
        
        observacion = builder.construir_observacion(sample_market_data, binance_state)
        
        # Debe manejar valores faltantes con defaults (0.0)
        assert observacion["portfolio"][0] == 0.0  # equity
        assert observacion["portfolio"][1] == 0.0  # pnl
        assert observacion["portfolio"][2] == 0.0  # posicion_abierta
        

class TestObservacionBuilderEdgeCases:
    """Tests de casos extremos."""
    
    @pytest.fixture
    def production_config(self, config_metadata_dict, fitted_scaler):
        """Fixture de configuración de producción."""
        config = ProductionConfig(
            **config_metadata_dict,
            train_id="test_train",
            model_path="/path/to/model",
            scaler_path="/path/to/scaler",
            is_live=False
        )
        config.scaler = fitted_scaler
        return config
    
    def test_equity_negativo(self, production_config, fitted_scaler, sample_market_data):
        """Test con equity negativo."""
        equity_inicial = 10000.0
        builder = ObservacionBuilder(production_config, fitted_scaler, equity_inicial)
        
        binance_state = {
            "equity": -500.0,  # Equity negativo
            "pnl_no_realizado": -1000.0,
            "posicion_abierta": True,
        }
        
        observacion = builder.construir_observacion(sample_market_data, binance_state)
        
        # Debe procesar valores negativos correctamente
        assert observacion["portfolio"][0] < 0
        assert observacion["portfolio"][1] < 0
        
    def test_pnl_muy_grande(self, production_config, fitted_scaler, sample_market_data):
        """Test con PnL muy grande."""
        equity_inicial = 10000.0
        builder = ObservacionBuilder(production_config, fitted_scaler, equity_inicial)
        
        binance_state = {
            "equity": 50000.0,
            "pnl_no_realizado": 40000.0,  # PnL muy grande
            "posicion_abierta": True,
        }
        
        observacion = builder.construir_observacion(sample_market_data, binance_state)
        
        # Debe normalizar correctamente incluso con valores grandes
        assert observacion["portfolio"][0] > 0
        assert observacion["portfolio"][1] > 0
        
    def test_ventana_exactamente_window_size(self, production_config, fitted_scaler, binance_state_dict):
        """Test con ventana del tamaño exacto."""
        equity_inicial = 10000.0
        builder = ObservacionBuilder(production_config, fitted_scaler, equity_inicial)
        
        # DataFrame con exactamente window_size filas
        df_exact = pd.DataFrame(
            np.random.randn(30, 14),
            columns=[f"feature_{i}" for i in range(14)]
        )
        
        observacion = builder.construir_observacion(df_exact, binance_state_dict)
        
        # Debe usar todas las filas
        assert observacion["market"].shape == (30, 14)

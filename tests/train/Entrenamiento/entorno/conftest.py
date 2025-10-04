"""Fixtures compartidas para los tests del entorno de entrenamiento."""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any
from sklearn.preprocessing import StandardScaler

from src.train.config.config import UnifiedConfig
from src.train.Entrenamiento.entorno.portafolio import Portafolio
from src.train.Entrenamiento.entorno.entorno import TradingEnv


@pytest.fixture
def valid_config_dict() -> Dict[str, Any]:
    """Retorna un diccionario con configuración válida para tests."""
    return {
        "data_downloader": {
            "symbol": "BTCUSDT",
            "interval": "1h",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "limit": 1000
        },
        "preprocesamiento": {
            "interpol_method": "linear",
            "indicadores": {
                "SMA_short": 10,
                "SMA_long": 50,
                "RSI_length": 14,
                "MACD_fast": 12,
                "MACD_slow": 26,
                "MACD_signal": 9,
                "BB_length": 20,
                "BB_std": 2.0
            }
        },
        "portafolio": {
            "capital_inicial": 10000.0,
            "apalancamiento": 1.0,
            "comision": 0.001,
            "slippage": 0.0005
        },
        "entorno": {
            "window_size": 30,
            "max_drawdown_permitido": 0.2,
            "factor_aversion_riesgo": 2.0,
            "umbral_mantener_posicion": 0.1,
            "penalizacion_no_operar": 0.0001,
            "episodios": 10,
            "normalizar_portfolio": True,
            "normalizar_recompensa": True,
            "penalizacion_pct": 0.00001
        },
        "SACmodel": {
            "policy": "MlpPolicy",
            "learning_rate": 0.0003,
            "buffer_size": 100000,
            "learning_starts": 100,
            "batch_size": 64,
            "tau": 0.005,
            "gamma": 0.99,
            "ent_coef": "auto",
            "train_freq": (1, "step"),
            "gradient_steps": 1,
            "verbose": 1,
            "seed": 42
        },
        "policy_kwargs": {
            "net_arch": {
                "pi": [256, 256],
                "qf": [256, 256]
            },
            "log_std_init": -3.0,
            "n_critics": 2
        },
        "Output": {
            "base_dir": "entrenamientos/test",
            "model_path": "entrenamientos/test/model.zip",
            "tensorboard_log": "entrenamientos/test/tensorboard",
            "scaler_train_path": "entrenamientos/test/scaler_train.pkl",
            "scaler_eval_path": "entrenamientos/test/scaler_eval.pkl",
            "metadata_filename": "config_metadata.yaml"
        }
    }


@pytest.fixture
def config(valid_config_dict) -> UnifiedConfig:
    """Retorna una instancia de UnifiedConfig válida."""
    return UnifiedConfig(**valid_config_dict)


@pytest.fixture
def sample_data() -> pd.DataFrame:
    """Genera un DataFrame de muestra con datos de mercado sintéticos."""
    n_rows = 100
    base_price = 50000.0
    
    # Generar timestamps
    start_date = datetime(2023, 1, 1)
    timestamps = [start_date + timedelta(hours=i) for i in range(n_rows)]
    
    # Generar datos de precio con algo de volatilidad
    np.random.seed(42)
    prices = base_price + np.cumsum(np.random.randn(n_rows) * 100)
    
    # Crear DataFrame con columnas típicas de trading
    data = pd.DataFrame({
        'timestamp': timestamps,
        'open': prices + np.random.randn(n_rows) * 50,
        'high': prices + np.abs(np.random.randn(n_rows) * 100),
        'low': prices - np.abs(np.random.randn(n_rows) * 100),
        'close': prices,
        'volume': np.random.randint(100, 1000, n_rows),
        'SMA_short': prices + np.random.randn(n_rows) * 20,
        'SMA_long': prices + np.random.randn(n_rows) * 30,
        'RSI': np.random.uniform(20, 80, n_rows),
        'MACD': np.random.randn(n_rows) * 10,
        'MACD_signal': np.random.randn(n_rows) * 10,
        'BB_upper': prices + np.random.randn(n_rows) * 150,
        'BB_lower': prices - np.random.randn(n_rows) * 150,
    })
    
    return data


@pytest.fixture
def sample_data_normalized(sample_data) -> tuple[pd.DataFrame, StandardScaler]:
    """Genera datos normalizados y retorna el DataFrame y el scaler."""
    scaler = StandardScaler()
    
    # Separar columnas numéricas (excluir timestamp)
    numeric_columns = [col for col in sample_data.columns if col != 'timestamp']
    
    # Ajustar y transformar
    data_normalized = sample_data.copy()
    data_normalized[numeric_columns] = scaler.fit_transform(sample_data[numeric_columns])
    
    return data_normalized, scaler


@pytest.fixture
def portafolio(config) -> Portafolio:
    """Retorna una instancia de Portafolio inicializada."""
    return Portafolio(config)


@pytest.fixture
def trading_env(config, sample_data, portafolio) -> TradingEnv:
    """Retorna una instancia de TradingEnv sin normalización."""
    return TradingEnv(config, sample_data, portafolio, scaler=None)


@pytest.fixture
def trading_env_normalized(config, sample_data_normalized, portafolio) -> TradingEnv:
    """Retorna una instancia de TradingEnv con normalización."""
    data, scaler = sample_data_normalized
    return TradingEnv(config, data, portafolio, scaler=scaler)


@pytest.fixture
def small_sample_data() -> pd.DataFrame:
    """Genera un DataFrame pequeño para tests específicos."""
    return pd.DataFrame({
        'timestamp': pd.date_range('2023-01-01', periods=50, freq='H'),
        'open': np.random.randn(50) * 100 + 50000,
        'high': np.random.randn(50) * 100 + 50100,
        'low': np.random.randn(50) * 100 + 49900,
        'close': np.random.randn(50) * 100 + 50000,
        'volume': np.random.randint(100, 1000, 50),
    })

"""Fixtures compartidas para los tests de adquisición de datos."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from typing import Dict, Any

from src.train.config.config import UnifiedConfig


@pytest.fixture
def mock_binance_client():
    """Mock del cliente de Binance."""
    client = MagicMock()
    
    # Configurar el comportamiento del mock para futures_historical_klines
    def mock_klines(symbol, interval, start_str, end_str, limit):
        """Simula la respuesta de Binance con datos de velas."""
        start_ms = int(start_str)
        end_ms = int(end_str)
        interval_ms = 3600000  # 1 hora en milisegundos
        
        klines = []
        current_ms = start_ms
        
        while current_ms < end_ms and len(klines) < limit:
            kline = [
                current_ms,  # timestamp
                "50000.0",   # open
                "50100.0",   # high
                "49900.0",   # low
                "50050.0",   # close
                "100.5",     # volume
                current_ms + interval_ms - 1,  # close_time
                "5002500.0",  # quote_asset_volume
                1000,        # number_of_trades
                "50.25",     # taker_buy_base_asset_volume
                "2501250.0", # taker_buy_quote_asset_volume
                "0"          # ignore
            ]
            klines.append(kline)
            current_ms += interval_ms
        
        return klines
    
    client.futures_historical_klines.side_effect = mock_klines
    return client


@pytest.fixture
def sample_config():
    """Configuración de ejemplo para tests."""
    config_dict = {
        "data_downloader": {
            "symbol": "BTCUSDT",
            "interval": "1h",
            "start_date": "2023-01-01",
            "end_date": "2023-01-02",
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
            "learning_starts": 1000,
            "batch_size": 256,
            "tau": 0.005,
            "gamma": 0.99,
            "ent_coef": "auto",
            "train_freq": (1, "episode"),
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
        }
    }
    return UnifiedConfig(**config_dict)


@pytest.fixture
def sample_ohlcv_dataframe():
    """DataFrame de ejemplo con datos OHLCV."""
    dates = pd.date_range(start='2023-01-01', periods=100, freq='1h')
    
    # Generar datos sintéticos más realistas
    np.random.seed(42)
    close_prices = 50000 + np.cumsum(np.random.randn(100) * 100)
    
    df = pd.DataFrame({
        'open': close_prices + np.random.randn(100) * 50,
        'high': close_prices + np.abs(np.random.randn(100) * 100),
        'low': close_prices - np.abs(np.random.randn(100) * 100),
        'close': close_prices,
        'volume': np.random.uniform(50, 200, 100)
    }, index=dates)
    
    return df


@pytest.fixture
def sample_ohlcv_with_gaps():
    """DataFrame con gaps en el índice temporal."""
    dates = pd.date_range(start='2023-01-01', periods=100, freq='1h')
    # Eliminar algunas fechas para crear gaps
    dates_with_gaps = dates.delete([10, 11, 12, 30, 31, 50])
    
    np.random.seed(42)
    close_prices = 50000 + np.cumsum(np.random.randn(len(dates_with_gaps)) * 100)
    
    df = pd.DataFrame({
        'open': close_prices + np.random.randn(len(dates_with_gaps)) * 50,
        'high': close_prices + np.abs(np.random.randn(len(dates_with_gaps)) * 100),
        'low': close_prices - np.abs(np.random.randn(len(dates_with_gaps)) * 100),
        'close': close_prices,
        'volume': np.random.uniform(50, 200, len(dates_with_gaps))
    }, index=dates_with_gaps)
    
    return df


@pytest.fixture
def sample_ohlcv_with_nans():
    """DataFrame con valores NaN."""
    dates = pd.date_range(start='2023-01-01', periods=100, freq='1h')
    
    np.random.seed(42)
    close_prices = 50000 + np.cumsum(np.random.randn(100) * 100)
    
    df = pd.DataFrame({
        'open': close_prices + np.random.randn(100) * 50,
        'high': close_prices + np.abs(np.random.randn(100) * 100),
        'low': close_prices - np.abs(np.random.randn(100) * 100),
        'close': close_prices,
        'volume': np.random.uniform(50, 200, 100)
    }, index=dates)
    
    # Insertar algunos NaN
    df.loc[df.index[5:8], 'close'] = np.nan
    df.loc[df.index[20], 'volume'] = np.nan
    
    return df

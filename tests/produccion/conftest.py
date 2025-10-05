"""Fixtures compartidas para los tests de producción."""

import pytest
import tempfile
import yaml
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, MagicMock
from sklearn.preprocessing import StandardScaler
from binance.client import Client
from binance import AsyncClient


@pytest.fixture
def config_metadata_dict() -> Dict[str, Any]:
    """Retorna un diccionario con configuración de metadata válida."""
    return {
        "apalancamiento": 2.0,
        "intervalo": "1h",
        "simbolo": "BTCUSDT",
        # NOTA: capital_inicial NO se incluye porque debe obtenerse de Binance API
        "comision": 0.001,
        "slippage": 0.0005,
        "window_size": 30,
        "max_drawdown_permitido": 0.2,
        "umbral_mantener_posicion": 0.1,
        "normalizar_portfolio": True,
        "sma_short": 10,
        "sma_long": 200,
        "rsi_length": 14,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "bbands_length": 20,
        "bbands_std": 2.0,
        "portafolio": {  # Campo requerido por ProductionConfig
            "equity": 10000.0,
            "balance": 10000.0,
            "posicion_activa": False
        }
    }


@pytest.fixture
def temp_training_dir(tmp_path):
    """Crea un directorio temporal de entrenamiento con configuración válida."""
    train_id = "test_train_20230101_120000"
    train_dir = tmp_path / "entrenamientos" / train_id
    train_dir.mkdir(parents=True, exist_ok=True)
    
    # Crear config_metadata.yaml con estructura correcta esperada por ProductionConfig
    config_metadata = {
        "portafolio": {
            "apalancamiento": 2.0,
            "capital_inicial": 10000.0,
            "comision": 0.001,
            "slippage": 0.0005,
        },
        "data_downloader": {
            "symbol": "BTCUSDT",
            "interval": "1h",
        },
        "Output": {
            "model_path": str(train_dir / "modelos" / "modelo.zip"),
            "scaler_train_path": str(train_dir / "scaler_train.pkl"),
        },
        "entorno": {
            "window_size": 30,
            "max_drawdown_permitido": 0.2,
            "umbral_mantener_posicion": 0.1,
            "normalizar_portfolio": True,
        },
        "preprocesamiento": {
            "indicadores": {
                "SMA_short": 10,
                "SMA_long": 200,
                "RSI_length": 14,
                "MACD_fast": 12,
                "MACD_slow": 26,
                "MACD_signal": 9,
                "BB_length": 20,
                "BB_std": 2.0,
            }
        }
    }
    
    config_path = train_dir / "config_metadata.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config_metadata, f)
    
    # Crear scaler dummy
    scaler = StandardScaler()
    # Fit con datos dummy (14 features como en producción)
    dummy_data = np.random.randn(100, 14)
    scaler.fit(dummy_data)
    
    scaler_path = train_dir / "scaler_train.pkl"
    with open(scaler_path, "wb") as f:
        pickle.dump(scaler, f)
    
    # Crear directorio de modelos
    modelos_dir = train_dir / "modelos"
    modelos_dir.mkdir(exist_ok=True)
    
    # Crear directorio de producción
    prod_dir = train_dir / "produccion"
    prod_dir.mkdir(exist_ok=True)
    
    return {
        "train_id": train_id,
        "train_dir": str(train_dir),
        "config_path": str(config_path),
        "scaler_path": str(scaler_path),
        "model_path": str(modelos_dir / "modelo.zip"),
        "base_path": str(tmp_path),
    }



@pytest.fixture
def mock_binance_client():
    """Mock del cliente de Binance."""
    client = Mock(spec=Client)
    
    # Mock futures_change_leverage
    client.futures_change_leverage.return_value = {
        "leverage": 2,
        "symbol": "BTCUSDT"
    }
    
    # Mock futures_account
    client.futures_account.return_value = {
        "totalWalletBalance": "10000.0",
        "totalUnrealizedProfit": "0.0",
        "totalMarginBalance": "10000.0",  # Campo requerido por binance.py
        "assets": [
            {
                "asset": "USDT",
                "walletBalance": "10000.0",
                "unrealizedProfit": "0.0",
                "marginBalance": "10000.0",
                "availableBalance": "10000.0"
            }
        ],
        "positions": []
    }
    
    # Mock futures_position_information
    client.futures_position_information.return_value = []
    
    # Mock futures_create_order
    client.futures_create_order.return_value = {
        "orderId": 12345,
        "symbol": "BTCUSDT",
        "status": "FILLED",
        "executedQty": "0.001",
        "avgPrice": "50000.0"
    }
    
    # Mock futures_get_all_orders
    client.futures_get_all_orders.return_value = []
    
    # Mock futures_cancel_all_open_orders
    client.futures_cancel_all_open_orders.return_value = {"msg": "success"}
    
    return client


@pytest.fixture
def mock_binance_connector(mock_binance_client, config_metadata_dict):
    """Mock del BinanceConnector ya inicializado con valores reales."""
    from src.produccion.binance import BinanceConnector
    from src.produccion.config.config import ProductionConfig
    
    # Crear config mínima
    config = ProductionConfig(
        **config_metadata_dict,
        train_id="test_train",
        model_path="/path/to/model",
        scaler_path="/path/to/scaler",
        is_live=False
    )
    
    # Crear connector
    connector = BinanceConnector(mock_binance_client, config)
    
    # Simular initialize_account
    connector._equity_inicial = 10000.0
    connector._balance_inicial = 10000.0
    connector._equity = 10000.0
    connector._balance = 10000.0
    connector._max_equity = 10000.0
    
    return connector


@pytest.fixture
def mock_async_client():
    """Mock del cliente asíncrono de Binance."""
    client = AsyncMock(spec=AsyncClient)
    
    # Mock futures_klines
    klines_data = []
    for i in range(100):
        klines_data.append([
            1609459200000 + i * 3600000,  # timestamp
            "50000.0",  # open
            "50100.0",  # high
            "49900.0",  # low
            "50050.0",  # close
            "100.5",    # volume
            1609462799999,  # close_time
            "5025000.0",    # quote_volume
            1000,           # trades
            "50.0",         # taker_buy_base
            "2500000.0",    # taker_buy_quote
            "0"             # ignore
        ])
    
    client.futures_klines.return_value = klines_data
    
    # Mock close
    client.close = AsyncMock()
    
    return client


@pytest.fixture
def sample_market_data():
    """Datos de mercado de ejemplo con indicadores."""
    dates = pd.date_range(start="2023-01-01", periods=100, freq="1h", name="timestamp")
    
    df = pd.DataFrame({
        "open": np.random.uniform(49000, 51000, 100),
        "high": np.random.uniform(50000, 52000, 100),
        "low": np.random.uniform(48000, 50000, 100),
        "close": np.random.uniform(49500, 50500, 100),
        "volume": np.random.uniform(100, 200, 100),
        "SMA_short": np.random.uniform(49000, 51000, 100),
        "SMA_long": np.random.uniform(49000, 51000, 100),
        "RSI": np.random.uniform(30, 70, 100),
        "MACD": np.random.uniform(-100, 100, 100),
        "MACD_signal": np.random.uniform(-100, 100, 100),
        "MACD_hist": np.random.uniform(-50, 50, 100),
        "BB_upper": np.random.uniform(51000, 52000, 100),
        "BB_middle": np.random.uniform(49500, 50500, 100),
        "BB_lower": np.random.uniform(48000, 49000, 100),
    }, index=dates)
    
    return df


@pytest.fixture
def fitted_scaler(sample_market_data):
    """Scaler ya ajustado con datos de mercado."""
    scaler = StandardScaler()
    scaler.fit(sample_market_data.values)
    return scaler


@pytest.fixture
def mock_sac_model():
    """Mock del modelo SAC."""
    model = Mock()
    
    # Mock predict method
    def predict_side_effect(obs, deterministic=True):
        # Retornar acción aleatoria entre -1 y 1
        action = np.array([np.random.uniform(-1, 1)])
        return action, None
    
    model.predict = Mock(side_effect=predict_side_effect)
    
    return model


@pytest.fixture
def binance_state_dict():
    """Estado del portfolio de Binance."""
    return {
        "balance": 10000.0,
        "equity": 10500.0,
        "max_drawdown": 0.05,
        "pnl_total": 500.0,
        "posicion_abierta": False,
        "tipo_posicion_activa": None,
        "precio_entrada_activa": None,
        "cantidad_activa": None,
        "pnl_no_realizado": 0.0,
    }


@pytest.fixture
def vela_dict():
    """Datos de una vela completa."""
    return {
        "timestamp": pd.Timestamp("2023-01-01 12:00:00"),
        "open": 50000.0,
        "high": 50100.0,
        "low": 49900.0,
        "close": 50050.0,
        "volume": 100.5,
        "is_closed": True,
    }
